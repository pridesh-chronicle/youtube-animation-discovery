#!/usr/bin/env python3
"""Simple viewer for the animated videos SQLite database."""

import sqlite3
import sys

def show_summary():
    """Show summary statistics"""
    conn = sqlite3.connect('animated_videos.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM videos')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT AVG(views), AVG(likes), AVG(subscribers) FROM videos WHERE views > 0')
    avg_views, avg_likes, avg_subs = cursor.fetchone()
    
    cursor.execute('SELECT MAX(views), title FROM videos')
    max_views, top_title = cursor.fetchone()
    
    print(f"📊 Database Summary")
    print(f"=" * 50)
    print(f"Total animated videos: {total}")
    print(f"Average views: {avg_views:,.0f}" if avg_views else "Average views: N/A")
    print(f"Average likes: {avg_likes:,.0f}" if avg_likes else "Average likes: N/A") 
    print(f"Average subscribers: {avg_subs:,.0f}" if avg_subs else "Average subscribers: N/A")
    print(f"Top video: {top_title} ({max_views:,} views)" if max_views else "Top video: N/A")
    print(f"=" * 50)
    
    conn.close()

def show_top_videos(limit=10):
    """Show top videos by views"""
    conn = sqlite3.connect('animated_videos.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT title, views, likes, youtuber, video_id 
        FROM videos 
        WHERE views > 0
        ORDER BY views DESC 
        LIMIT ?
    ''', (limit,))
    
    print(f"\n🏆 Top {limit} Videos by Views")
    print(f"=" * 80)
    
    for i, (title, views, likes, youtuber, video_id) in enumerate(cursor.fetchall(), 1):
        print(f"{i:2d}. {title[:50]}")
        print(f"    👀 {views:,} views | 👍 {likes:,} likes | 📺 {youtuber}")
        print(f"    🔗 https://www.youtube.com/watch?v={video_id}")
        print()
    
    conn.close()

def show_recent(limit=5):
    """Show recently discovered videos"""
    conn = sqlite3.connect('animated_videos.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT title, views, youtuber, discovered_at 
        FROM videos 
        ORDER BY discovered_at DESC 
        LIMIT ?
    ''', (limit,))
    
    print(f"\n🕒 Last {limit} Discovered Videos")
    print(f"=" * 60)
    
    for title, views, youtuber, discovered in cursor.fetchall():
        print(f"📺 {title[:40]}")
        print(f"   {views:,} views | {youtuber} | {discovered}")
        print()
    
    conn.close()

def search_videos(keyword):
    """Search videos by keyword"""
    conn = sqlite3.connect('animated_videos.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT title, views, youtuber, video_id 
        FROM videos 
        WHERE title LIKE ? OR youtuber LIKE ?
        ORDER BY views DESC
    ''', (f'%{keyword}%', f'%{keyword}%'))
    
    results = cursor.fetchall()
    
    print(f"\n🔍 Search Results for '{keyword}' ({len(results)} found)")
    print(f"=" * 60)
    
    for title, views, youtuber, video_id in results:
        print(f"📺 {title}")
        print(f"   👀 {views:,} views | 📺 {youtuber}")
        print(f"   🔗 https://www.youtube.com/watch?v={video_id}")
        print()
    
    conn.close()

def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "search" and len(sys.argv) > 2:
            search_videos(sys.argv[2])
        elif command == "recent":
            show_recent(10)
        elif command == "top":
            show_top_videos(20)
        else:
            print("Usage:")
            print("  python view_data.py              # Show summary")
            print("  python view_data.py top          # Show top 20 videos")
            print("  python view_data.py recent       # Show recent 10 videos")
            print("  python view_data.py search WORD  # Search for videos")
    else:
        show_summary()
        show_top_videos(5)
        show_recent(3)

if __name__ == "__main__":
    main() 