#!/usr/bin/env python3
"""NexDev — Frontend Developer Agent
Generates React/Vue/Angular components, pages, and full frontend implementations."""

import json
from typing import Dict, List
from datetime import datetime


class FrontendDeveloper:
    """Generates frontend code from design specs and architecture."""
    
    def __init__(self):
        self.supported_frameworks = ["react", "vue", "angular", "nextjs", "nuxt"]
    
    def detect_framework(self, spec_data: Dict) -> str:
        """Detect preferred frontend framework from spec."""
        text = json.dumps(spec_data).lower()
        for fw in self.supported_frameworks:
            if fw in text:
                return fw
        # Check tech stack
        tech = spec_data.get("tech_stack", {})
        frontend = tech.get("frontend", "").lower()
        for fw in self.supported_frameworks:
            if fw in frontend:
                return fw
        return "react"  # Default
    
    def generate_scaffold(self, framework: str, project_name: str) -> List[Dict]:
        """Generate project scaffold files."""
        if framework in ("react", "nextjs"):
            return [
                {"path": "package.json", "language": "json", "description": "Package manifest",
                 "content": json.dumps({
                     "name": project_name.lower().replace(" ", "-"),
                     "version": "0.1.0", "private": True,
                     "scripts": {"dev": "next dev" if framework == "nextjs" else "react-scripts start",
                                "build": "next build" if framework == "nextjs" else "react-scripts build",
                                "test": "jest --passWithNoTests"},
                     "dependencies": {
                         "react": "^18.3.0", "react-dom": "^18.3.0",
                         **({"next": "^14.0.0"} if framework == "nextjs" else {}),
                         "axios": "^1.7.0", "@tanstack/react-query": "^5.0.0",
                     },
                     "devDependencies": {
                         "typescript": "^5.3.0", "@types/react": "^18.3.0",
                         "tailwindcss": "^3.4.0", "jest": "^29.7.0",
                         "@testing-library/react": "^14.0.0",
                     }
                 }, indent=2)},
                {"path": "tailwind.config.js", "language": "javascript",
                 "description": "Tailwind CSS configuration",
                 "content": "/** @type {import('tailwindcss').Config} */\nmodule.exports = {\n  content: ['./src/**/*.{js,ts,jsx,tsx}', './app/**/*.{js,ts,jsx,tsx}'],\n  theme: { extend: {} },\n  plugins: [],\n}\n"},
                {"path": "tsconfig.json", "language": "json", "description": "TypeScript config",
                 "content": json.dumps({
                     "compilerOptions": {
                         "target": "ES2017", "lib": ["dom", "dom.iterable", "esnext"],
                         "strict": True, "jsx": "react-jsx", "module": "esnext",
                         "moduleResolution": "bundler", "paths": {"@/*": ["./src/*"]},
                     }, "include": ["src", "app"], "exclude": ["node_modules"]
                 }, indent=2)},
            ]
        return []
    
    def generate_component(self, name: str, props: List[Dict] = None, 
                          has_state: bool = False) -> Dict:
        """Generate a React component."""
        props_list = props or []
        props_type = "\n".join(f"  {p['name']}: {p.get('type', 'string')};" for p in props_list)
        props_destructure = ", ".join(p["name"] for p in props_list)
        
        code = f"""import React from 'react';

interface {name}Props {{
{props_type if props_type else '  // Add props here'}
}}

export const {name}: React.FC<{name}Props> = ({{{ props_destructure if props_destructure else '' }}}) => {{
  return (
    <div className="{name.lower()}" role="region" aria-label="{name}">
      <h2>{name}</h2>
      {{/* Component content */}}
    </div>
  );
}};

export default {name};
"""
        return {
            "path": f"src/components/{name}/{name}.tsx",
            "language": "typescript",
            "description": f"{name} component",
            "content": code,
        }


if __name__ == "__main__":
    fd = FrontendDeveloper()
    scaffold = fd.generate_scaffold("react", "my-app")
    print(f"Scaffold files: {len(scaffold)}")
    comp = fd.generate_component("UserProfile", [{"name": "userId", "type": "string"}])
    print(f"Component: {comp['path']}")
