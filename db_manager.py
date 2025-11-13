#!/usr/bin/env python3
"""
Database management script for BookBot
"""

import sys
from datetime import datetime, timedelta
from database import db

def init_database():
    """Initialize the database"""
    db.init_database()
    print("✅ Database initialized successfully!")

def show_posts():
    """Show all posts"""
    posts = db.execute_fetchall('''
        SELECT id, user_id, created_at, repost_count, 
               channel_message_id, text_content
        FROM posts 
        ORDER BY created_at DESC
    ''')
    
    if not posts:
        print("📭 No posts found in database.")
        return
    
    print(f"📚 Found {len(posts)} posts:")
    print("-" * 80)
    
    for post in posts:
        post_id, user_id, created_at, repost_count, channel_msg_id, text_content = post
        print(f"ID: {post_id} | User: {user_id} | Created: {created_at}")
        print(f"Reposts: {repost_count} | Channel MSG: {channel_msg_id}")
        print(f"Content: {text_content[:100]}{'...' if len(text_content) > 100 else ''}")
        print("-" * 80)


def delete_post(post_id):
    """Delete a post"""
    rowcount = db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    
    if rowcount > 0:
        print(f"✅ Post {post_id} deleted!")
    else:
        print(f"❌ Post {post_id} not found!")

def cleanup_old_posts(days=30):
    """Clean up posts older than specified days"""
    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = db.execute('DELETE FROM posts WHERE created_at < ?', (cutoff_date,))
    
    print(f"✅ Deleted {deleted_count} posts older than {days} days")

def show_stats():
    """Show database statistics"""
    # Total posts
    result = db.execute_fetchone('SELECT COUNT(*) FROM posts')
    total_posts = result[0] if result else 0
    
    # Active posts (all posts are now active)
    active_posts = total_posts
    
    # Posts needing repost
    week_ago = datetime.now() - timedelta(days=7)
    week_ago_str = week_ago.strftime('%Y-%m-%d %H:%M:%S')
    result = db.execute_fetchone('''
        SELECT COUNT(*) FROM posts 
        WHERE julianday(created_at) <= julianday(?) 
        AND (last_repost IS NULL OR julianday(last_repost) <= julianday(?))
    ''', (week_ago_str, week_ago_str))
    repost_needed = result[0] if result else 0
    
    print("Database Statistics:")
    print(f"Total posts: {total_posts}")
    print(f"Active posts: {active_posts}")
    print(f"Posts needing repost: {repost_needed}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("📚 BookBot Database Manager")
        print("\nUsage:")
        print("  python db_manager.py init          - Initialize database")
        print("  python db_manager.py show          - Show all posts")
        print("  python db_manager.py stats         - Show statistics")
        print("  python db_manager.py delete <id>   - Delete post")
        print("  python db_manager.py cleanup [days] - Clean up old posts")
        return
    
    command = sys.argv[1].lower()
    
    if command == "init":
        init_database()
    elif command == "show":
        show_posts()
    elif command == "stats":
        show_stats()
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ Please provide post ID")
            return
        try:
            post_id = int(sys.argv[2])
            delete_post(post_id)
        except ValueError:
            print("❌ Invalid post ID")
    elif command == "cleanup":
        days = 30
        if len(sys.argv) > 2:
            try:
                days = int(sys.argv[2])
            except ValueError:
                print("❌ Invalid number of days")
                return
        cleanup_old_posts(days)
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()
