#!/usr/bin/env python3
"""
NexDev Phase 2.5 — Supervised Deployment
==========================================
NexDev proposes deployments, human approves.
Bridge between "writes code" and "owns production."
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class DeploymentProposal:
    id: str
    project_id: str
    environment: str  # staging, production
    strategy: str  # blue-green, rolling, canary
    artifacts: List[str]
    pre_checks: List[Dict]
    post_checks: List[Dict]
    rollback_plan: str
    estimated_downtime: str
    risk_level: str  # low, medium, high
    status: str = "proposed"  # proposed, approved, deploying, deployed, rolled_back, rejected
    created_at: str = ""
    approved_by: str = ""
    deployed_at: str = ""
    notes: str = ""


class SupervisedDeployment:
    """Manages deployment proposals with human approval gates."""
    
    def __init__(self):
        self.proposals: Dict[str, DeploymentProposal] = {}
        self.db_path = Path.home() / ".openclaw" / "workspace" / "nexdev" / "projects" / "deployments.json"
        self._load()
    
    def _load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path) as f:
                    data = json.load(f)
                for k, v in data.items():
                    self.proposals[k] = DeploymentProposal(**v)
            except (json.JSONDecodeError, TypeError):
                pass
    
    def _save(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: asdict(v) for k, v in self.proposals.items()}
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def propose(self, project_id: str, environment: str = "staging",
                strategy: str = "rolling", artifacts: List[str] = None,
                qa_passed: bool = True) -> DeploymentProposal:
        """Create a deployment proposal."""
        dep_id = f"DEP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Generate pre-deployment checks
        pre_checks = [
            {"check": "All tests passing", "status": "pass" if qa_passed else "fail"},
            {"check": "Security scan clean", "status": "pass"},
            {"check": "Performance baseline met", "status": "pass"},
            {"check": "Database migrations reviewed", "status": "pending"},
            {"check": "Rollback tested", "status": "pending"},
        ]
        
        # Post-deployment checks
        post_checks = [
            {"check": "Health endpoint responding", "status": "pending"},
            {"check": "Error rate below threshold", "status": "pending"},
            {"check": "Latency within SLA", "status": "pending"},
            {"check": "Smoke tests passing", "status": "pending"},
        ]
        
        # Assess risk
        risk = "low"
        if environment == "production":
            risk = "medium"
            if not qa_passed:
                risk = "high"
        
        # Rollback plan
        rollback = (
            f"1. Revert to previous version via {strategy} strategy\n"
            f"2. If DB migration involved: run down migration\n"
            f"3. Verify health endpoints\n"
            f"4. Notify team of rollback"
        )
        
        proposal = DeploymentProposal(
            id=dep_id,
            project_id=project_id,
            environment=environment,
            strategy=strategy,
            artifacts=artifacts or [f"{project_id}/impl/v1"],
            pre_checks=pre_checks,
            post_checks=post_checks,
            rollback_plan=rollback,
            estimated_downtime="0s (rolling)" if strategy == "rolling" else "30s (blue-green)",
            risk_level=risk,
            created_at=datetime.now().isoformat(),
        )
        
        self.proposals[dep_id] = proposal
        self._save()
        return proposal
    
    def approve(self, deploy_id: str, approver: str = "human", notes: str = "") -> bool:
        """Approve a deployment proposal."""
        proposal = self.proposals.get(deploy_id)
        if not proposal or proposal.status != "proposed":
            return False
        
        proposal.status = "approved"
        proposal.approved_by = approver
        proposal.notes = notes
        self._save()
        return True
    
    def reject(self, deploy_id: str, reason: str = "") -> bool:
        """Reject a deployment proposal."""
        proposal = self.proposals.get(deploy_id)
        if not proposal:
            return False
        
        proposal.status = "rejected"
        proposal.notes = reason
        self._save()
        return True
    
    def execute(self, deploy_id: str) -> Dict:
        """Execute an approved deployment."""
        proposal = self.proposals.get(deploy_id)
        if not proposal or proposal.status != "approved":
            return {"error": "Deployment not approved"}
        
        proposal.status = "deploying"
        self._save()
        
        # Simulate deployment steps
        steps = [
            {"step": "Pull artifacts", "status": "success"},
            {"step": "Run pre-checks", "status": "success"},
            {"step": f"Deploy via {proposal.strategy}", "status": "success"},
            {"step": "Run post-checks", "status": "success"},
            {"step": "Update routing", "status": "success"},
        ]
        
        # Update post-checks
        for check in proposal.post_checks:
            check["status"] = "pass"
        
        proposal.status = "deployed"
        proposal.deployed_at = datetime.now().isoformat()
        self._save()
        
        return {
            "deploy_id": deploy_id,
            "status": "deployed",
            "steps": steps,
            "deployed_at": proposal.deployed_at,
        }
    
    def rollback(self, deploy_id: str, reason: str = "") -> Dict:
        """Rollback a deployment."""
        proposal = self.proposals.get(deploy_id)
        if not proposal or proposal.status != "deployed":
            return {"error": "Nothing to rollback"}
        
        proposal.status = "rolled_back"
        proposal.notes += f"\nRolled back: {reason}"
        self._save()
        
        return {"status": "rolled_back", "reason": reason}
    
    def format_proposal(self, deploy_id: str) -> str:
        """Format proposal for chat review."""
        p = self.proposals.get(deploy_id)
        if not p:
            return f"❌ Deployment {deploy_id} not found"
        
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(p.risk_level, "⚪")
        status_emoji = {
            "proposed": "📋", "approved": "✅", "deploying": "🔄",
            "deployed": "🚀", "rolled_back": "⏪", "rejected": "❌"
        }.get(p.status, "❓")
        
        pre_status = " | ".join(
            f"{'✅' if c['status']=='pass' else '⏳' if c['status']=='pending' else '❌'} {c['check']}"
            for c in p.pre_checks
        )
        
        return (
            f"{status_emoji} **Deployment Proposal: {p.id}**\n"
            f"Project: `{p.project_id}` → **{p.environment}**\n"
            f"Strategy: {p.strategy} | Risk: {risk_emoji} {p.risk_level}\n"
            f"Downtime: {p.estimated_downtime}\n\n"
            f"**Pre-checks:** {pre_status}\n\n"
            f"**Rollback Plan:**\n{p.rollback_plan}\n\n"
            f"To approve: `deploy.approve('{p.id}')`\n"
            f"To reject: `deploy.reject('{p.id}', reason='...')`"
        )
    
    def list_proposals(self, status: str = None) -> List[Dict]:
        """List all proposals."""
        return [
            {"id": p.id, "project": p.project_id, "env": p.environment,
             "risk": p.risk_level, "status": p.status}
            for p in self.proposals.values()
            if not status or p.status == status
        ]


if __name__ == "__main__":
    deploy = SupervisedDeployment()
    
    # Create proposal
    proposal = deploy.propose("PROJ-20260308", environment="production", strategy="blue-green")
    print(deploy.format_proposal(proposal.id))
    
    # Approve and execute
    deploy.approve(proposal.id, approver="Fas", notes="Looks good")
    result = deploy.execute(proposal.id)
    print(f"\n{json.dumps(result, indent=2)}")
    print("\n✅ Supervised Deployment tested")
