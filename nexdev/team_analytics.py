#!/usr/bin/env python3
"""
NexDev Team Velocity Analytics (Phase 3 Feature)

Track throughput, cycle time, bug rates, and team performance metrics.
Provides data-driven insights for sprint planning and continuous improvement.
Part of NexDev v3.0 World-Class Build Team Upgrade
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3

ANALYTICS_DB_PATH = Path.home() / ".openclaw/workspace/nexdev/analytics.db"


@dataclass
class TaskMetric:
    """Represents task completion metrics."""
    task_id: str
    story_points: int
    created_date: datetime
    started_date: datetime
    completed_date: datetime
    assigned_to: str
    status: str  # "completed", "in_progress", "blocked"
    priority: str  # "critical", "high", "medium", "low"
    type: str  # "feature", "bug", "tech_debt", "chore"


def init_analytics_db():
    """Initialize analytics database schema."""
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            story_points INTEGER,
            created_date TEXT,
            started_date TEXT,
            completed_date TEXT,
            assigned_to TEXT,
            status TEXT,
            priority TEXT,
            type TEXT,
            sprint_number INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sprint_metrics (
            sprint_number INTEGER PRIMARY KEY,
            start_date TEXT,
            end_date TEXT,
            planned_points INTEGER,
            completed_points INTEGER,
            carryover_points INTEGER,
            burndown_daily TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_name TEXT,
            date_range_start TEXT,
            date_range_end TEXT,
            tasks_completed INTEGER,
            points_delivered INTEGER,
            avg_cycle_time_hours REAL,
            bug_rate REAL,
            UNIQUE(member_name, date_range_start, date_range_end)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_priority ON tasks(priority)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_type ON tasks(type)')
    
    conn.commit()
    conn.close()


def add_task(task: TaskMetric):
    """Add or update task metric."""
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO tasks 
        (task_id, story_points, created_date, started_date, completed_date, 
         assigned_to, status, priority, type, sprint_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        task.task_id,
        task.story_points,
        task.created_date.isoformat(),
        task.started_date.isoformat() if task.started_date else None,
        task.completed_date.isoformat() if task.completed_date else None,
        task.assigned_to,
        task.status,
        task.priority,
        task.type,
        None  # Sprint number TBD
    ))
    
    conn.commit()
    conn.close()


def get_completed_tasks(days: int = 30) -> List[TaskMetric]:
    """Get tasks completed in last N days."""
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    cursor.execute('''
        SELECT task_id, story_points, created_date, started_date, completed_date,
               assigned_to, status, priority, type, sprint_number
        FROM tasks
        WHERE completed_date IS NOT NULL AND completed_date >= ?
    ''', (cutoff_date,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        TaskMetric(
            task_id=row[0],
            story_points=row[1],
            created_date=datetime.fromisoformat(row[2]) if row[2] else datetime.now(),
            started_date=datetime.fromisoformat(row[3]) if row[3] else None,
            completed_date=datetime.fromisoformat(row[4]) if row[4] else None,
            assigned_to=row[5],
            status=row[6],
            priority=row[7],
            type=row[8]
        )
        for row in rows
    ]


def calculate_velocity(sprint_number: int) -> Dict[str, Any]:
    """Calculate velocity for a specific sprint."""
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT SUM(story_points), COUNT(*)
        FROM tasks
        WHERE sprint_number = ? AND status = 'completed'
    ''', (sprint_number,))
    
    row = cursor.fetchone()
    conn.close()
    
    completed_points = row[0] or 0
    completed_count = row[1] or 0
    
    return {
        "sprint": sprint_number,
        "completed_points": completed_points,
        "completed_tasks": completed_count
    }


def calculate_cycle_time(task: TaskMetric) -> Optional[float]:
    """Calculate cycle time in hours for a task."""
    if not task.started_date or not task.completed_date:
        return None
    
    duration = task.completed_date - task.started_date
    return duration.total_seconds() / 3600


def get_team_velocity(team_members: List[str], weeks: int = 8) -> Dict[str, Any]:
    """
    Calculate team velocity over past N weeks.
    
    Args:
        team_members: List of team member names
        weeks: Number of weeks to analyze
        
    Returns:
        Dictionary with velocity trends
    """
    completed_tasks = get_completed_tasks(days=weeks * 7)
    
    # Filter by team members
    team_tasks = [t for t in completed_tasks if t.assigned_to in team_members]
    
    total_points = sum(t.story_points for t in team_tasks)
    total_tasks = len(team_tasks)
    avg_cycle_hours = []
    
    for task in team_tasks:
        cycle_time = calculate_cycle_time(task)
        if cycle_time:
            avg_cycle_hours.append(cycle_time)
    
    avg_cycle_time = sum(avg_cycle_hours) / len(avg_cycle_hours) if avg_cycle_hours else 0
    
    # Group by week
    weekly_breakdown = {}
    for task in team_tasks:
        week_num = (datetime.now() - task.completed_date).days // 7
        week_key = f"Week {-week_num}"
        
        if week_key not in weekly_breakdown:
            weekly_breakdown[week_key] = {"points": 0, "tasks": 0}
        
        weekly_breakdown[week_key]["points"] += task.story_points
        weekly_breakdown[week_key]["tasks"] += 1
    
    return {
        "team_size": len(team_members),
        "total_points": total_points,
        "total_tasks": total_tasks,
        "avg_points_per_week": total_points / weeks,
        "avg_tasks_per_week": total_tasks / weeks,
        "avg_cycle_time_hours": round(avg_cycle_time, 1),
        "weekly_breakdown": dict(sorted(weekly_breakdown.items())[-4:])  # Last 4 weeks
    }


def get_burndown_data(sprint_duration_days: int = 14) -> Dict[str, Any]:
    """Generate burndown chart data."""
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    cursor = conn.cursor()
    
    # Get all active tasks
    cursor.execute('''
        SELECT story_points, created_date, completed_date, type
        FROM tasks
        WHERE status IN ('completed', 'in_progress')
        ORDER BY created_date DESC
        LIMIT 50
    ''')
    
    tasks = cursor.fetchall()
    conn.close()
    
    # Generate daily burndown
    today = datetime.now().date()
    start_date = today - timedelta(days=sprint_duration_days)
    
    daily_data = []
    for day_offset in range(sprint_duration_days, -1, -1):
        current_date = start_date + timedelta(days=day_offset)
        remaining_points = 0
        
        for task in tasks:
            completed = task[2]
            if completed:
                comp_date = datetime.fromisoformat(completed).date()
                if comp_date > current_date:
                    remaining_points += task[0]
            elif task[1]:
                remaining_points += task[0]
        
        daily_data.append({
            "date": current_date.isoformat(),
            "remaining_points": remaining_points
        })
    
    return {
        "sprint_start": start_date.isoformat(),
        "sprint_end": today.isoformat(),
        "duration_days": sprint_duration_days,
        "daily_burndown": daily_data
    }


def generate_sprint_report(sprint_number: int, team_members: List[str]) -> Dict[str, Any]:
    """Generate comprehensive sprint report."""
    velocity = get_team_velocity(team_members, weeks=8)
    burndown = get_burndown_data()
    
    # Count by type
    type_counts = {"feature": 0, "bug": 0, "tech_debt": 0, "chore": 0}
    type_points = {"feature": 0, "bug": 0, "tech_debt": 0, "chore": 0}
    
    for task in get_completed_tasks(days=56):
        if task.type in type_counts:
            type_counts[task.type] += 1
            type_points[task.type] += task.story_points
    
    return {
        "sprint_number": sprint_number,
        "generated_at": datetime.now().isoformat(),
        "velocity_summary": {
            "total_points_last_8_weeks": velocity["total_points"],
            "avg_weekly_points": velocity["avg_points_per_week"],
            "projected_capacity_next_sprint": velocity["avg_points_per_week"] * 2
        },
        "work_distribution": {
            "by_type": type_counts,
            "by_points": type_points
        },
        "cycle_time": {
            "average_hours": velocity["avg_cycle_time_hours"],
            "trend": "stable"  # Would need historical comparison
        },
        "burndown_chart": burndown
    }


def get_bug_metrics(weeks: int = 4) -> Dict[str, Any]:
    """Analyze bug trends."""
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=weeks * 7)).isoformat()
    
    cursor.execute('''
        SELECT COUNT(*), 
               SUM(CASE WHEN type='bug' THEN 1 ELSE 0 END) as bug_count,
               SUM(CASE WHEN type='feature' THEN 1 ELSE 0 END) as feature_count
        FROM tasks
        WHERE created_date >= ?
    ''', (cutoff_date,))
    
    row = cursor.fetchone()
    conn.close()
    
    total_tasks = row[0] or 0
    bugs = row[1] or 0
    features = row[2] or 0
    
    bug_rate = (bugs / total_tasks * 100) if total_tasks > 0 else 0
    feature_ratio = (features / total_tasks * 100) if total_tasks > 0 else 0
    
    return {
        "period_weeks": weeks,
        "total_tasks": total_tasks,
        "bugs_reported": bugs,
        "features_shipped": features,
        "bug_rate_percentage": round(bug_rate, 1),
        "feature_ratio_percentage": round(feature_ratio, 1),
        "quality_indicator": "good" if bug_rate < 15 else "concerning" if bug_rate < 25 else "poor"
    }


def export_to_csv(output_path: str):
    """Export all metrics to CSV."""
    import csv
    
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT task_id, story_points, created_date, completed_date, 
               assigned_to, status, priority, type
        FROM tasks
        ORDER BY created_date DESC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Task ID", "Points", "Created", "Completed", "Assignee", "Status", "Priority", "Type"])
        writer.writerows(rows)


if __name__ == "__main__":
    # Demo mode
    print("=" * 60)
    print("📊 NEXDEV TEAM ANALYTICS - DEMO")
    print("=" * 60)
    
    init_analytics_db()
    
    # Add sample tasks
    from datetime import timedelta
    
    sample_tasks = [
        TaskMetric(
            task_id="TASK-001",
            story_points=5,
            created_date=datetime.now() - timedelta(days=10),
            started_date=datetime.now() - timedelta(days=8),
            completed_date=datetime.now() - timedelta(days=5),
            assigned_to="developer1",
            status="completed",
            priority="high",
            type="feature"
        ),
        TaskMetric(
            task_id="TASK-002",
            story_points=3,
            created_date=datetime.now() - timedelta(days=8),
            started_date=datetime.now() - timedelta(days=6),
            completed_date=datetime.now() - timedelta(days=3),
            assigned_to="developer2",
            status="completed",
            priority="medium",
            type="bug"
        ),
        TaskMetric(
            task_id="TASK-003",
            story_points=8,
            created_date=datetime.now() - timedelta(days=6),
            started_date=datetime.now() - timedelta(days=5),
            completed_date=datetime.now() - timedelta(days=2),
            assigned_to="developer1",
            status="completed",
            priority="high",
            type="feature"
        ),
        TaskMetric(
            task_id="TASK-004",
            story_points=2,
            created_date=datetime.now() - timedelta(days=5),
            started_date=datetime.now() - timedelta(days=4),
            completed_date=None,
            assigned_to="developer2",
            status="in_progress",
            priority="low",
            type="tech_debt"
        )
    ]
    
    print("\n📥 Adding sample task data...")
    for task in sample_tasks:
        add_task(task)
        print(f"   Added: {task.task_id} ({task.story_points}pts) - {task.type}")
    
    # Calculate velocity
    print("\n🚀 Calculating team velocity...")
    
    team = ["developer1", "developer2"]
    velocity = get_team_velocity(team, weeks=8)
    
    print(f"\n✅ Team: {len(team)} members")
    print(f"   Total Points (8 weeks): {velocity['total_points']}")
    print(f"   Avg Weekly Points: {velocity['avg_points_per_week']:.1f}")
    print(f"   Avg Cycle Time: {velocity['avg_cycle_time_hours']:.1f}h")
    
    print("\nWeekly Breakdown:")
    for week, data in list(velocity['weekly_breakdown'].items())[-4:]:
        print(f"   {week}: {data['points']}pts ({data['tasks']} tasks)")
    
    # Bug metrics
    print("\n🐛 Quality Metrics (4 weeks):")
    bugs = get_bug_metrics(weeks=4)
    print(f"   Bugs Reported: {bugs['bugs_reported']}")
    print(f"   Features Shipped: {bugs['features_shipped']}")
    print(f"   Bug Rate: {bugs['bug_rate_percentage']:.1f}%")
    print(f"   Quality Indicator: {bugs['quality_indicator'].upper()}")
    
    # Sprint report
    print("\n📈 Sample Sprint Report:")
    report = generate_sprint_report(sprint_number=5, team_members=team)
    print(f"   Projected Capacity Next Sprint: {report['velocity_summary']['projected_capacity_next_sprint']:.1f} pts")
    print(f"   Work Distribution:")
    for work_type, count in report['work_distribution']['by_type'].items():
        print(f"      • {work_type}: {count} tasks ({report['work_distribution']['by_points'][work_type]} pts)")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
