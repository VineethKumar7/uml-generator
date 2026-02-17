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
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime


def generate_id():
    """Generate a unique XMI ID"""
    return f"_{uuid.uuid4().hex[:16]}"


def get_class_positions_from_svg(svg_content, class_names):
    """
    Parse SVG to extract X,Y positions of class boxes.
    Returns dict: {class_name: (x, y)}
    """
    positions = {}
    
    # Parse SVG
    try:
        # Remove namespace for easier parsing
        svg_content = re.sub(r'\sxmlns[^"]*"[^"]*"', '', svg_content)
        root = ET.fromstring(svg_content)
        
        # Find text elements that match class names
        for text_elem in root.iter():
            if text_elem.text and text_elem.text.strip() in class_names:
                class_name = text_elem.text.strip()
                # Get position from transform or x,y attributes
                x = float(text_elem.get('x', 0))
                y = float(text_elem.get('y', 0))
                
                # Check parent group for transform
                parent = text_elem
                for _ in range(5):  # Check up to 5 levels
                    parent = root.find(f".//*[./{text_elem.tag}]")
                    if parent is not None:
                        transform = parent.get('transform', '')
                        if 'translate' in transform:
                            match = re.search(r'translate\(([\d.]+)[,\s]+([\d.]+)\)', transform)
                            if match:
                                x += float(match.group(1))
                                y += float(match.group(2))
                
                positions[class_name] = (x, y)
    except Exception as e:
        pass  # Fall back to default directions if parsing fails
    
    return positions


def get_direction_symbol(from_pos, to_pos):
    """
    Determine direction symbol based on relative positions.
    Returns: ► (right), ◄ (left), ▼ (down), ▲ (up)
    """
    if not from_pos or not to_pos:
        return '▼'  # Default
    
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    
    # Determine primary direction
    if abs(dx) > abs(dy):
        # Horizontal movement is primary
        return '►' if dx > 0 else '◄'
    else:
        # Vertical movement is primary
        return '▼' if dy > 0 else '▲'


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
    parser.add_argument('--graph', action='store_true', help='Generate Graph Schema instead of UML')
    
    args = parser.parse_args()
    
    # Read input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1
    
    with open(input_path, 'r') as f:
        model = yaml.safe_load(f)
    
    # Generate XMI (only for UML mode)
    if not args.graph:
        xmi_content = generate_xmi(model)
        
        # Write output
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.with_suffix('.xmi')
        
        with open(output_path, 'w') as f:
            f.write(xmi_content)
        
        print(f"✅ Generated: {output_path}")
    
    # Generate PlantUML (UML or Graph Schema)
    if args.plantuml:
        puml_path = input_path.with_suffix('.puml')
        if args.graph:
            puml_content = generate_graph_plantuml(model)
        else:
            puml_content = generate_plantuml(model)
        with open(puml_path, 'w') as f:
            f.write(puml_content)
        print(f"✅ Generated: {puml_path}")
    
    return 0


