#!/usr/bin/env python3
"""
Log viewer utility for YouTube Discovery Agent
Usage: python log_viewer.py [command]
"""

import sys
import json
import re
from datetime import datetime

def parse_log_line(line):
    """Parse a log line and extract structured data"""
    try:
        # Pattern: timestamp - module - level - message
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (\w+) - (.+)'
        match = re.match(pattern, line)
        
        if match:
            timestamp_str, module, level, message = match.groups()
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
            
            return {
                'timestamp': timestamp,
                'module': module,
                'level': level,
                'message': message,
                'raw': line.strip()
            }
    except:
        pass
    
    return None

def show_summary():
    """Show summary of log activity"""
    try:
        with open('discovery_agent.log', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("❌ No log file found. Run the discovery agent first.")
        return
    
    stats = {
        'total_lines': len(lines),
        'levels': {'INFO': 0, 'ERROR': 0, 'WARNING': 0, 'DEBUG': 0},
        'videos_processed': 0,
        'animated_found': 0,
        'errors': []
    }
    
    for line in lines:
        parsed = parse_log_line(line)
        if parsed:
            stats['levels'][parsed['level']] = stats['levels'].get(parsed['level'], 0) + 1
            
            if 'Processing individual video' in parsed['message']:
                stats['videos_processed'] += 1
            elif 'Animated video found' in parsed['message']:
                stats['animated_found'] += 1
            elif parsed['level'] == 'ERROR':
                stats['errors'].append(parsed['message'])
    
    print("📊 Discovery Agent Log Summary")
    print("=" * 50)
    print(f"Total log entries: {stats['total_lines']}")
    print(f"Videos processed: {stats['videos_processed']}")
    print(f"Animated videos found: {stats['animated_found']}")
    print()
    print("Log levels:")
    for level, count in stats['levels'].items():
        if count > 0:
            print(f"  {level}: {count}")
    
    if stats['errors']:
        print(f"\n❌ Errors ({len(stats['errors'])}):")
        for error in stats['errors'][-5:]:  # Show last 5 errors
            print(f"  • {error}")

def show_recent(count=10):
    """Show recent log entries"""
    try:
        with open('discovery_agent.log', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("❌ No log file found. Run the discovery agent first.")
        return
    
    print(f"📜 Last {count} Log Entries")
    print("=" * 50)
    
    for line in lines[-count:]:
        parsed = parse_log_line(line)
        if parsed:
            level_emoji = {
                'INFO': 'ℹ️',
                'ERROR': '❌',
                'WARNING': '⚠️',
                'DEBUG': '🔍'
            }.get(parsed['level'], '•')
            
            print(f"{level_emoji} {parsed['timestamp'].strftime('%H:%M:%S')} - {parsed['message']}")
        else:
            print(f"  {line.strip()}")

def show_errors():
    """Show all errors from the log"""
    try:
        with open('discovery_agent.log', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("❌ No log file found. Run the discovery agent first.")
        return
    
    errors = []
    for line in lines:
        parsed = parse_log_line(line)
        if parsed and parsed['level'] == 'ERROR':
            errors.append(parsed)
    
    if not errors:
        print("✅ No errors found in log!")
        return
    
    print(f"❌ All Errors ({len(errors)})")
    print("=" * 50)
    
    for error in errors:
        print(f"{error['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {error['message']}")

def show_animated():
    """Show all animated videos found"""
    try:
        with open('discovery_agent.log', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("❌ No log file found. Run the discovery agent first.")
        return
    
    animated_videos = []
    for line in lines:
        parsed = parse_log_line(line)
        if parsed and 'Animated video found' in parsed['message']:
            animated_videos.append(parsed)
    
    if not animated_videos:
        print("😞 No animated videos found yet.")
        return
    
    print(f"🎬 Animated Videos Found ({len(animated_videos)})")
    print("=" * 50)
    
    for video in animated_videos:
        print(f"{video['timestamp'].strftime('%H:%M:%S')} - {video['message']}")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "summary":
            show_summary()
        elif command == "recent":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            show_recent(count)
        elif command == "errors":
            show_errors()
        elif command == "animated":
            show_animated()
        elif command == "help":
            print("Usage:")
            print("  python log_viewer.py summary     # Show log summary")
            print("  python log_viewer.py recent [N]  # Show last N entries (default 10)")
            print("  python log_viewer.py errors      # Show all errors")
            print("  python log_viewer.py animated    # Show found animated videos")
        else:
            print(f"Unknown command: {command}")
            print("Use 'python log_viewer.py help' for available commands")
    else:
        show_summary()

if __name__ == "__main__":
    main() 