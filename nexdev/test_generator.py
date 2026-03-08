#!/usr/bin/env python3
"""
NexDev Auto-Test Generator (Tier 1 Feature)

Generates comprehensive unit/integration tests for generated code.
Supports pytest (Python), Jest (JavaScript/TypeScript), JUnit (Java).
Part of NexDev v3.0 World-Class Build Team Upgrade
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# Language Detection & Test Framework Mapping
# ──────────────────────────────────────────────────────────────────────────────

FRAMEWORKS = {
    "python": "pytest",
    "javascript": "jest",
    "typescript": "jest",
    "java": "junit",
    "go": "testing",
    "ruby": "rspec",
    "rust": "cargo_test"
}

@dataclass
class TestCase:
    """Represents a single generated test case."""
    name: str
    description: str
    setup_code: str
    test_code: str
    teardown_code: str
    expected_result: str


def detect_language(code: str) -> str:
    """Detect programming language from code snippet."""
    # Python indicators
    if re.search(r'^def \w+|import |class .+:', code, re.MULTILINE):
        return "python"
    
    # JavaScript/TypeScript indicators
    if re.search(r'const \w+=|let \w+=|function \w+\(|=>\s*{', code):
        return "typescript" if re.search(r':\s*(string|number|boolean|any)', code) else "javascript"
    
    # Java indicators
    if re.search(r'public class |public static void main|private ', code):
        return "java"
    
    # Go indicators
    if re.search(r'^func \w+|package main|import \(', code, re.MULTILINE):
        return "go"
    
    # Ruby indicators
    if re.search(r'def \w+.*end|class \w+.*end', code, re.DOTALL):
        return "ruby"
    
    # Default to Python
    return "python"


def extract_function_signatures(code: str, language: str) -> List[Dict[str, Any]]:
    """Extract function/method signatures from code."""
    functions = []
    
    if language == "python":
        pattern = r'def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*([^:]+))?\s*:'
        matches = re.findall(pattern, code, re.MULTILINE)
        
        for match in matches:
            func_name, params_str, return_type = match
            if not func_name.startswith('_'):  # Skip private methods
                params = [p.strip().split(':')[0].split('=')[0].strip() 
                         for p in params_str.split(',') if p.strip()]
                functions.append({
                    'name': func_name,
                    'params': params,
                    'return_type': return_type.strip() if return_type else None,
                    'type': 'function'
                })
    
    elif language in ["javascript", "typescript"]:
        pattern = r'(?:const|let|function)\s+(\w+)\s*(?:=\s*)?(?:\(([^)]*)\))?(\s*:[^{]+)?\s*=>'
        matches = re.findall(pattern, code)
        
        for match in matches:
            func_name, params_str, return_type = match
            params = [p.strip().split(':')[0].split('=')[0].strip() 
                     for p in params_str.split(',') if p.strip()]
            functions.append({
                'name': func_name,
                'params': params,
                'return_type': return_type.strip() if return_type else None,
                'type': 'function'
            })
    
    return functions


# ──────────────────────────────────────────────────────────────────────────────
# Test Case Generators
# ──────────────────────────────────────────────────────────────────────────────

def generate_pytest_tests(func_info: Dict[str, Any], doc: str = "") -> str:
    """Generate pytest test cases for a Python function."""
    func_name = func_info['name']
    params = func_info['params']
    return_type = func_info['return_type']
    
    # Base imports
    lines = [
        "# Auto-generated tests by NexDev v3.0",
        f"import pytest",
        "",
        "# Import the function being tested",
        f"# from your_module import {func_name}",
        ""
    ]
    
    # Happy path test
    test_cases = []
    
    # Test 1: Basic functionality with sample inputs
    sample_inputs = _generate_sample_inputs(params, return_type)
    if sample_inputs:
        test_lines = [
            "",
            f"def test_{func_name}_basic():",
            f'    """Test basic functionality of {func_name}"""',
            ""
        ]
        
        # Setup
        for i, (param_name, sample_value) in enumerate(sample_inputs.items(), 1):
            var_name = param_name if param_name else f"arg{i}"
            test_lines.append(f"    {var_name} = {sample_value}")
        
        # Function call
        arg_names = ", ".join([p if p else f"arg{i}" for i, p in enumerate(params, 1)])
        test_lines.append(f"    result = {func_name}({arg_names})")
        
        # Assertions
        test_lines.extend([
            "",
            "    # Assert result is not None",
            "    assert result is not None",
            "",
            "    # Add more specific assertions based on expected behavior",
            "    # Example:"
        ])
        
        if return_type and "str" in return_type:
            test_lines.append("    # assert isinstance(result, str)")
        elif return_type and "int" in return_type:
            test_lines.append("    # assert isinstance(result, int)")
        elif return_type and "bool" in return_type:
            test_lines.append("    # assert result is True or result is False")
        
        test_cases.append("\n".join(test_lines))
    
    # Test 2: Edge cases / error handling
    edge_case_lines = [
        "",
        f"def test_{func_name}_edge_cases():",
        f'    """Test edge cases for {func_name}"""',
        "",
        "    # Test with empty/null inputs",
        f"    # TODO: Add appropriate null values for parameter types",
        f"    # result = {func_name}(None)  # or '' or 0 depending on types",
        "    # assert result is not None",
        "",
        "    # Test with boundary values",
        "    # TODO: Add boundary-specific test cases",
    ]
    
    test_cases.append("\n".join(edge_case_lines))
    
    # Test 3: Exception handling (if applicable)
    if any(exc in doc.lower() for exc in ['error', 'exception', 'raise', 'invalid']):
        exception_lines = [
            "",
            f"def test_{func_name}_exceptions():",
            f'    """Test that {func_name} handles errors correctly"""',
            "",
            "    # Verify proper exception raising for invalid inputs",
            f"    # TODO: Replace ValueError with appropriate exception type",
            f"    # with pytest.raises(ValueError):",
            f"    #     {func_name}(invalid_input)",
        ]
        test_cases.append("\n".join(exception_lines))
    
    # Combine all tests
    return "\n".join(lines + test_cases + [""])


def generate_jest_tests(func_info: Dict[str, Any], doc: str = "") -> str:
    """Generate Jest test cases for JavaScript/TypeScript functions."""
    func_name = func_info['name']
    
    lines = [
        "// Auto-generated tests by NexDev v3.0",
        "",
        "// Import the function being tested",
        f"// const {{ {func_name} }} = require('./your_module');",
        "",
    ]
    
    test_blocks = [
        f"describe('{func_name}', () => {{",
        "",
        f"  it('should execute successfully with valid inputs', () => {{",
        f"    // TODO: Add appropriate sample inputs",
        f"    const sampleInput = {{}}; // Replace with actual test data",
        "",
        f"    const result = {func_name}(sampleInput);",
        "",
        f"    expect(result).toBeDefined();",
        f"    // TODO: Add more specific expectations",
        f"    // expect(result).toHaveProperty('someField');",
        f"  }});",
        "",
        f"  it('should handle edge cases gracefully', () => {{",
        f"    // TODO: Add edge case test scenarios",
        f"    // const edgeCaseInput = ...;",
        "",
        f"    // expect(() => {func_name}(edgeCaseInput)).not.toThrow();",
        f"  }});",
        "",
        f"  it('should throw errors for invalid inputs', () => {{",
        f"    // TODO: Define what constitutes an invalid input",
        f"    // const invalidInput = ...;",
        "",
        f"    // expect(() => {func_name}(invalidInput)).toThrow(Error);",
        f"  }});",
        "",
        "});"
    ]
    
    return "\n".join(lines + test_blocks + [""])


def _generate_sample_inputs(params: List[str], return_type: str) -> Dict[str, Any]:
    """Generate sample input values based on parameter hints."""
    samples = {}
    
    for param in params:
        param_lower = param.lower()
        
        # Simple heuristics for common parameter names
        if any(x in param_lower for x in ['id', 'num', 'count', 'qty', 'amount']):
            if 'float' in return_type.lower() if return_type else False:
                samples[param] = "3.14"
            else:
                samples[param] = "42"
        elif any(x in param_lower for x in ['name', 'title', 'desc', 'text', 'msg']):
            samples[param] = "'test'"
        elif any(x in param_lower for x in ['email', 'mail']):
            samples[param] = "'test@example.com'"
        elif any(x in param_lower for x in ['url', 'link', 'path']):
            samples[param] = "'https://example.com'"
        elif any(x in param_lower for x in ['flag', 'active', 'enabled', 'is_']):
            samples[param] = "True"
        elif any(x in param_lower for x in ['items', 'list', 'array', 'data']):
            samples[param] = "[1, 2, 3]"
        else:
            samples[param] = "None"
    
    return samples


# ──────────────────────────────────────────────────────────────────────────────
# Main Integration Functions
# ──────────────────────────────────────────────────────────────────────────────

def generate_tests_for_code(code: str, language: Optional[str] = None,
                           framework: Optional[str] = None,
                           output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate comprehensive test suite for given code.
    
    Args:
        code: Source code to generate tests for
        language: Programming language (auto-detected if not provided)
        framework: Test framework (auto-selected based on language)
        output_file: Optional file path to write tests to
        
    Returns:
        Dictionary with generated tests and metadata
    """
    # Detect language if not specified
    detected_lang = language or detect_language(code)
    
    # Select framework if not specified
    selected_framework = framework or FRAMEWORKS.get(detected_lang, "pytest")
    
    # Extract functions to test
    functions = extract_function_signatures(code, detected_lang)
    
    if not functions:
        return {
            "success": False,
            "message": "No testable functions found in provided code",
            "detected_language": detected_lang,
            "framework": selected_framework
        }
    
    # Generate tests for each function
    all_tests = []
    
    for func in functions:
        if detected_lang == "python":
            test_code = generate_pytest_tests(func, "")
        elif detected_lang in ["javascript", "typescript"]:
            test_code = generate_jest_tests(func, "")
        else:
            test_code = f"# Tests for {func['name']} ({detected_lang} - template needed)"
        
        all_tests.append({
            "function": func['name'],
            "test_code": test_code,
            "framework": selected_framework
        })
    
    # Write to file if requested
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        combined_tests = "\n\n".join([t["test_code"] for t in all_tests])
        with open(output_path, 'w') as f:
            f.write(combined_tests)
    
    return {
        "success": True,
        "language": detected_lang,
        "framework": selected_framework,
        "functions_tested": len(functions),
        "tests": all_tests,
        "output_file": output_file
    }


