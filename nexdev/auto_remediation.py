#!/usr/bin/env python3
"""
NexDev v3.0 - Track A: Self-Healing
Auto-Remediation Engine

Detects runtime errors from logs → analyzes root cause → generates patches → validates fixes
"""

import re
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime

# Local imports
try:
    from code_reviewer import CodeReviewer
    from engine import NexDevEngine
except ImportError:
    # Fallback for standalone execution
    pass


class AutoRemediation:
    """Automatically diagnose and fix runtime errors"""
    
    ERROR_PATTERNS = {
        'syntax_error': r'SyntaxError[:\s]+(.+)',
        'name_error': r"NameError[:\s]+name '(\w+)' is not defined",
        'attribute_error': r"AttributeError[:\s]+'(\w+)' object has no attribute '(\w+)'",
        'type_error': r'TypeError[:\s]+(.+)',
        'key_error': r"KeyError[:\s]+['\"]?(\w+)['\"]?",
        'file_not_found': r'FileNotFoundError[:\s]+\[Errno 2\] (.+)',
        'permission_denied': r'PermissionError[:\s]+\[Errno (\d+)\] (.+)',
        'import_error': r'ImportError[:\s]+(.+)',
        'timeout': r'(Timeout|timed out)[:\s]+(.+)',
        'connection_error': r'(ConnectionError|ConnectionRefusedError)[:\s]+(.+)',
        'memory_error': r'MemoryError[:\s]+(.+)',
        'division_by_zero': r'ZeroDivisionError[:\s]+(.+)',
        'validation_error': r'ValidationError[:\s]+(.+)',
        'database_error': r'(DatabaseError|OperationalError|psycopg2.+.Error)[:\s]+(.+)',
        'sql_injection': r'(SQL injection|syntax error near|UNION SELECT)',
        'null_pointer': r'(NullPointerException|NoneType.+has no attribute)',
    }
    
    # FIX_STRATEGIES defined after class (functions not available during class definition)
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.reviewer = CodeReviewer() if 'CodeReviewer' in dir() else None
        self.engine = NexDevEngine() if 'NexDevEngine' in dir() else None
        self.remediation_log = Path.home() / '.openclaw' / 'workspace' / 'nexdev' / 'logs' / 'remediation.jsonl'
        self.remediation_log.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize FIX_STRATEGIES after class definition
        self.FIX_STRATEGIES = {
            'name_error': self_fix_name_error,
            'attribute_error': self_fix_attribute_error,
            'import_error': self_fix_import_error,
            'file_not_found': self_fix_file_access,
            'permission_denied': self_fix_permissions,
            'syntax_error': self_fix_syntax,
            'type_error': self_fix_type_mismatch,
            'key_error': self_fix_key_error,
            'database_error': self_fix_database_connection,
            'timeout': self_fix_timeout,
        }
        
    def _load_config(self, config_path: str) -> Dict:
        default_config = {
            'auto_apply': False,  # Require human approval by default
            'max_fix_attempts': 3,
            'rollback_on_failure': True,
            'notify_on_success': True,
            'notify_on_failure': True,
            'severity_thresholds': {
                'critical': ['memory_error', 'security'],
                'high': ['database_error', 'connection_error'],
                'medium': ['timeout', 'type_error'],
                'low': ['name_error', 'syntax_error']
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
        
    def analyze_error(self, error_log: str, context: Dict = None) -> Dict:
        """
        Analyze error log to identify root cause
        
        Args:
            error_log: Full error traceback or message
            context: Optional code context, file paths, stack trace
            
        Returns:
            Diagnostic report with error type, confidence, and suggested fix
        """
        diagnostic = {
            'timestamp': datetime.now().isoformat(),
            'error_type': None,
            'confidence': 0.0,
            'description': None,
            'affected_files': [],
            'suggested_fixes': [],
            'severity': 'unknown',
            'root_cause': None
        }
        
        # Pattern matching for common errors
        for error_type, pattern in self.ERROR_PATTERNS.items():
            match = re.search(pattern, error_log, re.IGNORECASE | re.MULTILINE)
            if match:
                diagnostic['error_type'] = error_type
                diagnostic['confidence'] = 0.85
                diagnostic['description'] = match.group(0)[:200]
                
                # Assign severity based on error type
                for severity, types in self.config['severity_thresholds'].items():
                    if error_type in types:
                        diagnostic['severity'] = severity
                        break
                        
                # Extract additional context
                if 'line' in error_log.lower():
                    line_match = re.search(r'line (\d+)', error_log)
                    if line_match:
                        diagnostic['line_number'] = int(line_match.group(1))
                        
                if 'file' in error_log.lower():
                    file_matches = re.findall(r'File "([^"]+)"', error_log)
                    diagnostic['affected_files'] = list(set(file_matches))
                    
                break
                
        # If pattern matching failed, use LLM analysis
        if not diagnostic['error_type']:
            llm_diagnostic = self._llm_diagnose(error_log, context)
            diagnostic.update(llm_diagnostic)
            
        return diagnostic
        
    def generate_patch(self, diagnostic: Dict, source_code: str = None) -> Dict:
        """
        Generate code patch to fix the identified error
        
        Args:
            diagnostic: Error diagnostic from analyze_error()
            source_code: Original source code (optional)
            
        Returns:
            Patch proposal with diff and explanation
        """
        if not diagnostic.get('error_type'):
            return {'status': 'error', 'message': 'No error type identified'}
            
        fix_strategy = self.FIX_STRATEGIES.get(diagnostic['error_type'])
        
        if fix_strategy:
            patch = fix_strategy(diagnostic, source_code)
        else:
            # Fall back to LLM-based fix generation
            patch = self._llm_generate_fix(diagnostic, source_code)
            
        # Validate the patch
        validation = self._validate_patch(patch, source_code)
        patch['validation'] = validation
        
        return patch
        
    def apply_patch(self, patch: Dict, dry_run: bool = True) -> Dict:
        """
        Apply the generated patch to the target file(s)
        
        Args:
            patch: Patch dictionary from generate_patch()
            dry_run: If True, only simulate the changes
            
        Returns:
            Application result with status and details
        """
        result = {
            'status': 'pending',
            'applied': False,
            'backup_created': False,
            'changes_applied': [],
            'rollback_available': False
        }
        
        if not patch.get('target_file'):
            return {'status': 'error', 'message': 'No target file specified'}
            
        target = Path(patch['target_file'])
        
        if not target.exists():
            return {'status': 'error', 'message': f"Target file not found: {target}"}
            
        # Create backup before applying
        if not dry_run and self.config['rollback_on_failure']:
            backup_path = target.with_suffix(target.suffix + '.bak.' + datetime.now().strftime('%Y%m%d%H%M%S'))
            backup_path.write_text(target.read_text())
            result['backup_created'] = True
            result['backup_path'] = str(backup_path)
            result['rollback_available'] = True
            
        # Parse and apply the patch
        try:
            if 'diff' in patch:
                # Unified diff format
                applied_lines = self._apply_unified_diff(target, patch['diff'], dry_run)
            elif 'replacement' in patch:
                # Direct replacement
                old_content = target.read_text()
                new_content = old_content.replace(patch['old_text'], patch['replacement'])
                
                if not dry_run:
                    target.write_text(new_content)
                    result['applied'] = True
                    
                result['changes_applied'] = [{
                    'file': str(target),
                    'old_text': patch['old_text'][:100],
                    'new_text': patch['replacement'][:100],
                    'lines_changed': new_content.count('\n') - old_content.count('\n')
                }]
                
        except Exception as e:
            return {
                'status': 'failed',
                'message': str(e),
                'applied': False
            }
            
        result['status'] = 'success' if dry_run or result['applied'] else 'simulated'
        
        # Log the remediation attempt
        self._log_remediation({
            'action': 'patch_application',
            'result': result,
            'dry_run': dry_run,
            'timestamp': datetime.now().isoformat()
        })
        
        return result
        
    def _llm_diagnose(self, error_log: str, context: Dict = None) -> Dict:
        """Use LLM to analyze unknown error patterns"""
        prompt = """Analyze this error log and provide a diagnosis:

ERROR:
{}

{}

Provide JSON response with:
{{
    "error_type": "<category>",
    "confidence": <0.0-1.0>,
    "description": "<brief explanation>",
    "severity": "critical|high|medium|low",
    "root_cause": "<what caused this>"
}}""".format(error_log[:1000], '\nCONTEXT:\n' + str(context) if context else '')
        
        # This would call the engine with appropriate model
        # For now, return a placeholder
        return {
            'error_type': 'unknown',
            'confidence': 0.5,
            'description': 'Unable to classify error automatically',
            'severity': 'medium'
        }
        
    def _llm_generate_fix(self, diagnostic: Dict, source_code: str = None) -> Dict:
        """Use LLM to generate fix when strategy not available"""
        # Placeholder - would call engine with diagnostic context
        return {
            'status': 'generated',
            'target_file': diagnostic.get('affected_files', [None])[0],
            'explanation': 'Fix generated via AI analysis',
            'replacement': '# TODO: Manual review required'
        }
        
    def _validate_patch(self, patch: Dict, source_code: str = None) -> Dict:
        """Validate that the patch is safe to apply"""
        validation = {
            'syntax_valid': True,
            'secure': True,
            'non_breaking': True,
            'issues': []
        }
        
        # Check for obvious security issues
        dangerous_patterns = ['eval(', 'exec(', '__import__', 'os.system', 'subprocess.call']
        replacement = patch.get('replacement', '')
        
        for pattern in dangerous_patterns:
            if pattern in replacement:
                validation['secure'] = False
                validation['issues'].append(f'Dangerous pattern detected: {pattern}')
                
        # Check syntax if we have a Python snippet
        if source_code and patch.get('replacement'):
            try:
                compile(replacement, '<patch>', 'exec')
                validation['syntax_valid'] = True
            except SyntaxError as e:
                validation['syntax_valid'] = False
                validation['issues'].append(f'Syntax error: {e}')
                
        return validation
        
    def _apply_unified_diff(self, target_file: Path, diff_text: str, dry_run: bool) -> List:
        """Apply unified diff format patch"""
        # Simplified diff parsing - real implementation would use difflib
        lines = []
        
        if not dry_run:
            content = target_file.read_text()
            modified = content  # Apply diff logic here
            target_file.write_text(modified)
            
        return lines
        
    def _log_remediation(self, entry: Dict):
        """Log remediation attempt to JSONL file"""
        entry['timestamp'] = datetime.now().isoformat()
        
        with open(self.remediation_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')


def self_fix_name_error(diagnostic: Dict, source_code: str = None) -> Dict:
    """Fix strategy for NameError"""
    match = re.search(r"name '(\w+)' is not defined", diagnostic.get('description', ''))
    if match:
        undefined_var = match.group(1)
        
        return {
            'strategy': 'name_error_fix',
            'target_file': diagnostic.get('affected_files', [None])[0],
            'explanation': f"Variable '{undefined_var}' is used before definition",
            'suggestions': [
                f"Define '{undefined_var}' before use",
                f"Check for typos in variable name",
                f"Verify import statements if it should be from another module"
            ],
            'old_text': undefined_var,
            'replacement': f"# TODO: Define {undefined_var} before use\n{undefined_var}"
        }
        
    return {'status': 'unknown', 'message': 'Could not parse NameError'}


def self_fix_attribute_error(diagnostic: Dict, source_code: str = None) -> Dict:
    """Fix strategy for AttributeError"""
    match = re.search(r"'(\w+)' object has no attribute '(\w+)'", diagnostic.get('description', ''))
    if match:
        obj_type, missing_attr = match.groups()
        
        return {
            'strategy': 'attribute_error_fix',
            'target_file': diagnostic.get('affected_files', [None])[0],
            'explanation': f"'{obj_type}' object has no attribute '{missing_attr}'",
            'suggestions': [
                f"Check if attribute name is correct (typos?)",
                f"Ensure object is properly initialized",
                f"Add property/attribute '{missing_attr}' to class definition"
            ]
        }
        
    return {'status': 'unknown', 'message': 'Could not parse AttributeError'}


def self_fix_import_error(diagnostic: Dict, source_code: str = None) -> Dict:
    """Fix strategy for ImportError"""
    match = re.search(r"No module named '(\w+)'", diagnostic.get('description', ''))
    if match:
        missing_module = match.group(1)
        
        return {
            'strategy': 'import_error_fix',
            'target_file': diagnostic.get('affected_files', [None])[0],
            'explanation': f"Module '{missing_module}' is not installed",
            'suggestions': [
                f"Run: pip install {missing_module}",
                f"Check if module name is correct",
                f"Verify virtual environment activation"
            ],
            'pip_install_command': f"pip install {missing_module}"
        }
        
    return {'status': 'unknown', 'message': 'Could not parse ImportError'}


def self_fix_file_access(diagnostic: Dict, source_code: str = None) -> Dict:
    """Fix strategy for FileNotFoundError"""
    match = re.search(r"\[Errno 2\] (.+)", diagnostic.get('description', ''))
    if match:
        file_desc = match.group(1)
        
        return {
            'strategy': 'file_not_found_fix',
            'target_file': diagnostic.get('affected_files', [None])[0],
            'explanation': f"File or directory not found: {file_desc}",
            'suggestions': [
                "Verify file path is correct",
                "Check if file exists at expected location",
                "Use os.path.exists() check before accessing",
                "Consider using pathlib.Path with proper error handling"
            ]
        }
        
    return {'status': 'unknown', 'message': 'Could not parse FileNotFoundError'}


def self_fix_permissions(diagnostic: Dict, source_code: str = None) -> Dict:
    """Fix strategy for PermissionError"""
    return {
        'strategy': 'permission_fix',
        'target_file': diagnostic.get('affected_files', [None])[0],
        'explanation': 'Permission denied - insufficient access rights',
        'suggestions': [
            'Check file/directory permissions (chmod)',
            'Verify user has write access',
            'Run with appropriate privileges if needed'
        ]
    }


def self_fix_syntax(diagnostic: Dict, source_code: str = None) -> Dict:
    """Fix strategy for SyntaxError"""
    target_file = diagnostic.get('affected_files', [])
    
    return {
        'strategy': 'syntax_fix',
        'target_file': target_file[0] if target_file else 'Unknown',
        'explanation': 'Syntax error detected',
        'suggestions': [
            'Check for missing colons, parentheses, or quotes',
            'Verify indentation is consistent (spaces vs tabs)',
            'Look for incomplete statements'
        ]
    }


def self_fix_type_mismatch(diagnostic: Dict, source_code: str = None) -> Dict:
    """Fix strategy for TypeError"""
    return {
        'strategy': 'type_error_fix',
        'target_file': diagnostic.get('affected_files', [None])[0],
        'explanation': 'Type mismatch in operation',
        'suggestions': [
            'Check operand types before operation',
            'Add type conversions if needed (int(), str(), etc.)',
            'Verify function expects provided argument types'
        ]
    }


def self_fix_key_error(diagnostic: Dict, source_code: str = None) -> Dict:
    """Fix strategy for KeyError"""
    match = re.search(r"KeyError[:\s]+['\"]?(\w+)['\"]?", diagnostic.get('description', ''))
    if match:
        missing_key = match.group(1)
        
        return {
            'strategy': 'key_error_fix',
            'target_file': diagnostic.get('affected_files', [None])[0],
            'explanation': f"Dictionary key '{missing_key}' not found",
            'suggestions': [
                f"Use dict.get('{missing_key}', default) instead of direct access",
                f"Check if key exists with '{missing_key}' in dict before accessing",
                f"Add exception handling for missing keys"
            ],
            'code_example': f"# Use .get() method:\nvalue = my_dict.get('{missing_key}', default_value)"
        }
        
    return {'status': 'unknown', 'message': 'Could not parse KeyError'}


def self_fix_database_connection(diagnostic: Dict, source_code: str = None) -> Dict:
    """Fix strategy for DatabaseError"""
    return {
        'strategy': 'database_fix',
        'target_file': diagnostic.get('affected_files', [None])[0],
        'explanation': 'Database connection or query error',
        'suggestions': [
            'Verify database credentials are correct',
            'Check database server is running',
            'Verify network connectivity to database host',
            'Check connection pool settings',
            'Validate SQL query syntax'
        ]
    }


def self_fix_timeout(diagnostic: Dict, source_code: str = None) -> Dict:
    """Fix strategy for Timeout errors"""
    return {
        'strategy': 'timeout_fix',
        'target_file': diagnostic.get('affected_files', [None])[0],
        'explanation': 'Operation timed out',
        'suggestions': [
            'Increase timeout value if operation legitimately takes longer',
            'Add retry logic with exponential backoff',
            'Optimize the underlying operation for performance',
            'Implement circuit breaker pattern for repeated failures'
        ]
    }


# CLI Entry Point
if __name__ == '__main__':
    import sys
    
    print("NexDev Auto-Remediation Engine v3.0")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage: python auto_remediation.py '<error_log>'")
        print("\nExample:")
        print("  python auto_remediation.py \"NameError: name 'x' is not defined\"")
        sys.exit(1)
        
    error_log = sys.argv[1]
    
    analyzer = AutoRemediation()
    
    # Diagnose
    print("\n🔍 Diagnosing error...")
    diagnostic = analyzer.analyze_error(error_log)
    print(json.dumps(diagnostic, indent=2))
    
    # Generate patch
    if diagnostic.get('error_type'):
        print("\n🔧 Generating fix...")
        patch = analyzer.generate_patch(diagnostic)
        print(json.dumps(patch, indent=2))
        
        # Show preview
        print("\n💡 Suggested fix:")
        print(f"  Target: {patch.get('target_file', 'Unknown')}")
        print(f"  Strategy: {patch.get('strategy', 'Unknown')}")
        print(f"  Explanation: {patch.get('explanation', 'N/A')}")
