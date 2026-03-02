#!/usr/bin/env python3
"""
OpenClaw Command Handlers - Telegram command wrappers for knowledge retention.

Usage from OpenClaw:
    /remember <topic> [options]
    /recall <query>
    /knowledge <subcommand>
"""

import sys
import os
from pathlib import Path

# Add skill directory to path
SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR))

from knowledge_manager import manager, remember, recall


def handleRemember(args: list) -> str:
    """Handle /remember command."""
    if not args:
        return "❌ Usage: `/remember <topic> [options]`\n\n" \
               "Options:\n" \
               "-o, --outcome success|failure|partial\n" \
               "-p, --project <project-name>\n" \
               "-t, --tags tag1,tag2,tag3\n" \
               "-c, --context <brief-context>"
    
    # Parse topic (first word until --flag)
    topic_parts = []
    remaining_args = []
    
    for i, arg in enumerate(args):
        if arg.startswith('--') or arg.startswith('-'):
            remaining_args = args[i:]
            break
        topic_parts.append(arg)
    
    topic = ' '.join(topic_parts)
    if not topic:
        return "❌ Please provide a topic for the lesson."
    
    # Parse options
    outcome = 'success'
    project = None
    tags = None
    context = None
    
    i = 0
    while i < len(remaining_args):
        arg = remaining_args[i]
        
        if arg in ['-o', '--outcome']:
            outcome = remaining_args[i + 1] if i + 1 < len(remaining_args) else 'success'
            i += 2
        elif arg in ['-p', '--project']:
            project = remaining_args[i + 1] if i + 1 < len(remaining_args) else None
            i += 2
        elif arg in ['-t', '--tags']:
            tags = remaining_args[i + 1] if i + 1 < len(remaining_args) else None
            i += 2
        elif arg in ['-c', '--context']:
            context = remaining_args[i + 1] if i + 1 < len(remaining_args) else None
            i += 2
        else:
            i += 1
    
    # Save the lesson
    result = remember(
        topic=topic,
        content="Lesson captured via /remember command. Use `--context` for more details.",
        outcome=outcome,
        project=project,
        tags=[tag.strip() for tag in tags.split(',')] if tags else ['manual'],
        context=context
    )
    
    return f"✅ **Lesson Saved!**\n\n📁 {result}\n" \
           f"🏷️ Topic: `{topic}`\n" \
           f"🎯 Outcome: {outcome}"


def handleRecall(args: list) -> str:
    """Handle /recall command."""
    if not args:
        return "❌ Usage: `/recall <search-query>`\n\n" \
               "Example: `/recall telegram bot privacy`"
    
    query = ' '.join(args)
    results = recall(query, max_results=5)
    
    if not results:
        return f"🔍 No lessons found matching: *{query}*\n\n" \
               "Try different keywords or check spelling."
    
    response = [f"🔍 Found {len(results)} lesson(s) for *{query}*:\n"]
    
    for i, result in enumerate(results, 1):
        topic = result['topic'][:60] + '...' if len(result['topic']) > 60 else result['topic']
        date = result['date']
        outcome = result['outcome']
        
        emoji = {'success': '✅', 'failure': '⚠️', 'partial': '🟡'}.get(outcome, '📝')
        
        response.append(f"\n{emoji} **{i}. {topic}**")
        response.append(f"   📅 {date} | 🎯 {outcome}")
        
        if result.get('project'):
            response.append(f"   📁 Project: {result['project']}")
        
        if result.get('tags'):
            tags_str = ', '.join(result['tags'][:3])
            response.append(f"   🏷️ {tags_str}")
        
        summary = result.get('summary', '')[:120]
        if summary:
            response.append(f"   💬 _{summary}_...")
    
    # Add note about viewing full lesson
    if len(results) == 1:
        filename = results[0]['filename']
        response.append(f"\n💡 Use `/knowledge view {filename}` to see full lesson.")
    
    return '\n'.join(response)


