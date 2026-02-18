#!/usr/bin/env python3
"""
UWE Navigation Model SVG Generator - Graphviz Layout Edition
Uses Graphviz for optimal node placement and edge routing
"""

import yaml
import sys
import os
import subprocess
import tempfile
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

@dataclass
class Config:
    font_family: str = "Arial, Helvetica, sans-serif"
    font_size: int = 12
    font_size_stereotype: int = 10
    font_size_title: int = 13
    
    colors: Dict[str, str] = field(default_factory=lambda: {
        'navigationclass': '#FFFFCC',
        'menu': '#FFFFCC', 
        'index': '#CCFFCC',
        'query': '#CCFFCC',
        'processclass': '#FFCCCC',
        'guidedtour': '#E6E6FA',
        'externalnode': '#FFE4B5',
        'default': '#FFFFCC'
    })
    
    box_min_width: int = 120
    box_padding_x: int = 10
    box_padding_y: int = 6
    header_height: int = 40
    attr_line_height: int = 18
    
    margin: int = 100  # Larger margin to prevent label cutoff
    scale: float = 72.0  # Graphviz uses 72 DPI
    
    entry_circle_radius: int = 5
    entry_square_size: int = 8
    
    line_color: str = '#000000'
    line_width: float = 1.2


@dataclass
class Box:
    id: str
    name: str
    stereotype: str
    attributes: List[str] = field(default_factory=list)
    is_entry: bool = False
    is_landmark: bool = False
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0


@dataclass 
class Link:
    from_id: str
    to_id: str
    name: str = ""
    link_type: str = "navigation"
    condition: str = ""
    # Graphviz edge points
    points: List[Tuple[float, float]] = field(default_factory=list)
    label_x: float = 0
    label_y: float = 0


def estimate_text_width(text: str, font_size: int) -> float:
    return len(text) * font_size * 0.6


