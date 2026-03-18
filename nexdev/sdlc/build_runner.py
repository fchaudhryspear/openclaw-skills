#!/usr/bin/env python3
"""
NexDev Build & Test Runner — Actually executes generated code.

Creates isolated temp environments, installs dependencies,
runs linting/syntax checks, executes tests, and reports real results.
"""

import json
import os
import shutil
import subprocess
import tempfile
import venv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class BuildRunner:
    """Builds and verifies generated project code."""
    
    def __init__(self, project_dir: str = None):
        self.project_dir = project_dir
        self.results = {
            "syntax_checks": [],
            "lint_results": [],
            "build_result": None,
            "test_results": [],
            "summary": {},
        }
    
    def run_full_verification(self, impl_data: Dict) -> Dict:
        """
        Full build verification pipeline:
        1. Write files to temp directory
        2. Syntax check all source files
        3. Lint check (if tools available)
        4. Try to build/install dependencies
        5. Run generated tests
        6. Produce real results
        """
        with tempfile.TemporaryDirectory(prefix="nexdev_build_") as tmpdir:
            # Step 1: Write all files
            files_written = self._write_files(tmpdir, impl_data)
            
            # Step 2: Detect project language
            languages = set()
            for f in impl_data.get("files", []):
                lang = f.get("language", "").lower()
                if lang in ("python", "py"):
                    languages.add("python")
                elif lang in ("javascript", "js", "typescript", "ts"):
                    languages.add("javascript")
            
            # Step 3: Syntax checks
            for f in impl_data.get("files", []) + impl_data.get("test_files", []):
                path = os.path.join(tmpdir, f["path"])
                if not os.path.exists(path):
                    continue
                lang = f.get("language", "").lower()
                result = self._syntax_check(path, lang)
                self.results["syntax_checks"].append(result)
            
            # Step 4: Lint (Python only for now)
            if "python" in languages:
                self.results["lint_results"] = self._lint_python(tmpdir, impl_data)
            
            # Step 5: Build / dependency install
            if "python" in languages:
                self.results["build_result"] = self._build_python(tmpdir, impl_data)
            elif "javascript" in languages:
                self.results["build_result"] = self._build_node(tmpdir, impl_data)
            else:
                self.results["build_result"] = {"status": "skipped", "reason": "No supported language detected"}
            
            # Step 6: Run tests
            if "python" in languages:
                self.results["test_results"] = self._run_python_tests(tmpdir, impl_data)
            elif "javascript" in languages:
                self.results["test_results"] = self._run_node_tests(tmpdir, impl_data)
            
            # Step 7: Summary
            self.results["summary"] = self._build_summary()
            self.results["timestamp"] = datetime.now().isoformat()
            self.results["files_written"] = files_written
        
        return self.results
    
    def _write_files(self, tmpdir: str, impl_data: Dict) -> int:
        """Write implementation and test files to temp directory."""
        count = 0
        for file_list in [impl_data.get("files", []), impl_data.get("test_files", [])]:
            for f in file_list:
                path = os.path.join(tmpdir, f["path"])
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as fh:
                    fh.write(f.get("content", ""))
                count += 1
        
        # Write __init__.py files for Python packages
        for root, dirs, files in os.walk(tmpdir):
            for d in dirs:
                init_path = os.path.join(root, d, "__init__.py")
                if not os.path.exists(init_path):
                    # Check if any .py files in the directory
                    has_py = any(f.endswith(".py") for f in os.listdir(os.path.join(root, d)))
                    if has_py:
                        with open(init_path, "w") as fh:
                            fh.write("")
                        count += 1
        
        return count
    
    def _syntax_check(self, filepath: str, language: str) -> Dict:
        """Check syntax of a single file."""
        result = {
            "file": os.path.basename(filepath),
            "language": language,
            "status": "unknown",
            "errors": [],
        }
        
        if language in ("python", "py"):
            try:
                proc = subprocess.run(
                    ["python3", "-m", "py_compile", filepath],
                    capture_output=True, text=True, timeout=10
                )
                if proc.returncode == 0:
                    result["status"] = "pass"
                else:
                    result["status"] = "fail"
                    result["errors"] = [proc.stderr.strip()]
            except Exception as e:
                result["status"] = "error"
                result["errors"] = [str(e)]
        
        elif language in ("javascript", "js"):
            try:
                proc = subprocess.run(
                    ["node", "--check", filepath],
                    capture_output=True, text=True, timeout=10
                )
                if proc.returncode == 0:
                    result["status"] = "pass"
                else:
                    result["status"] = "fail"
                    result["errors"] = [proc.stderr.strip()]
            except FileNotFoundError:
                result["status"] = "skipped"
                result["errors"] = ["node not found"]
            except Exception as e:
                result["status"] = "error"
                result["errors"] = [str(e)]
        
        elif language in ("typescript", "ts"):
            result["status"] = "skipped"
            result["errors"] = ["TypeScript checking requires tsc"]
        
        else:
            result["status"] = "skipped"
        
        return result
    
    def _lint_python(self, tmpdir: str, impl_data: Dict) -> List[Dict]:
        """Run Python linting on generated code."""
        results = []
        for f in impl_data.get("files", []):
            if f.get("language", "").lower() not in ("python", "py"):
                continue
            filepath = os.path.join(tmpdir, f["path"])
            if not os.path.exists(filepath):
                continue
            
            # Try ruff first (fast), fall back to flake8, then pyflakes
            for linter, cmd in [
                ("ruff", ["ruff", "check", "--select=E,F,W", "--no-fix", filepath]),
                ("flake8", ["flake8", "--select=E,F,W", "--max-line-length=120", filepath]),
                ("pyflakes", ["pyflakes", filepath]),
            ]:
                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                    issues = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
                    results.append({
                        "file": f["path"],
                        "linter": linter,
                        "issues": issues[:20],  # Cap at 20
                        "issue_count": len(issues),
                        "status": "clean" if not issues else "issues_found",
                    })
                    break  # Use first available linter
                except FileNotFoundError:
                    continue
                except Exception as e:
                    results.append({
                        "file": f["path"],
                        "linter": linter,
                        "status": "error",
                        "issues": [str(e)],
                    })
                    break
        
        return results
    
    def _build_python(self, tmpdir: str, impl_data: Dict) -> Dict:
        """Try to install Python dependencies."""
        req_file = os.path.join(tmpdir, "requirements.txt")
        if not os.path.exists(req_file):
            return {"status": "skipped", "reason": "No requirements.txt"}
        
        try:
            # Dry-run: just check if pip can resolve dependencies
            proc = subprocess.run(
                ["pip3", "install", "--dry-run", "-r", req_file],
                capture_output=True, text=True, timeout=30,
                cwd=tmpdir
            )
            if proc.returncode == 0:
                return {"status": "pass", "message": "Dependencies resolved successfully"}
            else:
                return {
                    "status": "fail",
                    "message": "Dependency resolution failed",
                    "errors": proc.stderr.strip().split("\n")[-3:],
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _build_node(self, tmpdir: str, impl_data: Dict) -> Dict:
        """Try to validate Node.js project."""
        pkg_file = os.path.join(tmpdir, "package.json")
        if not os.path.exists(pkg_file):
            # Check for deps in impl_data
            deps = impl_data.get("dependencies", {})
            if deps:
                pkg = {"name": "nexdev-project", "version": "1.0.0", "dependencies": deps}
                with open(pkg_file, "w") as f:
                    json.dump(pkg, f, indent=2)
            else:
                return {"status": "skipped", "reason": "No package.json or dependencies"}
        
        try:
            proc = subprocess.run(
                ["npm", "install", "--dry-run"],
                capture_output=True, text=True, timeout=30,
                cwd=tmpdir
            )
            if proc.returncode == 0:
                return {"status": "pass", "message": "npm dependencies resolved"}
            else:
                return {"status": "fail", "errors": proc.stderr.strip().split("\n")[-3:]}
        except FileNotFoundError:
            return {"status": "skipped", "reason": "npm not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _run_python_tests(self, tmpdir: str, impl_data: Dict) -> List[Dict]:
        """Run pytest on generated test files."""
        test_files = impl_data.get("test_files", [])
        if not test_files:
            return [{"status": "skipped", "reason": "No test files generated"}]
        
        try:
            proc = subprocess.run(
                ["python3", "-m", "pytest", "--tb=short", "-q", "--no-header"],
                capture_output=True, text=True, timeout=30,
                cwd=tmpdir,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            
            output = proc.stdout + proc.stderr
            lines = output.strip().split("\n")
            
            return [{
                "runner": "pytest",
                "exit_code": proc.returncode,
                "status": "pass" if proc.returncode == 0 else "fail",
                "output": output[:2000],
                "summary_line": lines[-1] if lines else "No output",
            }]
        except FileNotFoundError:
            return [{"status": "error", "reason": "pytest not found"}]
        except subprocess.TimeoutExpired:
            return [{"status": "timeout", "reason": "Tests took >30s"}]
        except Exception as e:
            return [{"status": "error", "reason": str(e)}]
    
    def _run_node_tests(self, tmpdir: str, impl_data: Dict) -> List[Dict]:
        """Run node tests if available."""
        # Check for test script in package.json
        test_files = impl_data.get("test_files", [])
        if not test_files:
            return [{"status": "skipped", "reason": "No test files"}]
        
        # Try running with node directly
        results = []
        for tf in test_files:
            path = os.path.join(tmpdir, tf["path"])
            if os.path.exists(path):
                try:
                    proc = subprocess.run(
                        ["node", path],
                        capture_output=True, text=True, timeout=15,
                        cwd=tmpdir
                    )
                    results.append({
                        "file": tf["path"],
                        "exit_code": proc.returncode,
                        "status": "pass" if proc.returncode == 0 else "fail",
                        "output": (proc.stdout + proc.stderr)[:500],
                    })
                except Exception as e:
                    results.append({"file": tf["path"], "status": "error", "reason": str(e)})
        
        return results or [{"status": "skipped", "reason": "No runnable tests"}]
    
    def _build_summary(self) -> Dict:
        """Generate summary from all results."""
        syntax_pass = sum(1 for s in self.results["syntax_checks"] if s["status"] == "pass")
        syntax_fail = sum(1 for s in self.results["syntax_checks"] if s["status"] == "fail")
        syntax_total = len(self.results["syntax_checks"])
        
        lint_issues = sum(r.get("issue_count", 0) for r in self.results["lint_results"])
        lint_clean = sum(1 for r in self.results["lint_results"] if r.get("status") == "clean")
        
        build_ok = self.results["build_result"] and self.results["build_result"].get("status") == "pass"
        
        tests_pass = any(t.get("status") == "pass" for t in self.results["test_results"])
        tests_run = any(t.get("status") not in ("skipped", None) for t in self.results["test_results"])
        
        # Overall grade
        if syntax_fail > 0:
            grade = "F"
            verdict = "Syntax errors — code won\'t run"
        elif not build_ok and self.results["build_result"] and self.results["build_result"].get("status") == "fail":
            grade = "D"
            verdict = "Build failed — missing or incompatible dependencies"
        elif not tests_run:
            grade = "C"
            verdict = "No tests executed — can\'t verify correctness"
        elif not tests_pass:
            grade = "C-"
            verdict = "Tests failed — implementation has issues"
        elif lint_issues > 10:
            grade = "B"
            verdict = "Code works but has quality issues"
        elif lint_issues > 0:
            grade = "B+"
            verdict = "Minor lint issues, otherwise solid"
        else:
            grade = "A"
            verdict = "Clean build, tests pass, no lint issues"
        
        return {
            "grade": grade,
            "verdict": verdict,
            "syntax": f"{syntax_pass}/{syntax_total} files pass",
            "lint_issues": lint_issues,
            "build": self.results["build_result"].get("status", "unknown") if self.results["build_result"] else "skipped",
            "tests": "pass" if tests_pass else ("fail" if tests_run else "not_run"),
        }


def verify_implementation(impl_data: Dict) -> Dict:
    """Convenience function to verify an implementation."""
    runner = BuildRunner()
    return runner.run_full_verification(impl_data)
