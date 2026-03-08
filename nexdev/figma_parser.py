#!/usr/bin/env python3
"""
NexDev v3.0 - Track B: Ecosystem
Figma Mockup Parser

Extract technical specifications from Figma mockup screenshots
Detects: component trees, interaction flows, responsive breakpoints, style guide
"""

import json
import requests
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ComponentSpec:
    name: str
    type: str  # button, input, card, modal, etc.
    position: Dict  # x, y, width, height
    styles: Dict  # colors, fonts, spacing
    interactions: List[Dict]  # clicks, hovers, states
    children: List['ComponentSpec'] = None


@dataclass
class ScreenSpec:
    name: str
    width: int
    height: int
    components: List[ComponentSpec]
    breakpoints: List[Dict]
    assets: List[Dict]


@dataclass
class DesignSpec:
    screen_count: int
    screens: List[ScreenSpec]
    design_system: Dict  # colors, typography, spacing
    user_flows: List[Dict]
    requirements: List[str]
    generated_at: str


class FigmaParser:
    """Extract technical specs from Figma designs"""
    
    # Figma API endpoints
    FIGMA_API_BASE = "https://api.figma.com/v1"
    
    # Component type detection patterns
    COMPONENT_PATTERNS = {
        'button': ['btn', 'button', 'action', 'submit', 'clickable'],
        'input': ['input', 'text field', 'textfield', 'form', 'search'],
        'card': ['card', 'container', 'panel', 'box'],
        'modal': ['modal', 'dialog', 'popup', 'overlay'],
        'navigation': ['nav', 'menu', 'sidebar', 'header', 'footer'],
        'image': ['image', 'photo', 'avatar', 'logo', 'icon'],
        'text': ['text', 'label', 'heading', 'title', 'paragraph'],
        'list': ['list', 'table', 'grid', 'repeater'],
        'form': ['form', 'checkout', 'signup', 'login']
    }
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.cache_dir = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'figma_cache'
        self.specs_dir = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'generated_specs'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.specs_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        default_config = {
            'figma': {
                'api_token': '',
                'default_file_key': '',
                'export_format': 'png'
            },
            'detection': {
                'min_confidence': 0.7,
                'detect_interactions': True,
                'detect_responsiveness': True,
                'extract_design_tokens': True
            },
            'output': {
                'format': 'markdown',  # markdown, json, prd
                'include_mockup_references': True,
                'generate_user_stories': True
            },
            'framework': {
                'preferred': 'react',  # react, vue, angular, svelte
                'ui_library': 'tailwind'  # tailwind, material, bootstrap, chakra
            }
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path) as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception:
                pass
                
        return default_config
        
    async def parse_figma_file(self, file_key: str, node_ids: List[str] = None) -> DesignSpec:
        """
        Parse entire Figma file into technical specification
        
        Args:
            file_key: Figma file key (from URL)
            node_ids: Specific nodes to parse (defaults to all)
            
        Returns:
            Complete design specification
        """
        api_token = self.config['figma']['api_token']
        
        if not api_token:
            raise ValueError("Figma API token not configured")
            
        headers = {
            'X-Figma-Token': api_token,
            'Content-Type': 'application/json'
        }
        
        # Fetch file structure
        if not node_ids:
            response = requests.get(
                f"{self.FIGMA_API_BASE}/files/{file_key}",
                headers=headers,
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"Figma API error: {response.status_code} {response.text}")
                
            file_data = response.json()
            root_node = file_data['document']
        else:
            # Fetch specific nodes
            node_id_str = ','.join(node_ids)
            response = requests.get(
                f"{self.FIGMA_API_BASE}/files/{file_key}?ids={node_id_str}",
                headers=headers,
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"Figma API error: {response.status_code}")
                
            file_data = response.json()
            root_node = list(file_data['documents'].values())[0]
            
        # Extract design system tokens
        design_system = self._extract_design_system(root_node)
        
        # Parse all screens/pages
        screens = []
        for child in root_node.get('children', []):
            screen_spec = self._parse_node(child, depth=0)
            if screen_spec:
                screens.append(screen_spec)
                
        # Generate user flows from navigation patterns
        user_flows = self._extract_user_flows(screens)
        
        # Convert to requirements
        requirements = self._generate_requirements(screens, design_system)
        
        return DesignSpec(
            screen_count=len(screens),
            screens=screens,
            design_system=design_system,
            user_flows=user_flows,
            requirements=requirements,
            generated_at=datetime.now().isoformat()
        )
        
    def _parse_node(self, node: Dict, depth: int = 0) -> Optional[ScreenSpec]:
        """Parse a Figma node into component spec"""
        # Skip hidden or very small elements
        if node.get('hidden', False):
            return None
            
        node_type = node.get('type', '')
        name = node.get('name', '')
        
        # Detect screen/page
        if node_type in ['CANVAS', 'FRAME'] and depth == 0:
            # This is a screen/frame
            components = []
            assets = []
            
            for child in node.get('children', []):
                component = self._parse_component(child, depth + 1)
                if component:
                    if component.type == 'asset':
                        assets.append(component)
                    else:
                        components.append(component)
                        
            # Detect breakpoints based on frame variants
            breakpoints = self._detect_breakpoints(node)
            
            return ScreenSpec(
                name=name,
                width=node.get('absoluteBoundingBox', {}).get('width', 1440),
                height=node.get('absoluteBoundingBox', {}).get('height', 900),
                components=components,
                breakpoints=breakpoints,
                assets=assets
            )
        else:
            return None
            
    def _parse_component(self, node: Dict, depth: int) -> ComponentSpec:
        """Parse a single component"""
        comp_type = self._detect_component_type(node)
        
        # Get positioning
        bbox = node.get('absoluteBoundingBox', {})
        position = {
            'x': bbox.get('x', 0),
            'y': bbox.get('y', 0),
            'width': bbox.get('width', 0),
            'height': bbox.get('height', 0)
        }
        
        # Extract styles
        styles = self._extract_styles(node)
        
        # Detect interactions
        interactions = []
        if self.config['detection']['detect_interactions']:
            interactions = self._detect_interactions(node)
            
        # Recursively parse children
        children = []
        for child in node.get('children', []):
            child_comp = self._parse_component(child, depth + 1)
            if child_comp and child_comp.type != 'asset':
                children.append(child_comp)
                
        return ComponentSpec(
            name=node.get('name', 'Unnamed'),
            type=comp_type,
            position=position,
            styles=styles,
            interactions=interactions,
            children=children if children else None
        )
        
    def _detect_component_type(self, node: Dict) -> str:
        """Detect component type from name and properties"""
        name = node.get('name', '').lower()
        node_type = node.get('type', '')
        
        # Check for known patterns
        for comp_type, patterns in self.COMPONENT_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in name:
                    return comp_type
                    
        # Heuristic detection based on properties
        if node_type == 'RECTANGLE':
            if node.get('fills') and len(node.get('fills', [])) > 0:
                fill = node['fills'][0]
                if fill.get('type') == 'IMAGE':
                    return 'image'
                    
        if node_type == 'TEXT':
            font_size = node.get('characters', '')
            if len(font_size) < 20:
                return 'text'
                
        # Default
        return 'container'
        
    def _extract_styles(self, node: Dict) -> Dict:
        """Extract visual styles from node"""
        styles = {}
        
        # Colors
        fills = node.get('fills', [])
        if fills:
            fill = fills[0]
            if fill.get('type') == 'SOLID':
                color = fill['color']
                styles['background_color'] = self._rgba_to_hex(
                    color.get('r', 0),
                    color.get('g', 0),
                    color.get('b', 0),
                    color.get('a', 1)
                )
                
        # Typography
        if node.get('type') == 'TEXT':
            styles['font_family'] = node.get('style', {}).get('fontPostScriptName', 'Inter')
            styles['font_size'] = node.get('fontSize', 16)
            styles['font_weight'] = node.get('style', {}).get('fontWeight', 400)
            styles['text_align'] = node.get('textAlignHorizontal', 'LEFT').lower()
            styles['line_height'] = node.get('lineHeight', {})
            
        # Borders
        strokes = node.get('strokes', [])
        if strokes:
            stroke = strokes[0]
            if stroke.get('type') == 'SOLID':
                color = stroke['color']
                styles['border_color'] = self._rgba_to_hex(
                    color.get('r', 0),
                    color.get('g', 0),
                    color.get('b', 0),
                    color.get('a', 1)
                )
                styles['border_width'] = node.get('strokeWeight', 1)
                
        # Effects (shadows, blur)
        effects = node.get('effects', [])
        if effects:
            for effect in effects:
                if effect.get('type') == 'DROP_SHADOW':
                    styles['box_shadow'] = {
                        'blur': effect.get('radius', 0),
                        'offset_x': effect.get('offset', {}).get('x', 0),
                        'offset_y': effect.get('offset', {}).get('y', 0),
                        'color': self._rgba_to_hex(
                            effect.get('color', {}).get('r', 0),
                            effect.get('color', {}).get('g', 0),
                            effect.get('color', {}).get('b', 0),
                            effect.get('color', {}).get('a', 0)
                        )
                    }
                    
        return styles
        
    def _rgba_to_hex(self, r: float, g: float, b: float, a: float = 1.0) -> str:
        """Convert RGBA to hex color"""
        r_int = int(r * 255)
        g_int = int(g * 255)
        b_int = int(b * 255)
        a_int = int(a * 255)
        
        if a_int == 255:
            return f"#{r_int:02x}{g_int:02x}{b_int:02x}"
        else:
            return f"#{r_int:02x}{g_int:02x}{b_int:02x}{a_int:02x}"
            
    def _detect_interactions(self, node: Dict) -> List[Dict]:
        """Detect interactive behaviors"""
        interactions = []
        
        # Check for variant properties
        if node.get('variant'):
            interactions.append({
                'type': 'state_variant',
                'variants': node.get('variant', [])
            })
            
        # Check for component properties
        props = node.get('componentPropertyReferences', {})
        if props:
            interactions.append({
                'type': 'property_binding',
                'properties': list(props.keys())
            })
            
        # Detect hover/click states from naming conventions
        name = node.get('name', '').lower()
        if 'hover' in name or ':hover' in name:
            interactions.append({'type': 'hover_state'})
        if 'active' in name or ':active' in name:
            interactions.append({'type': 'active_state'})
        if 'disabled' in name or ':disabled' in name:
            interactions.append({'type': 'disabled_state'})
            
        return interactions
        
    def _detect_breakpoints(self, node: Dict) -> List[Dict]:
        """Detect responsive breakpoints from variants"""
        breakpoints = []
        
        # Look for variant naming patterns
        name = node.get('name', '')
        
        # Check for common breakpoint indicators
        if 'mobile' in name.lower() or 'phone' in name.lower():
            breakpoints.append({'name': 'mobile', 'max_width': 640})
        elif 'tablet' in name.lower():
            breakpoints.append({'name': 'tablet', 'max_width': 1024})
        elif 'desktop' in name.lower() or 'lg' in name.lower():
            breakpoints.append({'name': 'desktop', 'min_width': 1024})
        elif 'xl' in name.lower():
            breakpoints.append({'name': 'xl', 'min_width': 1440})
            
        # If no explicit breakpoints found, suggest standard ones
        if not breakpoints:
            breakpoints = [
                {'name': 'mobile', 'max_width': 640},
                {'name': 'tablet', 'max_width': 1024},
                {'name': 'desktop', 'min_width': 1024}
            ]
            
        return breakpoints
        
    def _extract_design_system(self, root_node: Dict) -> Dict:
        """Extract global design tokens"""
        design_system = {
            'colors': {},
            'typography': {},
            'spacing': {},
            'components': {}
        }
        
        # Look for style guides or design token pages
        for child in root_node.get('children', []):
            name = child.get('name', '').lower()
            
            if 'color' in name or 'palette' in name:
                # Extract color tokens
                for swatch in child.get('children', []):
                    if swatch.get('fills'):
                        color = swatch['fills'][0]
                        if color.get('type') == 'SOLID':
                            color_name = swatch.get('name', 'unknown')
                            rgba = color['color']
                            design_system['colors'][color_name] = self._rgba_to_hex(
                                rgba.get('r', 0),
                                rgba.get('g', 0),
                                rgba.get('b', 0),
                                rgba.get('a', 1)
                            )
                            
            elif 'typography' in name or 'text' in name:
                # Extract text styles
                for style in child.get('children', []):
                    if style.get('type') == 'TEXT':
                        style_name = style.get('name', 'unknown')
                        design_system['typography'][style_name] = {
                            'font_family': style.get('style', {}).get('fontPostScriptName'),
                            'font_size': style.get('fontSize'),
                            'font_weight': style.get('style', {}).get('fontWeight')
                        }
                        
        return design_system
        
    def _extract_user_flows(self, screens: List[ScreenSpec]) -> List[Dict]:
        """Extract user flows from navigation patterns"""
        flows = []
        
        # Find navigation components across screens
        nav_components = []
        for screen in screens:
            for comp in screen.components:
                if comp.type == 'navigation':
                    nav_components.append({
                        'screen': screen.name,
                        'component': comp
                    })
                    
        # Simplified flow detection
        if len(screens) > 1:
            flows.append({
                'name': 'Primary Flow',
                'steps': [screen.name for screen in screens[:5]],  # First 5 screens
                'entry_point': screens[0].name if screens else None
            })
            
        return flows
        
    def _generate_requirements(self, screens: List[ScreenSpec], 
                               design_system: Dict) -> List[str]:
        """Generate technical requirements from design"""
        requirements = []
        
        # Component requirements
        component_types = set()
        for screen in screens:
            for comp in screen.components:
                component_types.add(comp.type)
                
        requirements.append(f"**Components:** Implement {len(component_types)} component types: {', '.join(component_types)}")
        
        # Responsive requirements
        total_breakpoints = sum(len(s.breakpoints) for s in screens)
        if total_breakpoints > 0:
            requirements.append(f"**Responsive:** Support {total_breakpoints} breakpoint configurations")
            
        # Style requirements
        if design_system.get('colors'):
            requirements.append(f"**Styling:** Use {len(design_system['colors'])} design tokens from theme")
            
        # Framework-specific requirements
        framework = self.config['framework']['preferred']
        ui_lib = self.config['framework']['ui_library']
        requirements.append(f"**Tech Stack:** {framework} components with {ui_lib} styling")
        
        # Accessibility
        requirements.append("**Accessibility:** WCAG 2.1 AA compliance (contrast ratios, keyboard navigation)")
        
        # Performance
        requirements.append("**Performance:** Lazy-load images, optimize bundle size, implement code splitting")
        
        return requirements
        
    def generate_spec_document(self, design_spec: DesignSpec, 
                               output_format: str = None) -> str:
        """Generate human-readable specification document"""
        fmt = output_format or self.config['output']['format']
        
        if fmt == 'json':
            return json.dumps(asdict(design_spec), indent=2)
        elif fmt == 'markdown':
            return self._generate_markdown_spec(design_spec)
        elif fmt == 'prd':
            return self._generate_prd_spec(design_spec)
        else:
            return self._generate_markdown_spec(design_spec)
            
    def _generate_markdown_spec(self, spec: DesignSpec) -> str:
        """Generate Markdown specification"""
        lines = [
            "# Design Specification",
            "",
            f"**Generated:** {spec.generated_at}",
            f"**Screens:** {spec.screen_count}",
            "",
            "---",
            "",
            "## Design System",
            ""
        ]
        
        # Colors
        if spec.design_system.get('colors'):
            lines.append("### Colors")
            lines.append("")
            lines.append("| Token | Value |")
            lines.append("|-------|-------|")
            for name, value in spec.design_system['colors'].items():
                lines.append(f"| {name} | `{value}` |")
            lines.append("")
            
        # Typography
        if spec.design_system.get('typography'):
            lines.append("### Typography")
            lines.append("")
            for name, style in spec.design_system['typography'].items():
                lines.append(f"- **{name}**: {style.get('font_size')}px {style.get('font_family')}")
            lines.append("")
            
        # Screens
        lines.append("---")
        lines.append("")
        lines.append("## Screens")
        lines.append("")
        
        for screen in spec.screens:
            lines.append(f"### {screen.name}")
            lines.append("")
            lines.append(f"**Dimensions:** {screen.width} × {screen.height}px")
            lines.append("")
            
            # Breakpoints
            if screen.breakpoints:
                lines.append("**Breakpoints:**")
                for bp in screen.breakpoints:
                    if 'max_width' in bp:
                        lines.append(f"- ≤{bp['max_width']}px ({bp['name']})")
                    else:
                        lines.append(f"≥{bp['min_width']}px ({bp['name']})")
                lines.append("")
                
            # Components
            lines.append("**Components:**")
            for comp in screen.components[:10]:  # Limit preview
                lines.append(f"- {comp.type}: `{comp.name}`")
            if len(screen.components) > 10:
                lines.append(f"- _and {len(screen.components) - 10} more..._")
            lines.append("")
            
        # Requirements
        lines.append("---")
        lines.append("")
        lines.append("## Technical Requirements")
        lines.append("")
        for req in spec.requirements:
            lines.append(f"- {req}")
        lines.append("")
        
        # User stories (if enabled)
        if self.config['output']['generate_user_stories']:
            lines.append("---")
            lines.append("")
            lines.append("## User Stories")
            lines.append("")
            for i, screen in enumerate(spec.screens[:5]):
                lines.append(f"**Story #{i+1}:** As a user, I want to view {screen.name.lower()} so that...")
                lines.append("")
                lines.append("```yaml")
                lines.append(f"acceptance_criteria:")
                lines.append(f"  - Display {screen.width}×{screen.height}px layout")
                lines.append(f"  - Support {len(screen.breakpoints)} breakpoints")
                lines.append(f"  - {len(screen.components)} interactive components")
                lines.append("```")
                lines.append("")
                
        return "\n".join(lines)
        
    def _generate_prd_spec(self, spec: DesignSpec) -> str:
        """Generate Product Requirements Document format"""
        lines = [
            "# Product Requirements Document",
            "",
            f"**Design Source:** Figma",
            f"**Generated:** {spec.generated_at}",
            "",
            "## Overview",
            "",
            f"This PRD describes implementation requirements for {spec.screen_count} screens.",
            "",
            "## Functional Requirements",
            ""
        ]
        
        for i, screen in enumerate(spec.screens, 1):
            lines.append(f"### FR-{i}: {screen.name}")
            lines.append("")
            lines.append(f"**Description:** Render {screen.name} interface")
            lines.append(f"**Priority:** High")
            lines.append(f"**Complexity:** Medium")
            lines.append("")
            lines.append("Acceptance Criteria:")
            lines.append("")
            lines.append("```yaml")
            lines.append("layout:")
            lines.append(f"  desktop: {screen.width}x{screen.height}")
            if screen.breakpoints:
                lines.append("  mobile:")
                lines.append(f"    max_width: {screen.breakpoints[0].get('max_width', 640)}")
            lines.append("components:")
            for comp in screen.components:
                lines.append(f"  - type: {comp.type}")
                lines.append(f"    name: {comp.name}")
                if comp.interactions:
                    lines.append(f"    interactions: {[i['type'] for i in comp.interactions]}")
            lines.append("```\n")
            
        return "\n".join(lines)