class GraphvizSVGGenerator:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.boxes: Dict[str, Box] = {}
        self.links: List[Link] = []
        self.graph_width = 0
        self.graph_height = 0
        
    def parse_yaml(self, data: dict) -> None:
        entry_point = data.get('entryPoint', '')
        
        for name, page_data in data.get('pages', {}).items():
            page_data = page_data or {}
            attrs = self._parse_attributes(page_data.get('attributes', []))
            is_home = page_data.get('isHome', False)
            
            self.boxes[name] = Box(
                id=name, name=name, stereotype='navigationclass',
                attributes=attrs, is_entry=(name == entry_point) or is_home,
                is_landmark=page_data.get('isLandmark', False)
            )
        
        for name, menu_data in data.get('menus', {}).items():
            menu_data = menu_data or {}
            self.boxes[name] = Box(id=name, name=name, stereotype='menu',
                                   is_landmark=menu_data.get('isLandmark', False))
        
        for name, index_data in data.get('indexes', {}).items():
            index_data = index_data or {}
            attrs = self._parse_attributes(index_data.get('attributes', []))
            if index_data.get('ref'):
                attrs.insert(0, f"●- {index_data['ref']}")
            self.boxes[name] = Box(id=name, name=name, stereotype='index', attributes=attrs)
        
        for name, query_data in data.get('queries', {}).items():
            query_data = query_data or {}
            attrs = self._parse_attributes(query_data.get('attributes', []))
            self.boxes[name] = Box(id=name, name=name, stereotype='query', attributes=attrs)
        
        for name, proc_data in data.get('processes', {}).items():
            proc_data = proc_data or {}
            attrs = self._parse_attributes(proc_data.get('attributes', []))
            self.boxes[name] = Box(id=name, name=name, stereotype='processclass', attributes=attrs)
        
        for link_data in data.get('links', []):
            self.links.append(Link(
                from_id=link_data.get('from', ''),
                to_id=link_data.get('to', ''),
                name=link_data.get('name', ''),
                link_type=link_data.get('type', 'navigation'),
                condition=link_data.get('condition', '')
            ))
    
    def _parse_attributes(self, attrs: list) -> List[str]:
        result = []
        for attr in attrs:
            if isinstance(attr, dict):
                for k, v in attr.items():
                    result.append(f"- {k} : {v}")
            else:
                result.append(f"- {attr}")
        return result
    
    def _calculate_box_dimensions(self):
        """Calculate box dimensions based on content"""
        cfg = self.config
        for box in self.boxes.values():
            stereo_width = estimate_text_width(f"<<{box.stereotype}>>", cfg.font_size_stereotype)
            name_width = estimate_text_width(box.name, cfg.font_size_title)
            attr_widths = [estimate_text_width(a, cfg.font_size) for a in box.attributes]
            
            content_width = max([stereo_width, name_width] + (attr_widths or [0]))
            box.width = max(cfg.box_min_width, content_width + cfg.box_padding_x * 2)
            box.height = cfg.header_height
            if box.attributes:
                box.height += len(box.attributes) * cfg.attr_line_height + cfg.box_padding_y
    
    def _generate_dot(self) -> str:
        """Generate Graphviz DOT format with icon spacers as invisible nodes"""
        lines = ['digraph G {']
        lines.append('  rankdir=TB;')  # Top to bottom
        lines.append('  splines=polyline;')  # Polyline edges (more robust than ortho)
        lines.append('  nodesep=1.0;')  # Increased horizontal separation
        lines.append('  ranksep=1.2;')  # Increased vertical separation for labels
        lines.append('  node [shape=box];')
        lines.append('')
        
        # Icon spacer dimensions (invisible nodes above each box)
        icon_w = 30 / self.config.scale
        icon_h = 25 / self.config.scale
        
        # Main nodes with sizes (include extra top margin for icon)
        for box in self.boxes.values():
            w_inch = box.width / self.config.scale
            h_inch = box.height / self.config.scale
            lines.append(f'  "{box.id}" [width={w_inch:.2f}, height={h_inch:.2f}, fixedsize=true];')
            # Add invisible icon spacer node above each box
            lines.append(f'  "{box.id}_icon" [width={icon_w:.2f}, height={icon_h:.2f}, fixedsize=true, style=invis];')
        
        lines.append('')
        
        # Calculate label sizes for each edge
        label_nodes = []
        for i, link in enumerate(self.links):
            label_parts = []
            if link.link_type == 'process':
                label_parts.append('<<processlink>>')
            if link.condition:
                label_parts.append(f'{{{link.condition}}}')
            if link.name:
                label_parts.append(f'- {link.name}')
            
            if label_parts:
                label_text = ' '.join(label_parts)
                label_w = (len(label_text) * 7 + 10) / self.config.scale
                label_h = 18 / self.config.scale
                label_node_id = f"label_e{i}"
                lines.append(f'  "{label_node_id}" [width={label_w:.2f}, height={label_h:.2f}, fixedsize=true, style=invis];')
                label_nodes.append((i, label_node_id, link.from_id, link.to_id))
        
        lines.append('')
        
        # Constraints: icon nodes same rank as their boxes (but positioned by Graphviz)
        # Use invisible edges to keep icons near their boxes
        for box in self.boxes.values():
            lines.append(f'  "{box.id}_icon" -> "{box.id}" [style=invis, weight=100];')
        
        lines.append('')
        
        # Real edges - route through label nodes where applicable
        label_edge_map = {ln[0]: ln[1] for ln in label_nodes}
        
        for i, link in enumerate(self.links):
            if i in label_edge_map:
                # Edge with label: from -> label_node -> to
                label_id = label_edge_map[i]
                lines.append(f'  "{link.from_id}" -> "{label_id}" [id="e{i}a", arrowhead=none];')
                lines.append(f'  "{label_id}" -> "{link.to_id}" [id="e{i}b"];')
            else:
                # Edge without label
                lines.append(f'  "{link.from_id}" -> "{link.to_id}" [id="e{i}"];')
        
        lines.append('}')
        return '\n'.join(lines)
    
    def _run_graphviz(self, dot_content: str) -> str:
        """Run Graphviz and get plain output with positions"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dot', delete=False) as f:
            f.write(dot_content)
            dot_file = f.name
        
        try:
            # Run dot with plain output format
            result = subprocess.run(
                ['dot', '-Tplain', dot_file],
                capture_output=True, text=True, check=True
            )
            return result.stdout
        finally:
            os.unlink(dot_file)
    
    def _parse_plain_output(self, plain: str):
        """Parse Graphviz plain output to get positions including icon and label nodes"""
        lines = plain.strip().split('\n')
        
        # Store positions for special nodes
        self.icon_positions: Dict[str, Tuple[float, float]] = {}
        self.label_positions: Dict[str, Tuple[float, float]] = {}
        
        # Store partial edge paths (for edges split through label nodes)
        edge_parts: Dict[str, List[Tuple[float, float]]] = {}
        
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            
            if parts[0] == 'graph':
                # graph scale width height
                self.graph_width = float(parts[2]) * self.config.scale
                self.graph_height = float(parts[3]) * self.config.scale
            
            elif parts[0] == 'node':
                # node name x y width height label style shape color fillcolor
                node_id = parts[1].strip('"')
                x = float(parts[2]) * self.config.scale
                y = self.graph_height - float(parts[3]) * self.config.scale
                
                if node_id in self.boxes:
                    # Main box node
                    self.boxes[node_id].x = x - self.boxes[node_id].width / 2
                    self.boxes[node_id].y = y - self.boxes[node_id].height / 2
                elif node_id.endswith('_icon'):
                    # Icon spacer node
                    box_id = node_id[:-5]  # Remove '_icon' suffix
                    self.icon_positions[box_id] = (x, y)
                elif node_id.startswith('label_e'):
                    # Label node - extract edge index
                    self.label_positions[node_id] = (x, y)
            
            elif parts[0] == 'edge':
                # edge tail head n x1 y1 x2 y2 ... [label lx ly] style color
                tail = parts[1].strip('"')
                head = parts[2].strip('"')
                n_points = int(parts[3])
                
                # Parse edge points
                points = []
                for i in range(n_points):
                    px = float(parts[4 + i*2]) * self.config.scale
                    py = self.graph_height - float(parts[5 + i*2]) * self.config.scale
                    points.append((px, py))
                
                # Check if this is a split edge (through label node)
                if head.startswith('label_e'):
                    # First half: from -> label
                    edge_idx = head[7:]  # Extract index after 'label_e'
                    if edge_idx.endswith('a'):
                        edge_idx = edge_idx[:-1]
                    edge_parts[f"{edge_idx}_a"] = points
                elif tail.startswith('label_e'):
                    # Second half: label -> to
                    edge_idx = tail[7:]
                    if edge_idx.endswith('b'):
                        edge_idx = edge_idx[:-1]
                    edge_parts[f"{edge_idx}_b"] = points
                else:
                    # Direct edge (no label node)
                    for link in self.links:
                        if link.from_id == tail and link.to_id == head and not link.points:
                            link.points = points
                            # Calculate label position at midpoint
                            if points:
                                mid_idx = len(points) // 2
                                link.label_x = points[mid_idx][0]
                                link.label_y = points[mid_idx][1]
                            break
        
        # Combine split edges and assign label positions
        for i, link in enumerate(self.links):
            label_node_id = f"label_e{i}"
            if label_node_id in self.label_positions:
                # This edge was split through a label node
                part_a = edge_parts.get(f"{i}_a", [])
                part_b = edge_parts.get(f"{i}_b", [])
                
                # Combine paths (skip duplicate middle point)
                if part_a and part_b:
                    link.points = part_a + part_b[1:] if part_b else part_a
                elif part_a:
                    link.points = part_a
                elif part_b:
                    link.points = part_b
                
                # Label position is the label node position
                lx, ly = self.label_positions[label_node_id]
                link.label_x = lx
                link.label_y = ly
    
    def calculate_layout(self):
        """Use Graphviz for layout"""
        self._calculate_box_dimensions()
        dot = self._generate_dot()
        plain = self._run_graphviz(dot)
        self._parse_plain_output(plain)
        
        # Calculate bounding box including ALL elements (boxes + edge points + labels)
        all_x = []
        all_y = []
        
        # Include box positions
        for box in self.boxes.values():
            all_x.extend([box.x, box.x + box.width])
            all_y.extend([box.y - 20, box.y + box.height])  # -20 for icon above
        
        # Include edge routing points
        for link in self.links:
            for px, py in link.points:
                all_x.append(px)
                all_y.append(py)
            # Include label position
            if link.label_x and link.label_y:
                all_x.append(link.label_x)
                all_y.append(link.label_y)
        
        if not all_x or not all_y:
            return 400, 300  # Default size
        
        min_x = min(all_x)
        min_y = min(all_y)
        max_x_raw = max(all_x)
        max_y_raw = max(all_y)
        
        # Add margins - offset everything so minimum is at margin
        offset_x = self.config.margin - min_x
        offset_y = self.config.margin + 40 - min_y  # Extra for entry point
        
        for box in self.boxes.values():
            box.x += offset_x
            box.y += offset_y
        
        for link in self.links:
            link.points = [(p[0] + offset_x, p[1] + offset_y) for p in link.points]
            link.label_x += offset_x
            link.label_y += offset_y
        
        # Calculate total dimensions (including edge points now)
        max_x = max_x_raw + offset_x + self.config.margin
        max_y = max_y_raw + offset_y + self.config.margin
        
        return max_x, max_y
    
    def generate_svg(self, title: str = "Navigation Model") -> str:
        width, height = self.calculate_layout()
        cfg = self.config
        
        # Package frame
        pkg_label = f"pkg {title}"
        pkg_tab_width = estimate_text_width(pkg_label, 12) + 20
        pkg_tab_height = 25
        pkg_padding = 15
        
        total_width = width + pkg_padding * 2
        total_height = height + pkg_tab_height + pkg_padding
        
        svg = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{total_height}">',
            f'  <defs>',
            f'    <!-- Open/unfilled arrowhead (UWE standard) -->',
            f'    <marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="strokeWidth">',
            f'      <path d="M0,0 L10,6 L0,12" fill="none" stroke="{cfg.line_color}" stroke-width="1.5"/>',
            f'    </marker>',
            f'    <!-- Filled diamond for containment -->',
            f'    <marker id="diamond" markerWidth="12" markerHeight="12" refX="0" refY="6" orient="auto" markerUnits="strokeWidth">',
            f'      <path d="M0,6 L6,0 L12,6 L6,12 z" fill="{cfg.line_color}"/>',
            f'    </marker>',
            f'  </defs>',
            f'  <style>',
            f'    text {{ font-family: {cfg.font_family}; }}',
            f'    .stereotype {{ font-size: {cfg.font_size_stereotype}px; fill: #333; }}',
            f'    .classname {{ font-size: {cfg.font_size_title}px; font-weight: bold; }}',
            f'    .attribute {{ font-size: {cfg.font_size}px; fill: #333; }}',
            f'    .link-label {{ font-size: 11px; fill: #000; }}',
            f'  </style>',
            f'  <rect width="100%" height="100%" fill="white"/>',
        ]
        
        # Package frame
        frame_x = pkg_padding
        frame_y = pkg_padding
        
        svg.append(f'  <rect x="{frame_x}" y="{frame_y + pkg_tab_height}" '
                   f'width="{width}" height="{height}" fill="none" stroke="{cfg.line_color}"/>')
        svg.append(f'  <path d="M{frame_x},{frame_y + pkg_tab_height} L{frame_x},{frame_y} '
                   f'L{frame_x + pkg_tab_width},{frame_y} L{frame_x + pkg_tab_width + 10},{frame_y + pkg_tab_height}" '
                   f'fill="none" stroke="{cfg.line_color}"/>')
        svg.append(f'  <text x="{frame_x + 10}" y="{frame_y + 17}" font-size="12" font-weight="bold">{pkg_label}</text>')
        
        # Offset for content
        for box in self.boxes.values():
            box.x += pkg_padding
            box.y += pkg_tab_height
        for link in self.links:
            link.points = [(p[0] + pkg_padding, p[1] + pkg_tab_height) for p in link.points]
            link.label_x += pkg_padding
            link.label_y += pkg_tab_height
        
        # Draw links
        for link in self.links:
            svg.append(self._render_link(link))
        
        # Draw boxes
        for box in self.boxes.values():
            svg.append(self._render_box(box))
        
        svg.append('</svg>')
        return '\n'.join(svg)
    
    def _render_box(self, box: Box) -> str:
        cfg = self.config
        color = cfg.colors.get(box.stereotype, cfg.colors['default'])
        
        elements = [f'  <g id="{box.id}">']
        elements.append(f'    <rect x="{box.x}" y="{box.y}" width="{box.width}" height="{box.height}" '
                       f'fill="{color}" stroke="{cfg.line_color}"/>')
        
        stereo_y = box.y + cfg.box_padding_y + cfg.font_size_stereotype
        elements.append(f'    <text class="stereotype" x="{box.x + box.width/2}" y="{stereo_y}" '
                       f'text-anchor="middle">&lt;&lt;{box.stereotype}&gt;&gt;</text>')
        
        name_y = stereo_y + cfg.font_size_title + 3
        elements.append(f'    <text class="classname" x="{box.x + box.width/2}" y="{name_y}" '
                       f'text-anchor="middle">{box.name}</text>')
        
        if box.attributes:
            sep_y = box.y + cfg.header_height
            elements.append(f'    <line x1="{box.x}" y1="{sep_y}" x2="{box.x + box.width}" y2="{sep_y}" stroke="{cfg.line_color}"/>')
            attr_y = sep_y + cfg.box_padding_y + cfg.font_size
            for attr in box.attributes:
                attr_esc = attr.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                elements.append(f'    <text class="attribute" x="{box.x + cfg.box_padding_x}" y="{attr_y}">{attr_esc}</text>')
                attr_y += cfg.attr_line_height
        
        # Entry point marker
        # Stereotype icon at top-right corner OUTSIDE the box (like entry point)
        icon_size = 14
        icon_x = box.x + box.width - icon_size - 4
        icon_y = box.y - icon_size - 4
        elements.append(self._draw_stereotype_icon(box.stereotype, icon_x, icon_y, icon_size))
        
        # Entry point marker (● □) - positioned to the LEFT of the stereotype icon
        if box.is_entry:
            sq = cfg.entry_square_size
            cr = cfg.entry_circle_radius
            mx = icon_x - sq - cr - 10  # Left of the stereotype icon
            my = icon_y + (icon_size - sq) / 2  # Vertically centered with icon
            elements.append(f'    <circle cx="{mx + cr}" cy="{my + sq/2}" r="{cr}" fill="{cfg.line_color}"/>')
            elements.append(f'    <line x1="{mx + cr*2}" y1="{my + sq/2}" x2="{mx + cr*2 + 4}" y2="{my + sq/2}" stroke="{cfg.line_color}" stroke-width="1.5"/>')
            elements.append(f'    <rect x="{mx + cr*2 + 4}" y="{my}" width="{sq}" height="{sq}" fill="white" stroke="{cfg.line_color}" stroke-width="1.5"/>')
        
        elements.append('  </g>')
        return '\n'.join(elements)
    
    def _find_label_position(self, points: List[Tuple[float, float]], label: str) -> Tuple[float, float]:
        """Find a position along the edge that doesn't overlap with icons, boxes, or other elements"""
        if len(points) < 2:
            return (0, 0)
        
        # Try different positions along the path (25%, 50%, 75%)
        positions_to_try = [0.5, 0.35, 0.65, 0.25, 0.75, 0.15, 0.85]
        
        label_width = len(label) * 7  # Approximate width (slightly larger estimate)
        label_height = 16
        
        def check_box_overlap(lx: float, ly: float) -> bool:
            """Check if label rectangle overlaps with any box"""
            # Label rectangle (text is anchored at baseline, so box extends upward)
            label_left = lx
            label_right = lx + label_width
            label_top = ly - label_height
            label_bottom = ly + 4  # Small padding below baseline
            
            for box in self.boxes.values():
                # Check box overlap (with some padding)
                box_left = box.x - 5
                box_right = box.x + box.width + 5
                box_top = box.y - 5
                box_bottom = box.y + box.height + 5
                
                if (label_left < box_right and label_right > box_left and
                    label_top < box_bottom and label_bottom > box_top):
                    return True
                
                # Also check icon area (top-right corner outside box)
                icon_x = box.x + box.width - 20
                icon_y = box.y - 20
                icon_w = 30
                icon_h = 25
                
                if (label_left < icon_x + icon_w and label_right > icon_x and
                    label_top < icon_y + icon_h and label_bottom > icon_y):
                    return True
            
            return False
        
        # Calculate total path length and segment info once
        total_len = 0
        segment_lengths = []
        for i in range(len(points) - 1):
            dx = points[i+1][0] - points[i][0]
            dy = points[i+1][1] - points[i][1]
            seg_len = (dx*dx + dy*dy) ** 0.5
            segment_lengths.append(seg_len)
            total_len += seg_len
        
        if total_len == 0:
            return (points[0][0] + 10, points[0][1] - 15)
        
        # Try different positions and offsets
        offsets_to_try = [
            (0, -12),   # Above
            (10, 0),    # Right
            (-10, 0),   # Left  
            (0, 18),    # Below
            (15, -8),   # Upper-right
            (-15, -8),  # Upper-left
        ]
        
        for ratio in positions_to_try:
            target_len = total_len * ratio
            current_len = 0
            
            for i, seg_len in enumerate(segment_lengths):
                if current_len + seg_len >= target_len:
                    # Interpolate within this segment
                    t = (target_len - current_len) / seg_len if seg_len > 0 else 0
                    px = points[i][0] + t * (points[i+1][0] - points[i][0])
                    py = points[i][1] + t * (points[i+1][1] - points[i][1])
                    
                    # Determine segment direction for smart offset
                    dx = points[i+1][0] - points[i][0]
                    dy = points[i+1][1] - points[i][1]
                    
                    # Order offsets based on segment direction
                    if abs(dx) > abs(dy):
                        # Horizontal segment - prefer above/below
                        ordered_offsets = [(0, -12), (0, 18), (15, -8), (-15, -8), (10, 0), (-10, 0)]
                    else:
                        # Vertical segment - prefer left/right
                        ordered_offsets = [(10, 0), (-10, 0), (15, -8), (-15, -8), (0, -12), (0, 18)]
                    
                    # Try each offset
                    for ox, oy in ordered_offsets:
                        lx = px + ox
                        ly = py + oy
                        
                        if not check_box_overlap(lx, ly):
                            return (lx, ly)
                    
                    break
                current_len += seg_len
        
        # Fallback: place far from all boxes
        # Find the point furthest from any box center
        best_dist = -1
        best_point = (points[len(points)//2][0] + 20, points[len(points)//2][1] - 20)
        
        for ratio in [0.3, 0.5, 0.7]:
            target_len = total_len * ratio
            current_len = 0
            for i, seg_len in enumerate(segment_lengths):
                if current_len + seg_len >= target_len:
                    t = (target_len - current_len) / seg_len if seg_len > 0 else 0
                    px = points[i][0] + t * (points[i+1][0] - points[i][0])
                    py = points[i][1] + t * (points[i+1][1] - points[i][1])
                    
                    # Find min distance to any box
                    min_box_dist = float('inf')
                    for box in self.boxes.values():
                        cx = box.x + box.width / 2
                        cy = box.y + box.height / 2
                        dist = ((px - cx)**2 + (py - cy)**2) ** 0.5
                        min_box_dist = min(min_box_dist, dist)
                    
                    if min_box_dist > best_dist:
                        best_dist = min_box_dist
                        best_point = (px + 15, py - 15)
                    break
                current_len += seg_len
        
        return best_point
    
    def _draw_stereotype_icon(self, stereotype: str, x: float, y: float, size: float) -> str:
        """Draw stereotype icon at given position"""
        s = size
        stroke = self.config.line_color
        
        if stereotype == 'navigationclass':
            # □ Empty square
            return f'    <rect x="{x}" y="{y}" width="{s}" height="{s}" fill="white" stroke="{stroke}" stroke-width="1.2"/>'
        
        elif stereotype == 'menu':
            # ≡ Three horizontal lines (hamburger menu)
            lines = []
            lines.append(f'    <rect x="{x}" y="{y}" width="{s}" height="{s}" fill="white" stroke="{stroke}" stroke-width="1"/>')
            gap = s / 4
            for i in range(3):
                ly = y + gap * (i + 0.75)
                lines.append(f'    <line x1="{x+2}" y1="{ly}" x2="{x+s-2}" y2="{ly}" stroke="{stroke}" stroke-width="1.5"/>')
            return '\n'.join(lines)
        
        elif stereotype == 'index':
            # ≡ Three horizontal lines (same as menu)
            lines = []
            lines.append(f'    <rect x="{x}" y="{y}" width="{s}" height="{s}" fill="white" stroke="{stroke}" stroke-width="1"/>')
            gap = s / 4
            for i in range(3):
                ly = y + gap * (i + 0.75)
                lines.append(f'    <line x1="{x+2}" y1="{ly}" x2="{x+s-2}" y2="{ly}" stroke="{stroke}" stroke-width="1.5"/>')
            return '\n'.join(lines)
        
        elif stereotype == 'query':
            # ? Question mark in box
            return f'''    <rect x="{x}" y="{y}" width="{s}" height="{s}" fill="white" stroke="{stroke}" stroke-width="1"/>
    <text x="{x + s/2}" y="{y + s*0.75}" text-anchor="middle" font-size="{s*0.8}" font-weight="bold">?</text>'''
        
        elif stereotype == 'processclass':
            # ≫ Double chevron
            return f'''    <rect x="{x}" y="{y}" width="{s}" height="{s}" fill="white" stroke="{stroke}" stroke-width="1"/>
    <path d="M{x+2},{y+s*0.2} L{x+s/2},{y+s/2} L{x+2},{y+s*0.8}" fill="none" stroke="{stroke}" stroke-width="1.5"/>
    <path d="M{x+s/2},{y+s*0.2} L{x+s-2},{y+s/2} L{x+s/2},{y+s*0.8}" fill="none" stroke="{stroke}" stroke-width="1.5"/>'''
        
        elif stereotype == 'guidedtour':
            # →| Arrow with bar
            return f'''    <rect x="{x}" y="{y}" width="{s}" height="{s}" fill="white" stroke="{stroke}" stroke-width="1"/>
    <line x1="{x+2}" y1="{y+s/2}" x2="{x+s-4}" y2="{y+s/2}" stroke="{stroke}" stroke-width="1.5"/>
    <path d="M{x+s-6},{y+s*0.3} L{x+s-2},{y+s/2} L{x+s-6},{y+s*0.7}" fill="none" stroke="{stroke}" stroke-width="1.5"/>'''
        
        elif stereotype == 'externalnode':
            # ⇨ Arrow in box pointing out
            return f'''    <rect x="{x}" y="{y}" width="{s}" height="{s}" fill="white" stroke="{stroke}" stroke-width="1"/>
    <line x1="{x+3}" y1="{y+s/2}" x2="{x+s-3}" y2="{y+s/2}" stroke="{stroke}" stroke-width="1.5"/>
    <path d="M{x+s-6},{y+s*0.3} L{x+s-2},{y+s/2} L{x+s-6},{y+s*0.7}" fill="none" stroke="{stroke}" stroke-width="1.5"/>'''
        
        else:
            # Default: empty square
            return f'    <rect x="{x}" y="{y}" width="{s}" height="{s}" fill="white" stroke="{stroke}" stroke-width="1"/>'
    
    def _extend_to_box(self, px, py, box) -> Tuple[float, float]:
        """Extend a point to the nearest edge of a box"""
        # Find which edge is closest
        dist_top = abs(py - box.y)
        dist_bottom = abs(py - (box.y + box.height))
        dist_left = abs(px - box.x)
        dist_right = abs(px - (box.x + box.width))
        
        min_dist = min(dist_top, dist_bottom, dist_left, dist_right)
        
        if min_dist == dist_top:
            return px, box.y
        elif min_dist == dist_bottom:
            return px, box.y + box.height
        elif min_dist == dist_left:
            return box.x, py
        else:
            return box.x + box.width, py
    
    def _render_link(self, link: Link) -> str:
        cfg = self.config
        
        if not link.points or len(link.points) < 2:
            return ''
        
        from_box = self.boxes.get(link.from_id)
        to_box = self.boxes.get(link.to_id)
        
        # Copy points and extend to box edges
        points = list(link.points)
        if from_box:
            points[0] = self._extend_to_box(points[0][0], points[0][1], from_box)
        if to_box:
            points[-1] = self._extend_to_box(points[-1][0], points[-1][1], to_box)
        
        elements = [f'  <g class="link">']
        
        # Build path from points
        path_parts = [f"M{points[0][0]},{points[0][1]}"]
        for p in points[1:]:
            path_parts.append(f"L{p[0]},{p[1]}")
        path = " ".join(path_parts)
        
        if link.link_type == 'containment':
            elements.append(f'    <path d="{path}" fill="none" stroke="{cfg.line_color}" '
                           f'stroke-width="{cfg.line_width}" marker-start="url(#diamond)" marker-end="url(#arrow)"/>')
        else:
            elements.append(f'    <path d="{path}" fill="none" stroke="{cfg.line_color}" '
                           f'stroke-width="{cfg.line_width}" marker-end="url(#arrow)"/>')
        
        # Label - use Graphviz-calculated position from label nodes
        label_parts = []
        if link.link_type == 'process':
            label_parts.append('&lt;&lt;processlink&gt;&gt;')
        if link.condition:
            label_parts.append(f'{{{link.condition}}}')
        if link.name:
            label_parts.append(f'- {link.name}')
        
        if label_parts:
            label = ' '.join(label_parts)
            # Use pre-calculated position (set by Graphviz via label node)
            lx = link.label_x
            ly = link.label_y
            elements.append(f'    <text class="link-label" x="{lx}" y="{ly}">{label}</text>')
        
        elements.append('  </g>')
        return '\n'.join(elements)


def main():
    if len(sys.argv) < 2:
        print("Usage: nav_svg_graphviz.py <model.yaml> [-o output_base]")
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
    
    generator = GraphvizSVGGenerator()
    generator.parse_yaml(data)
    
    title = data.get('name', 'Navigation Model')
    svg = generator.generate_svg(title)
    
    with open(f'{output_base}.svg', 'w') as f:
        f.write(svg)
    
    print(f'Generated: {output_base}.svg')


if __name__ == '__main__':
    main()
