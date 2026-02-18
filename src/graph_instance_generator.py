#!/usr/bin/env python3
"""
Graph Instance (Example Graph) Generator
Creates instance diagrams showing actual data values

Format:
- Labels with colon prefix: :Person
- Properties with equals: name = John
- Plain lines (no arrowheads) with relationship names

Supports two modes:
1. Direct instance data (nodes/edges in YAML)
2. Auto-generate from schema (classes/associations in YAML)
"""

import yaml
import sys
import os


def auto_generate_instances(data: dict) -> dict:
    """
    Auto-generate example instances from a domain model schema.
    Creates sample data for each class and relationship.
    """
    classes = data.get('classes', {})
    associations = data.get('associations', [])
    enumerations = data.get('enumerations', {})
    generalizations = data.get('generalizations', [])
    
    if not classes:
        return data  # Not a schema, return as-is
    
    nodes = []
    edges = []
    node_counter = {}
    
    # Find child classes (to skip abstract parents if needed)
    child_classes = set()
    for gen in generalizations:
        child_classes.add(gen.get('child', ''))
    
    # Generate sample nodes for each class
    for class_name, class_data in classes.items():
        class_data = class_data or {}
        attrs = class_data.get('attributes', [])
        
        # Create 1-2 instances per class (2 for Person to show relationships)
        num_instances = 2 if class_name.lower() in ['person', 'user', 'customer', 'patient', 'doctor'] else 1
        
        for i in range(num_instances):
            node_id = f"{class_name.lower()}{i+1}"
            node_counter[class_name] = node_counter.get(class_name, 0) + 1
            
            # Generate sample property values
            props = {}
            for attr in attrs:
                if isinstance(attr, dict):
                    attr_name = attr.get('name', '')
                    attr_type = attr.get('type', 'String')
                else:
                    attr_name = str(attr)
                    attr_type = 'String'
                
                # Generate sample value based on type
                if attr_type in enumerations:
                    enum_values = enumerations[attr_type]
                    props[attr_name] = enum_values[i % len(enum_values)] if enum_values else 'VALUE'
                elif attr_type.lower() in ['int', 'integer', 'number', 'float', 'double']:
                    props[attr_name] = (i + 1) * 100
                elif attr_type.lower() in ['date', 'datetime']:
                    props[attr_name] = f"2026-0{i+1}-15"
                elif attr_type.lower() == 'boolean':
                    props[attr_name] = 'true' if i % 2 == 0 else 'false'
                elif 'name' in attr_name.lower():
                    sample_names = ['John', 'Alice', 'Bob', 'Carol', 'David']
                    props[attr_name] = sample_names[i % len(sample_names)]
                elif 'email' in attr_name.lower():
                    props[attr_name] = f"user{i+1}@example.com"
                else:
                    props[attr_name] = f"{attr_name.capitalize()}{i+1}"
            
            nodes.append({
                'id': node_id,
                'label': class_name,
                'properties': props
            })
    
    # Build node lookup by class
    nodes_by_class = {}
    for node in nodes:
        label = node['label']
        if label not in nodes_by_class:
            nodes_by_class[label] = []
        nodes_by_class[label].append(node['id'])
    
    # Generate edges from associations
    for assoc in associations:
        from_class = assoc.get('from', '')
        to_class = assoc.get('to', '')
        assoc_name = assoc.get('name', '')
        assoc_type = assoc.get('type', 'association')
        
        # Convert to graph relationship name
        if assoc_type == 'composition':
            rel_name = 'CONTAINS'
        elif assoc_name:
            rel_name = f"HAS_{assoc_name.upper().replace(' ', '_')}"
        else:
            rel_name = f"HAS_{to_class.upper()}"
        
        # Create edges between instances
        from_nodes = nodes_by_class.get(from_class, [])
        to_nodes = nodes_by_class.get(to_class, [])
        
        if from_nodes and to_nodes:
            # Connect first from_node to first to_node
            edges.append({
                'from': from_nodes[0],
                'to': to_nodes[0],
                'type': rel_name
            })
            
            # If multiple nodes, create more relationships for realism
            if len(from_nodes) > 1 and len(to_nodes) > 1:
                edges.append({
                    'from': from_nodes[1],
                    'to': to_nodes[min(1, len(to_nodes)-1)],
                    'type': rel_name
                })
    
    # Handle self-referencing (e.g., Person -> Person for friends)
    for assoc in associations:
        from_class = assoc.get('from', '')
        to_class = assoc.get('to', '')
        if from_class == to_class:
            nodes_list = nodes_by_class.get(from_class, [])
            if len(nodes_list) >= 2:
                assoc_name = assoc.get('name', 'RELATED')
                rel_name = f"HAS_{assoc_name.upper().replace(' ', '_')}"
                edges.append({
                    'from': nodes_list[0],
                    'to': nodes_list[1],
                    'type': rel_name
                })
    
    return {
        'name': data.get('name', 'Example Graph'),
        'nodes': nodes,
        'edges': edges
    }


