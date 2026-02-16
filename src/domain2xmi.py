#!/usr/bin/env python3
"""
Domain Model to XMI Generator
Generates Astah-compatible XMI files from YAML domain model definitions.

Usage:
    python3 domain2xmi.py model.yaml -o output.xmi
    
YAML Format:
    name: "My Domain Model"
    enumerations:
      Status:
        - APPROVED
        - NOT_APPROVED
    classes:
      Person:
        attributes:
          - name: firstName
            type: String
          - name: age
            type: Integer
    associations:
      - from: Person
        to: Contract
        name: has
        fromMultiplicity: "1"
        toMultiplicity: "1..*"
        type: association  # or composition, aggregation
"""

import argparse
import yaml
import uuid
from pathlib import Path
from datetime import datetime


def generate_id():
    """Generate a unique XMI ID"""
    return f"_{uuid.uuid4().hex[:16]}"


def generate_xmi(model: dict) -> str:
    """Generate XMI 2.1 from model definition"""
    
    model_name = model.get('name', 'DomainModel')
    model_id = generate_id()
    
    # Track IDs for classes
    class_ids = {}
    enum_ids = {}
    
    # Start XMI document
    xmi_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<xmi:XMI xmi:version="2.1"',
        '    xmlns:xmi="http://schema.omg.org/spec/XMI/2.1"',
        '    xmlns:uml="http://schema.omg.org/spec/UML/2.1">',
        f'  <uml:Model xmi:id="{model_id}" name="{model_name}">',
    ]
    
    # Generate Enumerations
    for enum_name, values in model.get('enumerations', {}).items():
        enum_id = generate_id()
        enum_ids[enum_name] = enum_id
        xmi_parts.append(f'    <packagedElement xmi:type="uml:Enumeration" xmi:id="{enum_id}" name="{enum_name}">')
        for value in values:
            literal_id = generate_id()
            xmi_parts.append(f'      <ownedLiteral xmi:type="uml:EnumerationLiteral" xmi:id="{literal_id}" name="{value}"/>')
        xmi_parts.append('    </packagedElement>')
    
    # Generate Classes
    for class_name, class_def in model.get('classes', {}).items():
        class_id = generate_id()
        class_ids[class_name] = class_id
        
        stereotypes = class_def.get('stereotypes', [])
        is_abstract = class_def.get('abstract', False)
        
        abstract_attr = ' isAbstract="true"' if is_abstract else ''
        xmi_parts.append(f'    <packagedElement xmi:type="uml:Class" xmi:id="{class_id}" name="{class_name}"{abstract_attr}>')
        
        # Add attributes
        for attr in class_def.get('attributes', []):
            attr_id = generate_id()
            attr_name = attr.get('name', 'unnamed')
            attr_type = attr.get('type', 'String')
            visibility = attr.get('visibility', 'private')
            
            # Map visibility
            vis_map = {'private': 'private', 'public': 'public', 'protected': 'protected', '-': 'private', '+': 'public', '#': 'protected'}
            vis = vis_map.get(visibility, 'private')
            
            # Check if type is an enum
            if attr_type in enum_ids:
                xmi_parts.append(f'      <ownedAttribute xmi:type="uml:Property" xmi:id="{attr_id}" name="{attr_name}" visibility="{vis}" type="{enum_ids[attr_type]}"/>')
            else:
                type_id = generate_id()
                xmi_parts.append(f'      <ownedAttribute xmi:type="uml:Property" xmi:id="{attr_id}" name="{attr_name}" visibility="{vis}">')
                xmi_parts.append(f'        <type xmi:type="uml:PrimitiveType" href="http://schema.omg.org/spec/UML/2.1/uml.xml#{attr_type}"/>')
                xmi_parts.append('      </ownedAttribute>')
        
        xmi_parts.append('    </packagedElement>')
    
    # Generate Associations
    for assoc in model.get('associations', []):
        assoc_id = generate_id()
        from_class = assoc.get('from')
        to_class = assoc.get('to')
        assoc_name = assoc.get('name', '')
        from_mult = assoc.get('fromMultiplicity', '1')
        to_mult = assoc.get('toMultiplicity', '1')
        assoc_type = assoc.get('type', 'association')  # association, composition, aggregation
        from_role = assoc.get('fromRole', '')
        to_role = assoc.get('toRole', '')
        
        if from_class not in class_ids or to_class not in class_ids:
            print(f"Warning: Skipping association {from_class} -> {to_class}, class not found")
            continue
        
        end1_id = generate_id()
        end2_id = generate_id()
        
        # Determine aggregation kind
        agg1 = ''
        agg2 = ''
        if assoc_type == 'composition':
            agg1 = ' aggregation="composite"'
        elif assoc_type == 'aggregation':
            agg1 = ' aggregation="shared"'
        
        xmi_parts.append(f'    <packagedElement xmi:type="uml:Association" xmi:id="{assoc_id}" name="{assoc_name}">')
        
        # Parse multiplicities
        def parse_mult(mult_str):
            if mult_str == '*':
                return ('0', '*')
            elif mult_str == '1..*':
                return ('1', '*')
            elif mult_str == '0..1':
                return ('0', '1')
            elif mult_str == '0..*':
                return ('0', '*')
            elif '..' in mult_str:
                parts = mult_str.split('..')
                return (parts[0], parts[1])
            else:
                return (mult_str, mult_str)
        
        from_lower, from_upper = parse_mult(from_mult)
        to_lower, to_upper = parse_mult(to_mult)
        
        # Member ends
        xmi_parts.append(f'      <memberEnd xmi:idref="{end1_id}"/>')
        xmi_parts.append(f'      <memberEnd xmi:idref="{end2_id}"/>')
        
        # Owned ends
        role1_attr = f' name="{from_role}"' if from_role else ''
        role2_attr = f' name="{to_role}"' if to_role else ''
        
        xmi_parts.append(f'      <ownedEnd xmi:type="uml:Property" xmi:id="{end1_id}" type="{class_ids[from_class]}"{agg1}{role1_attr}>')
        xmi_parts.append(f'        <lowerValue xmi:type="uml:LiteralInteger" value="{from_lower}"/>')
        if from_upper == '*':
            xmi_parts.append(f'        <upperValue xmi:type="uml:LiteralUnlimitedNatural" value="-1"/>')
        else:
            xmi_parts.append(f'        <upperValue xmi:type="uml:LiteralInteger" value="{from_upper}"/>')
        xmi_parts.append('      </ownedEnd>')
        
        xmi_parts.append(f'      <ownedEnd xmi:type="uml:Property" xmi:id="{end2_id}" type="{class_ids[to_class]}"{role2_attr}>')
        xmi_parts.append(f'        <lowerValue xmi:type="uml:LiteralInteger" value="{to_lower}"/>')
        if to_upper == '*':
            xmi_parts.append(f'        <upperValue xmi:type="uml:LiteralUnlimitedNatural" value="-1"/>')
        else:
            xmi_parts.append(f'        <upperValue xmi:type="uml:LiteralInteger" value="{to_upper}"/>')
        xmi_parts.append('      </ownedEnd>')
        
        xmi_parts.append('    </packagedElement>')
    
    # Generate Generalizations (Inheritance)
    for gen in model.get('generalizations', []):
        child_class = gen.get('child')
        parent_class = gen.get('parent')
        
        if child_class not in class_ids or parent_class not in class_ids:
            print(f"Warning: Skipping generalization {child_class} -> {parent_class}, class not found")
            continue
        
        # Add generalization to child class (need to modify the class element)
        # For simplicity, we'll add it as a separate element
        gen_id = generate_id()
        xmi_parts.append(f'    <packagedElement xmi:type="uml:Generalization" xmi:id="{gen_id}" general="{class_ids[parent_class]}" specific="{class_ids[child_class]}"/>')
    
    # Close model and XMI
    xmi_parts.append('  </uml:Model>')
    xmi_parts.append('</xmi:XMI>')
    
    return '\n'.join(xmi_parts)