def generate_plantuml(model: dict) -> str:
    """
    Generate PlantUML from model definition with Astah-like styling.
    
    Layout Rules (learned from testing):
    1. Top-to-bottom layout (NOT left-to-right) - prevents label overlap
    2. Node separation 80px, rank separation 60px - gives room for labels
    3. Single-line role labels "- roleName mult" - prevents text overlap with classes
    4. Scale 1.2 with 150 DPI - good resolution without being too large
    5. Smaller fonts (11/10px) - reduces visual clutter
    6. Package frame with "pkg ModelName" - matches Astah style
    7. Yellow/beige (#FFFFCC) background - matches Astah class color
    """
    model_name = model.get('name', 'DomainModel')
    
    lines = [
        f'@startuml {model_name.replace(" ", "_")}',
        '',
        "' Image size and layout",
        'scale 1.2',
        'skinparam dpi 150',
        '',
        "' Astah-like styling",
        'skinparam backgroundColor white',
        'skinparam class {',
        '    BackgroundColor #FFFFCC',
        '    BorderColor #000000',
        '    ArrowColor #000000',
        '    FontName Arial',
        '    FontSize 11',
        '    AttributeFontSize 10',
        '}',
        'skinparam enum {',
        '    BackgroundColor #FFFFCC',
        '    BorderColor #000000',
        '}',
        "' Smaller font for role labels to prevent overlap",
        'skinparam classFontSize 11',
        'skinparam classAttributeFontSize 10',
        'skinparam ArrowFontSize 9',
        'skinparam package {',
        '    BackgroundColor white',
        '    BorderColor #000000',
        '    FontSize 12',
        '    FontStyle bold',
        '}',
        'skinparam stereotype {',
        '    CBackgroundColor #FFFFCC',
        '}',
        "' Spacing - increased to prevent role label overlap",
        'skinparam nodesep 100',
        'skinparam ranksep 80',
        '',
        f'package "pkg {model_name}" <<Frame>> {{',
        '',
    ]
    
    # Enumerations
    for enum_name, values in model.get('enumerations', {}).items():
        lines.append(f'  enum {enum_name} <<enumeration>> {{')
        for value in values:
            lines.append(f'    + {value}()')
        lines.append('  }')
        lines.append('')
    
    # Classes
    for class_name, class_def in model.get('classes', {}).items():
        abstract = 'abstract ' if class_def.get('abstract', False) else ''
        lines.append(f'  {abstract}class {class_name} {{')
        for attr in class_def.get('attributes', []):
            vis = attr.get('visibility', '-')
            if vis == 'private': vis = '-'
            elif vis == 'public': vis = '+'
            elif vis == 'protected': vis = '#'
            attr_type = attr.get("type", "String")
            lines.append(f'    {vis} {attr["name"]} : {attr_type}')
        lines.append('  }')
        lines.append('')
    
    lines.append('}')  # Close package
    lines.append('')
    
    # Associations (outside package for cleaner rendering)
    for assoc in model.get('associations', []):
        from_c = assoc.get('from')
        to_c = assoc.get('to')
        from_mult = assoc.get('fromMultiplicity', '1')
        to_mult = assoc.get('toMultiplicity', '1')
        assoc_type = assoc.get('type', 'association')
        name = assoc.get('name', '')
        from_role = assoc.get('fromRole', '')
        to_role = assoc.get('toRole', '')
        
        if assoc_type == 'composition':
            arrow = '*--'
        elif assoc_type == 'aggregation':
            arrow = 'o--'
        else:
            arrow = '--'
        
        # Build labels - role names near multiplicity (single line to avoid overlap)
        from_label = from_mult
        to_label = to_mult
        
        if from_role:
            from_label = f"- {from_role} {from_mult}"
        if to_role:
            to_label = f"- {to_role} {to_mult}"
        
        assoc_label = f' : {name}' if name else ''
        lines.append(f'{from_c} "{from_label}" {arrow} "{to_label}" {to_c}{assoc_label}')
    
    lines.append('')
    
    # Generalizations
    for gen in model.get('generalizations', []):
        lines.append(f'{gen["parent"]} <|-- {gen["child"]}')
    
    lines.append('')
    lines.append('@enduml')
    
    return '\n'.join(lines)