def generate_plantuml(data: dict) -> str:
    """Generate PlantUML for graph instance diagram with package boundary"""
    lines = ['@startuml']
    lines.append('skinparam backgroundColor white')
    lines.append('skinparam package {')
    lines.append('  BackgroundColor white')
    lines.append('  BorderColor black')
    lines.append('  FontSize 14')
    lines.append('  FontStyle bold')
    lines.append('}')
    lines.append('skinparam class {')
    lines.append('  BackgroundColor #E8F5E9')  # Light green for instances
    lines.append('  BorderColor #2E7D32')
    lines.append('  FontSize 12')
    lines.append('}')
    lines.append('skinparam classAttributeFontSize 11')
    lines.append('hide circle')
    lines.append('hide methods')
    lines.append('')
    
    title = data.get('name', 'Example Graph')
    
    # Package boundary
    lines.append(f'package "pkg {title}" {{')
    lines.append('')
    
    # Generate nodes (instances)
    nodes = data.get('nodes', [])
    for node in nodes:
        node_id = node.get('id', '')
        label = node.get('label', '')
        props = node.get('properties', {})
        
        # Class with colon prefix
        lines.append(f'  class ":{label}" as {node_id} {{')
        for prop_name, prop_value in props.items():
            # Format: name = value (no quotes per professor's style)
            lines.append(f'    {prop_name} = {prop_value}')
        lines.append('  }')
        lines.append('')
    
    # Generate relationships (plain lines, no arrows)
    edges = data.get('edges', [])
    for edge in edges:
        from_id = edge.get('from', '')
        to_id = edge.get('to', '')
        rel_type = edge.get('type', '')
        
        # Plain line with label (no arrowhead)
        lines.append(f'  {from_id} -- {to_id} : {rel_type}')
    
    lines.append('}')  # Close package
    lines.append('@enduml')
    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: graph_instance_generator.py <instance.yaml> [-o output]")
        print("")
        print("YAML format:")
        print("""
name: "Online Shop Example"

nodes:
  - id: john
    label: Person
    properties:
      name: John
      
  - id: alice
    label: Person
    properties:
      name: Alice
      
  - id: purchase1
    label: Purchase
    properties:
      quantity: 1
      
  - id: laptop1
    label: Product
    properties:
      name: Laptop 1
      price: 1500

edges:
  - from: john
    to: alice
    type: HAS_FRIEND
    
  - from: john
    to: purchase1
    type: HAS_PURCHASE
    
  - from: purchase1
    to: laptop1
    type: HAS_PRODUCT
""")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_base = None
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] in ['-o', '--output']:
            output_base = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    if not output_base:
        output_base = os.path.splitext(input_file)[0]
    
    with open(input_file, 'r') as f:
        data = yaml.safe_load(f)
    
    # Check if this is a schema (has classes) or instance data (has nodes)
    # If schema, auto-generate example instances
    if 'classes' in data and 'nodes' not in data:
        print("📊 Auto-generating example instances from schema...")
        data = auto_generate_instances(data)
    elif 'examples' in data:
        # Use provided examples section
        data = {
            'name': data.get('name', 'Example Graph'),
            'nodes': data['examples'].get('nodes', []),
            'edges': data['examples'].get('edges', [])
        }
    
    puml = generate_plantuml(data)
    
    puml_file = f'{output_base}.puml'
    with open(puml_file, 'w') as f:
        f.write(puml)
    print(f'✅ Generated: {puml_file}')
    
    return puml_file, output_base


if __name__ == '__main__':
    main()