# CLI Entry Point
if __name__ == '__main__':
    import asyncio
    import sys
    
    print("NexDev Figma Parser v3.0")
    print("=" * 50)
    
    parser = FigmaParser()
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python figma_parser.py parse <file_key> [node_ids]")
        print("  python figma_parser.py demo")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == 'demo':
        # Generate sample spec for demonstration
        print("\n🎨 Generating sample design spec...\n")
        
        sample_spec = DesignSpec(
            screen_count=3,
            screens=[
                ScreenSpec(
                    name="Login Screen",
                    width=1440,
                    height=900,
                    components=[
                        ComponentSpec(
                            name="Email Input",
                            type="input",
                            position={'x': 400, 'y': 350, 'width': 640, 'height': 48},
                            styles={'background_color': '#ffffff', 'border_color': '#d1d5db'},
                            interactions=[]
                        ),
                        ComponentSpec(
                            name="Sign In Button",
                            type="button",
                            position={'x': 400, 'y': 420, 'width': 640, 'height': 48},
                            styles={'background_color': '#3b82f6'},
                            interactions=[{'type': 'click'}]
                        )
                    ],
                    breakpoints=[{'name': 'mobile', 'max_width': 640}],
                    assets=[]
                )
            ],
            design_system={
                'colors': {'primary': '#3b82f6', 'background': '#ffffff'},
                'typography': {'heading': {'font_size': 32, 'font_family': 'Inter'}}
            },
            user_flows=[],
            requirements=["React + Tailwind CSS", "WCAG AA compliance"],
            generated_at=datetime.now().isoformat()
        )
        
        spec_doc = parser.generate_spec_document(sample_spec, 'markdown')
        print(spec_doc)
        
    elif command == 'parse':
        if len(sys.argv) < 3:
            print("Usage: python figma_parser.py parse <file_key>")
            sys.exit(1)
            
        file_key = sys.argv[2]
        
        try:
            spec = asyncio.run(parser.parse_figma_file(file_key))
            doc = parser.generate_spec_document(spec)
            print(doc)
            
            # Save to file
            output_file = parser.specs_dir / f"spec_{file_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(output_file, 'w') as f:
                f.write(doc)
            print(f"\n✅ Saved to: {output_file}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print("\nMake sure Figma API token is configured in config.json")
