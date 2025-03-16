import ifcopenshell
import csv
import logging
from io import StringIO
from decimal import Decimal
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class IFCProcessor:
    def __init__(self, file_path):
        self.ifc_file = None
        if file_path:
            try:
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
            structural_items = self.ifc_file.by_type('IfcStructuralItem')
            beams = self.ifc_file.by_type('IfcBeam')
            columns = self.ifc_file.by_type('IfcColumn')
            plates = self.ifc_file.by_type('IfcPlate')
            members = self.ifc_file.by_type('IfcMember')
            fasteners = self.ifc_file.by_type('IfcFastener')

            # 全ての要素を処理
            all_elements = structural_items + beams + columns + plates + members + fasteners
            logger.info(f"Found total {len(all_elements)} elements to process")

            for element in all_elements:
                try:
                    material_info = self._process_element(element)
                    if material_info:
                        materials.append(material_info)
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
            info = {
                'name': element.Name if hasattr(element, 'Name') else None,
                'element_type': element.is_a(),
                'global_id': element.GlobalId if hasattr(element, 'GlobalId') else None
            }

            # 材料情報の取得
            material_props = self._get_material_properties(element)
            if material_props:
                info.update(material_props)

            # プロファイル情報の取得
            profile_props = self._get_profile_properties(element)
            if profile_props:
                info.update(profile_props)

            # 寸法情報の取得
            if hasattr(element, 'ObjectPlacement'):
                dim_props = self._get_dimensions(element)
                if dim_props:
                    info.update(dim_props)

            return info

        except Exception as e:
            logger.warning(f"Error in _process_element: {str(e)}")
            return None

    def _get_material_properties(self, element):
        """材料プロパティの取得"""
        try:
            for rel in element.HasAssociations:
                if rel.is_a('IfcRelAssociatesMaterial'):
                    material = rel.RelatingMaterial
                    if material.is_a('IfcMaterial'):
                        return {
                            'material_name': material.Name,
                            'material_type': 'IfcMaterial'
                        }
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
                            if profile.is_a('IfcIShapeProfileDef'):
                                return {
                                    'profile_type': 'I形鋼',
                                    'overall_depth': float(profile.OverallDepth),
                                    'flange_width': float(profile.OverallWidth),
                                    'web_thickness': float(profile.WebThickness),
                                    'flange_thickness': float(profile.FlangeThickness)
                                }
                            elif profile.is_a('IfcRectangleProfileDef'):
                                return {
                                    'profile_type': '矩形',
                                    'width': float(profile.XDim),
                                    'height': float(profile.YDim)
                                }
        except Exception as e:
            logger.warning(f"Error in _get_profile_properties: {str(e)}")
        return None

    def _get_dimensions(self, element):
        """要素の寸法を取得"""
        try:
            if hasattr(element, 'Representation'):
                for representation in element.Representation.Representations:
                    if representation.RepresentationType == 'BoundingBox':
                        bbox = representation.Items[0]
                        return {
                            'length': float(bbox.XDim),
                            'width': float(bbox.YDim),
                            'height': float(bbox.ZDim)
                        }
        except Exception as e:
            logger.warning(f"Error in _get_dimensions: {str(e)}")
        return None

    def _decimal_default(self, obj):
        """JSON変換用のヘルパーメソッド"""
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError

    def generate_csv(self, materials):
        """CSV形式でデータを出力"""
        try:
            output = StringIO()
            fieldnames = [
                'name', 'element_type', 'global_id',
                'material_name', 'material_type',
                'profile_type', 'overall_depth', 'flange_width',
                'web_thickness', 'flange_thickness',
                'width', 'height', 'length'
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            for material in materials:
                writer.writerow({k: v for k, v in material.items() if k in fieldnames})

            return output.getvalue()
        except Exception as e:
            logger.error(f"Error generating CSV: {str(e)}", exc_info=True)
            raise ValueError(f"CSVの生成中にエラーが発生しました: {str(e)}")