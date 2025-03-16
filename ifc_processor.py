import ifcopenshell
import csv
import logging
from io import StringIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IFCProcessor:
    def __init__(self, file_path):
        self.ifc_file = None
        if file_path:
            try:
                self.ifc_file = ifcopenshell.open(file_path)
            except Exception as e:
                logging.error(f"Error opening IFC file: {str(e)}")
                raise ValueError(f"IFCファイルを開けませんでした: {str(e)}")

    def get_profile_properties(self, element):
        """断面プロファイルの情報を取得"""
        try:
            if hasattr(element, 'Representation'):
                representation = element.Representation
                if representation:
                    items = representation.Representations[0].Items[0]
                    if hasattr(items, 'SweptArea'):
                        profile = items.SweptArea
                        if profile.is_a('IfcIShapeProfileDef'):
                            return {
                                'profile_type': 'I形鋼',
                                'overall_depth': profile.OverallDepth,
                                'flange_width': profile.OverallWidth,
                                'web_thickness': profile.WebThickness,
                                'flange_thickness': profile.FlangeThickness
                            }
                        elif profile.is_a('IfcRectangleProfileDef'):
                            return {
                                'profile_type': '矩形',
                                'width': profile.XDim,
                                'height': profile.YDim
                            }
        except Exception as e:
            logger.warning(f"Error getting profile properties: {str(e)}")
        return None

    def get_fastener_properties(self, element):
        """ボルトなどの接合部材の情報を取得"""
        try:
            if element.is_a('IfcFastener'):
                psets = element.IsDefinedBy
                for definition in psets:
                    if definition.is_a('IfcRelDefinesByProperties'):
                        props = definition.RelatingPropertyDefinition
                        if props.is_a('IfcPropertySet'):
                            properties = {}
                            for prop in props.HasProperties:
                                if prop.Name in ['Grade', 'NominalDiameter', 'Type']:
                                    properties[prop.Name] = prop.NominalValue.wrappedValue
                            return properties
        except Exception as e:
            logger.warning(f"Error getting fastener properties: {str(e)}")
        return None

    def extract_material_sizes(self):
        if not self.ifc_file:
            raise ValueError("IFCファイルが読み込まれていません。")

        materials = []
        try:
            # 全ての要素を取得
            elements = self.ifc_file.by_type('IfcElement')
            logger.info(f"Found {len(elements)} elements")

            for element in elements:
                material_info = {
                    'name': None,
                    'element_type': element.is_a(),
                    'global_id': element.GlobalId,
                    'length': None,
                    'width': None,
                    'height': None
                }

                # 材料情報の取得
                material_select = element.HasAssociations
                for association in material_select:
                    if association.is_a('IfcRelAssociatesMaterial'):
                        material = association.RelatingMaterial
                        if material.is_a('IfcMaterial'):
                            material_info['name'] = material.Name

                # プロファイル情報の取得
                profile_props = self.get_profile_properties(element)
                if profile_props:
                    material_info.update(profile_props)

                # ボルト情報の取得
                if element.is_a('IfcFastener'):
                    fastener_props = self.get_fastener_properties(element)
                    if fastener_props:
                        material_info.update(fastener_props)

                # 寸法情報の取得
                if hasattr(element, 'ObjectPlacement'):
                    bbox = self.get_bounding_box(element)
                    if bbox:
                        material_info.update(bbox)

                materials.append(material_info)

            logger.info(f"Successfully extracted {len(materials)} materials")
            return materials

        except Exception as e:
            logger.error(f"Error extracting materials: {str(e)}")
            raise ValueError(f"材料データの抽出中にエラーが発生しました: {str(e)}")

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

    def generate_csv(self, materials):
        try:
            output = StringIO()
            fieldnames = ['name', 'element_type', 'global_id', 'profile_type', 
                         'overall_depth', 'flange_width', 'web_thickness', 
                         'flange_thickness', 'width', 'height', 'Grade', 
                         'NominalDiameter', 'Type']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            for material in materials:
                writer.writerow(material)

            return output.getvalue()
        except Exception as e:
            logger.error(f"Error generating CSV: {str(e)}")
            raise ValueError(f"CSVの生成中にエラーが発生しました: {str(e)}")