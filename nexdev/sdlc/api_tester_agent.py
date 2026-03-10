#!/usr/bin/env python3
"""NexDev -- API Tester Agent. Generates and runs HTTP-based API tests."""

import json
import subprocess
import tempfile
import os
from typing import Dict, List


class APITester:
    """Generates and optionally runs API test suites."""

    def generate_test_suite(self, endpoints: List[Dict], base_url: str = "http://localhost:8000") -> Dict:
        """Generate a pytest-based API test suite from endpoint definitions."""
        lines = [
            "import pytest", "import httpx", "import json", "",
            f'BASE_URL = "{base_url}"',
            "client = httpx.Client(base_url=BASE_URL, timeout=10.0)", "",
        ]

        test_count = 0
        for ep in endpoints:
            method = ep.get("method", "GET").upper()
            path = ep.get("path", "/")
            name = ep.get("name", path.replace("/", "_").strip("_"))
            expected = ep.get("expected_status", 200)
            body = ep.get("request_body")

            func_name = f"test_{method.lower()}_{name}"
            lines.append(f"def {func_name}():")
            lines.append(f'    """Test {method} {path}"""')

            if method == "GET":
                lines.append(f'    response = client.get("{path}")')
            elif method in ("POST", "PUT", "PATCH"):
                lines.append(f"    payload = {json.dumps(body or {})}")
                lines.append(f'    response = client.{method.lower()}("{path}", json=payload)')
            elif method == "DELETE":
                lines.append(f'    response = client.delete("{path}")')

            lines.append(f"    assert response.status_code == {expected}, "
                        f'f"Expected {expected}, got {{response.status_code}}"')
            lines.append("")
            test_count += 1

        # Standard tests
        lines.extend([
            "def test_invalid_endpoint_returns_404():",
            '    response = client.get("/nonexistent-endpoint-xyz")',
            "    assert response.status_code == 404",
            "",
            "def test_method_not_allowed():",
            '    response = client.patch("/")',
            "    assert response.status_code in [405, 404, 307]",
            "",
        ])
        test_count += 2

        return {
            "test_file": {
                "path": "tests/test_api.py",
                "language": "python",
                "description": "API integration test suite",
                "content": "\n".join(lines),
            },
            "endpoints_tested": len(endpoints),
            "test_count": test_count,
        }

    def run_api_tests(self, test_code: str, timeout: int = 30) -> Dict:
        """Run API tests and return results."""
        with tempfile.TemporaryDirectory(prefix="nexdev_api_") as tmpdir:
            test_path = os.path.join(tmpdir, "test_api.py")
            with open(test_path, "w") as f:
                f.write(test_code)
            try:
                proc = subprocess.run(
                    ["python3", "-m", "pytest", test_path, "--tb=short", "-q"],
                    capture_output=True, text=True, timeout=timeout, cwd=tmpdir
                )
                output = (proc.stdout + proc.stderr)[:2000]
                summary = proc.stdout.strip().split("\n")[-1] if proc.stdout else ""
                return {
                    "status": "pass" if proc.returncode == 0 else "fail",
                    "exit_code": proc.returncode,
                    "output": output,
                    "summary": summary,
                }
            except subprocess.TimeoutExpired:
                return {"status": "timeout"}
            except Exception as e:
                return {"status": "error", "output": str(e)}


if __name__ == "__main__":
    tester = APITester()
    suite = tester.generate_test_suite([
        {"method": "GET", "path": "/api/users", "name": "list_users"},
        {"method": "POST", "path": "/api/users", "name": "create_user",
         "request_body": {"email": "test@test.com"}, "expected_status": 201},
    ])
    print(f"Generated {suite['test_count']} tests")
