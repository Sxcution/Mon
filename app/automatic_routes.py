#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 DEBUG: Automatic Seeding Routes
Routes xử lý Auto Seeding Scheduler
Ported from Main.pyw - uses SQLite database
"""

from flask import Blueprint, request, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime

# Tạo Blueprint
automatic_bp = Blueprint('automatic', __name__, url_prefix='/automatic')

# Đường dẫn database
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
DATABASE_PATH = DATA_DIR / 'Data.db'

print('🔍 DEBUG: Automatic routes module loaded')


def get_db_connection():
    """🔍 Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@automatic_bp.route('/api/seeding/settings', methods=['GET'])
def get_seeding_settings():
    """🔍 Lấy cài đặt auto seeding từ database (match Main.pyw)"""
    print('🔍 GET /automatic/api/seeding/settings')
    try:
        conn = get_db_connection()
        row = conn.execute('SELECT * FROM auto_seeding_settings WHERE id = 1').fetchone()
        conn.close()
        
        if row:
            # Convert SQLite row to dict
            settings = dict(row)
            print(f'🔍 Returning seeding settings: {settings}')
            return jsonify(settings)
        else:
            # Return defaults
            defaults = {
                'core': 5,
                'delay_per_session': 10,
                'delay_between_batches': 600,
                'admin_enabled': False,
                'admin_delay': 10
            }
            print(f'🔍 No settings found, returning defaults')
            return jsonify(defaults)
            
    except Exception as e:
        print(f'🔍 ERROR in get_seeding_settings: {e}')
        return jsonify({'error': str(e)}), 500


@automatic_bp.route('/api/seeding/settings', methods=['POST'])
def save_seeding_settings():
    """🔍 Lưu cài đặt auto seeding vào database (match Main.pyw)"""
    print('🔍 POST /automatic/api/seeding/settings')
    try:
        settings = request.json
        
        conn = get_db_connection()
        
        # Update full settings (including scheduler settings)
        conn.execute(
            """UPDATE auto_seeding_settings SET
                 is_enabled = ?,
                 run_time = ?,
                 end_run_time = ?,
                 run_daily = ?,
                 target_session_group_id = ?,
                 task_name = ?,
                 core = ?,
                 delay_per_session = ?,
                 delay_between_batches = ?,
                 admin_enabled = ?,
                 admin_delay = ?
               WHERE id = 1;
            """,
            (
                settings.get('is_enabled', False),
                settings.get('run_time'),
                settings.get('end_run_time'),
                settings.get('run_daily', False),
                settings.get('target_session_group_id'),
                settings.get('task_name', 'seedingGroup'),
                settings.get('core', 5),
                settings.get('delay_per_session', 10),
                settings.get('delay_between_batches', 600),
                settings.get('admin_enabled', False),
                settings.get('admin_delay', 10)
            )
        )
        
        conn.commit()
        conn.close()
        
        print(f'🔍 Saved seeding settings: {settings}')
        return jsonify({'message': 'Đã lưu cài đặt Auto Seeding'})
        
    except Exception as e:
        print(f'🔍 ERROR in save_seeding_settings: {e}')
        return jsonify({'error': str(e)}), 500


print('🔍 DEBUG: Automatic routes defined successfully')
