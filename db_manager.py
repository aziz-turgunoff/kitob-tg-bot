#!/usr/bin/env python3
"""
Database management script for BookBot
"""

import sqlite3
import sys
from datetime import datetime, timedelta

def init_database():
    """Initialize the database"""
    conn = sqlite3.connect('bookbot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message_id INTEGER,
            channel_message_id INTEGER,
            text_content TEXT,
            image_path TEXT,
            file_ids TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            repost_count INTEGER DEFAULT 0,
            last_repost TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

def show_posts():
    """Show all posts"""
    conn = sqlite3.connect('bookbot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, user_id, created_at, repost_count, is_sold, 
               channel_message_id, text_content
        FROM posts 
        ORDER BY created_at DESC
    ''')
    
    posts = cursor.fetchall()
    
    if not posts:
        print("📭 No posts found in database.")
        return
    
    print(f"📚 Found {len(posts)} posts:")
    print("-" * 80)
    
    for post in posts:
        post_id, user_id, created_at, repost_count, is_sold, channel_msg_id, text_content = post
        status = "✅ SOLD" if is_sold else "🔄 ACTIVE"
        print(f"ID: {post_id} | User: {user_id} | Created: {created_at}")
        print(f"Status: {status} | Reposts: {repost_count} | Channel MSG: {channel_msg_id}")
        print(f"Content: {text_content[:100]}{'...' if len(text_content) > 100 else ''}")
        print("-" * 80)
    
    conn.close()


def delete_post(post_id):
    """Delete a post"""
    conn = sqlite3.connect('bookbot.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    
    if cursor.rowcount > 0:
        print(f"✅ Post {post_id} deleted!")
    else:
        print(f"❌ Post {post_id} not found!")
    
    conn.commit()
    conn.close()

def cleanup_old_posts(days=30):
    """Clean up posts older than specified days"""
    conn = sqlite3.connect('bookbot.db')
    cursor = conn.cursor()
    
    cutoff_date = datetime.now() - timedelta(days=days)
    cursor.execute('DELETE FROM posts WHERE created_at < ?', (cutoff_date,))
    
    deleted_count = cursor.rowcount
    print(f"✅ Deleted {deleted_count} posts older than {days} days")
    
    conn.commit()
    conn.close()

def show_stats():
    """Show database statistics"""
    conn = sqlite3.connect('bookbot.db')
    cursor = conn.cursor()
    
    # Total posts
    cursor.execute('SELECT COUNT(*) FROM posts')
    total_posts = cursor.fetchone()[0]
    
    # Active posts (all posts are now active)
    active_posts = total_posts
    
    # Posts needing repost
    week_ago = datetime.now() - timedelta(days=7)
    cursor.execute('''
        SELECT COUNT(*) FROM posts 
        WHERE created_at <= ? 
        AND (last_repost IS NULL OR last_repost <= ?)
    ''', (week_ago, week_ago))
    repost_needed = cursor.fetchone()[0]
    
    print("Database Statistics:")
    print(f"Total posts: {total_posts}")
    print(f"Active posts: {active_posts}")
    print(f"Posts needing repost: {repost_needed}")
    
    conn.close()

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