def add_tests_to_project(project_dir: str, code_files: List[str]) -> Dict[str, Any]:
    """
    Generate and add tests to a project structure.
    
    Args:
        project_dir: Root directory of the project
        code_files: List of source files to generate tests for
        
    Returns:
        Summary of tests generated
    """
    project_path = Path(project_dir)
    tests_dir = project_path / "tests"
    tests_dir.mkdir(exist_ok=True)
    
    # Create pytest.ini or jest.config.js
    lang = detect_language("")
    config_content = ""
    
    if lang == "python":
        config_content = "[pytest]\ntestpaths = tests\npython_files = test_*.py\n"
        (tests_dir / "pytest.ini").write_text(config_content)
        
        # Create __init__.py
        (tests_dir / "__init__.py").write_text("")
    
    results = []
    
    for code_file in code_files:
        file_path = project_path / code_file
        
        if not file_path.exists():
            continue
        
        code = file_path.read_text()
        test_result = generate_tests_for_code(
            code=code,
            output_file=str(tests_dir / f"test_{Path(code_file).stem}.py")
        )
        
        results.append({
            "source_file": code_file,
            "test_result": test_result
        })
    
    return {
        "project_dir": project_dir,
        "tests_dir": str(tests_dir),
        "files_processed": len(results),
        "results": results
    }


if __name__ == "__main__":
    # Demo mode
    print("=" * 60)
    print("🧪 NEXDEV TEST GENERATOR - DEMO")
    print("=" * 60)
    
    # Sample Python code
    sample_code = """
def calculate_total(items, tax_rate):
    \"\"\"Calculate order total with tax.\"\"\"
    total = sum(item.price * item.quantity for item in items)
    return total * (1 + tax_rate)

def validate_email(email):
    \"\"\"Validate email format.\"\"\"
    import re
    pattern = r'^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$'
    return bool(re.match(pattern, email))
"""
    
    print("\nSample Code:")
    print("-" * 60)
    print(sample_code)
    
    result = generate_tests_for_code(sample_code)
    
    print("\nGenerated Tests:")
    print("-" * 60)
    
    if result["success"]:
        print(f"\nLanguage: {result['language']}")
        print(f"Framework: {result['framework']}")
        print(f"Functions Tested: {result['functions_tested']}")
        
        for test in result["tests"]:
            print(f"\n{'=' * 60}")
            print(f"Function: {test['function']}")
            print(f"{'=' * 60}")
            print(test["test_code"])
    else:
        print(f"Error: {result['message']}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