def generate_graph_plantuml(model: dict) -> str:
    """
    Generate PlantUML for Graph Schema (Neo4j property graph).
    
    Conversion Rules (from Graph_Schema.md):
    1. No colon prefix on labels: "Person" not ":Person"
    2. Flatten inheritance:
       - Abstract → Concrete: copy properties only
       - Concrete → Concrete: copy properties AND relationships
    3. Relationships:
       - Derive name from role: "purchases" → "HAS_PURCHASE"
       - Composition → "CONTAINS"
       - Arrow (►) in name points toward target
       - NO multiplicities
    4. Remove abstract classes entirely
    """
    model_name = model.get('name', 'GraphSchema')
    
    # Build inheritance map
    generalizations = model.get('generalizations', [])
    parent_to_children = {}  # parent -> [children]
    child_to_parent = {}     # child -> parent
    
    for gen in generalizations:
        parent = gen.get('parent')
        child = gen.get('child')
        child_to_parent[child] = parent
        if parent not in parent_to_children:
            parent_to_children[parent] = []
        parent_to_children[parent].append(child)
    
    # Identify abstract classes
    classes = model.get('classes', {})
    abstract_classes = set()
    for class_name, class_def in classes.items():
        if class_def.get('abstract', False):
            abstract_classes.add(class_name)
    
    # Build flattened classes (with inherited properties)
    flattened_classes = {}
    
    def get_all_properties(class_name, visited=None):
        """Recursively get all properties including inherited ones"""
        if visited is None:
            visited = set()
        if class_name in visited:
            return []
        visited.add(class_name)
        
        props = []
        # Get parent properties first
        if class_name in child_to_parent:
            parent = child_to_parent[class_name]
            props.extend(get_all_properties(parent, visited))
        # Add own properties
        if class_name in classes:
            props.extend(classes[class_name].get('attributes', []))
        return props
    
    # Flatten classes (skip abstract classes)
    for class_name, class_def in classes.items():
        if class_name in abstract_classes:
            continue  # Skip abstract classes
        flattened_classes[class_name] = {
            'attributes': get_all_properties(class_name)
        }
    
    # Build relationship map with inheritance
    # For concrete inheritance, child gets parent's relationships
    associations = model.get('associations', [])
    flattened_associations = []
    
    def get_descendants(class_name):
        """Get all descendants of a class"""
        descendants = []
        for child in parent_to_children.get(class_name, []):
            if child not in abstract_classes:
                descendants.append(child)
            descendants.extend(get_descendants(child))
        return descendants
    
    for assoc in associations:
        from_c = assoc.get('from')
        to_c = assoc.get('to')
        
        # Skip if involving only abstract classes
        if from_c in abstract_classes and to_c in abstract_classes:
            continue
        
        # If 'from' is abstract, skip (shouldn't have outgoing)
        # If 'to' is abstract, skip
        if from_c in abstract_classes or to_c in abstract_classes:
            continue
        
        # Add original association
        flattened_associations.append(assoc)
        
        # If 'to' class has children (concrete inheritance), copy relationship to children
        to_descendants = get_descendants(to_c)
        for desc in to_descendants:
            new_assoc = assoc.copy()
            new_assoc['to'] = desc
            flattened_associations.append(new_assoc)
        
        # If 'from' class has children, copy relationship from children
        from_descendants = get_descendants(from_c)
        for desc in from_descendants:
            new_assoc = assoc.copy()
            new_assoc['from'] = desc
            flattened_associations.append(new_assoc)
    
    # Generate PlantUML
    lines = [
        f'@startuml {model_name.replace(" ", "_")}_Graph',
        '',
        "' Graph Schema styling (Neo4j property graph)",
        "' Professor's format: straight lines, NO arrowheads, direction in text",
        'scale 1.2',
        'skinparam dpi 150',
        '',
        "' Use polyline for straighter lines that stay in bounds",
        'skinparam linetype polyline',
        '',
        "' Remove all arrowheads from lines",
        'skinparam ArrowHeadColor transparent',
        '',
        'skinparam class {',
        '    BackgroundColor #90EE90',  # Light green for graph nodes
        '    BorderColor #000000',
        '    FontName Arial',
        '    FontSize 11',
        '    AttributeFontSize 10',
        '}',
        'skinparam package {',
        '    BackgroundColor white',
        '    BorderColor #000000',
        '    FontSize 12',
        '    FontStyle bold',
        '}',
        'skinparam nodesep 100',
        'skinparam ranksep 80',
        'skinparam minClassWidth 100',
        '',
        "' Hide class circle icon (C), methods, and stereotypes",
        'hide circle',
        'hide methods',
        'hide stereotype',
        '',
        f'package "pkg Graph Schema" <<Frame>> {{',
        '',
    ]
    
    # Node types (flattened classes)
    for class_name, class_def in flattened_classes.items():
        lines.append(f'  class {class_name} {{')
        for attr in class_def.get('attributes', []):
            attr_type = attr.get("type", "String")
            lines.append(f'    - {attr["name"]} : {attr_type}')
        lines.append('  }')
        lines.append('')
    
    # Relationships (with Graph Schema naming) - INSIDE package
    lines.append('')
    seen_relationships = set()  # Avoid duplicates
    
    for assoc in flattened_associations:
        from_c = assoc.get('from')
        to_c = assoc.get('to')
        assoc_type = assoc.get('type', 'association')
        to_role = assoc.get('toRole', '')
        name = assoc.get('name', '')
        
        # Skip if classes don't exist in flattened
        if from_c not in flattened_classes or to_c not in flattened_classes:
            continue
        
        # Derive relationship name
        if assoc_type == 'composition':
            rel_name = 'CONTAINS'
        elif to_role:
            # Convert role to relationship name: "purchases" -> "HAS_PURCHASE"
            singular = to_role.rstrip('s')  # Simple singularize
            rel_name = f'HAS_{singular.upper()}'
        elif name:
            rel_name = name.upper().replace(' ', '_')
        else:
            rel_name = 'RELATES_TO'
        
        # Create unique key to avoid duplicates
        rel_key = (from_c, to_c, rel_name)
        if rel_key in seen_relationships:
            continue
        seen_relationships.add(rel_key)
        
        # Graph Schema: plain lines, direction determined by actual position
        # Symbol will be set in second pass based on SVG positions
        
        if from_c == to_c:
            # Self-loop: always points right
            lines.append(f'{from_c} -- {to_c} : {rel_name} ►')
        else:
            # Use placeholder {DIR} - will be replaced in second pass
            lines.append(f'{from_c} -- {to_c} : {rel_name} {{DIR:{from_c}:{to_c}}}')
    
    lines.append('')
    lines.append('}')  # Close package
    lines.append('')
    lines.append("' Note: Graph schemas have NO inheritance arrows")
    lines.append("' Inheritance is flattened (properties + relationships copied)")
    lines.append("' Direction: ► = right, ◄ = left, ▼ = down, ▲ = up")
    lines.append('')
    lines.append('@enduml')
    
    puml_content = '\n'.join(lines)
    
    # Two-pass: if there are {DIR:...} placeholders, resolve them
    if '{DIR:' in puml_content:
        puml_content = resolve_directions(puml_content, list(flattened_classes.keys()))
    
    return puml_content


