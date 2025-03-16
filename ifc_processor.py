import ifcopenshell
import csv
import logging
from io import StringIO
from decimal import Decimal
import json
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class IFCProcessor:
    def __init__(self, file_path):
        self.ifc_file = None
        if file_path:
            try:
                # パスの正規化
                file_path = os.path.abspath(file_path)
                self.ifc_file = ifcopenshell.open(file_path)
                logger.info(f"Successfully opened IFC file: {file_path}")
            except Exception as e:
                logger.error(f"Error opening IFC file: {str(e)}")
                raise ValueError(f"IFCファイルを開けませんでした: {str(e)}")

    def extract_material_sizes(self):
        """IFCファイルから材料情報を抽出"""
        if not self.ifc_file:
            raise ValueError("IFCファイルが読み込まれていません。")

        materials = []
        try:
            # 構造要素の取得
            structural_items = self.ifc_file.by_type('IfcStructuralItem') or []
            beams = self.ifc_file.by_type('IfcBeam') or []
            columns = self.ifc_file.by_type('IfcColumn') or []
            plates = self.ifc_file.by_type('IfcPlate') or []
            members = self.ifc_file.by_type('IfcMember') or []
            fasteners = self.ifc_file.by_type('IfcFastener') or []

            # 全ての要素を処理
            all_elements = structural_items + beams + columns + plates + members + fasteners
            logger.info(f"Found total {len(all_elements)} elements to process")

            for element in all_elements:
                try:
                    material_info = self._process_element(element)
                    if material_info:
                        materials.append(material_info)
                        logger.debug(f"Successfully processed element: {element.GlobalId}")
                except Exception as elem_error:
                    logger.warning(f"Error processing element {element.id()}: {str(elem_error)}")
                    continue

            logger.info(f"Successfully processed {len(materials)} materials")
            return materials

        except Exception as e:
            logger.error(f"Error extracting materials: {str(e)}", exc_info=True)
            raise ValueError(f"材料データの抽出中にエラーが発生しました: {str(e)}")

    def _process_element(self, element):
        """個別の要素を処理"""
        try:
            # 基本情報の取得
            material_info = {
                'name': element.Name if hasattr(element, 'Name') else None,
                'element_type': element.is_a(),
                'global_id': element.GlobalId if hasattr(element, 'GlobalId') else None
            }

            # 材料情報の取得
            material_props = self._get_material_properties(element)
            if material_props:
                material_info.update(material_props)

            # プロファイル情報の取得
            profile_props = self._get_profile_properties(element)
            if profile_props:
                material_info.update(profile_props)

            # 要素固有のプロパティを取得
            element_props = self._get_element_properties(element)
            if element_props:
                material_info.update(element_props)

            # 数値データの型変換と不正な値の除去
            cleaned_info = {}
            for key, value in material_info.items():
                try:
                    if isinstance(value, (int, float, Decimal)):
                        cleaned_info[key] = float(value)
                    elif isinstance(value, str):
                        cleaned_info[key] = value.strip()
                    elif value is None:
                        cleaned_info[key] = None
                    else:
                        cleaned_info[key] = str(value)
                except Exception as conv_error:
                    logger.warning(f"Error converting value for key {key}: {str(conv_error)}")
                    cleaned_info[key] = str(value)

            return cleaned_info

        except Exception as e:
            logger.warning(f"Error in _process_element: {str(e)}")
            return None

    def _get_property_single_value(self, prop):
        """プロパティから単一の値を取得"""
        try:
            if hasattr(prop, 'NominalValue'):
                if hasattr(prop.NominalValue, 'wrappedValue'):
                    return prop.NominalValue.wrappedValue
            return None
        except Exception as e:
            logger.warning(f"Error getting property value: {str(e)}")
            return None

    def _get_material_properties(self, element):
        """材料プロパティの取得"""
        try:
            for rel in element.HasAssociations:
                if rel.is_a('IfcRelAssociatesMaterial'):
                    material = rel.RelatingMaterial

                    # 基本的な材料情報の取得
                    if material.is_a('IfcMaterial'):
                        material_props = {
                            'material_name': material.Name,
                            'material_type': 'IfcMaterial'
                        }

                        # 材料プロパティの取得
                        if hasattr(material, 'HasProperties'):
                            for prop in material.HasProperties:
                                if prop.Name in ['Grade', 'Type', 'Strength']:
                                    value = self._get_property_single_value(prop)
                                    if value is not None:
                                        material_props[prop.Name.lower()] = value

                        return material_props

                    # 層構造を持つ材料の処理
                    elif material.is_a('IfcMaterialLayerSetUsage'):
                        layer_set = material.ForLayerSet
                        if layer_set and layer_set.MaterialLayers:
                            layer = layer_set.MaterialLayers[0]
                            if layer.Material:
                                return {
                                    'material_name': layer.Material.Name,
                                    'material_type': 'IfcMaterialLayer',
                                    'layer_thickness': float(layer.LayerThickness)
                                }

        except Exception as e:
            logger.warning(f"Error in _get_material_properties: {str(e)}")
        return None

    def _get_profile_properties(self, element):
        """断面プロパティの取得"""
        try:
            if hasattr(element, 'Representation'):
                for representation in element.Representation.Representations:
                    for item in representation.Items:
                        if hasattr(item, 'SweptArea'):
                            profile = item.SweptArea

                            # I形鋼の処理
                            if profile.is_a('IfcIShapeProfileDef'):
                                return {
                                    'profile_type': 'I形鋼',
                                    'overall_depth': float(profile.OverallDepth),
                                    'flange_width': float(profile.OverallWidth),
                                    'web_thickness': float(profile.WebThickness),
                                    'flange_thickness': float(profile.FlangeThickness)
                                }

                            # 矩形断面の処理
                            elif profile.is_a('IfcRectangleProfileDef'):
                                return {
                                    'profile_type': '矩形',
                                    'width': float(profile.XDim),
                                    'height': float(profile.YDim)
                                }

                            # 円形断面の処理
                            elif profile.is_a('IfcCircleProfileDef'):
                                return {
                                    'profile_type': '円形',
                                    'diameter': float(profile.Radius * 2)
                                }

        except Exception as e:
            logger.warning(f"Error in _get_profile_properties: {str(e)}")
        return None

    def _get_element_properties(self, element):
        """要素の固有プロパティを取得"""
        properties = {}
        try:
            for definition in element.IsDefinedBy:
                if definition.is_a('IfcRelDefinesByProperties'):
                    property_set = definition.RelatingPropertyDefinition
                    if property_set.is_a('IfcPropertySet'):
                        for prop in property_set.HasProperties:
                            if prop.Name in ['Grade', 'NominalDiameter', 'Type', 'Length']:
                                value = self._get_property_single_value(prop)
                                if value is not None:
                                    properties[prop.Name.lower()] = value
        except Exception as e:
            logger.warning(f"Error getting element properties: {str(e)}")
        return properties

    def generate_csv(self, materials):
        """CSV形式でデータを出力"""
        try:
            output = StringIO()
            fieldnames = [
                'name', 'element_type', 'global_id',
                'material_name', 'material_type',
                'profile_type', 'overall_depth', 'flange_width',
                'web_thickness', 'flange_thickness',
                'width', 'height', 'diameter',
                'grade', 'nominal_diameter', 'type', 'length'
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            for material in materials:
                try:
                    row = {k: v for k, v in material.items() if k in fieldnames}
                    writer.writerow(row)
                except Exception as row_error:
                    logger.warning(f"Error writing row: {str(row_error)}")
                    continue

            return output.getvalue()
        except Exception as e:
            logger.error(f"Error generating CSV: {str(e)}", exc_info=True)
            raise ValueError(f"CSVの生成中にエラーが発生しました: {str(e)}")