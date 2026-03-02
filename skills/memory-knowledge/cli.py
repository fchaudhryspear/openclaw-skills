#!/usr/bin/env python3
"""
Knowledge Retention CLI - Command-line interface for /remember and /recall commands.

Usage:
    remember <topic> [options]  - Store a new lesson
    recall <query>              - Search for relevant lessons
    list                        - List all lessons
    stats                       - Show knowledge base statistics
    export                      - Export all lessons
    import <file>               - Import lessons from file
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from knowledge_manager import manager, remember, recall


def cmdRemember(args):
    """Store a new lesson."""
    result = remember(
        topic=args.topic,
        content=args.content or "No content provided",
        outcome=args.outcome or 'success',
        project=args.project,
        tags=args.tags.split(',') if args.tags else None,
        context=args.context
    )
    print(result)
    return 0


def cmdRecall(args):
    """Search for lessons."""
    results = recall(args.query, max_results=args.limit)
    print(results)
    return 0


def cmdList(args):
    """List all lessons with optional filters."""
    lessons = manager.list_lessons(
        outcome=args.outcome,
        project=args.project,
        days=args.days
    )
    
    if not lessons:
        print("No lessons found.")
        return 0
    
    print(f"📚 Found {len(lessons)} lesson(s):\n")
    for i, lesson in enumerate(lessons, 1):
        print(f"{i}. **{lesson['topic']}**")
        print(f"   📅 {lesson['date']} | 🎯 {lesson['outcome']}")
        if lesson.get('project'):
            print(f"   📁 Project: {lesson['project']}")
        if lesson.get('tags'):
            print(f"   🏷️ Tags: {', '.join(lesson['tags'])}")
        print()
    
    return 0


def cmdStats(args):
    """Show knowledge base statistics."""
    stats = manager.get_stats()
    
    print("📊 Knowledge Base Statistics\n")
    print(f"Total Lessons: {stats['total_lessons']}")
    print(f"Today's Activity: {stats['recent_activity']}")
    
    print("\n🎯 Outcomes:")
    for outcome, count in sorted(stats['outcomes'].items()):
        print(f"   {outcome}: {count}")
    
    if stats['projects']:
        print("\n📁 Top Projects:")
        for project, count in list(stats['projects'].items())[:5]:
            print(f"   {project}: {count}")
    
    if stats['top_tags']:
        print("\n🏷️ Top Tags:")
        for tag, count in list(stats['top_tags'].items())[:5]:
            print(f"   {tag}: {count}")
    
    return 0


def cmdExport(args):
    """Export all lessons."""
    output_file = args.output or f"knowledge-export-{datetime.now().strftime('%Y%m%d')}.md"
    
    lessons = manager.list_lessons()
    with open(output_file, 'w') as f:
        f.write("# Knowledge Export\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total Lessons: {len(lessons)}\n\n")
        f.write("---\n\n")
        
        for lesson in lessons:
            content = manager.get_lesson_content(lesson['filename'])
            if content:
                f.write(content)
                f.write("\n\n---\n\n")
    
    print(f"✅ Exported {len(lessons)} lessons to {output_file}")
    return 0


def cmdImport(args):
    """Import lessons from a file."""
    input_file = Path(args.file)
    if not input_file.exists():
        print(f"❌ File not found: {input_file}")
        return 1
    
    # Simple import: treat each section between --- as a lesson
    content = input_file.read_text()
    sections = content.split('---')
    
    imported = 0
    for section in sections:
        if '# ' in section:
            # Extract topic (first line after #)
            lines = section.strip().split('\n')
            topic = lines[0].replace('#', '').strip() if lines else 'Imported Lesson'
            
            # Use rest as content
            lesson_content = '\n'.join(lines[2:]) if len(lines) > 2 else section
            
            try:
                manager.save_lesson(topic=topic, content=lesson_content)
                imported += 1
            except Exception as e:
                print(f"⚠️ Failed to import '{topic}': {e}")
    
    print(f"✅ Imported {imported} lessons from {input_file}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Knowledge Retention System - Store and retrieve lessons learned'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Remember command
    remember_parser = subparsers.add_parser('remember', help='Store a new lesson')
    remember_parser.add_argument('topic', help='Topic/title of the lesson')
    remember_parser.add_argument('--content', '-c', help='Lesson content')
    remember_parser.add_argument('--outcome', '-o', 
                                choices=['success', 'failure', 'partial'],
                                help='Outcome type')
    remember_parser.add_argument('--project', '-p', help='Related project')
    remember_parser.add_argument('--tags', '-t', help='Comma-separated tags')
    remember_parser.add_argument('--context', help='Brief context description')
    
    # Recall command
    recall_parser = subparsers.add_parser('recall', help='Search for lessons')
    recall_parser.add_argument('query', help='Search query')
    recall_parser.add_argument('--limit', '-l', type=int, default=5,
                              help='Maximum results to show')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all lessons')
    list_parser.add_argument('--outcome', '-o', 
                            choices=['success', 'failure', 'partial'],
                            help='Filter by outcome')
    list_parser.add_argument('--project', '-p', help='Filter by project')
    list_parser.add_argument('--days', '-d', type=int, help='Last N days only')
    
    # Stats command
    subparsers.add_parser('stats', help='Show knowledge base statistics')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export all lessons')
    export_parser.add_argument('--output', '-o', help='Output file path')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import lessons from file')
    import_parser.add_argument('file', help='Input file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    commands = {
        'remember': cmdRemember,
        'recall': cmdRecall,
        'list': cmdList,
        'stats': cmdStats,
        'export': cmdExport,
        'import': cmdImport
    }
    
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
