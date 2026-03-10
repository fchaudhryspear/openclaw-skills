#!/usr/bin/env python3
"""NexDev - Rapid Prototyper Agent. Fast MVP generation, skip reviews."""

import json
from typing import Dict
from datetime import datetime


class RapidPrototyper:
    """Generates minimal viable implementations fast. No over-engineering."""

    def prototype(self, request: str) -> Dict:
        """Generate a rapid prototype spec."""
        return {
            "mode": "rapid_prototype",
            "skip_reviews": True,
            "max_files": 5,
            "prefer": ["single-file", "sqlite", "flask", "minimal-deps"],
            "request": request,
            "created_at": datetime.now().isoformat(),
        }

    def generate_flask_app(self, features: list) -> Dict:
        """Generate a single-file Flask app as MVP."""
        routes = []
        for feat in features:
            name = feat.lower().replace(" ", "_")
            routes.append(
                f"@app.route('/api/{name}', methods=['GET', 'POST'])\n"
                f"def {name}_handler():\n"
                f"    db = get_db()\n"
                f"    if request.method == 'POST':\n"
                f"        data = request.get_json()\n"
                f"        db.execute('INSERT INTO {name} (data) VALUES (?)', [json.dumps(data)])\n"
                f"        db.commit()\n"
                f"        return jsonify({{'status': 'created', 'data': data}}), 201\n"
                f"    rows = db.execute('SELECT * FROM {name}').fetchall()\n"
                f"    return jsonify([dict(r) for r in rows])\n"
            )

        tables = "\n".join(
            f"    db.execute('CREATE TABLE IF NOT EXISTS {f.lower().replace(' ','_')} "
            f"(id INTEGER PRIMARY KEY, data TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')"
            for f in features
        )

        date_str = datetime.now().strftime('%Y-%m-%d')
        features_json = json.dumps(features)

        app_lines = [
            "#!/usr/bin/env python3",
            f"# Auto-generated MVP - {date_str}",
            "import json",
            "import sqlite3",
            "from flask import Flask, request, jsonify, g",
            "",
            "app = Flask(__name__)",
            "DATABASE = 'app.db'",
            "",
            "def get_db():",
            "    if 'db' not in g:",
            "        g.db = sqlite3.connect(DATABASE)",
            "        g.db.row_factory = sqlite3.Row",
            "    return g.db",
            "",
            "@app.teardown_appcontext",
            "def close_db(exc):",
            "    db = g.pop('db', None)",
            "    if db:",
            "        db.close()",
            "",
            "def init_db():",
            "    db = get_db()",
            tables,
            "    db.commit()",
            "",
            "with app.app_context():",
            "    init_db()",
            "",
            "@app.route('/')",
            "def index():",
            f"    return jsonify({{'status': 'ok', 'features': {features_json}}})",
            "",
        ]

        for route in routes:
            app_lines.append(route)

        app_lines.extend([
            "if __name__ == '__main__':",
            "    app.run(debug=True, port=5000)",
        ])

        app_code = "\n".join(app_lines)

        return {
            "files": [
                {"path": "app.py", "language": "python", "description": "Single-file Flask MVP",
                 "content": app_code},
                {"path": "requirements.txt", "language": "text", "description": "Minimal deps",
                 "content": "flask>=3.0\n"},
            ],
            "test_files": [],
            "run_command": "python app.py",
            "dependencies": {"flask": ">=3.0"},
        }


if __name__ == "__main__":
    rp = RapidPrototyper()
    result = rp.generate_flask_app(["users", "tasks", "notes"])
    print(f"Files: {len(result['files'])}")
    print(result["files"][0]["content"][:300])
