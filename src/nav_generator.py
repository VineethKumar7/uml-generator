#!/usr/bin/env python3
"""
UWE Navigation Model Generator
Generates PlantUML navigation diagrams from YAML definitions
"""

import yaml
import sys
import os

def sanitize_name(name):
    """Convert name to valid PlantUML identifier"""
    return name.replace(' ', '_').replace('-', '_')


def generate_nav_plantuml(data):
    """Generate PlantUML for UWE Navigation Model"""
    
    lines = ['@startuml']
    
    # Skinparams for UWE look
    lines.append('skinparam backgroundColor white')
    lines.append('skinparam defaultFontName Arial')
    lines.append('skinparam defaultFontSize 11')
    lines.append('skinparam dpi 150')
    lines.append('skinparam padding 2')
    lines.append('skinparam nodesep 60')
    lines.append('skinparam ranksep 50')
    lines.append('')
    
    # Class styling by stereotype
    lines.append('skinparam class {')
    lines.append('  BackgroundColor #FFFFCC')
    lines.append('  BorderColor #333333')
    lines.append('  FontSize 12')
    lines.append('}')
    lines.append('')
    
    # Color coding by stereotype (matching FRS diagram)
    lines.append('skinparam stereotypeCBackgroundColor<<navigationClass>> #FFFFCC')
    lines.append('skinparam stereotypeCBackgroundColor<<menu>> #FFFFCC')
    lines.append('skinparam stereotypeCBackgroundColor<<index>> #90EE90')
    lines.append('skinparam stereotypeCBackgroundColor<<query>> #90EE90')
    lines.append('skinparam stereotypeCBackgroundColor<<processClass>> #FFB6C1')
    lines.append('skinparam stereotypeCBackgroundColor<<guidedTour>> #E6E6FA')
    lines.append('skinparam stereotypeCBackgroundColor<<externalNode>> #FFA500')
    lines.append('')
    
    # Package frame
    name = data.get('name', 'Navigation Model')
    lines.append(f'package "pkg {name}" {{')
    lines.append('')
    
    # Entry point
    entry_point = data.get('entryPoint')
    
    # Generate nodes
    pages = data.get('pages', {})
    menus = data.get('menus', {})
    indexes = data.get('indexes', {})
    queries = data.get('queries', {})
    processes = data.get('processes', {})
    
    # NavigationClass nodes (pages)
    for page_name, page_data in pages.items():
        page_data = page_data or {}
        is_home = page_data.get('isHome', False)
        is_landmark = page_data.get('isLandmark', False)
        alias = sanitize_name(page_name)
        
        # Tags
        tags = []
        if is_home:
            tags.append('{isHome}')
        if is_landmark:
            tags.append('{isLandmark}')
        tags_str = ' '.join(tags)
        
        lines.append(f'class "{page_name}" as {alias} <<navigationClass>> {{')
        
        # Attributes
        attrs = page_data.get('attributes', [])
        if attrs:
            for attr in attrs:
                if isinstance(attr, dict):
                    for attr_name, attr_type in attr.items():
                        # Check for domain reference (●)
                        domain_ref = page_data.get('domainRef')
                        prefix = '●' if domain_ref else ''
                        lines.append(f'  {prefix}- {attr_name} : {attr_type}')
                else:
                    lines.append(f'  - {attr}')
        
        lines.append('}')
        
        # Entry point marker
        if page_name == entry_point or is_home:
            lines.append(f'note top of {alias} : ● □')
        
        lines.append('')
    
    # Menu nodes
    for menu_name, menu_data in menus.items():
        menu_data = menu_data or {}
        is_landmark = menu_data.get('isLandmark', False)
        alias = sanitize_name(menu_name)
        
        lines.append(f'class "{menu_name}" as {alias} <<menu>> {{')
        lines.append('}')
        
        if is_landmark:
            lines.append(f'note right of {alias} : {{isLandmark}}')
        
        lines.append('')
    
    # Index nodes
    for index_name, index_data in indexes.items():
        index_data = index_data or {}
        alias = sanitize_name(index_name)
        
        lines.append(f'class "{index_name}" as {alias} <<index>> {{')
        
        # Attributes with domain reference
        attrs = index_data.get('attributes', [])
        ref = index_data.get('ref', '')  # e.g., "items: Item[*]"
        
        if ref:
            lines.append(f'  ●- {ref}')
        
        for attr in attrs:
            if isinstance(attr, dict):
                for attr_name, attr_type in attr.items():
                    lines.append(f'  - {attr_name} : {attr_type}')
            else:
                lines.append(f'  - {attr}')
        
        lines.append('}')
        lines.append('')
    
    # Query nodes
    for query_name, query_data in queries.items():
        query_data = query_data or {}
        alias = sanitize_name(query_name)
        
        lines.append(f'class "{query_name}" as {alias} <<query>> {{')
        
        attrs = query_data.get('attributes', [])
        for attr in attrs:
            if isinstance(attr, dict):
                for attr_name, attr_type in attr.items():
                    lines.append(f'  - {attr_name} : {attr_type}')
            else:
                lines.append(f'  - {attr}')
        
        lines.append('}')
        lines.append('')
    
    # Process nodes
    for proc_name, proc_data in processes.items():
        proc_data = proc_data or {}
        alias = sanitize_name(proc_name)
        
        lines.append(f'class "{proc_name}" as {alias} <<processClass>> {{')
        
        attrs = proc_data.get('attributes', [])
        for attr in attrs:
            if isinstance(attr, dict):
                for attr_name, attr_type in attr.items():
                    lines.append(f'  - {attr_name} : {attr_type}')
            else:
                lines.append(f'  - {attr}')
        
        lines.append('}')
        lines.append('')
    
    # Generate links
    links = data.get('links', [])
    for link in links:
        from_node = sanitize_name(link.get('from', ''))
        to_node = sanitize_name(link.get('to', ''))
        link_name = link.get('name', '')
        link_type = link.get('type', 'navigation')  # navigation, process, containment
        condition = link.get('condition', '')
        
        # Build arrow
        if link_type == 'containment':
            # Composition arrow (diamond)
            arrow = '*-->'
        elif link_type == 'process':
            # Process link (solid with stereotype label)
            arrow = '-->'
        else:
            # Navigation link (solid)
            arrow = '-->'
        
        # Build label
        labels = []
        if link_type == 'process':
            labels.append('<<processlink>>')
        if condition:
            labels.append(f'{{{condition}}}')
        if link_name:
            labels.append(f'- {link_name}')
        
        label_str = ' '.join(labels)
        
        if label_str:
            lines.append(f'{from_node} {arrow} {to_node} : {label_str}')
        else:
            lines.append(f'{from_node} {arrow} {to_node}')
    
    lines.append('')
    lines.append('}')  # end package
    lines.append('@enduml')
    
    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: nav_generator.py <model.yaml> [-o output_base]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_base = None
    
    # Parse args
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] in ['-o', '--output']:
            output_base = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    if not output_base:
        output_base = os.path.splitext(input_file)[0]
    
    # Load YAML
    with open(input_file, 'r') as f:
        data = yaml.safe_load(f)
    
    # Generate PlantUML
    puml = generate_nav_plantuml(data)
    
    # Write output
    puml_file = f'{output_base}.puml'
    with open(puml_file, 'w') as f:
        f.write(puml)
    
    print(f'Generated: {puml_file}')


if __name__ == '__main__':
    main()