def main():
    parser = argparse.ArgumentParser(description='Generate XMI from YAML domain model')
    parser.add_argument('input', help='Input YAML file')
    parser.add_argument('-o', '--output', help='Output XMI file (default: input name with .xmi)')
    parser.add_argument('--plantuml', action='store_true', help='Also generate PlantUML file')
    
    args = parser.parse_args()
    
    # Read input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1
    
    with open(input_path, 'r') as f:
        model = yaml.safe_load(f)
    
    # Generate XMI
    xmi_content = generate_xmi(model)
    
    # Write output
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.xmi')
    
    with open(output_path, 'w') as f:
        f.write(xmi_content)
    
    print(f"✅ Generated: {output_path}")
    
    # Optionally generate PlantUML
    if args.plantuml:
        puml_path = input_path.with_suffix('.puml')
        puml_content = generate_plantuml(model)
        with open(puml_path, 'w') as f:
            f.write(puml_content)
        print(f"✅ Generated: {puml_path}")
    
    return 0


def generate_plantuml(model: dict) -> str:
    """Generate PlantUML from model definition"""
    lines = ['@startuml ' + model.get('name', 'DomainModel').replace(' ', '_'), '']
    
    # Enumerations
    for enum_name, values in model.get('enumerations', {}).items():
        lines.append(f'enum {enum_name} {{')
        for value in values:
            lines.append(f'  {value}')
        lines.append('}')
        lines.append('')
    
    # Classes
    for class_name, class_def in model.get('classes', {}).items():
        abstract = 'abstract ' if class_def.get('abstract', False) else ''
        lines.append(f'{abstract}class {class_name} {{')
        for attr in class_def.get('attributes', []):
            vis = attr.get('visibility', '-')
            if vis == 'private': vis = '-'
            elif vis == 'public': vis = '+'
            elif vis == 'protected': vis = '#'
            lines.append(f'  {vis} {attr["name"]} : {attr.get("type", "String")}')
        lines.append('}')
        lines.append('')
    
    # Associations
    for assoc in model.get('associations', []):
        from_c = assoc.get('from')
        to_c = assoc.get('to')
        from_mult = assoc.get('fromMultiplicity', '1')
        to_mult = assoc.get('toMultiplicity', '1')
        assoc_type = assoc.get('type', 'association')
        name = assoc.get('name', '')
        
        if assoc_type == 'composition':
            arrow = '*--'
        elif assoc_type == 'aggregation':
            arrow = 'o--'
        else:
            arrow = '--'
        
        label = f' : {name}' if name else ''
        lines.append(f'{from_c} "{from_mult}" {arrow} "{to_mult}" {to_c}{label}')
    
    # Generalizations
    for gen in model.get('generalizations', []):
        lines.append(f'{gen["parent"]} <|-- {gen["child"]}')
    
    lines.append('')
    lines.append('@enduml')
    
    return '\n'.join(lines)


if __name__ == '__main__':
    exit(main())
