#!/usr/bin/env python3
"""
Graph Instance (Example Graph) Generator
Creates instance diagrams showing actual data values

Format:
- Labels with colon prefix: :Person
- Properties with equals: name = John
- Plain lines (no arrowheads) with relationship names
"""

import yaml
import sys
import os

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
    
    puml = generate_plantuml(data)
    
    puml_file = f'{output_base}.puml'
    with open(puml_file, 'w') as f:
        f.write(puml)
    print(f'✅ Generated: {puml_file}')
    
    return puml_file, output_base


if __name__ == '__main__':
    main()
