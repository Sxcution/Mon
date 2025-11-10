#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 DEBUG: Telegram API Routes
Routes xử lý các API cho Telegram Manager
Ported from Main.pyw để match 100%
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import json
import uuid
import traceback
import shutil
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Thread

# Import workers
from app.telegram_workers import (
    check_single_session_worker,
    join_group_worker,
    seeding_group_worker,
    run_task_in_thread
)

# Tạo Blueprint cho Telegram
telegram_bp = Blueprint('telegram', __name__, url_prefix='/telegram')

# Đường dẫn lưu trữ
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
DATABASE_PATH = DATA_DIR / 'Data.db'
UPLOAD_FOLDER = DATA_DIR / 'uploaded_sessions'
ADMIN_SESSION_FOLDER = "Adminsession"

# Global task storage (in-memory, like Main.pyw)
TASKS = {}

# Tạo thư mục nếu chưa có
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

print('🔍 DEBUG: Telegram routes module loaded')


def get_db_connection():
    """🔍 Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_proxies():
    """🔍 Load proxies from database or file"""
    proxy_file = DATA_DIR / 'telegram' / 'proxy_config.json'
    if proxy_file.exists():
        try:
            with open(proxy_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'enabled': False, 'proxies': []}


def save_proxies(proxy_config):
    """🔍 Save proxies to file"""
    proxy_file = DATA_DIR / 'telegram' / 'proxy_config.json'
    proxy_file.parent.mkdir(parents=True, exist_ok=True)
    with open(proxy_file, 'w', encoding='utf-8') as f:
        json.dump(proxy_config, f, ensure_ascii=False, indent=2)


@telegram_bp.route('/api/groups', methods=['GET', 'POST'])
def manage_groups():
    """🔍 Lấy danh sách hoặc tạo nhóm session (match Main.pyw)"""
    conn = get_db_connection()
    
    if request.method == 'GET':
        print('🔍 GET /telegram/api/groups')
        groups = conn.execute("SELECT * FROM session_groups ORDER BY name").fetchall()
        conn.close()
        result = [dict(row) for row in groups]
        print(f'🔍 Returning {len(result)} groups')
        return jsonify(result)
    
    if request.method == 'POST':
        print('🔍 POST /telegram/api/groups')
        try:
            name = request.form.get('name')
            files = request.files.getlist('session_files')
            
            print(f'🔍 Group name: {name}, Files: {len(files)}')
            
            if not name or not files or files[0].filename == '':
                conn.close()
                return jsonify({'error': 'Tên nhóm và file không được trống'}), 400
            
            # Check if group name already exists in database
            print(f'🔍 Checking if group name exists in database: {name}')
            existing_group = conn.execute(
                'SELECT id FROM session_groups WHERE name = ?', (name,)
            ).fetchone()
            
            if existing_group:
                conn.close()
                print(f'🔍 ERROR: Group name already exists in database')
                return jsonify({'error': f'Tên nhóm "{name}" đã tồn tại.'}), 409
            
            group_folder_name = secure_filename(name)
            group_path = os.path.join(UPLOAD_FOLDER, group_folder_name)
            
            # If folder exists but not in DB, remove it first (cleanup orphaned folders)
            if os.path.exists(group_path):
                print(f'🔍 WARNING: Folder exists but not in DB, removing orphaned folder')
                shutil.rmtree(group_path)
            
            os.makedirs(group_path)
            
            saved_count = 0
            for file in files:
                if file and file.filename.endswith('.session'):
                    file.save(os.path.join(group_path, secure_filename(file.filename)))
                    saved_count += 1
                    print(f'🔍 Saved session: {file.filename}')
            
            try:
                conn.execute(
                    'INSERT INTO session_groups (name, folder_path) VALUES (?, ?)',
                    (name, group_path),
                )
                conn.commit()
                print(f'🔍 Created group {name} with {saved_count} sessions')
                return jsonify({'success': True, 'message': f'Tạo nhóm thành công với {saved_count} sessions'}), 201
            except sqlite3.IntegrityError:
                shutil.rmtree(group_path)
                return jsonify({'error': 'Tên nhóm đã tồn tại trong DB.'}), 409
            finally:
                conn.close()
                
        except Exception as e:
            print(f'🔍 ERROR in manage_groups POST: {e}')
            print(f'🔍 Traceback: {traceback.format_exc()}')
            conn.close()
            return jsonify({'error': str(e)}), 500


@telegram_bp.route('/api/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """🔍 Xóa nhóm session (match Main.pyw)"""
    print(f'🔍 DELETE /telegram/api/groups/{group_id}')
    conn = get_db_connection()
    try:
        group = conn.execute(
            'SELECT folder_path FROM session_groups WHERE id = ?', (group_id,)
        ).fetchone()
        
        if group and os.path.exists(group['folder_path']):
            shutil.rmtree(group['folder_path'])
            print(f'🔍 Deleted folder: {group["folder_path"]}')
        
        conn.execute('DELETE FROM session_metadata WHERE group_id = ?', (group_id,))
        conn.execute('DELETE FROM session_groups WHERE id = ?', (group_id,))
        conn.commit()
        
        print(f'🔍 Deleted group {group_id}')
        return jsonify({'success': True})
        
    except Exception as e:
        print(f'🔍 ERROR in delete_group: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@telegram_bp.route('/api/groups/<int:group_id>/sessions', methods=['GET'])
def get_group_sessions(group_id):
    """🔍 Lấy danh sách session trong nhóm (match Main.pyw)"""
    print(f'🔍 GET /telegram/api/groups/{group_id}/sessions')
    conn = get_db_connection()
    try:
        group = conn.execute(
            'SELECT folder_path FROM session_groups WHERE id = ?', (group_id,)
        ).fetchone()
        
        if not group:
            return jsonify({'error': 'Không tìm thấy nhóm'}), 404
        
        # Lấy metadata từ database
        metadata_rows = conn.execute(
            'SELECT * FROM session_metadata WHERE group_id = ?', (group_id,)
        ).fetchall()
        
        metadata_map = {row['filename']: dict(row) for row in metadata_rows}
        
        sessions = []
        folder_path = group['folder_path']
        
        if os.path.exists(folder_path):
            session_files = sorted(
                [f for f in os.listdir(folder_path) if f.endswith('.session')]
            )
            
            for i, filename in enumerate(session_files):
                meta = metadata_map.get(filename, {})
                
                # Extract phone từ filename
                phone_match = re.search(r'\+?\d{9,15}', filename.replace('.session', ''))
                phone = phone_match.group(0) if phone_match else filename
                
                sessions.append({
                    'stt': i + 1,
                    'phone': phone,
                    'filename': filename,
                    'full_name': meta.get('full_name', 'Chưa kiểm tra'),
                    'username': meta.get('username', ''),
                    'is_live': meta.get('is_live'),
                    'status_text': meta.get('status_text', 'Sẵn sàng'),
                })
        
        print(f'🔍 Returning {len(sessions)} sessions')
        return jsonify(sessions)
        
    except Exception as e:
        print(f'🔍 ERROR in get_group_sessions: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@telegram_bp.route('/api/upload-admin-sessions', methods=['POST'])
def upload_admin_sessions():
    """🔍 Upload admin sessions (match Main.pyw)"""
    print('🔍 POST /telegram/api/upload-admin-sessions')
    try:
        files = request.files.getlist('admin_session_files')
        
        if not files or not files[0].filename:
            return jsonify({'error': 'Không có file nào được tải lên'}), 400
        
        admin_folder_path = os.path.join(UPLOAD_FOLDER, ADMIN_SESSION_FOLDER)
        if not os.path.exists(admin_folder_path):
            os.makedirs(admin_folder_path)
        
        file_count = 0
        for file in files:
            if file and file.filename.endswith('.session'):
                file.save(os.path.join(admin_folder_path, secure_filename(file.filename)))
                file_count += 1
                print(f'🔍 Saved admin session: {file.filename}')
        
        if file_count == 0:
            return jsonify({'error': 'Không có file .session hợp lệ'}), 400
        
        # Ensure Adminsession group exists in database
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO session_groups (name, folder_path) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET folder_path=excluded.folder_path',
                (ADMIN_SESSION_FOLDER, admin_folder_path),
            )
            conn.commit()
        finally:
            conn.close()
        
        print(f'🔍 Uploaded {file_count} admin sessions')
        return jsonify({
            'success': True,
            'message': f'Đã tải lên {file_count} session admin.'
        })
        
    except Exception as e:
        print(f'🔍 ERROR in upload_admin_sessions: {e}')
        print(f'🔍 Traceback: {traceback.format_exc()}')
        return jsonify({'error': str(e)}), 500


@telegram_bp.route('/api/config/<task_name>', methods=['GET', 'POST'])
def manage_config(task_name):
    """🔍 Lấy hoặc lưu cấu hình task (match Main.pyw)"""
    print(f'🔍 {request.method} /telegram/api/config/{task_name}')
    conn = get_db_connection()
    try:
        if request.method == 'GET':
            row = conn.execute(
                'SELECT config_json FROM task_configs WHERE task_name = ?', (task_name,)
            ).fetchone()
            result = json.loads(row['config_json']) if row else {}
            print(f'🔍 Loaded config for {task_name}: {result}')
            return jsonify(result)
        
        if request.method == 'POST':
            config_data = request.get_json()
            conn.execute(
                'INSERT INTO task_configs (task_name, config_json) VALUES (?, ?) ON CONFLICT(task_name) DO UPDATE SET config_json=excluded.config_json',
                (task_name, json.dumps(config_data, ensure_ascii=False)),
            )
            conn.commit()
            print(f'🔍 Saved config for {task_name}')
            return jsonify({'success': True, 'message': 'Đã lưu cấu hình.'})
            
    except Exception as e:
        print(f'🔍 ERROR in manage_config: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@telegram_bp.route('/api/proxies', methods=['GET'])
def get_proxies():
    """🔍 Lấy cấu hình proxy"""
    print('🔍 GET /telegram/api/proxies')
    return jsonify(load_proxies())


@telegram_bp.route('/api/proxies', methods=['POST'])
def update_proxies():
    """🔍 Cập nhật proxy"""
    print('🔍 POST /telegram/api/proxies')
    try:
        data = request.json
        enabled = data.get('enabled', False)
        proxies_text = data.get('proxies', '')
        
        # Parse proxies
        proxies = [p.strip() for p in proxies_text.split('\n') if p.strip()]
        
        proxy_config = {
            'enabled': enabled,
            'proxies': proxies
        }
        
        save_proxies(proxy_config)
        print(f'🔍 Saved {len(proxies)} proxies, enabled={enabled}')
        
        return jsonify({'success': True, 'message': f'Đã lưu {len(proxies)} proxy.'})
        
    except Exception as e:
        print(f'🔍 ERROR in update_proxies: {e}')
        return jsonify({'error': str(e)}), 500


@telegram_bp.route('/api/run-task', methods=['POST'])
def run_task():
    """🔍 Chạy task (match Main.pyw - với skeleton worker)"""
    print('🔍 POST /telegram/api/run-task')
    try:
        data = request.get_json() or {}
        print(f'🔍 Received data: {data}')
        
        # Extract parameters (match Main.pyw)
        group_id = data.get('groupId')
        task_name = data.get('task')
        config = data.get('config', {})
        filenames = data.get('filenames', [])
        core = int(data.get('core', 5))
        delay_per_session = int(data.get('delay_per_session', 10))
        delay_between_batches = int(data.get('delay_between_batches', 600))
        admin_enabled = bool(data.get('admin_enabled', False))
        admin_delay = int(data.get('admin_delay', 10))
        
        print(f'🔍 Task: {task_name}, Group: {group_id}, Sessions: {len(filenames)}')
        print(f'🔍 Core: {core}, Delay/Session: {delay_per_session}, Delay/Batch: {delay_between_batches}')
        print(f'🔍 Admin enabled: {admin_enabled}, Admin delay: {admin_delay}')
        print(f'🔍 Config keys: {list(config.keys())}')
        if 'admin_session_file' in config:
            print(f'🔍 Admin session file: {config.get("admin_session_file")}')
        if 'admin_messages' in config:
            print(f'🔍 Admin messages count: {len(config.get("admin_messages", []))}')
        
        if not all([group_id, task_name, filenames]):
            return jsonify({'error': 'Dữ liệu không hợp lệ'}), 400
        
        # Get group info
        conn = get_db_connection()
        group = conn.execute('SELECT folder_path FROM session_groups WHERE id = ?', (group_id,)).fetchone()
        conn.close()
        
        if not group or not group['folder_path']:
            return jsonify({'error': 'Không tìm thấy nhóm hoặc đường dẫn thư mục của nhóm không hợp lệ.'}), 404
        
        # Load proxies
        proxy_config = load_proxies()
        proxies_to_use = proxy_config['proxies'] if proxy_config.get('enabled', False) else []
        
        # Create task (match Main.pyw structure)
        task_id = str(uuid.uuid4())
        TASKS[task_id] = {
            'task_name': task_name,
            'group_id': group_id,
            'status': 'running',
            'total': len(filenames),
            'processed': 0,
            'success': 0,
            'failed': 0,
            'results': [],
            'messages': []
        }
        
        print(f'🔍 Created task {task_id}')
        
        # Determine worker function based on task name
        worker_func, args = None, []
        if task_name == "check-live":
            worker_func = check_single_session_worker
        elif task_name == "joinGroup":
            worker_func = join_group_worker
            args = [config.get("links", [])]
        elif task_name == "seedingGroup":
            worker_func = seeding_group_worker
            args = [config]  # Pass whole config
        
        if not worker_func:
            if task_id in TASKS:
                del TASKS[task_id]
            return jsonify({'error': 'Tác vụ không được hỗ trợ'}), 400
        
        # Start worker thread (match Main.pyw)
        # Get UPLOAD_FOLDER from Flask config to pass to worker
        from flask import current_app
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "")
        
        thread = Thread(
            target=run_task_in_thread,
            args=(
                task_id, group_id, group['folder_path'], filenames, core,
                delay_per_session, delay_between_batches, admin_enabled, admin_delay,
                worker_func, upload_folder, *args
            ),
            kwargs={"proxies": proxies_to_use}
        )
        thread.daemon = True
        thread.start()
        
        print(f'🔍 ✅ Task started in thread: {task_id}')
        return jsonify({'task_id': task_id}), 202
        
    except Exception as e:
        print(f'🔍 ERROR in run_task: {e}')
        print(f'🔍 Traceback: {traceback.format_exc()}')
        return jsonify({'error': str(e)}), 500


@telegram_bp.route('/api/global-settings', methods=['POST'])
def save_telegram_global_settings():
    """🔍 Lưu cài đặt global (match Main.pyw)"""
    print('🔍 POST /telegram/api/global-settings')
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        
        conn = get_db_connection()
        # Match Main.pyw: UPDATE auto_seeding_settings
        conn.execute(
            """UPDATE auto_seeding_settings SET
                 core = ?,
                 delay_per_session = ?,
                 delay_between_batches = ?,
                 admin_enabled = ?,
                 admin_delay = ?
               WHERE id = 1;
            """,
            (
                data.get('core', 5),
                data.get('delay_per_session', 10),
                data.get('delay_between_batches', 600),
                data.get('admin_enabled', False),
                data.get('admin_delay', 10)
            )
        )
        conn.commit()
        conn.close()
        
        print(f'🔍 Saved global settings: {data}')
        return jsonify({'success': True, 'message': 'Đã lưu cài đặt chung.'})
        
    except sqlite3.Error as e:
        print(f'🔍 ERROR (Database): {e}')
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        print(f'🔍 ERROR: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@telegram_bp.route('/api/task-status/<task_id>')
def task_status(task_id):
    """🔍 Lấy trạng thái task (match Main.pyw)"""
    # Removed spam log: print(f'🔍 GET /telegram/api/task-status/{task_id}')
    task = TASKS.get(task_id)
    if not task:
        return jsonify({'status': 'not_found'}), 404
    
    # Match Main.pyw: Return and clear results/messages
    response = task.copy()
    response['results'], response['messages'] = task.get('results', []), task.get('messages', [])
    task['results'], task['messages'] = [], []
    
    return jsonify(response)


@telegram_bp.route('/api/stop-task/<task_id>', methods=['POST'])
def stop_task_route(task_id):
    """🔍 Dừng task (match Main.pyw)"""
    print(f'🔍 POST /telegram/api/stop-task/{task_id}')
    if task_id in TASKS:
        TASKS[task_id]['status'] = 'stopped'
        print(f'🔍 Stopped task {task_id}')
    return jsonify({'message': 'Yêu cầu dừng đã được gửi.'}), 200


@telegram_bp.route('/api/active-tasks')
def get_active_tasks():
    """🔍 Lấy danh sách task đang chạy (match Main.pyw)"""
    print('🔍 GET /telegram/api/active-tasks')
    active_tasks = {
        task_id: {
            'task_name': task_data.get('task_name'),
            'group_id': task_data.get('group_id'),
            'status': task_data.get('status'),
            'total': task_data.get('total'),
            'processed': task_data.get('processed'),
            'success': task_data.get('success'),
            'failed': task_data.get('failed'),
        }
        for task_id, task_data in TASKS.items()
        if task_data.get('status') in ['running', 'stopped']
    }
    print(f'🔍 Active tasks: {len(active_tasks)}')
    return jsonify(active_tasks)


@telegram_bp.route('/api/sessions/delete', methods=['POST'])
def delete_sessions():
    """🔍 Xóa sessions (match Main.pyw)"""
    print('🔍 POST /telegram/api/sessions/delete')
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        
        group_id = data.get('group_id')
        filenames = data.get('filenames', [])
        
        if not group_id:
            return jsonify({'error': 'group_id is required'}), 400
        
        if not filenames or not isinstance(filenames, list):
            return jsonify({'error': 'filenames must be a non-empty list'}), 400
        
        # Check if any task is running
        active_tasks = [task for task in TASKS.values() if task.get('status') == 'running']
        if active_tasks:
            return jsonify({'error': 'Task is running'}), 409
        
        conn = get_db_connection()
        try:
            group = conn.execute('SELECT folder_path FROM session_groups WHERE id = ?', (group_id,)).fetchone()
            if not group:
                return jsonify({'error': 'Group not found'}), 404
            
            group_folder = group['folder_path']
            if not os.path.exists(group_folder):
                return jsonify({'error': 'Group folder not found'}), 404
            
            deleted = []
            missing = []
            failed = []
            
            for filename in filenames:
                # Sanitize filename
                clean_filename = os.path.basename(filename)
                if clean_filename != filename or not clean_filename:
                    failed.append(filename)
                    continue
                
                file_path = os.path.join(group_folder, clean_filename)
                
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        deleted.append(clean_filename)
                        
                        # Remove from metadata
                        conn.execute('DELETE FROM session_metadata WHERE group_id = ? AND filename = ?',
                                   (group_id, clean_filename))
                        print(f'🔍 Deleted session: {clean_filename}')
                    else:
                        missing.append(clean_filename)
                except OSError as e:
                    failed.append(clean_filename)
                    print(f'🔍 Failed to delete {file_path}: {e}')
            
            conn.commit()
            
            print(f'🔍 Deleted {len(deleted)} sessions')
            return jsonify({
                'deleted': deleted,
                'missing': missing,
                'failed': failed
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f'🔍 ERROR in delete_sessions: {e}')
        print(f'🔍 Traceback: {traceback.format_exc()}')
        return jsonify({'error': str(e)}), 500


@telegram_bp.route('/api/update-session-info', methods=['POST'])
def update_session_info():
    """🔍 Cập nhật thông tin session (match Main.pyw)"""
    print('🔍 POST /telegram/api/update-session-info')
    try:
        data = request.get_json()
        group_id = data.get('group_id')
        filename = data.get('filename')
        field = data.get('field')
        value = data.get('value')
        
        print(f'🔍 Updating {field}={value} for {filename} in group {group_id}')
        
        if field not in ['full_name', 'username']:
            return jsonify({'error': 'Invalid field'}), 400
        
        conn = get_db_connection()
        try:
            # Check if metadata exists
            existing = conn.execute(
                'SELECT * FROM session_metadata WHERE group_id = ? AND filename = ?',
                (group_id, filename)
            ).fetchone()
            
            if existing:
                # Update
                conn.execute(
                    f'UPDATE session_metadata SET {field} = ? WHERE group_id = ? AND filename = ?',
                    (value, group_id, filename)
                )
            else:
                # Insert
                conn.execute(
                    'INSERT INTO session_metadata (group_id, filename, full_name, username) VALUES (?, ?, ?, ?)',
                    (group_id, filename, value if field == 'full_name' else None, value if field == 'username' else None)
                )
            
            conn.commit()
            
            print(f'🔍 Updated {field} successfully')
            return jsonify({
                'success': True,
                'message': f'Đã cập nhật {field}',
                'updated_value': value
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f'🔍 ERROR in update_session_info: {e}')
        print(f'🔍 Traceback: {traceback.format_exc()}')
        return jsonify({'error': str(e)}), 500


print('🔍 DEBUG: Telegram routes defined successfully (matched with Main.pyw)')
