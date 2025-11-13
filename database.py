#!/usr/bin/env python3
"""
Database abstraction layer supporting both SQLite and PostgreSQL
Automatically detects database type from DATABASE_URL environment variable
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Any
from urllib.parse import urlparse

# Try to import psycopg2, but don't fail if it's not installed (for SQLite-only setups)
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import sql as pg_sql
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

logger = logging.getLogger(__name__)

# Fix SQLite datetime deprecation warning for Python 3.12+
def adapt_datetime_iso(val):
    """Adapt datetime.datetime to ISO 8601 date."""
    return val.isoformat()

def convert_datetime(val):
    """Convert ISO 8601 datetime to datetime.datetime object."""
    return datetime.fromisoformat(val.decode())

# Register the adapter and converter
sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter("datetime", convert_datetime)


class Database:
    """Database abstraction class supporting SQLite and PostgreSQL"""
    
    def __init__(self):
        self.db_type = None
        self.connection_string = None
        self._conn = None
        self._detect_database_type()
    
    def _detect_database_type(self):
        """Detect database type from environment variables"""
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            # Parse DATABASE_URL to determine database type
            parsed = urlparse(database_url)
            if parsed.scheme.startswith('postgres'):
                self.db_type = 'postgresql'
                self.connection_string = database_url
                logger.info("Using PostgreSQL database")
            else:
                self.db_type = 'sqlite'
                self.connection_string = database_url.replace('sqlite:///', '') if database_url.startswith('sqlite:///') else 'bookbot.db'
                logger.info(f"Using SQLite database: {self.connection_string}")
        else:
            # Default to SQLite for local development
            self.db_type = 'sqlite'
            self.connection_string = 'bookbot.db'
            logger.info("Using SQLite database (default)")
    
    def get_connection(self):
        """Get database connection"""
        if self.db_type == 'postgresql':
            if not PSYCOPG2_AVAILABLE:
                raise ImportError("psycopg2 is required for PostgreSQL. Install it with: pip install psycopg2-binary")
            return psycopg2.connect(self.connection_string)
        else:
            conn = sqlite3.connect(
                self.connection_string,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
    
    def execute(self, query: str, params: tuple = None, fetch: bool = False):
        """Execute a query and return results if fetch=True"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Convert SQLite syntax to PostgreSQL if needed
            if self.db_type == 'postgresql':
                query = self._convert_sqlite_to_postgresql(query)
                if params:
                    # Convert ? placeholders to %s
                    query = query.replace('?', '%s')
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                if self.db_type == 'postgresql':
                    # PostgreSQL returns tuples
                    results = cursor.fetchall()
                else:
                    results = cursor.fetchall()
                conn.commit()
                conn.close()
                return results
            else:
                conn.commit()
                conn.close()
                return cursor.rowcount
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def execute_fetchone(self, query: str, params: tuple = None):
        """Execute a query and return one result"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.db_type == 'postgresql':
                query = self._convert_sqlite_to_postgresql(query)
                if params:
                    query = query.replace('?', '%s')
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            result = cursor.fetchone()
            conn.close()
            return result
        except Exception as e:
            conn.close()
            raise e
    
    def execute_fetchall(self, query: str, params: tuple = None):
        """Execute a query and return all results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.db_type == 'postgresql':
                query = self._convert_sqlite_to_postgresql(query)
                if params:
                    query = query.replace('?', '%s')
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            conn.close()
            raise e
    
    def execute_with_cursor(self, callback):
        """Execute operations with cursor access (for complex operations)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            result = callback(cursor, conn)
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _convert_sqlite_to_postgresql(self, query: str) -> str:
        """Convert SQLite-specific SQL to PostgreSQL"""
        # Replace AUTOINCREMENT with SERIAL (handled in table creation)
        query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        query = query.replace('AUTOINCREMENT', '')
        
        # Replace INSERT OR REPLACE with INSERT ... ON CONFLICT
        if 'INSERT OR REPLACE INTO' in query.upper():
            # Extract table name and values
            query_upper = query.upper()
            table_start = query_upper.find('INSERT OR REPLACE INTO') + len('INSERT OR REPLACE INTO')
            table_end = query_upper.find('(', table_start)
            table_name = query[table_start:table_end].strip()
            
            # Find the column list
            col_start = query.find('(', table_end)
            col_end = query.find(')', col_start)
            columns = query[col_start+1:col_end]
            
            # Find VALUES
            values_start = query_upper.find('VALUES', col_end)
            values_end = query.find(')', values_start + 6)
            values = query[values_start + 6:values_end + 1]
            
            # Extract primary key column (first column in INSERT OR REPLACE)
            first_col = columns.split(',')[0].strip()
            
            # Reconstruct as INSERT ... ON CONFLICT
            new_query = f"INSERT INTO {table_name} ({columns}) {values} ON CONFLICT ({first_col}) DO UPDATE SET "
            # Update all columns except the primary key
            cols = [c.strip() for c in columns.split(',')]
            updates = [f"{col} = EXCLUDED.{col}" for col in cols[1:]]  # Skip first (primary key)
            new_query += ", ".join(updates)
            
            return new_query
        
        # Replace julianday() with PostgreSQL date comparison
        if 'julianday' in query.lower():
            import re
            # Replace julianday(column) <= julianday(?) with column <= ?
            # This works because PostgreSQL can compare timestamps directly
            query = re.sub(
                r'julianday\(([^)]+)\)\s*<=\s*julianday\(([^)]+)\)',
                r'\1 <= \2',
                query,
                flags=re.IGNORECASE
            )
            # Replace remaining julianday() calls
            query = re.sub(
                r'julianday\(([^)]+)\)',
                r'\1',
                query,
                flags=re.IGNORECASE
            )
        
        return query
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.db_type == 'postgresql':
                # PostgreSQL table creation
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS posts (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        message_id INTEGER,
                        channel_message_id INTEGER,
                        channel_message_ids TEXT,
                        text_content TEXT,
                        image_path TEXT,
                        file_ids TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        repost_count INTEGER DEFAULT 0,
                        last_repost TIMESTAMP
                    )
                ''')
                
                # Add channel_message_ids column if it doesn't exist
                cursor.execute('''
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='posts' AND column_name='channel_message_ids'
                        ) THEN
                            ALTER TABLE posts ADD COLUMN channel_message_ids TEXT;
                        END IF;
                    END $$;
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS admins (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            else:
                # SQLite table creation
                conn.execute("PRAGMA foreign_keys = ON")
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        message_id INTEGER,
                        channel_message_id INTEGER,
                        channel_message_ids TEXT,
                        text_content TEXT,
                        image_path TEXT,
                        file_ids TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        repost_count INTEGER DEFAULT 0,
                        last_repost TIMESTAMP
                    )
                ''')
                
                # Add channel_message_ids column if it doesn't exist
                try:
                    cursor.execute('ALTER TABLE posts ADD COLUMN channel_message_ids TEXT')
                except sqlite3.OperationalError:
                    pass  # Column already exists
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS admins (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error initializing database: {e}")
            raise
        finally:
            conn.close()


# Global database instance
db = Database()