def handleKnowledge(args: list) -> str:
    """Handle /knowledge subcommands."""
    if not args:
        return "📚 Knowledge Management Commands:\n\n" \
               "`/knowledge list` - List all lessons\n" \
               "`/knowledge stats` - Show statistics\n" \
               "`/knowledge export` - Export all lessons\n" \
               "`/knowledge view <filename>` - View specific lesson\n" \
               "`/knowledge recent` - Show recently added lessons"
    
    subcommand = args[0].lower()
    
    if subcommand == 'list':
        lessons = manager.list_lessons()
        
        if not lessons:
            return "📭 No lessons in database yet."
        
        response = [f"📚 Found {len(lessons)} lesson(s):\n"]
        for lesson in lessons[:15]:  # Limit to 15
            topic = lesson['topic'][:50] + '...' if len(lesson['topic']) > 50 else lesson['topic']
            emoji = {'success': '✅', 'failure': '⚠️', 'partial': '🟡'}.get(lesson['outcome'], '📝')
            response.append(f"{emoji} {lesson['date']} - {topic}")
        
        if len(lessons) > 15:
            response.append(f"\n... and {len(lessons) - 15} more. Use `/recall` to search.")
        
        return '\n'.join(response)
    
    elif subcommand == 'stats':
        stats = manager.get_stats()
        
        response = [
            "📊 **Knowledge Base Statistics**",
            "",
            f"Total Lessons: `{stats['total_lessons']}`",
            f"Today's Activity: `{stats['recent_activity']}`",
            ""
        ]
        
        if stats['outcomes']:
            response.append("🎯 **Outcomes:**")
            for outcome, count in sorted(stats['outcomes'].items()):
                response.append(f"   • {outcome}: `{count}`")
        
        if stats['top_tags']:
            response.append("")
            response.append("🏷️ **Top Tags:**")
            for tag, count in list(stats['top_tags'].items())[:5]:
                response.append(f"   • `{tag}`: {count}")
        
        return '\n'.join(response)
    
    elif subcommand == 'export':
        output_file = f"knowledge-export-{manager._load_index()[0]['date'] if manager._load_index() else 'full'}.md"
        lessons = manager.list_lessons()
        
        with open(output_file, 'w') as f:
            f.write("# Knowledge Export\n")
            f.write(f"Generated: {__import__('datetime').datetime.now().isoformat()}\n")
            f.write(f"Total Lessons: {len(lessons)}\n\n")
            f.write("---\n\n")
            
            for lesson in lessons:
                content = manager.get_lesson_content(lesson['filename'])
                if content:
                    f.write(content)
                    f.write("\n\n---\n\n")
        
        return f"✅ Exported {len(lessons)} lessons to:\n`{output_file}`"
    
    elif subcommand == 'view':
        if len(args) < 2:
            return "❌ Usage: `/knowledge view <filename>`"
        
        filename = args[1]
        content = manager.get_lesson_content(filename)
        
        if not content:
            return f"❌ Lesson not found: `{filename}`"
        
        # Truncate if too long
        if len(content) > 3000:
            content = content[:3000] + "\n\n...(truncated, use local file viewer)"
        
        return f"📄 **{filename}**\n\n```\n{content}\n```"
    
    elif subcommand == 'recent':
        lessons = manager.list_lessons(days=7)
        
        if not lessons:
            return "🕒 No lessons in the last 7 days."
        
        response = ["🕒 Recent Lessons (last 7 days):\n"]
        for lesson in lessons:
            topic = lesson['topic'][:60] + '...' if len(lesson['topic']) > 60 else lesson['topic']
            emoji = {'success': '✅', 'failure': '⚠️', 'partial': '🟡'}.get(lesson['outcome'], '📝')
            response.append(f"{emoji} {lesson['date']} - {topic}")
        
        return '\n'.join(response)
    
    else:
        return f"❌ Unknown subcommand: `{subcommand}`\n\nUse `/knowledge` for help."


# Main entry point for direct execution
if __name__ == '__main__':
    # Simulate command-line arguments
    if len(sys.argv) < 2:
        print("Usage: python command_handler.py <command> [args...]")
        print("Commands: remember, recall, knowledge")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    if command == 'remember':
        print(handleRemember(args))
    elif command == 'recall':
        print(handleRecall(args))
    elif command == 'knowledge':
        print(handleKnowledge(args))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
