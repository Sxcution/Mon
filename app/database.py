#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database initialization and migration script
Matches Main.pyw database structure
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
DATABASE_PATH = DATA_DIR / 'Data.db'
UPLOAD_FOLDER = DATA_DIR / 'uploaded_sessions'

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

print('🔍 DEBUG: Database module loaded')


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database with all required tables (match Main.pyw)"""
    print('🔍 Initializing database...')
    conn = get_db_connection()
    
    # Telegram tables
    conn.execute(
        """CREATE TABLE IF NOT EXISTS session_groups (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            folder_path TEXT NOT NULL
        )"""
    )
    
    conn.execute(
        """CREATE TABLE IF NOT EXISTS session_metadata (
            id INTEGER PRIMARY KEY,
            group_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            full_name TEXT,
            username TEXT,
            is_live BOOLEAN,
            status_text TEXT,
            last_checked TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES session_groups (id),
            UNIQUE (group_id, filename)
        )"""
    )
    
    conn.execute(
        """CREATE TABLE IF NOT EXISTS task_configs (
            task_name TEXT PRIMARY KEY,
            config_json TEXT NOT NULL
        )"""
    )
    
    # Auto Seeding table
    conn.execute(
        """CREATE TABLE IF NOT EXISTS auto_seeding_settings (
            id INTEGER PRIMARY KEY,
            is_enabled BOOLEAN NOT NULL DEFAULT 0,
            run_time TEXT,
            end_run_time TEXT,
            run_daily BOOLEAN NOT NULL DEFAULT 0,
            target_session_group_id INTEGER,
            last_run_timestamp TEXT,
            task_name TEXT NOT NULL DEFAULT 'seedingGroup',
            core INTEGER NOT NULL DEFAULT 5,
            delay_per_session INTEGER NOT NULL DEFAULT 10,
            delay_between_batches INTEGER NOT NULL DEFAULT 600,
            admin_enabled BOOLEAN NOT NULL DEFAULT 0,
            admin_delay INTEGER NOT NULL DEFAULT 10
        )"""
    )
    
    # Ensure row exists for auto_seeding_settings
    existing = conn.execute('SELECT id FROM auto_seeding_settings WHERE id = 1').fetchone()
    if not existing:
        conn.execute('''
            INSERT INTO auto_seeding_settings (id) VALUES (1)
        ''')
    
    # Notes table
    conn.execute(
        """CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            title_html TEXT,
            content_html TEXT,
            due_time TEXT,
            status TEXT,
            modified_at TEXT,
            is_marked INTEGER DEFAULT 0
        )"""
    )
    
    # MXH tables
    conn.execute(
        """CREATE TABLE IF NOT EXISTS mxh_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT NOT NULL,
            icon TEXT,
            created_at TEXT NOT NULL
        )"""
    )
    
    conn.execute(
        """CREATE TABLE IF NOT EXISTS mxh_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_name TEXT NOT NULL,
            group_id INTEGER,
            platform TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_muted INTEGER DEFAULT 0,
            is_disabled INTEGER DEFAULT 0,
            FOREIGN KEY (group_id) REFERENCES mxh_groups(id) ON DELETE SET NULL
        )"""
    )
    
    conn.execute(
        """CREATE TABLE IF NOT EXISTS mxh_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL,
            is_primary INTEGER DEFAULT 0,
            account_name TEXT,
            username TEXT,
            password TEXT,
            email TEXT,
            phone TEXT,
            twofa_code TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (card_id) REFERENCES mxh_cards(id) ON DELETE CASCADE
        )"""
    )
    
    conn.commit()
    conn.close()
    
    print('🔍 Database initialized successfully')


def migrate_auto_seeding_schema():
    """Migrate auto_seeding_settings to add core, delay columns (match Main.pyw)"""
    migration_flag = DATA_DIR / 'auto_seeding_schema_v2.flag'
    
    if migration_flag.exists():
        print('🔍 Auto seeding migration already completed')
        return
    
    print('🔍 Running auto_seeding_settings schema migration...')
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(auto_seeding_settings)')
        existing_columns = [row['name'] for row in cursor.fetchall()]
        
        # Final columns we want
        final_columns = [
            'id', 'is_enabled', 'run_time', 'end_run_time', 'run_daily',
            'target_session_group_id', 'last_run_timestamp', 'task_name',
            'core', 'delay_per_session', 'delay_between_batches',
            'admin_enabled', 'admin_delay'
        ]
        
        # Check if migration needed
        if all(col in existing_columns for col in final_columns):
            print('🔍 All columns already exist, migration not needed')
            migration_flag.write_text(datetime.now().isoformat())
            conn.close()
            return
        
        # Columns to copy from old table
        columns_to_copy = [col for col in final_columns if col in existing_columns]
        columns_to_copy_str = ', '.join(columns_to_copy)
        
        print(f'🔍 Migrating columns: {columns_to_copy_str}')
        
        # Create new table with correct schema
        cursor.execute("""
            CREATE TABLE auto_seeding_settings_new (
                id INTEGER PRIMARY KEY,
                is_enabled BOOLEAN NOT NULL DEFAULT 0,
                run_time TEXT,
                end_run_time TEXT,
                run_daily BOOLEAN NOT NULL DEFAULT 0,
                target_session_group_id INTEGER,
                last_run_timestamp TEXT,
                task_name TEXT NOT NULL DEFAULT 'seedingGroup',
                core INTEGER NOT NULL DEFAULT 5,
                delay_per_session INTEGER NOT NULL DEFAULT 10,
                delay_between_batches INTEGER NOT NULL DEFAULT 600,
                admin_enabled BOOLEAN NOT NULL DEFAULT 0,
                admin_delay INTEGER NOT NULL DEFAULT 10
            )
        """)
        
        # Copy data from old table
        if columns_to_copy:
            cursor.execute(f"""
                INSERT INTO auto_seeding_settings_new ({columns_to_copy_str})
                SELECT {columns_to_copy_str} FROM auto_seeding_settings
            """)
            print('🔍 Data copied to new table')
        
        # Drop old table and rename new one
        cursor.execute('DROP TABLE auto_seeding_settings')
        cursor.execute('ALTER TABLE auto_seeding_settings_new RENAME TO auto_seeding_settings')
        
        conn.commit()
        
        # Create flag file
        migration_flag.write_text(datetime.now().isoformat())
        print('🔍 Migration complete')
        
    except sqlite3.Error as e:
        print(f'🔍 ERROR during migration: {e}')
        conn.rollback()
    finally:
        conn.close()


def ensure_database():
    """Ensure database is initialized and migrated"""
    init_database()
    migrate_auto_seeding_schema()
    print('🔍 Database ready')


if __name__ == '__main__':
    ensure_database()
