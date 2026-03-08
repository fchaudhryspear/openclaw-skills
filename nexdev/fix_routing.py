#!/usr/bin/env python3
"""NexDev Integration Layer - Routing Fix Script
Fixes: topic-aware model selection + enhanced complexity estimation
Run: python3 fix_routing.py
"""
import pathlib

p = pathlib.Path(__file__).parent / 'integration_layer.py'
c = p.read_text()

# Fix 1: Enhanced complexity estimation
old_est = """    def _estimate_complexity(self, query: str) -> float:
        \"\"\"Quick complexity estimation\"\"\"
        complexity_score = 0.3
        
        high_complexity_keywords = [
            'design', 'architect', 'implement', 'refactor',
            'optimize', 'debug', 'troubleshoot', 'analyze'
        ]
        
        low_complexity_keywords = [
            'what', 'when', 'where', 'who', 'define', 'explain'
        ]
        
        query_lower = query.lower()
        
        for keyword in high_complexity_keywords:
            if keyword in query_lower:
                complexity_score += 0.1
        
        for keyword in low_complexity_keywords:
            if query_lower.startswith(keyword):
                complexity_score -= 0.1
        
        return max(0.2, min(0.95, complexity_score))"""

new_est = """    def _estimate_complexity(self, query: str) -> float:
        \"\"\"Enhanced complexity estimation with multi-word patterns\"\"\"
        score = 0.3
        q = query.lower()
        # High-value multi-word patterns (+0.25)
        for p in ['multi-tenant', 'from scratch', 'end to end', 'production ready',
                   'high availability', 'real-time', 'microservice']:
            if p in q:
                score += 0.25
        # High complexity keywords (+0.15)
        for k in ['design', 'architect', 'implement', 'refactor', 'optimize',
                   'debug', 'troubleshoot', 'analyze', 'migrate', 'deploy',
                   'integrate', 'scale', 'secure', 'automate', 'orchestrate',
                   'pipeline', 'infrastructure', 'authentication', 'authorization']:
            if k in q:
                score += 0.15
        # Medium complexity keywords (+0.1)
        for k in ['write', 'create', 'build', 'parse', 'function', 'class',
                   'api', 'endpoint', 'database', 'query', 'test', 'fix',
                   'lambda', 'cognito', 'docker', 'kubernetes', 'terraform']:
            if k in q:
                score += 0.1
        # Low complexity starters (-0.1)
        for s in ['what is', 'when is', 'where is', 'who is', 'define ', 'explain ']:
            if q.startswith(s):
                score -= 0.1
        # Length bonus
        if len(q.split()) > 15:
            score += 0.1
        elif len(q.split()) > 8:
            score += 0.05
        return max(0.2, min(0.95, score))"""

# Fix 2: Topic-aware model selection
old_sel = """    def _select_final_model(self, topic: str, complexity: float, preferred_model: str = None) -> str:
        \"\"\"Apply priority rules to select final model\"\"\"
        if preferred_model:
            return preferred_model
        
        if complexity >= 0.8:
            return 'Sonnet'
        elif complexity >= 0.6:
            return 'Qwen35'
        elif complexity >= 0.4:
            return 'GeminiFlash'
        else:
            return 'QwenFlash'"""

new_sel = """    def _select_final_model(self, topic: str, complexity: float, preferred_model: str = None) -> str:
        \"\"\"Topic-aware model routing\"\"\"
        if preferred_model:
            return preferred_model
        code_topics = {'authentication', 'lambda-development', 'api-development',
                       'web-development', 'debugging', 'refactoring', 'testing'}
        summary_topics = {'documentation', 'summarization', 'comparison', 'database-design'}
        arch_topics = {'system-architecture', 'infrastructure', 'multi-tenant', 'security-audit'}if complexity >= 0.8:
            return 'Sonnet'
        elif complexity >= 0.6:
            if topic in arch_topics:
                return 'Sonnet'
            return 'Qwen35'
        elif complexity >= 0.4:
            if topic in code_topics:
                return 'QwenCoder'
            if topic in summary_topics:
                return 'GeminiFlash'
            if topic in arch_topics:
                return 'Qwen35'
            return 'GeminiFlash'
        else:
            if topic in code_topics:
                return 'QwenCoder'
            return 'QwenFlash'"""

# Fix 3: Move complexity before early exit
old_early = """        # PHASE 5: Early Exit Check
        early_exit = await self._lazy_load_component('early_exit')
        if early_exit and self.config['features']['early_exit']:
            classification = early_exit.classify_query(query)
            result['routing_decisions']['early_exit'] = classification
            
            if classification.get('route_type') == 'fast_path':"""

new_early = """        # Estimate complexity BEFORE early exit
        complexity_score = self._estimate_complexity(query)
        result['routing_decisions']['complexity_score'] = complexity_score
        
        # PHASE 5: Early Exit (only for simple queries)
        early_exit = await self._lazy_load_component('early_exit')
        if early_exit and self.config['features']['early_exit']:
            classification = early_exit.classify_query(query)
            result['routing_decisions']['early_exit'] = classification
            
            if classification.get('route_type') == 'fast_path' and complexity_score < 0.4:"""

old_dup = """        # PHASE 6: Adaptive Threshold Calculation
        complexity_score = self._estimate_complexity(query)"""

new_dup = """        # PHASE 6: Adaptive Threshold Calculation (complexity already computed)"""

applied = []
if old_est in c:
    c = c.replace(old_est, new_est); applied.append('complexity')
if old_sel in c:
    c = c.replace(old_sel, new_sel); applied.append('model_select')
if old_early in c:
    c = c.replace(old_early, new_early); applied.append('early_exit')
if old_dup in c:
    c = c.replace(old_dup, new_dup); applied.append('dedup')

p.write_text(c)
print(f'Patches applied: {applied}')
if not applied:
    print('WARNING: No patches matched - file may already be patched or modified')
