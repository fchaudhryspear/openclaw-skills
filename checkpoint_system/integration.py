#!/usr/bin/env python3
"""
OpenClaw Integration Layer - Auto-checkpoint hooks for agent tools

This module provides automatic checkpoint triggers for OpenClaw agent operations:
- Pre-execution checkpoints before long-running commands
- Post-subagent spawn checkpoints  
- Context limit warnings with auto-save
- Manual checkpoint commands via message channels
"""

import os
import json
import time
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, Callable
from pathlib import Path
import threading


class AutoCheckpointIntegration:
    """
    Integrates checkpoint system with OpenClaw agent tools.
    
    Provides automatic checkpointing based on:
    - Time intervals
    - Token/usage limits
    - Critical operation triggers
    - User commands
    """
    
    def __init__(self, checkpoint_manager, wake_handler, config: Dict[str, Any] = None):
        """
        Initialize the integration layer.
        
        Args:
            checkpoint_manager: CheckpointManager instance
            wake_handler: WakeHandler instance
            config: Configuration dictionary
        """
        self.checkpoint_manager = checkpoint_manager
        self.wake_handler = wake_handler
        
        # Default configuration
        self.config = {
            "auto_checkpoint_interval_minutes": 10,
            "checkpoint_before_long_exec": True,
            "long_exec_threshold_seconds": 30,
            "checkpoint_before_subagent_spawn": True,
            "context_limit_warning_percent": 80,
            "max_context_tokens": 125000,  # Kimi K2 context window
            "backup_workspace": True,
            "enable_time_based": True,
            "event_based_triggers": True
        }
        
        if config:
            self.config.update(config)
        
        # Tracking state
        self._last_checkpoint_time = None
        self._checkpoint_timer_thread = None
        self._running = False
        self._pending_commands = []
        
        # Command handlers registry
        self._command_handlers = {}
    
    def start_background_monitor(self):
        """Start background monitoring for time-based checkpoints."""
        if self._running:
            return
        
        self._running = True
        interval_seconds = self.config["auto_checkpoint_interval_minutes"] * 60
        
        def monitor_loop():
            while self._running:
                time.sleep(interval_seconds)
                if self._running and self.config["enable_time_based"]:
                    self._trigger_auto_checkpoint(reason="time_interval")
        
        self._checkpoint_timer_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._checkpoint_timer_thread.start()
        print(f"✅ Auto-checkpoint monitor started (interval: {interval_seconds}s)")
    
    def stop_background_monitor(self):
        """Stop background monitoring."""
        self._running = False
        if self._checkpoint_timer_thread:
            self._checkpoint_timer_thread.join(timeout=5)
            self._checkpoint_timer_thread = None
        print("✅ Auto-checkpoint monitor stopped")
    
    def _trigger_auto_checkpoint(self, reason: str, context: Dict[str, Any] = None):
        """Trigger an automatic checkpoint."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n⚡ AUTO-CHECKPOINT TRIGGERED: {reason} at {timestamp}")
        
        # Build checkpoint context
        checkpoint_context = context or {}
        checkpoint_context["_auto_checkpoint"] = True
        checkpoint_context["_trigger_reason"] = reason
        checkpoint_context["_timestamp"] = timestamp
        
        # Save checkpoint
        workspace_root = os.environ.get("WORKSPACE_ROOT", 
                                       "/Users/faisalshomemacmini/.openclaw/workspace")
        
        try:
            path = self.checkpoint_manager.save_checkpoint(
                checkpoint_context,
                workspace_root=workspace_root if self.config["backup_workspace"] else None,
                include_workspace_diff=self.config["backup_workspace"],
                backup_deleted=True
            )
            print(f"✅ Auto-checkpoint saved: {path}")
            self._last_checkpoint_time = datetime.now()
        except Exception as e:
            print(f"❌ Auto-checkpoint failed: {e}")
    
    def should_checkpoint_before_tool(self, tool_name: str, params: Dict[str, Any]) -> bool:
        """
        Determine if a checkpoint should be taken before executing a tool.
        
        Args:
            tool_name: Name of the tool being called
            params: Tool parameters
            
        Returns:
            True if checkpoint recommended
        """
        if not self.config["event_based_triggers"]:
            return False
        
        # Long-running exec commands
        if tool_name == "exec":
            if self.config["checkpoint_before_long_exec"]:
                timeout = params.get("timeoutMs", 0) / 1000
                return timeout > self.config["long_exec_threshold_seconds"]
        
        # Subagent spawning
        if tool_name == "subagents" and params.get("action") != "list":
            return self.config["checkpoint_before_subagent_spawn"]
        
        # Browser navigation to external sites
        if tool_name == "browser":
            action = params.get("action")
            if action in ["open", "navigate"]:
                return True
        
        return False
    
    async def pre_tool_hook(self, tool_name: str, params: Dict[str, Any], 
                           current_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook that runs before tool execution.
        
        Can inject checkpoint context if needed.
        
        Args:
            tool_name: Name of tool being called
            params: Tool parameters
            current_context: Current agent context
            
        Returns:
            Updated context to use for this turn
        """
        if self.should_checkpoint_before_tool(tool_name, params):
            print(f"\n💾 PRE-EXEC CHECKPOINT: About to execute {tool_name}")
            
            # Add checkpoint marker to context
            current_context["_pre_exec_checkpoint_pending"] = {
                "tool": tool_name,
                "params": params,
                "timestamp": datetime.now().isoformat()
            }
        
        return current_context
    
    def post_tool_hook(self, tool_name: str, result: Any, 
                      context: Dict[str, Any]):
        """
        Hook that runs after tool execution.
        
        Can trigger immediate checkpoint if certain conditions met.
        
        Args:
            tool_name: Name of tool that was executed
            result: Tool result
            context: Agent context
        """
        # Remove checkpoint pending marker
        if "_pre_exec_checkpoint_pending" in context:
            del context["_pre_exec_checkpoint_pending"]
        
        # Optionally checkpoint successful critical operations
        if tool_name in ["exec", "subagents"] and isinstance(result, dict):
            if result.get("status") == "success" or result.get("exitCode", 0) == 0:
                # Could add logic here to checkpoint important results
    
                        pass
    
    def check_context_limit(self, token_count: int) -> Optional[Dict[str, Any]]:
        """
        Check if we're approaching context limits and suggest checkpoint.
        
        Args:
            token_count: Estimated current token count
            
        Returns:
            Warning dict if approaching limit, None otherwise
        """
        limit = self.config["max_context_tokens"]
        warning_threshold = int(limit * self.config["context_limit_warning_percent"] / 100)
        
        if token_count > warning_threshold:
            percent_used = (token_count / limit) * 100
            return {
                "warning": "CONTEXT_LIMIT_APPROACHING",
                "current_tokens": token_count,
                "limit": limit,
                "percent_used": percent_used,
                "suggestion": "Consider creating a checkpoint and restarting"
            }
        
        return None
    
    def handle_manual_checkpoint_command(self, message: str, 
                                        current_context: Dict[str, Any]) -> str:
        """
        Handle manual /checkpoint command from user.
        
        Args:
            message: Full command message
            current_context: Current agent context
            
        Returns:
            Response message
        """
        # Parse command options
        force = "--force" in message.lower()
        no_workspace = "--no-workspace" in message.lower()
        
        # Save checkpoint
        workspace_root = None if no_workspace else os.environ.get(
            "WORKSPACE_ROOT", 
            "/Users/faisalshomemacmini/.openclaw/workspace"
        )
        
        try:
            # Enhance context with metadata
            enhanced_context = {
                **current_context,
                "_manual_checkpoint": True,
                "_command": message,
                "_timestamp": datetime.now().isoformat()
            }
            
            path = self.checkpoint_manager.save_checkpoint(
                enhanced_context,
                workspace_root=workspace_root,
                include_workspace_diff=not no_workspace,
                backup_deleted=True
            )
            
            return f"✅ Checkpoint created successfully!\n📍 Location: {path}"
            
        except Exception as e:
            return f"❌ Failed to create checkpoint: {e}"
    
    def handle_wake_command(self, message: str) -> str:
        """
        Handle manual /wake command from user.
        
        Args:
            message: Full command message
            
        Returns:
            Response message
        """
        dry_run = "--dry-run" in message.lower()
        target = None
        
        # Parse target checkpoint ID if provided
        parts = message.split()
        for i, part in enumerate(parts):
            if part in ["--checkpoint", "-c"] and i + 1 < len(parts):
                target = parts[i + 1]
        
        try:
            context, path = self.wake_handler.wake_agent(
                target_checkpoint=target,
                restore_workspace=True,
                dry_run=dry_run
            )
            
            if not context:
                return "❌ No valid checkpoint found."
            
            status = "(DRY RUN)" if dry_run else ""
            return f"✅ Agent awakened successfully! {status}\n📍 From: {path}"
            
        except Exception as e:
            return f"❌ Wake failed: {e}"
    
    def register_command_handler(self, command: str, handler: Callable):
        """Register a custom command handler."""
        self._command_handlers[command] = handler
    
    def process_user_command(self, command: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Process a user command through registered handlers.
        
        Args:
            command: User command string
            context: Current agent context
            
        Returns:
            Response message or None if not handled
        """
        # Built-in handlers
        if command.lower().startswith("/checkpoint"):
            return self.handle_manual_checkpoint_command(command, context)
        
        if command.lower().startswith("/wake"):
            return self.handle_wake_command(command)
        
        # Custom handlers
        for prefix, handler in self._command_handlers.items():
            if command.lower().startswith(prefix):
                try:
                    return handler(command, context)
                except Exception as e:
                    return f"❌ Handler error: {e}"
        
        return None


class CheckpointContextInjector:
    """
    Middleware that injects checkpoint data into agent conversations.
    
    When an agent wakes from a checkpoint, this class helps reconstruct
    the conversation context and tool states.
    """
    
    def __init__(self, checkpoint_data: Dict[str, Any]):
        self.checkpoint_data = checkpoint_data
    
    def reconstruct_chat_history(self, max_messages: int = 20) -> list:
        """Reconstruct recent chat history from checkpoint."""
        history = self.checkpoint_data.get("chat_history", [])
        return history[-max_messages:] if history else []
    
    def get_active_task_plan(self) -> Optional[list]:
        """Get the current task plan."""
        return self.checkpoint_data.get("task_plan")
    
    def get_current_step(self) -> int:
        """Get the current step index."""
        return self.checkpoint_data.get("current_step", 0)
    
    def mark_step_complete(self) -> Dict[str, Any]:
        """Mark current step as complete and return updated context."""
        context = self.checkpoint_data.copy()
        current = context.get("current_step", 0)
        context["current_step"] = current + 1
        context["completed_steps"] = context.get("completed_steps", []) + [current]
        return context
    
    def get_memory_summary(self) -> str:
        """Generate a summary of stored memory items."""
        memory = self.checkpoint_data.get("memory", [])
        if not memory:
            return "No active memory items."
        
        summary = f"Active Memory ({len(memory)} items):\n"
        for i, item in enumerate(memory[-10:], 1):  # Last 10 items
            summary += f"  {i}. {item}\n"
        
        if len(memory) > 10:
            summary += f"  ... and {len(memory) - 10} more"
        
        return summary
    
    def get_workspace_changes_summary(self) -> str:
        """Summarize workspace changes since last checkpoint."""
        diff = self.checkpoint_data.get("workspace_diff", {})
        
        if not diff:
            return "No workspace changes recorded."
        
        summary = "Workspace Changes:\n"
        
        added = diff.get("added", [])
        if added:
            summary += f"  +{len(added)} files added\n"
            for f in added[:5]:
                summary += f"    • {f['path']}\n"
            if len(added) > 5:
                summary += f"    ... and {len(added) - 5} more\n"
        
        modified = diff.get("modified", [])
        if modified:
            summary += f"  ~{len(modified)} files modified\n"
            for f in modified[:5]:
                summary += f"    • {f['path']}\n"
        
        deleted = diff.get("deleted", [])
        if deleted:
            summary += f"  -{len(deleted)} files deleted\n"
            for f in deleted[:5]:
                summary += f"    • {f['path']}\n"
        
        return summary
    
    def generate_resumption_prompt(self) -> str:
        """Generate a prompt to help the agent resume from checkpoint."""
        lines = [
            "You are resuming work from a previous checkpoint.",
            "",
            self.get_memory_summary(),
            "",
            self.get_workspace_changes_summary(),
            "",
            "TASK STATUS:",
            f"  Plan: {len(self.get_active_task_plan())} steps" if self.get_active_task_plan() else "  No active task plan",
            f"  Current step: {self.get_current_step()}",
            "",
            "Continue your work from where you left off."
        ]
        
        return "\n".join(lines)


# Example usage demonstration
if __name__ == "__main__":
    from checkpoint_manager import CheckpointManager
    from wake_handler import WakeHandler
    from security_utils import SecurityUtils
    
    # Setup
    AGENT_ID = "test_integration"
    WORKSPACE_ROOT = "/Users/faisalshomemacmini/.openclaw/workspace"
    CHECKPOINT_BASE_DIR = "./.checkpoints"
    MASTER_KEY = os.urandom(32)
    
    security = SecurityUtils(MASTER_KEY)
    cp_manager = CheckpointManager(AGENT_ID, CHECKPOINT_BASE_DIR, security)
    wake_handler = WakeHandler(cp_manager, WORKSPACE_ROOT)
    
    # Create integration instance
    config = {
        "auto_checkpoint_interval_minutes": 5,
        "checkpoint_before_long_exec": True,
        "long_exec_threshold_seconds": 10,
        "backup_workspace": True
    }
    
    integration = AutoCheckpointIntegration(cp_manager, wake_handler, config)
    
    # Test pre-tool hook
    print("\n=== Testing Pre-Tool Hooks ===")
    
    test_cases = [
        ("exec", {"command": "sleep 60", "timeoutMs": 60000}),
        ("exec", {"command": "ls -la", "timeoutMs": 5000}),
        ("subagents", {"action": "spawn", "message": "do something"}),
        ("browser", {"action": "open", "targetUrl": "https://example.com"})
    ]
    
    for tool_name, params in test_cases:
        should_cp = integration.should_checkpoint_before_tool(tool_name, params)
        print(f"{tool_name}: {'✓ Should checkpoint' if should_cp else '○ Skip'}")
    
    # Test context limit checking
    print("\n=== Testing Context Limits ===")
    test_tokens = [50000, 100000, 110000, 120000]
    for tokens in test_tokens:
        warning = integration.check_context_limit(tokens)
        if warning:
            print(f"{tokens} tokens: ⚠️ {warning['percent_used']:.1f}% - {warning['suggestion']}")
        else:
            print(f"{tokens} tokens: ✓ Safe")
    
    # Test manual commands
    print("\n=== Testing Manual Commands ===")
    test_context = {
        "task_plan": ["step1", "step2"],
        "current_step": 1,
        "memory": ["test memory"]
    }
    
    response = integration.handle_manual_checkpoint_command("/checkpoint --force", test_context)
    print(response)
    
    response = integration.handle_wake_command("/wake --dry-run")
    print(response)
    
    # Cleanup
    import shutil
    shutil.rmtree(CHECKPOINT_BASE_DIR)
    integration.stop_background_monitor()