def resolve_directions(puml_content, class_names):
    """
    Two-pass direction resolution:
    1. Generate SVG from PlantUML (with placeholder symbols)
    2. Parse SVG to get class positions
    3. Replace placeholders with correct direction symbols
    """
    import tempfile
    import os
    
    # Replace placeholders with temporary symbol for first pass
    temp_puml = re.sub(r'\{DIR:[^}]+\}', '?', puml_content)
    
    # Find plantuml.jar
    script_dir = Path(__file__).resolve().parent.parent
    plantuml_jar = script_dir / 'plantuml.jar'
    
    if not plantuml_jar.exists():
        # Can't do two-pass, use default
        return re.sub(r'\{DIR:[^}]+\}', '▼', puml_content)
    
    try:
        # Generate SVG in temp directory
        temp_dir = tempfile.mkdtemp()
        temp_puml_path = os.path.join(temp_dir, 'graph.puml')
        
        with open(temp_puml_path, 'w') as f:
            f.write(temp_puml)
        
        # Run PlantUML to generate SVG
        result = subprocess.run(
            ['java', '-jar', str(plantuml_jar), '-tsvg', '-o', temp_dir, temp_puml_path],
            capture_output=True,
            timeout=30
        )
        
        # Find the generated SVG (PlantUML names it after @startuml name)
        svg_files = [f for f in os.listdir(temp_dir) if f.endswith('.svg')]
        temp_svg_path = os.path.join(temp_dir, svg_files[0]) if svg_files else None
        
        if temp_svg_path and os.path.exists(temp_svg_path):
            with open(temp_svg_path, 'r') as f:
                svg_content = f.read()
            
            # Get positions
            positions = get_class_positions_from_svg(svg_content, class_names)
            
            # Replace placeholders with correct symbols
            def replace_dir(match):
                parts = match.group(0)[5:-1].split(':')  # Extract from {DIR:from:to}
                from_c, to_c = parts[0], parts[1]
                from_pos = positions.get(from_c)
                to_pos = positions.get(to_c)
                return get_direction_symbol(from_pos, to_pos)
            
            puml_content = re.sub(r'\{DIR:[^}]+\}', replace_dir, puml_content)
            
            # Cleanup
            os.unlink(temp_svg_path)
        
        os.unlink(temp_puml_path)
        os.rmdir(temp_dir)
        
    except Exception as e:
        # Fall back to default direction
        puml_content = re.sub(r'\{DIR:[^}]+\}', '▼', puml_content)
    
    return puml_content


if __name__ == '__main__':
    exit(main())
