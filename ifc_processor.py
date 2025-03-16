import ifcopenshell
import csv
from io import StringIO

class IFCProcessor:
    def __init__(self, file_path):
        self.ifc_file = ifcopenshell.open(file_path)
        
    def extract_material_sizes(self):
        materials = []
        
        # Get all elements with material assignments
        for element in self.ifc_file.by_type('IfcElement'):
            material_select = element.HasAssociations
            
            for association in material_select:
                if association.is_a('IfcRelAssociatesMaterial'):
                    material = association.RelatingMaterial
                    
                    if material.is_a('IfcMaterial'):
                        # Extract basic material information
                        material_info = {
                            'name': material.Name,
                            'element_type': element.is_a(),
                            'global_id': element.GlobalId
                        }
                        
                        # Try to get material properties
                        if hasattr(element, 'ObjectPlacement'):
                            bbox = self.get_bounding_box(element)
                            if bbox:
                                material_info.update(bbox)
                                
                        materials.append(material_info)
                        
        return materials
    
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
        except:
            return None
            
    def generate_csv(self, materials):
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=['name', 'element_type', 'global_id', 'length', 'width', 'height'])
        writer.writeheader()
        
        for material in materials:
            writer.writerow(material)
            
        return output.getvalue()
