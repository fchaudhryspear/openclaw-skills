#!/usr/bin/env python3
"""
NexDev Phase 1.2 — Test Generation Agent (Basic TDD)
=====================================================
Generates unit tests from function descriptions and code.
Supports Python, JavaScript/TypeScript, and Go.
"""

import json
import re
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class TestGenAgent:
    """Generates test scaffolding for TDD workflow."""
    
    TEMPLATES = {
        "python": {
            "import": "import pytest\nfrom unittest.mock import Mock, patch, MagicMock\n",
            "test_func": '''
def test_{name}_happy_path():
    """{description} - happy path"""
    # Arrange
    {arrange}
    
    # Act
    result = {call}
    
    # Assert
    {assert_stmt}


def test_{name}_edge_case():
    """{description} - edge case"""
    # Arrange — empty/null/boundary input
    {edge_arrange}
    
    # Act & Assert
    {edge_assert}


def test_{name}_error_handling():
    """{description} - error handling"""
    with pytest.raises({expected_error}):
        {error_call}
''',
            "class_test": '''
class Test{class_name}:
    """Tests for {class_name}"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.instance = {class_name}({init_args})
    
    {methods}
''',
        },
        "javascript": {
            "import": "const {{ describe, it, expect, beforeEach }} = require('@jest/globals');\n",
            "test_func": '''
describe('{name}', () => {{
  it('should handle happy path', () => {{
    // Arrange
    {arrange}
    
    // Act
    const result = {call};
    
    // Assert
    {assert_stmt}
  }});

  it('should handle edge cases', () => {{
    {edge_arrange}
    {edge_assert}
  }});

  it('should handle errors', () => {{
    expect(() => {{
      {error_call}
    }}).toThrow();
  }});
}});
''',
        },
    }
    
    def generate_from_description(self, description: str, 
                                   language: str = "python",
                                   function_name: str = None) -> str:
        """
        Generate test scaffolding from a natural language description.
        
        Args:
            description: What the function/module does
            language: Target language (python, javascript)
            function_name: Override function name
        
        Returns:
            Test code as string
        """
        name = function_name or self._extract_name(description)
        lang = language.lower()
        
        template = self.TEMPLATES.get(lang, self.TEMPLATES["python"])
        
        # Detect what kind of tests to generate
        test_type = self._classify_function(description)
        
        test_code = template["import"] + "\n"
        
        if test_type == "crud":
            test_code += self._generate_crud_tests(name, description, lang)
        elif test_type == "validation":
            test_code += self._generate_validation_tests(name, description, lang)
        elif test_type == "calculation":
            test_code += self._generate_calculation_tests(name, description, lang)
        elif test_type == "api":
            test_code += self._generate_api_tests(name, description, lang)
        else:
            test_code += self._generate_generic_tests(name, description, lang)
        
        return test_code
    
    def generate_from_code(self, source_code: str, 
                           language: str = "python") -> str:
        """
        Analyze source code and generate corresponding tests.
        
        Args:
            source_code: The actual source code to test
            language: Source language
        
        Returns:
            Test code as string
        """
        if language == "python":
            return self._analyze_python(source_code)
        elif language in ["javascript", "typescript"]:
            return self._analyze_javascript(source_code)
        else:
            return f"# Test generation for {language} not yet supported\n"
    
    def _extract_name(self, description: str) -> str:
        """Extract a function name from description."""
        words = description.lower().split()[:5]
        name = "_".join(w for w in words if w.isalnum())
        return name or "function_under_test"
    
    def _classify_function(self, description: str) -> str:
        """Classify what type of function this is."""
        desc = description.lower()
        if any(w in desc for w in ["create", "read", "update", "delete", "crud", "save", "fetch"]):
            return "crud"
        if any(w in desc for w in ["validate", "check", "verify", "ensure", "parse"]):
            return "validation"
        if any(w in desc for w in ["calculate", "compute", "sum", "average", "total", "convert"]):
            return "calculation"
        if any(w in desc for w in ["api", "endpoint", "request", "response", "route"]):
            return "api"
        return "generic"
    
    def _generate_crud_tests(self, name: str, desc: str, lang: str) -> str:
        """Generate CRUD operation tests."""
        if lang == "python":
            return f'''
# Tests for: {desc}

def test_{name}_create():
    """Test creating a new record"""
    # Arrange
    data = {{"name": "test", "value": "test_value"}}
    
    # Act
    result = {name}(data)
    
    # Assert
    assert result is not None
    assert result.get("id") is not None
    assert result["name"] == "test"


def test_{name}_create_missing_required():
    """Test creating with missing required fields"""
    with pytest.raises((ValueError, KeyError)):
        {name}({{}})


def test_{name}_read():
    """Test reading an existing record"""
    # Arrange
    test_id = "test-id-123"
    
    # Act
    result = get_{name}(test_id)
    
    # Assert
    assert result is not None
    assert result["id"] == test_id


def test_{name}_read_not_found():
    """Test reading a non-existent record"""
    result = get_{name}("nonexistent-id")
    assert result is None


def test_{name}_update():
    """Test updating an existing record"""
    test_id = "test-id-123"
    updates = {{"name": "updated"}}
    
    result = update_{name}(test_id, updates)
    
    assert result["name"] == "updated"


def test_{name}_delete():
    """Test deleting a record"""
    test_id = "test-id-123"
    
    result = delete_{name}(test_id)
    
    assert result is True
    assert get_{name}(test_id) is None
'''
        return f"// CRUD tests for {name}\n"
    
    def _generate_validation_tests(self, name: str, desc: str, lang: str) -> str:
        """Generate validation tests."""
        if lang == "python":
            return f'''
# Tests for: {desc}

def test_{name}_valid_input():
    """Test with valid input"""
    assert {name}("valid_input") is True


def test_{name}_empty_input():
    """Test with empty input"""
    assert {name}("") is False


def test_{name}_none_input():
    """Test with None input"""
    with pytest.raises(TypeError):
        {name}(None)


def test_{name}_boundary_values():
    """Test boundary values"""
    # Min boundary
    assert {name}("a") is True  # or False depending on rules
    
    # Max boundary
    assert {name}("a" * 10000) is False  # Likely exceeds limits


def test_{name}_special_characters():
    """Test with special characters"""
    assert {name}("<script>alert('xss')</script>") is False
    assert {name}("Robert'); DROP TABLE users;--") is False
'''
        return f"// Validation tests for {name}\n"
    
    def _generate_calculation_tests(self, name: str, desc: str, lang: str) -> str:
        """Generate calculation tests."""
        if lang == "python":
            return f'''
# Tests for: {desc}

def test_{name}_basic():
    """Test basic calculation"""
    result = {name}(10, 20)
    assert result == 30  # Adjust expected value


def test_{name}_zero():
    """Test with zero values"""
    result = {name}(0, 0)
    assert result == 0


def test_{name}_negative():
    """Test with negative values"""
    result = {name}(-5, 10)
    assert result == 5  # Adjust expected


def test_{name}_large_numbers():
    """Test with very large numbers"""
    result = {name}(10**18, 10**18)
    assert isinstance(result, (int, float))


def test_{name}_floating_point():
    """Test floating point precision"""
    result = {name}(0.1, 0.2)
    assert abs(result - 0.3) < 1e-9  # Float comparison
'''
        return f"// Calculation tests for {name}\n"
    
    def _generate_api_tests(self, name: str, desc: str, lang: str) -> str:
        """Generate API endpoint tests."""
        if lang == "python":
            return f'''
# Tests for: {desc}

@pytest.fixture
def client():
    """Test client fixture"""
    # Replace with your app's test client setup
    from app import create_app
    app = create_app(testing=True)
    return app.test_client()


def test_{name}_success(client):
    """Test successful API call"""
    response = client.get("/api/{name}")
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None


def test_{name}_not_found(client):
    """Test 404 response"""
    response = client.get("/api/{name}/nonexistent")
    assert response.status_code == 404


def test_{name}_unauthorized(client):
    """Test unauthorized access"""
    response = client.get("/api/{name}")
    # Without auth header
    assert response.status_code in [401, 403]


def test_{name}_bad_request(client):
    """Test malformed request"""
    response = client.post("/api/{name}", json={{}})
    assert response.status_code == 400


def test_{name}_method_not_allowed(client):
    """Test wrong HTTP method"""
    response = client.delete("/api/{name}")
    assert response.status_code == 405
'''
        return f"// API tests for {name}\n"
    
    def _generate_generic_tests(self, name: str, desc: str, lang: str) -> str:
        """Generate generic test scaffolding."""
        if lang == "python":
            return f'''
# Tests for: {desc}

def test_{name}_returns_expected_type():
    """Test that function returns expected type"""
    result = {name}()
    assert result is not None
    # assert isinstance(result, expected_type)


def test_{name}_handles_empty_input():
    """Test empty input handling"""
    result = {name}("")
    assert result is not None  # or raises


def test_{name}_handles_none():
    """Test None handling"""
    with pytest.raises((TypeError, ValueError)):
        {name}(None)


def test_{name}_idempotent():
    """Test that repeated calls produce same result"""
    result1 = {name}("same_input")
    result2 = {name}("same_input")
    assert result1 == result2
'''
        return f"// Generic tests for {name}\n"
    
    def _analyze_python(self, source: str) -> str:
        """Analyze Python source and generate tests."""
        tests = ["import pytest\n"]
        
        # Find functions
        func_pattern = r'def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*\w+)?:'
        for match in re.finditer(func_pattern, source):
            func_name = match.group(1)
            params = match.group(2)
            
            if func_name.startswith('_'):
                continue  # Skip private
            
            # Get docstring if available
            doc_pattern = rf'def\s+{func_name}\s*\([^)]*\)[^:]*:\s*"""([^"]*?)"""'
            doc_match = re.search(doc_pattern, source)
            description = doc_match.group(1) if doc_match else f"Test {func_name}"
            
            tests.append(self.generate_from_description(
                description, "python", func_name
            ))
        
        # Find classes
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, source):
            class_name = match.group(1)
            tests.append(f"\n\nclass Test{class_name}:\n")
            tests.append(f'    """Tests for {class_name}"""\n\n')
            tests.append(f"    def setup_method(self):\n")
            tests.append(f"        self.instance = {class_name}()\n\n")
            tests.append(f"    def test_init(self):\n")
            tests.append(f"        assert self.instance is not None\n")
        
        return "\n".join(tests)
    
    def _analyze_javascript(self, source: str) -> str:
        """Analyze JavaScript source and generate tests."""
        tests = ["const { describe, it, expect } = require('@jest/globals');\n"]
        
        # Find exported functions
        func_patterns = [
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)',
            r'(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(',
        ]
        
        for pattern in func_patterns:
            for match in re.finditer(pattern, source):
                func_name = match.group(1)
                tests.append(self.generate_from_description(
                    f"Test {func_name}", "javascript", func_name
                ))
        
        return "\n".join(tests)


if __name__ == "__main__":
    tg = TestGenAgent()
    
    # Generate from description
    print("=== From Description ===")
    tests = tg.generate_from_description(
        "Calculate the total cost of items in a shopping cart",
        language="python",
        function_name="calculate_cart_total"
    )
    print(tests)
    
    # Generate from code
    print("\n=== From Code ===")
    sample_code = '''
def validate_email(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def create_user(name: str, email: str) -> dict:
    """Create a new user"""
    if not name or not email:
        raise ValueError("Name and email required")
    return {"id": "uuid", "name": name, "email": email}
'''
    tests = tg.generate_from_code(sample_code, "python")
    print(tests[:1000])
