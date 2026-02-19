
# orchestrator.py

import json
import hashlib
from datetime import datetime, timedelta

# --- Configuration ---
MODEL_CONFIG = {
    "grok": {"model_name": "xai/grok-4", "cost_per_million_tokens": 8.00}, # Placeholder
    "kimi": {"model_name": "moonshot/kimi-k2.5", "cost_per_million_tokens": 15.00}, # Placeholder
    "claude": {"model_name": "anthropic/claude-3-opus-20240229", "cost_per_million_tokens": 75.00}, # Placeholder
    "gemini_flash": {"model_name": "google/gemini-2.5-flash", "cost_per_million_tokens": 2.00} # Placeholder
}

# Model usage percentages from memory
USAGE_PERCENTAGES = {
    "grok": 0.60, # Simple extraction, Q&A
    "kimi": 0.30, # Style matching, long docs
    "claude": 0.10, # Reasoning, code, orchestration
    "gemini_flash": 1.00 # Default if no specific routing
}

# --- Writing Style Cache (Simplified for demonstration) ---
STYLE_CACHE = {} # { "user_id": {"style_vector": [...], "timestamp": "ISO_DATETIME"} }
CACHE_EXPIRATION_DAYS = 7

def get_writing_style(user_id):
    """Retrieves cached writing style or simulates generation."""
    if user_id in STYLE_CACHE and datetime.fromisoformat(STYLE_CACHE[user_id]["timestamp"]) > datetime.now() - timedelta(days=CACHE_EXPIRATION_DAYS):
        print(f"DEBUG: Using cached style for {user_id}")
        return STYLE_CACHE[user_id]["style_vector"]
    else:
        # Simulate style generation for now
        style = {"tone": "casual", "sarcasm_level": "medium", "conciseness": "direct"}
        STYLE_CACHE[user_id] = {"style_vector": style, "timestamp": datetime.now().isoformat()}
        print(f"DEBUG: Generating and caching new style for {user_id}")
        return style

# --- Model Abstraction (Dummy) ---
def call_llm(model_name, prompt, user_id=None, task_type="generic"):
    """Simulates calling an LLM and applies style if relevant."""
    print(f"DEBUG: Calling model '{model_name}' for task '{task_type}' with prompt: '{prompt[:50]}...'")

    response_prefix = f"[{model_name.split('/')[-1]}-response]"

    if task_type == "style_matching":
        style = get_writing_style(user_id)
        return f"{response_prefix} (Style Applied: {style}) Simulated response for '{prompt}'"
    else:
        return f"{response_prefix} Simulated response for '{prompt}'"

# --- Request Router ---
def route_request(prompt, user_id, task_type="generic", force_model=None):
    """
    Routes the request to the most appropriate LLM based on task type and configuration.
    Defaults to Gemini Flash for cost optimization unless explicitly routed.
    """
    target_model_key = "gemini_flash" # Default to Gemini Flash (cost optimization)

    if force_model:
        if force_model in MODEL_CONFIG:
            target_model_key = force_model
        else:
            print(f"WARNING: Forced model '{force_model}' not found in config. Defaulting to Gemini Flash.")
    elif task_type == "simple_extraction" or task_type == "qa":
        target_model_key = "grok"
    elif task_type == "style_matching" or task_type == "long_document_processing":
        target_model_key = "kimi"
    elif task_type == "reasoning" or task_type == "code_generation" or task_type == "orchestration":
        target_model_key = "claude"

    # Fallback/default logic for usage percentages (not strictly implemented in this routing,
    # but good to keep in mind for future statistical routing)
    # This current logic prioritizes task-based routing over simple percentage distribution.

    model_name = MODEL_CONFIG[target_model_key]["model_name"]
    response = call_llm(model_name, prompt, user_id, task_type)
    return response, target_model_key

# --- Example Usage ---
if __name__ == "__main__":
    fas_id = "Fas"

    print("\n--- Scenario 1: Simple Q&A (should use Grok) ---")
    response, model_used = route_request("What's the capital of France?", fas_id, task_type="qa")
    print(f"Response: {response}")
    print(f"Model Used: {model_used}\n")

    print("--- Scenario 2: Style Matching (should use Kimi and cache style) ---")
    response, model_used = route_request("Draft a casual email about a meeting.", fas_id, task_type="style_matching")
    print(f"Response: {response}")
    print(f"Model Used: {model_used}\n")

    print("--- Scenario 3: Complex Reasoning (should use Claude) ---")
    response, model_used = route_request("Explain quantum entanglement to a 5-year-old.", fas_id, task_type="reasoning")
    print(f"Response: {response}")
    print(f"Model Used: {model_used}\n")

    print("--- Scenario 4: Generic request (should default to Gemini Flash) ---")
    response, model_used = route_request("Tell me a short story.", fas_id)
    print(f"Response: {response}")
    print(f"Model Used: {model_used}\n")

    print("--- Scenario 5: Force a model (e.g., Grok) ---")
    response, model_used = route_request("Summarize the main points.", fas_id, force_model="grok")
    print(f"Response: {response}")
    print(f"Model Used: {model_used}\n")

    print("--- Scenario 6: Style Matching again (should use cached style) ---")
    response, model_used = route_request("Write another casual message.", fas_id, task_type="style_matching")
    print(f"Response: {response}")
    print(f"Model Used: {model_used}\n")

    # Simulate passing time
    STYLE_CACHE[fas_id]["timestamp"] = (datetime.now() - timedelta(days=CACHE_EXPIRATION_DAYS + 1)).isoformat()
    print("\n--- Scenario 7: Style Matching after cache expiration (should regenerate style) ---")
    response, model_used = route_request("One more casual note.", fas_id, task_type="style_matching")
    print(f"Response: {response}")
    print(f"Model Used: {model_used}\n")
