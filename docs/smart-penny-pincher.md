# Smart Penny Pincher with ClawVault Context

## Overview

Enhanced model routing system that queries ClawVault memory before selecting a model, tracks project progress, and maintains context across sessions.

## Core Principles

1. **Memory-First Routing** - Check ClawVault for previous related work before choosing a model
2. **Project State Persistence** - Track what steps are complete/in-progress
3. **Model Performance Learning** - Remember which models work best for which topics
4. **Cost Optimization** - Still prioritize cheap models, but with context awareness

## Model Selection Algorithm

```
1. Parse user query for:
   - Topic keywords
   - Project identifiers
   - Complexity indicators

2. Query ClawVault:
   - Previous similar queries
   - Last used model for this topic
   - Project state/progress
   - Previously successful approaches

3. Decision Tree:
   
   IF project_state EXISTS:
     - Continue with same model that was working
     - Load previous context
   
   ELSE IF similar_query FOUND in memory:
     - Use model that succeeded before
     - Reference previous solution
   
   ELSE IF complexity = HIGH:
     - Use capability-based selection (Sonnet/Opus)
   
   ELSE:
     - Use standard penny pincher chain
```

## Model Performance Tracking

Track success metrics per model per topic:

```json
{
  "model_performance": {
    "aws-lambda": {
      "GeminiFlash": {"success": 12, "cost": 0.50, "avg_time": 45},
      "Sonnet": {"success": 3, "cost": 18.00, "avg_time": 30}
    },
    "snowflake-auth": {
      "Kimi": {"success": 5, "cost": 3.10, "avg_time": 60}
    }
  }
}
```

## Project State Schema

```json
{
  "projects": {
    "data-lake-portal": {
      "status": "in_progress",
      "current_step": "cors-fixes",
      "completed_steps": [
        "lambda-deployment",
        "api-gateway-setup",
        "snowflake-connection"
      ],
      "pending_steps": [
        "user-management",
        "alert-system"
      ],
      "last_model": "Kimi",
      "last_session": "2026-02-20T22:00:00Z",
      "context_summary": "Fixing CORS issues on portal pages"
    }
  }
}
```

## Cost Optimization with Context

### Scenario 1: Continuing a Project
```
User: "fix the users page cors issue"
ClawVault Query: Found project "data-lake-portal", step "cors-fixes"
Last Model: Kimi (working well on this)
Decision: Use Kimi again for continuity
```

### Scenario 2: Similar Previous Query
```
User: "deploy another lambda function"
ClawVault Query: Found 12 previous lambda deployments using GeminiFlash
Success Rate: 100% with GeminiFlash
Decision: Use GeminiFlash (cheap + proven)
```

### Scenario 3: New Complex Topic
```
User: "design a kubernetes cluster"
ClawVault Query: No previous k8s work found
Complexity: HIGH (architecture design)
Decision: Start with Sonnet, track performance
```

## Implementation

### 1. Memory Query Function
```python
def query_project_state(topic):
    """Check ClawVault for existing project context"""
    # Search memory files for project markers
    # Return: project_id, current_step, last_model, context
    pass

def query_model_performance(topic):
    """Find best performing model for this topic"""
    # Check MODEL_PERFORMANCE.json in memory
    # Return: recommended_model, success_rate
    pass
```

### 2. Smart Router
```python
def smart_model_select(query, context):
    # Step 1: Check for active project
    project = query_project_state(extract_topic(query))
    if project and project['status'] == 'in_progress':
        return project['last_model'], project['context_summary']
    
    # Step 2: Check model performance history
    performance = query_model_performance(extract_topic(query))
    if performance['success_rate'] > 0.8:
        return performance['recommended_model'], None
    
    # Step 3: Standard penny pincher
    return penny_pincher_chain(query)
```

### 3. Project State Updates
```python
def update_project_state(project_id, step_completed, model_used):
    """Update ClawVault with project progress"""
    # Append to memory file
    # Track which model is working
    pass
```

## Usage in Agent

### Before Responding:
1. Parse user message for topic/project
2. Query ClawVault for context
3. Check HEARTBEAT.md for active projects
4. Select model based on findings
5. Include context in system prompt

### After Responding:
1. Update project state if applicable
2. Log model performance for topic
3. Save significant decisions to MEMORY.md

## Example Memory Structure

```
~/memory/
├── model_performance.json          # Model success tracking
├── active_projects.json            # Current project states
├── topic_model_mapping.json        # Best model per topic
└── 2026-02-20/
    ├── data-lake-portal-progress.md
    └── lambda-deployment-log.md
```

## Cost Benefits

- **Project Continuity**: Avoid switching models mid-project (reduces context loss)
- **Proven Approaches**: Use cheap models that have succeeded before
- **Failure Avoidance**: Don't use models that failed on similar tasks
- **Context Efficiency**: Less re-explaining = fewer tokens = lower cost

## Commands

```bash
# View model performance
/clawvault model-stats [topic]

# View project status  
/clawvault project-status [project-name]

# Force model override
/model [model-name] --reason "[why]"

# Mark project complete
/project complete [project-name]
```

## Integration with Existing System

This enhances (not replaces) the existing penny pincher:
- Still uses the cost-based model chain as fallback
- Adds intelligence layer on top
- Maintains all existing commands
- Backwards compatible

## Next Steps

1. Create `model_performance.json` tracking file
2. Implement `query_project_state()` function
3. Update model selection logic
4. Add project state management to HEARTBEAT.md
5. Test with active projects