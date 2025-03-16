import ifcopenshell
import csv
import logging
from io import StringIO

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class IFCProcessor:
    def __init__(self, file_path):
        self.ifc_file = None
        if file_path:
            try:
                self.ifc_file = ifcopenshell.open(file_path)
            except Exception as e:
                logger.error(f"Error opening IFC file: {str(e)}")
                raise ValueError(f"IFCファイルを開けませんでした: {str(e)}")

    def get_property_values(self, element):
        """要素のプロパティ値を取得"""
        properties = {}
        try:
            for definition in element.IsDefinedBy:
                if definition.is_a('IfcRelDefinesByProperties'):
                    property_set = definition.RelatingPropertyDefinition
                    if property_set.is_a('IfcPropertySet'):
                        for prop in property_set.HasProperties:
                            if hasattr(prop, 'NominalValue'):
                                properties[prop.Name] = prop.NominalValue.wrappedValue
        except Exception as e:
            logger.warning(f"Error getting property values: {str(e)}")
        return properties

    def get_profile_properties(self, element):
        """断面プロファイルの情報を取得"""
        try:
            logger.debug(f"Getting profile for element type: {element.is_a()}")
            if hasattr(element, 'Representation'):
                representations = element.Representation.Representations
                for rep in representations:
                    if rep.Items and len(rep.Items) > 0:
                        item = rep.Items[0]
                        if hasattr(item, 'SweptArea'):
                            profile = item.SweptArea
                            logger.debug(f"Found profile type: {profile.is_a()}")

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
                            # その他の断面形状の処理を追加
        except Exception as e:
            logger.warning(f"Error getting profile properties: {str(e)}", exc_info=True)
        return None

    def get_material_properties(self, element):
        """材料プロパティを取得"""
        try:
            for rel in element.HasAssociations:
                if rel.is_a('IfcRelAssociatesMaterial'):
                    material = rel.RelatingMaterial
                    if material.is_a('IfcMaterial'):
                        properties = {'name': material.Name}
                        # 材料のプロパティを取得
                        if hasattr(material, 'HasProperties'):
                            for prop in material.HasProperties:
                                if hasattr(prop, 'Name') and hasattr(prop, 'NominalValue'):
                                    properties[prop.Name] = prop.NominalValue.wrappedValue
                        return properties
                    elif material.is_a('IfcMaterialLayerSetUsage'):
                        layer_set = material.ForLayerSet
                        if layer_set and layer_set.MaterialLayers:
                            layer = layer_set.MaterialLayers[0]
                            if layer.Material:
                                return {'name': layer.Material.Name, 'thickness': layer.LayerThickness}
        except Exception as e:
            logger.warning(f"Error getting material properties: {str(e)}", exc_info=True)
        return None

    def get_fastener_properties(self, element):
        """ボルトなどの接合部材の情報を取得"""
        try:
            if element.is_a('IfcFastener'):
                logger.debug(f"Processing fastener: {element.Name if hasattr(element, 'Name') else 'unnamed'}")
                properties = self.get_property_values(element)
                if properties:
                    relevant_props = {
                        'grade': properties.get('Grade'),
                        'nominal_diameter': properties.get('NominalDiameter'),
                        'type': properties.get('Type'),
                        'length': properties.get('Length')
                    }
                    logger.debug(f"Found fastener properties: {relevant_props}")
                    return relevant_props
        except Exception as e:
            logger.warning(f"Error getting fastener properties: {str(e)}", exc_info=True)
        return None

    def extract_material_sizes(self):
        if not self.ifc_file:
            raise ValueError("IFCファイルが読み込まれていません。")

        materials = []
        try:
            elements = self.ifc_file.by_type('IfcElement')
            logger.info(f"Found {len(elements)} elements")

            for element in elements:
                logger.debug(f"Processing element: {element.is_a()}")

                material_info = {
                    'name': None,
                    'element_type': element.is_a(),
                    'global_id': element.GlobalId
                }

                # 材料情報の取得
                mat_props = self.get_material_properties(element)
                if mat_props:
                    material_info.update(mat_props)

                # プロファイル情報の取得
                profile_props = self.get_profile_properties(element)
                if profile_props:
                    material_info.update(profile_props)
                    logger.debug(f"Added profile properties: {profile_props}")

                # ボルト情報の取得
                if element.is_a('IfcFastener'):
                    fastener_props = self.get_fastener_properties(element)
                    if fastener_props:
                        material_info.update(fastener_props)
                        logger.debug(f"Added fastener properties: {fastener_props}")

                # 要素固有のプロパティを取得
                element_props = self.get_property_values(element)
                if element_props:
                    material_info.update(element_props)

                materials.append(material_info)

            logger.info(f"Successfully extracted {len(materials)} materials")
            return materials

        except Exception as e:
            logger.error(f"Error extracting materials: {str(e)}", exc_info=True)
            raise ValueError(f"材料データの抽出中にエラーが発生しました: {str(e)}")

    def generate_csv(self, materials):
        try:
            output = StringIO()
            fieldnames = [
                'name', 'element_type', 'global_id',
                'profile_type', 'overall_depth', 'flange_width',
                'web_thickness', 'flange_thickness', 'width', 'height',
                'grade', 'nominal_diameter', 'type', 'length'
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            for material in materials:
                writer.writerow(material)

            return output.getvalue()
        except Exception as e:
            logger.error(f"Error generating CSV: {str(e)}", exc_info=True)
            raise ValueError(f"CSVの生成中にエラーが発生しました: {str(e)}")

    def get_bounding_box(self, element):
        try:
            bbox = {
                'length': None,
                'width': None,
                'height': None
            }

            if hasattr(element, 'Representation'):
                representation = element.Representation
                if representation:
                    for rep in representation.Representations:
                        if rep.RepresentationType == 'BoundingBox':
                            bbox['length'] = rep.BoundingBox.XDim
                            bbox['width'] = rep.BoundingBox.YDim
                            bbox['height'] = rep.BoundingBox.ZDim
            return bbox
        except Exception as e:
            logger.warning(f"Error getting bounding box for element: {str(e)}")
            return None