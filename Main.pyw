import os
import re
import json
import uuid
import time
import shutil
import asyncio
import sqlite3
import webbrowser
import threading
import sys
import winshell
from threading import Thread
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    Blueprint,
    flash,
    redirect,
    url_for,
    send_from_directory,
)
from werkzeug.utils import secure_filename
from telethon.sync import TelegramClient
from telethon.tl.types import PeerChannel
from telethon.errors import (
    SessionPasswordNeededError,
    FloodWaitError,
    UserBannedInChannelError,
    UsernameInvalidError,
    UsernameOccupiedError,
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import SendMessageRequest, SendReactionRequest
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from PIL import Image, ImageDraw
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup, NavigableString
import pystray
from itertools import cycle
import random


# --- CẤU HÌNH ỨNG DỤNG FLASK ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=".")
app.secret_key = "your_super_secret_key_for_flask_app"

# Cấu hình để tự động reload templates và static files
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# --- CẤU HÌNH FILE DỮ LIỆU ---
# TODO: These JSON file constants can be removed after the one-time migration is confirmed successful.
DATA_DIR = os.path.join(APP_ROOT, "data")
NOTES_DATA_FILE = os.path.join(DATA_DIR, "reminders.json")
FACEBOOK_ACCOUNTS_FILE = os.path.join(DATA_DIR, "facebook_accounts.json")
DATABASE_PATH = os.path.join(DATA_DIR, "Data.db")
PROXIES_FILE = os.path.join(DATA_DIR, "proxies.json")
UPLOAD_FOLDER = os.path.join(APP_ROOT, "data", "uploaded_sessions")
SOUNDS_FOLDER = os.path.join(DATA_DIR, "sounds")
DASHBOARD_SETTINGS_FILE = os.path.join(DATA_DIR, "dashboard_settings.json")
OPEN_APPS_SETTINGS_FILE = os.path.join(DATA_DIR, "open_apps_settings.json")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SOUNDS_FOLDER"] = SOUNDS_FOLDER

# --- BIẾN TOÀN CỤC CHO TELEGRAM ---
TASKS = {}
API_ID, API_HASH = 28610130, "eda4079a5b9d4f3f88b67dacd799f902"
ADMIN_SESSION_FOLDER = "Adminsession"


# --- KHỞI TẠO DATABASE & FILES ---
def init_database():
    # Telegram
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    conn = get_db_connection()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS session_groups (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, folder_path TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS session_metadata (id INTEGER PRIMARY KEY, group_id INTEGER NOT NULL, filename TEXT NOT NULL, full_name TEXT, username TEXT, is_live BOOLEAN, status_text TEXT, last_checked TIMESTAMP, FOREIGN KEY (group_id) REFERENCES session_groups (id), UNIQUE (group_id, filename))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS task_configs (task_name TEXT PRIMARY KEY, config_json TEXT NOT NULL)"
    )
    try:
        conn.execute("SELECT username FROM session_metadata LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE session_metadata ADD COLUMN username TEXT")
    
    # Notes
    conn.execute(
        """CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            title_html TEXT,
            content_html TEXT,
            due_time TEXT,
            status TEXT,
            modified_at TEXT
        )"""
    )
    
    try:
        conn.execute("SELECT is_marked FROM notes LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding 'is_marked' column to notes table...")
        conn.execute("ALTER TABLE notes ADD COLUMN is_marked INTEGER DEFAULT 0")
    
    # Auto Seeding
    conn.execute(
        """CREATE TABLE IF NOT EXISTS auto_seeding_settings (
            id INTEGER PRIMARY KEY,
            is_enabled BOOLEAN NOT NULL DEFAULT 0,
            run_time TEXT,
            end_run_time TEXT,
            run_daily BOOLEAN NOT NULL DEFAULT 0,
            target_session_group_id INTEGER,
            last_run_timestamp TEXT,
            task_name TEXT NOT NULL DEFAULT 'seedingGroup'
        )"""
    )
    
    # Kcal Foods
    conn.execute(
        """CREATE TABLE IF NOT EXISTS kcal_foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            fat REAL NOT NULL,
            carbs REAL NOT NULL
        )"""
    )

    # Body Settings for Kcal Calculator
    conn.execute(
        """CREATE TABLE IF NOT EXISTS body_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            initial_weight REAL,
            current_weight REAL,
            height REAL,
            age INTEGER,
            gender TEXT CHECK(gender IN ('male', 'female')) DEFAULT 'male',
            activity_level TEXT CHECK(activity_level IN ('sedentary', 'light', 'moderate', 'active', 'very_active')) DEFAULT 'moderate',
            last_reset TEXT,
            start_date TEXT,
            daily_calories_target REAL
        )"""
    )
    
    conn.commit()

    # --- Pre-populate kcal_foods table if it's empty ---
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM kcal_foods")
    count = cursor.fetchone()[0]
    if count == 0:
        print("Pre-populating kcal_foods table with default data...")
        default_foods = [
            # Tinh Bột (carbs)
            ('Cơm Trắng', 'carbs', 130, 2.7, 0.3, 28),
            ('Khoai Lang', 'carbs', 90, 2, 0.1, 21),
            ('Khoai Tây', 'carbs', 93, 2.5, 0.1, 21),
            ('Chuối chín', 'carbs', 89, 1.1, 0.3, 23),
            ('Xoài', 'carbs', 60, 0.8, 0.4, 15),
            ('Sầu Riêng', 'carbs', 147, 1.5, 5, 27),
            # Thịt/Cá (protein)
            ('Ức gà', 'protein', 165, 31, 3.6, 0),
            ('Trứng Gà', 'protein', 155, 13, 11, 1.1),
            ('Thịt bò (nạc)', 'protein', 250, 26, 15, 0),
            ('Cá thu', 'protein', 205, 24, 11, 0),
            ('Cá chép', 'protein', 162, 23, 7, 0),
            ('Cá hồi', 'protein', 208, 20, 13, 0),
            # Rau/Củ (veggies)
            ('Bầu', 'veggies', 15, 0.6, 0.2, 3.4),
            ('Bí xanh', 'veggies', 13, 0.4, 0.2, 3),
            ('Bí đỏ', 'veggies', 20, 1, 0.1, 5),
            ('Đậu que', 'veggies', 35, 1.9, 0.2, 8),
            ('Bông cải xanh', 'veggies', 35, 2.4, 0.4, 7),
            ('Rau muống', 'veggies', 19, 2.6, 0.2, 3),
        ]
        cursor.executemany(
            "INSERT INTO kcal_foods (name, category, calories, protein, fat, carbs) VALUES (?, ?, ?, ?, ?, ?)",
            default_foods
        )
        conn.commit()
    
    # MXH Tables
    conn = get_db_connection()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS mxh_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT NOT NULL,
            icon TEXT DEFAULT 'bi-share-fill',
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS mxh_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_name TEXT NOT NULL,
            group_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            username TEXT NOT NULL,
            url TEXT,
            created_at TEXT NOT NULL,
            wechat_created_day INTEGER DEFAULT 1,
            wechat_created_month INTEGER DEFAULT 1,
            wechat_created_year INTEGER DEFAULT 2024,
            wechat_scan_create INTEGER DEFAULT 0,
            wechat_scan_rescue INTEGER DEFAULT 0,
            wechat_status TEXT DEFAULT 'available',
            FOREIGN KEY (group_id) REFERENCES mxh_groups (id)
        )"""
    )
    conn.commit()
    conn.close()

    # MXH WeChat Migration - Add WeChat columns if they don't exist
    conn = get_db_connection()
    try:
        # Check if WeChat columns exist
        cursor = conn.execute("PRAGMA table_info(mxh_accounts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        wechat_columns = [
            'wechat_created_day', 'wechat_created_month', 'wechat_created_year',
            'wechat_scan_create', 'wechat_scan_rescue', 'wechat_status',
            'wechat_last_scan_date', 'wechat_scan_count', 'phone', 'status',
            'login_username', 'login_password'
        ]
        
        for column in wechat_columns:
            if column not in columns:
                if column == 'wechat_created_day':
                    conn.execute(f"ALTER TABLE mxh_accounts ADD COLUMN {column} INTEGER DEFAULT {datetime.now().day}")
                elif column == 'wechat_created_month':
                    conn.execute(f"ALTER TABLE mxh_accounts ADD COLUMN {column} INTEGER DEFAULT {datetime.now().month}")
                elif column == 'wechat_created_year':
                    conn.execute(f"ALTER TABLE mxh_accounts ADD COLUMN {column} INTEGER DEFAULT {datetime.now().year}")
                elif column in ['wechat_scan_create', 'wechat_scan_rescue']:
                    conn.execute(f"ALTER TABLE mxh_accounts ADD COLUMN {column} INTEGER DEFAULT 0")
                elif column == 'wechat_status':
                    conn.execute(f"ALTER TABLE mxh_accounts ADD COLUMN {column} TEXT DEFAULT 'available'")
                elif column == 'wechat_last_scan_date':
                    conn.execute(f"ALTER TABLE mxh_accounts ADD COLUMN {column} TEXT DEFAULT NULL")
                elif column == 'wechat_scan_count':
                    conn.execute(f"ALTER TABLE mxh_accounts ADD COLUMN {column} INTEGER DEFAULT 0")
                elif column == 'phone':
                    conn.execute(f"ALTER TABLE mxh_accounts ADD COLUMN {column} TEXT DEFAULT NULL")
                elif column == 'status':
                    conn.execute(f"ALTER TABLE mxh_accounts ADD COLUMN {column} TEXT DEFAULT 'active'")
                elif column in ['login_username', 'login_password']:
                    conn.execute(f"ALTER TABLE mxh_accounts ADD COLUMN {column} TEXT DEFAULT NULL")
        
        # Add icon column to mxh_groups if it doesn't exist
        try:
            # Check if icon column exists
            cursor = conn.execute("PRAGMA table_info(mxh_groups)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'icon' not in columns:
                conn.execute("ALTER TABLE mxh_groups ADD COLUMN icon TEXT DEFAULT 'bi-share-fill'")
                print("Added icon column to mxh_groups table.")
        except Exception as e:
            print(f"Error adding icon column: {e}")
        
        # Migration for secondary WeChat account columns
        secondary_columns = {
            'secondary_card_name': 'TEXT',
            'secondary_username': 'TEXT',
            'secondary_phone': 'TEXT',
            'secondary_wechat_created_day': 'INTEGER',
            'secondary_wechat_created_month': 'INTEGER',
            'secondary_wechat_created_year': 'INTEGER',
            'secondary_wechat_scan_create': 'INTEGER DEFAULT 0',
            'secondary_wechat_scan_rescue': 'INTEGER DEFAULT 0',
            'secondary_wechat_status': 'TEXT DEFAULT \'available\'',
            'secondary_wechat_last_scan_date': 'TEXT',
            'secondary_wechat_scan_count': 'INTEGER DEFAULT 0',
            'secondary_status': 'TEXT DEFAULT \'active\'',
        'muted_until': 'TEXT',
        'secondary_muted_until': 'TEXT',
        'die_date': 'TEXT',
        'rescue_count': 'INTEGER DEFAULT 0',
        'rescue_success_count': 'INTEGER DEFAULT 0',
        'secondary_die_date': 'TEXT',
        'secondary_rescue_count': 'INTEGER DEFAULT 0',
        'secondary_rescue_success_count': 'INTEGER DEFAULT 0'
        }
        
        cursor = conn.execute("PRAGMA table_info(mxh_accounts)")
        existing_columns = [column[1] for column in cursor.fetchall()]

        for col, col_type in secondary_columns.items():
            if col not in existing_columns:
                conn.execute(f"ALTER TABLE mxh_accounts ADD COLUMN {col} {col_type}")
                print(f"Added secondary column '{col}' to mxh_accounts table.")
        
        conn.commit()
        print("MXH WeChat columns migration completed successfully.")
    except Exception as e:
        print(f"Error during MXH WeChat migration: {e}")
        conn.rollback()
    finally:
        conn.close()

    # Facebook
    if not os.path.exists(FACEBOOK_ACCOUNTS_FILE):
        with open(FACEBOOK_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def migrate_json_to_sqlite():
    migration_flag_file = os.path.join(DATA_DIR, 'migration_done.flag')
    if os.path.exists(migration_flag_file):
        return # Migration has already been done.

    print("Running one-time data migration from JSON to SQLite...")
    conn = get_db_connection()
    cursor = conn.cursor()



    # Migrate reminders.json (notes)
    try:
        if os.path.exists(NOTES_DATA_FILE):
            with open(NOTES_DATA_FILE, 'r', encoding='utf-8') as f:
                notes_data = json.load(f)
                for note in notes_data:
                    cursor.execute(
                        "INSERT OR IGNORE INTO notes (id, title_html, content_html, due_time, status, modified_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (note.get('id'), note.get('title_html'), note.get('content_html'), note.get('due_time'), note.get('status'), note.get('modified_at'))
                    )
            print(f"Migrated {len(notes_data)} notes.")
    except Exception as e:
        print(f"Error migrating notes: {e}")

    conn.commit()
    conn.close()
    
    # Create flag file to prevent re-running
    with open(migration_flag_file, 'w') as f:
        f.write(datetime.now().isoformat())
    print("Migration complete.")




# --- FACEBOOK MANAGER: BLUEPRINT & LOGIC ---
facebook_bp = Blueprint("facebook", __name__, url_prefix="/facebook")


def load_fb_accounts():
    if not os.path.exists(FACEBOOK_ACCOUNTS_FILE):
        return []
    with open(FACEBOOK_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_fb_accounts(accounts):
    with open(FACEBOOK_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=4, ensure_ascii=False)


def get_next_fb_id(accounts):
    return max([acc.get("id", 0) for acc in accounts] or [0]) + 1


@facebook_bp.route("/add", methods=["POST"])
def add_fb_account():
    accounts = load_fb_accounts()
    nickname = request.form.get("nickname", "").strip()
    url = request.form.get("url", "").strip()
    if not nickname or not url:
        flash("Nickname và URL Facebook là bắt buộc.", "facebook_danger")
        return redirect(url_for("main_dashboard", tab="facebook"))
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    if not re.match(r"https?://(www\.)?facebook\.com/.*", url):
        flash(
            "URL Facebook không hợp lệ. Vui lòng nhập link dạng https://facebook.com/...",
            "facebook_danger",
        )
        return redirect(url_for("main_dashboard", tab="facebook"))
    new_account = {
        "id": get_next_fb_id(accounts),
        "nickname": nickname,
        "url": url,
        "notes": request.form.get("notes", ""),
    }
    accounts.append(new_account)
    save_fb_accounts(accounts)
    flash("Đã thêm tài khoản Facebook thành công!", "facebook_success")
    return redirect(url_for("main_dashboard", tab="facebook"))


@facebook_bp.route("/update/<int:account_id>", methods=["POST"])
def update_fb_account(account_id):
    accounts = load_fb_accounts()
    account = next((acc for acc in accounts if acc.get("id") == account_id), None)
    if account:
        nickname = request.form.get("nickname", "").strip()
        url = request.form.get("url", "").strip()
        if not nickname or not url:
            flash("Nickname và URL Facebook là bắt buộc.", "facebook_danger")
            return redirect(url_for("main_dashboard", tab="facebook"))
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        if not re.match(r"https?://(www\.)?facebook\.com/.*", url):
            flash("URL Facebook không hợp lệ.", "facebook_danger")
            return redirect(url_for("main_dashboard", tab="facebook"))
        account.update(
            {
                "nickname": nickname,
                "url": url,
                "notes": request.form.get("notes", ""),
            }
        )
        save_fb_accounts(accounts)
        flash("Đã cập nhật tài khoản Facebook thành công!", "facebook_success")
    else:
        flash("Không tìm thấy tài khoản Facebook!", "facebook_danger")
    return redirect(url_for("main_dashboard", tab="facebook"))


@facebook_bp.route("/delete/<int:account_id>", methods=["POST"])
def delete_fb_account(account_id):
    accounts = load_fb_accounts()
    new_accounts = [acc for acc in accounts if acc.get("id") != account_id]
    if len(accounts) > len(new_accounts):
        save_fb_accounts(new_accounts)
        flash("Đã xóa tài khoản Facebook thành công!", "facebook_info")
    else:
        flash("Không tìm thấy tài khoản Facebook!", "facebook_danger")
    return redirect(url_for("main_dashboard", tab="facebook"))


# --- TELEGRAM MANAGER: BLUEPRINT & LOGIC ---
telegram_bp = Blueprint("telegram", __name__, url_prefix="/telegram")


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@telegram_bp.route("/api/groups", methods=["GET", "POST"])
def manage_groups():
    conn = get_db_connection()
    if request.method == "GET":
        groups = conn.execute("SELECT * FROM session_groups ORDER BY name").fetchall()
        conn.close()
        return jsonify([dict(row) for row in groups])
    if request.method == "POST":
        name = request.form.get("name")
        files = request.files.getlist("session_files")
        if not name or not files or files[0].filename == "":
            conn.close()
            return jsonify({"error": "Tên nhóm và file không được trống"}), 400
        group_folder_name = secure_filename(name)
        group_path = os.path.join(app.config["UPLOAD_FOLDER"], group_folder_name)
        if os.path.exists(group_path):
            conn.close()
            return jsonify({"error": f'Tên nhóm "{name}" đã tồn tại.'}), 409
        os.makedirs(group_path)
        for file in files:
            if file and file.filename.endswith(".session"):
                file.save(os.path.join(group_path, secure_filename(file.filename)))
        try:
            conn.execute(
                "INSERT INTO session_groups (name, folder_path) VALUES (?, ?)",
                (name, group_path),
            )
            conn.commit()
            return jsonify({"success": True, "message": "Tạo nhóm thành công"}), 201
        except sqlite3.IntegrityError:
            shutil.rmtree(group_path)
            return jsonify({"error": "Tên nhóm đã tồn tại trong DB."}), 409
        finally:
            conn.close()


@telegram_bp.route("/api/groups/<int:group_id>", methods=["DELETE"])
def delete_group(group_id):
    conn = get_db_connection()
    group = conn.execute(
        "SELECT folder_path FROM session_groups WHERE id = ?", (group_id,)
    ).fetchone()
    if group and os.path.exists(group["folder_path"]):
        shutil.rmtree(group["folder_path"])
    conn.execute("DELETE FROM session_metadata WHERE group_id = ?", (group_id,))
    conn.execute("DELETE FROM session_groups WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@telegram_bp.route("/api/groups/<int:group_id>/sessions", methods=["GET"])
def get_group_sessions(group_id):
    conn = get_db_connection()
    group = conn.execute(
        "SELECT folder_path FROM session_groups WHERE id = ?", (group_id,)
    ).fetchone()
    if not group:
        conn.close()
        return jsonify({"error": "Không tìm thấy nhóm"}), 404
    metadata_rows = conn.execute(
        "SELECT * FROM session_metadata WHERE group_id = ?", (group_id,)
    ).fetchall()
    conn.close()
    metadata_map = {row["filename"]: dict(row) for row in metadata_rows}
    sessions = []
    folder_path = group["folder_path"]
    if os.path.exists(folder_path):
        session_files = sorted(
            [f for f in os.listdir(folder_path) if f.endswith(".session")]
        )
        for i, filename in enumerate(session_files):
            meta = metadata_map.get(filename, {})
            phone_match = re.search(r"\+?\d{9,15}", filename.replace(".session", ""))
            phone = phone_match.group(0) if phone_match else filename
            sessions.append(
                {
                    "stt": i + 1,
                    "phone": phone,
                    "filename": filename,
                    "full_name": meta.get("full_name", "Chưa kiểm tra"),
                    "username": meta.get("username", ""),
                    "is_live": meta.get("is_live"),
                    "status_text": meta.get("status_text", "Sẵn sàng"),
                }
            )
    return jsonify(sessions)


@telegram_bp.route("/api/upload-admin-sessions", methods=["POST"])
def upload_admin_sessions():
    files = request.files.getlist("admin_session_files")
    if not files or not files[0].filename:
        return jsonify({"error": "Không có file nào được tải lên"}), 400
    admin_folder_path = os.path.join(app.config["UPLOAD_FOLDER"], ADMIN_SESSION_FOLDER)
    if not os.path.exists(admin_folder_path):
        os.makedirs(admin_folder_path)
    file_count = 0
    for file in files:
        if file and file.filename.endswith(".session"):
            file.save(os.path.join(admin_folder_path, secure_filename(file.filename)))
            file_count += 1
    if file_count == 0:
        return jsonify({"error": "Không có file .session hợp lệ"}), 400
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO session_groups (name, folder_path) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET folder_path=excluded.folder_path",
            (ADMIN_SESSION_FOLDER, admin_folder_path),
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify(
        {"success": True, "message": f"Đã tải lên {file_count} session admin."}
    )


@app.route('/telegram/api/groups/<int:group_id>/upload-sessions', methods=['POST'])
def upload_sessions_to_group(group_id):
    conn = get_db_connection()
    group = conn.execute("SELECT folder_path FROM session_groups WHERE id = ?", (group_id,)).fetchone()
    conn.close()
    if not group:
        return jsonify({"error": "Không tìm thấy nhóm"}), 404
    folder_path = group["folder_path"] if isinstance(group, dict) else group[0]
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    files = request.files.getlist('session_files')
    count = 0
    for file in files:
        if file and file.filename.endswith('.session'):
            file.save(os.path.join(folder_path, secure_filename(file.filename)))
            count += 1
    return jsonify({"success": True, "uploaded": count})


@telegram_bp.route("/api/config/<task_name>", methods=["GET", "POST"])
def manage_config(task_name):
    conn = get_db_connection()
    try:
        if request.method == "GET":
            row = conn.execute(
                "SELECT config_json FROM task_configs WHERE task_name = ?", (task_name,)
            ).fetchone()
            return jsonify(json.loads(row["config_json"]) if row else {})
        if request.method == "POST":
            config_data = request.get_json()
            conn.execute(
                "INSERT INTO task_configs (task_name, config_json) VALUES (?, ?) ON CONFLICT(task_name) DO UPDATE SET config_json=excluded.config_json",
                (task_name, json.dumps(config_data)),
            )
            conn.commit()
            return jsonify({"success": True})
    finally:
        conn.close()


# --- Helper cho proxy ---
def load_proxies():
    """
    Tải cấu hình proxy. Tự động nâng cấp từ định dạng cũ (list) sang định dạng mới (dict).
    """
    if not os.path.exists(PROXIES_FILE):
        return {"enabled": False, "proxies": []}
    try:
        with open(PROXIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"enabled": True, "proxies": data}
            return {
                "enabled": data.get("enabled", False),
                "proxies": data.get("proxies", [])
            }
    except (json.JSONDecodeError, IOError):
        return {"enabled": False, "proxies": []}

def save_proxies(proxy_config):
    """
    Lưu cấu hình proxy (bao gồm trạng thái bật/tắt và danh sách proxy).
    """
    with open(PROXIES_FILE, "w", encoding="utf-8") as f:
        json.dump(proxy_config, f, indent=4, ensure_ascii=False)

def parse_proxy_string(proxy_str):
    if not proxy_str:
        return None
    try:
        parts = proxy_str.strip().split(':')
        if len(parts) == 4:
            return {
                'proxy_type': 'http',
                'addr': parts[0],
                'port': int(parts[1]),
                'username': parts[2],
                'password': parts[3]
            }
        elif len(parts) == 2:
            return {
                'proxy_type': 'http',
                'addr': parts[0],
                'port': int(parts[1])
            }
        return None
    except (ValueError, IndexError):
        return None

async def join_group_worker(session_path, links, *args, **kwargs):
    """Worker function for joining groups/channels."""
    proxy_info = kwargs.get("proxy_info")
    status = {"is_live": False, "full_name": "Lỗi", "username": "", "status_text": "Lỗi không xác định", "joined_count": 0}
    client = None
    if not links:
        status["status_text"] = "Không có link"
        return status
    try:
        proxy_dict = parse_proxy_string(proxy_info)
        client = TelegramClient(session_path, API_ID, API_HASH, proxy=proxy_dict)
        await client.connect()
        if not await client.is_user_authorized():
            status["status_text"] = "Session die"
            return status

        me = await client.get_me()
        status["is_live"] = True
        status["full_name"] = f"{me.first_name or ''} {me.last_name or ''}".strip()
        status["username"] = me.username or ""
        
        joined_count = 0
        for link in links:
            try:
                await client(JoinChannelRequest(link))
                joined_count += 1
                await asyncio.sleep(1)
            except (ValueError, TypeError):
                continue
            except (UserBannedInChannelError, FloodWaitError):
                continue
        status["status_text"] = f"Đã join {joined_count}/{len(links)} nhóm"
        status["joined_count"] = joined_count
    except Exception as e:
        status["status_text"] = str(e)[:50]
        # Preserve last known name if an error occurs mid-task
        if 'me' in locals() and me:
            status["full_name"] = f"{me.first_name or ''} {me.last_name or ''}".strip()
            status["username"] = me.username or ""
    finally:
        if client and client.is_connected():
            await client.disconnect()
    return status

async def seeding_group_worker(session_path, group_link, message, send_silent=False, *args, **kwargs):
    """Worker function for seeding groups with specific message and group."""
    proxy_info = kwargs.get("proxy_info")
    status = {"is_live": False, "full_name": "Lỗi", "username": "", "status_text": "Lỗi seeding"}
    client = None
    try:
        proxy_dict = parse_proxy_string(proxy_info)
        client = TelegramClient(session_path, API_ID, API_HASH, proxy=proxy_dict)
        await client.connect()
        if not await client.is_user_authorized():
            status["status_text"] = "Session die"
            return status

        me = await client.get_me()
        status["is_live"] = True
        status["full_name"] = f"{me.first_name or ''} {me.last_name or ''}".strip()
        status["username"] = me.username or ""
        
        try:
            await client(JoinChannelRequest(group_link))
        except Exception:
             pass # Continue even if join fails

        await client.send_message(group_link, message, silent=send_silent)
        status["status_text"] = "Đã gửi tin nhắn"
        
    except Exception as e:
        status["status_text"] = str(e)[:50]
        # Preserve last known name if an error occurs mid-task
        if 'me' in locals() and me:
            status["full_name"] = f"{me.first_name or ''} {me.last_name or ''}".strip()
            status["username"] = me.username or ""
    finally:
        if client and client.is_connected():
            await client.disconnect()
    return status

async def run_admin_task(admin_session_path, group_link, message):
    """A dedicated function to run the admin session task."""
    client = None
    try:
        # Admin does not use proxy in this logic
        client = TelegramClient(admin_session_path, API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            print("Admin session is not authorized.")
            return

        # Ensure the admin is in the group before sending a message.
        try:
            await client(JoinChannelRequest(group_link))
        except Exception as join_error:
            # Log the error but continue, as the session might already be in the channel.
            print(f"Admin session join error (might be already in channel): {join_error}")

        await client.send_message(group_link, message)
        print(f"Admin sent message to {group_link}")
    except Exception as e:
        print(f"Admin task failed for group {group_link}: {e}")
    finally:
        if client and client.is_connected():
            await client.disconnect()

async def check_single_session_worker(session_path, *args, **kwargs):
    proxy_info = kwargs.get("proxy_info")
    status = {"is_live": False, "full_name": "Lỗi", "username": "", "status_text": "Error"}
    client = None
    try:
        proxy_dict = parse_proxy_string(proxy_info)
        client = TelegramClient(session_path, API_ID, API_HASH, proxy=proxy_dict)
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            status = {"is_live": True, "full_name": f"{me.first_name or ''} {me.last_name or ''}".strip(), "username": me.username or "", "status_text": "Live"}
        else:
            status["status_text"] = "Dead"
    except SessionPasswordNeededError:
        status["status_text"] = "2FA Enabled"
    except Exception as e:
        status["status_text"] = str(e)[:50]
    finally:
        if client and client.is_connected():
            await client.disconnect()
    return status

async def task_worker(task_id, group_id, session_path, filename, coro_func, *args, **kwargs):
    proxy_info = kwargs.get("proxy_info")
    status_result = await coro_func(session_path, *args, proxy_info=proxy_info)
    
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO session_metadata (group_id, filename, full_name, username, is_live, status_text, last_checked) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) ON CONFLICT(group_id, filename) DO UPDATE SET full_name=excluded.full_name, username=excluded.username, is_live=excluded.is_live, status_text=excluded.status_text, last_checked=CURRENT_TIMESTAMP",
            (group_id, filename, status_result.get("full_name"), status_result.get("username"), status_result.get("is_live"), status_result.get("status_text"))
        )
        conn.commit()
    finally:
        conn.close()

    task = TASKS.get(task_id)
    if task:
        task["processed"] += 1
        if status_result.get("is_live"):
            task["success"] += 1
        else:
            task["failed"] += 1
        task["results"].append({"filename": filename, **status_result})

def run_task_in_thread(
    task_id, group_id, folder_path, filenames,
    core, delay_per_session, delay_between_batches,
    admin_enabled, admin_delay,
    worker_coro_func, *args, **kwargs
):
    async def main():
        task = TASKS.get(task_id)
        if not task or not folder_path:
            if task: task["status"] = "failed"
            return

        proxies = kwargs.get("proxies", [])
        config = args[0] if args else {}
        
        # Prepare list of tasks to run
        tasks_to_run = []
        for f in filenames:
            if not f:
                task["total"] = max(0, task["total"] - 1)
                continue
            session_file_path = os.path.join(folder_path, f)
            if os.path.exists(session_file_path):
                tasks_to_run.append((session_file_path, f))

        # Determine concurrency and batching logic based on task type
        is_seeding_task = task.get("task_name") == "seedingGroup"
        if is_seeding_task:
            group_links = config.get("group_links", [])
            if not group_links:
                task["status"] = "failed"; task["messages"].append("Lỗi: Seeding cần ít nhất 1 link nhóm.")
                return
            concurrency = len(group_links)
            group_cycler = cycle(group_links)
            scenario_cycler = cycle(config.get("messages", []))
        else:
            concurrency = core
        
        proxy_cycler = cycle(proxies) if proxies else cycle([None])
        admin_group_index = 0

        # Main execution loop, iterating in batches
        for i in range(0, len(tasks_to_run), concurrency):
            if task.get("status") == "stopped": break

            batch_files = tasks_to_run[i : i + concurrency]
            async_tasks = []

            # Staggered start loop for tasks within the batch
            for session_path, filename in batch_files:
                if task.get("status") == "stopped": break
                
                worker_args = []
                if is_seeding_task:
                    worker_args = [next(group_cycler), next(scenario_cycler), config.get('send_silent', False)]
                elif args: # For other tasks like joinGroup
                    worker_args = list(args)

                # Create the async task
                coro = task_worker(
                    task_id, group_id, session_path, filename,
                    worker_coro_func, *worker_args, proxy_info=next(proxy_cycler)
                )
                async_tasks.append(asyncio.create_task(coro))

                # Wait for the per-session delay before starting the next one
                if delay_per_session > 0:
                    await asyncio.sleep(delay_per_session)

            # Wait for all tasks in the current batch to complete
            await asyncio.gather(*async_tasks)

            # Admin Logic after each batch
            if is_seeding_task and admin_enabled and task.get("status") != "stopped":
                admin_session_file = config.get("admin_session_file")
                admin_messages = config.get("admin_messages", [])
                admin_folder = os.path.join(app.config["UPLOAD_FOLDER"], ADMIN_SESSION_FOLDER)
                admin_session_path = os.path.join(admin_folder, admin_session_file) if admin_session_file else None

                if admin_session_path and os.path.exists(admin_session_path) and admin_messages:
                    admin_target_group = group_links[admin_group_index]
                    admin_response = random.choice(admin_messages)
                    
                    if admin_delay > 0:
                        for j in range(admin_delay, 0, -1):
                            if task.get("status") == "stopped": break
                            task["messages"].append(f"Admin trả lời sau... {j}s")
                            await asyncio.sleep(1)

                    if task.get("status") != "stopped":
                        await run_admin_task(admin_session_path, admin_target_group, admin_response)
                        admin_group_index = (admin_group_index + 1) % len(group_links)

            # Delay between batches
            if i + concurrency < len(tasks_to_run) and task.get("status") != "stopped" and delay_between_batches > 0:
                for j in range(delay_between_batches, 0, -1):
                    if task.get("status") == "stopped": break
                    task["messages"].append(f"Đang chờ đợt tiếp... {j}s")
                    await asyncio.sleep(1)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        task = TASKS.get(task_id)
        if task and task.get("status") != "stopped":
            task["status"] = "completed"
        loop.close()


# --- API quản lý proxy ---
@telegram_bp.route("/api/proxies", methods=["GET"])
def get_proxies():
    return jsonify(load_proxies())

@telegram_bp.route("/api/proxies", methods=["POST"])
def update_proxies():
    data = request.json
    is_enabled = data.get("enabled", False)
    proxy_list_str = data.get("proxies", "")
    proxy_list = [line.strip() for line in proxy_list_str.splitlines() if line.strip()]
    
    proxy_config = {
        "enabled": is_enabled,
        "proxies": proxy_list
    }
    save_proxies(proxy_config)
    status_text = "Bật" if is_enabled else "Tắt"
    return jsonify({"success": True, "message": f"Đã lưu {len(proxy_list)} proxy. Trạng thái: {status_text}."})


# --- Sửa logic sử dụng proxy trong run_task ---
@telegram_bp.route("/api/run-task", methods=["POST"])
def run_task():
    data = request.get_json() or {}
    # Extract all new and existing parameters
    group_id = data.get("groupId")
    task_name = data.get("task")
    config = data.get("config", {})
    filenames = data.get("filenames", [])
    core = int(data.get("core", 5))
    delay_per_session = int(data.get("delay_per_session", 10))
    delay_between_batches = int(data.get("delay_between_batches", 600))
    admin_enabled = bool(data.get("admin_enabled", False))
    admin_delay = int(data.get("admin_delay", 10))

    if not all([group_id, task_name, filenames]):
        return jsonify({"error": "Dữ liệu không hợp lệ"}), 400

    conn = get_db_connection()
    group = conn.execute("SELECT folder_path FROM session_groups WHERE id = ?", (group_id,)).fetchone()
    conn.close()
    if not group or not group["folder_path"]:
        return jsonify({"error": "Không tìm thấy nhóm hoặc đường dẫn thư mục của nhóm không hợp lệ."}), 404
    
    proxy_config = load_proxies()
    proxies_to_use = proxy_config['proxies'] if proxy_config.get('enabled', False) else []

    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "task_name": task_name, "group_id": group_id, "status": "running",
        "total": len(filenames), "processed": 0, "success": 0, "failed": 0,
        "results": [], "messages": []
    }
    
    worker_func, args = None, []
    if task_name == "check-live":
        worker_func = check_single_session_worker
    elif task_name == "joinGroup":
        worker_func = join_group_worker
        args = [config.get("links", [])]
    elif task_name == "seedingGroup":
        worker_func = seeding_group_worker
        args = [config] # Pass whole config
    
    if not worker_func:
        if task_id in TASKS: del TASKS[task_id]
        return jsonify({"error": "Tác vụ không được hỗ trợ"}), 400
    
    # Note the new arguments passed to the thread
    thread = Thread(
        target=run_task_in_thread,
        args=(
            task_id, group_id, group["folder_path"], filenames, core,
            delay_per_session, delay_between_batches, admin_enabled, admin_delay,
            worker_func, *args
        ),
        kwargs={"proxies": proxies_to_use}
    )
    thread.daemon = True
    thread.start()
    return jsonify({"task_id": task_id}), 202


@telegram_bp.route("/api/global-settings", methods=["POST"])
def save_telegram_global_settings():
    """Saves the global Telegram settings (Core, Delays, Admin) to the database."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400

        conn = get_db_connection()
        # Use a targeted UPDATE. We assume the row with id=1 exists.
        # This only touches the columns relevant to the main control bar.
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
                data.get("core", 5),
                data.get("delay_per_session", 10),
                data.get("delay_between_batches", 600),
                data.get("admin_enabled", False),
                data.get("admin_delay", 10)
            )
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Đã lưu cài đặt chung."})

    except sqlite3.Error as e:
        print(f"CRITICAL (SAVE-GLOBAL): Database error: {e}")
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        print(f"CRITICAL (SAVE-GLOBAL): General error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@telegram_bp.route("/api/task-status/<task_id>")
def task_status(task_id):
    task = TASKS.get(task_id)
    if not task:
        return jsonify({"status": "not_found"}), 404
    response = task.copy()
    response["results"], response["messages"] = task.get("results", []), task.get(
        "messages", []
    )
    task["results"], task["messages"] = [], []
    return jsonify(response)


@telegram_bp.route("/api/stop-task/<task_id>", methods=["POST"])
def stop_task_route(task_id):
    if task_id in TASKS:
        TASKS[task_id]["status"] = "stopped"
    return jsonify({"message": "Yêu cầu dừng đã được gửi."}), 200


@telegram_bp.route("/api/active-tasks")
def get_active_tasks():
    active_tasks = {
        task_id: {
            "task_name": task_data.get("task_name"),
            "group_id": task_data.get("group_id"),
            "status": task_data.get("status"),
            "total": task_data.get("total"),
            "processed": task_data.get("processed"),
            "success": task_data.get("success"),
            "failed": task_data.get("failed"),
        }
        for task_id, task_data in TASKS.items()
        if task_data.get("status") in ["running", "stopped"]
    }
    return jsonify(active_tasks)


@telegram_bp.route("/api/sessions/delete", methods=["POST"])
def delete_sessions():
    """Delete dead session files from a group's folder and filesystem."""
    import os.path
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400
    
    group_id = data.get("group_id")
    filenames = data.get("filenames", [])
    
    # Validate input
    if not group_id:
        return jsonify({"error": "group_id is required"}), 400
    
    if not filenames or not isinstance(filenames, list):
        return jsonify({"error": "filenames must be a non-empty list"}), 400
    
    # Check if any task is currently running (concurrency guard)
    active_tasks = [task for task in TASKS.values() if task.get("status") == "running"]
    if active_tasks:
        return jsonify({"error": "Task is running"}), 409
    
    # Get group info from database
    conn = get_db_connection()
    try:
        group = conn.execute("SELECT folder_path FROM session_groups WHERE id = ?", (group_id,)).fetchone()
        if not group:
            return jsonify({"error": "Group not found"}), 404
        
        group_folder = group["folder_path"]
        if not os.path.exists(group_folder):
            return jsonify({"error": "Group folder not found"}), 404
        
        # Ensure the group folder is within the expected upload folder (security check)
        upload_folder = app.config["UPLOAD_FOLDER"]
        if not group_folder.startswith(upload_folder):
            return jsonify({"error": "Invalid group folder path"}), 400
        
        deleted = []
        missing = []
        failed = []
        
        # Delete each session file
        for filename in filenames:
            # Sanitize filename (prevent path traversal)
            clean_filename = os.path.basename(filename)
            if clean_filename != filename or not clean_filename:
                failed.append(filename)
                continue
            
            file_path = os.path.join(group_folder, clean_filename)
            
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted.append(clean_filename)
                    
                    # Also remove from session_metadata if exists
                    conn.execute("DELETE FROM session_metadata WHERE group_id = ? AND filename = ?", 
                               (group_id, clean_filename))
                else:
                    missing.append(clean_filename)
            except OSError as e:
                failed.append(clean_filename)
                print(f"Failed to delete {file_path}: {e}")
        
        conn.commit()
        
        return jsonify({
            "deleted": deleted,
            "missing": missing, 
            "failed": failed
        })
        
    finally:
        conn.close()





# --- NOTES (REMINDER) MANAGER: BLUEPRINT & LOGIC ---
notes_bp = Blueprint("notes", __name__, url_prefix="/notes")

# Hàng đợi thông báo trong bộ nhớ
NOTIFICATIONS_QUEUE = []

def check_and_queue_reminders():
    """Checks for due reminders from SQLite and queues them for notification."""
    conn = get_db_connection()
    now_utc_iso = datetime.now(timezone.utc).isoformat()
    due_notes = conn.execute(
        "SELECT * FROM notes WHERE status = 'active' AND due_time IS NOT NULL AND due_time <= ?",
        (now_utc_iso,)
    ).fetchall()

    if not due_notes:
        conn.close()
        return

    sound_files = []
    if os.path.exists(SOUNDS_FOLDER):
        sound_files = [f for f in os.listdir(SOUNDS_FOLDER) if f.endswith((".wav", ".mp3", ".ogg"))]
    
    ids_to_update = []
    for note in due_notes:
        note_dict = dict(note)
        title_lower = (note_dict.get("title_html") or "").lower() # Use title_html
        sound_url = "/notes/sounds/notification.wav" # Default
        for sf in sound_files:
            if os.path.splitext(sf)[0].lower() in title_lower:
                sound_url = f"/notes/sounds/{sf}"
                break
        
        notification_payload = {
            "id": note_dict["id"],
            "title": BeautifulSoup(note_dict["title_html"], "html.parser").get_text(),
            "notes": note_dict.get("content_html", ""),
            "sound_url": sound_url
        }
        if not any(q['id'] == note_dict['id'] for q in NOTIFICATIONS_QUEUE):
            NOTIFICATIONS_QUEUE.append(notification_payload)
        
        ids_to_update.append(note_dict["id"])

    if ids_to_update:
        # Update status in bulk
        placeholders = ','.join('?' for _ in ids_to_update)
        conn.execute(f"UPDATE notes SET status = 'notified', due_time = NULL WHERE id IN ({placeholders})", ids_to_update)
        conn.commit()
    
    conn.close()

@notes_bp.route("/api/get")
def api_get_notes():
    check_and_queue_reminders()
    conn = get_db_connection()
    notes_rows = conn.execute("SELECT * FROM notes ORDER BY modified_at DESC").fetchall()
    conn.close()
    return jsonify([dict(row) for row in notes_rows])

@notes_bp.route("/api/add", methods=["POST"])
def api_add_note():
    data = request.json
    title_html, content_html = data.get("title_html", "").strip(), data.get("content_html", "").strip()
    if not title_html and not content_html:
        return jsonify({"error": "Tiêu đề hoặc nội dung không được để trống"}), 400
    
    now = datetime.now(timezone.utc).isoformat()
    new_note = {
        "id": str(uuid.uuid4()), "title_html": title_html, "content_html": content_html,
        "due_time": data.get("due_time") or None, "status": "active" if data.get("due_time") else "none", "modified_at": now
    }

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO notes (id, title_html, content_html, due_time, status, modified_at) VALUES (?, ?, ?, ?, ?, ?)",
        (new_note['id'], new_note['title_html'], new_note['content_html'], new_note['due_time'], new_note['status'], new_note['modified_at'])
    )
    conn.commit()
    conn.close()
    return jsonify(new_note), 201

@notes_bp.route("/api/update/<note_id>", methods=["POST"])
def api_update_note(note_id):
    data = request.json
    title_html, content_html = data.get("title_html", "").strip(), data.get("content_html", "").strip()
    if not title_html and not content_html:
        return jsonify({"error": "Tiêu đề hoặc nội dung không được để trống"}), 400
    
    due_time = data.get("due_time") or None
    status = "active" if due_time else "none" # Simplified status logic, you may need to adjust if "notified" state is handled differently
    modified_at = datetime.now(timezone.utc).isoformat()

    conn = get_db_connection()
    cursor = conn.execute(
        "UPDATE notes SET title_html = ?, content_html = ?, due_time = ?, status = ?, modified_at = ? WHERE id = ?",
        (title_html, content_html, due_time, status, modified_at, note_id)
    )
    conn.commit()
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Không tìm thấy ghi chú"}), 404
    
    updated_note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    return jsonify(dict(updated_note))

@notes_bp.route("/api/delete/<note_id>", methods=["POST"])
def api_delete_note(note_id):
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True}) if cursor.rowcount > 0 else (jsonify({"error": "Không tìm thấy ghi chú"}), 404)

@notes_bp.route("/api/mark/<note_id>", methods=["POST"])
def api_toggle_mark(note_id):
    conn = get_db_connection()
    note = conn.execute("SELECT is_marked FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        conn.close()
        return jsonify({"error": "Không tìm thấy ghi chú"}), 404
    
    new_marked_state = not note["is_marked"]
    conn.execute("UPDATE notes SET is_marked = ? WHERE id = ?", (new_marked_state, note_id))
    conn.commit()
    
    updated_note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    return jsonify(dict(updated_note))

@notes_bp.route("/api/acknowledge-notification/<note_id>", methods=["POST"])
def acknowledge_notification(note_id):
    conn = get_db_connection()
    conn.execute("UPDATE notes SET status = 'notified', due_time = NULL WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@notes_bp.route("/api/check-notifications")
def api_check_notifications():
    """Endpoint để frontend kiểm tra xem có thông báo mới không."""
    check_and_queue_reminders()
    if NOTIFICATIONS_QUEUE:
        # Lấy thông báo đầu tiên và xóa khỏi hàng đợi
        notification_to_send = NOTIFICATIONS_QUEUE.pop(0)
        return jsonify(notification_to_send)
    return jsonify(None) # Trả về null nếu không có gì

@notes_bp.route("/sounds/<path:filename>")
def serve_sound(filename):
    return send_from_directory(os.path.join(DATA_DIR, "sounds"), filename)


# --- Inline Editing: Update Telegram Session Info ---
async def update_profile_worker(session_path, field, value, proxy_info):
    """
    Worker to connect to Telegram and update profile (name or username).
    """
    client = None
    result = {"success": False, "error": "Unknown error."}
    try:
        proxy_dict = parse_proxy_string(proxy_info)
        client = TelegramClient(session_path, API_ID, API_HASH, proxy=proxy_dict)
        await client.connect()

        if not await client.is_user_authorized():
            raise Exception("Session is dead or logged out.")

        if field == 'full_name':
            first_name = value.split(' ', 1)[0] if ' ' in value else value
            last_name = value.split(' ', 1)[1] if ' ' in value else ""
            await client(UpdateProfileRequest(first_name=first_name, last_name=last_name))
            result["message"] = "Full name updated successfully."

        elif field == 'username':
            await client(UpdateUsernameRequest(value))
            result["message"] = "Username updated successfully."
        
        me = await client.get_me()
        result.update({
            "success": True,
            "updated_value": me.username if field == 'username' else f"{me.first_name or ''} {me.last_name or ''}".strip(),
            "updated_full_name": f"{me.first_name or ''} {me.last_name or ''}".strip(),
            "updated_username": me.username or "",
            "is_live": True
        })

    except UsernameInvalidError:
        result["error"] = "Invalid username format."
    except UsernameOccupiedError:
        result["error"] = "Username is already taken."
    except FloodWaitError as e:
        result["error"] = f"Flood wait: please wait {e.seconds}s."
    except Exception as e:
        result["error"] = str(e)
    finally:
        if client and client.is_connected():
            await client.disconnect()
    return result

@telegram_bp.route("/api/update-session-info", methods=["POST"])
def update_session_info():
    data = request.get_json()
    group_id, filename, field, value = data.get("group_id"), data.get("filename"), data.get("field"), data.get("value")

    if not all([group_id, filename, field, value]):
        return jsonify({"error": "Missing required data"}), 400
    if field not in ['full_name', 'username']:
        return jsonify({"error": "Invalid field to update"}), 400

    conn = get_db_connection()
    group = conn.execute("SELECT folder_path FROM session_groups WHERE id = ?", (group_id,)).fetchone()
    if not group:
        conn.close()
        return jsonify({"error": "Group not found"}), 404
    
    session_path = os.path.join(group["folder_path"], filename)
    if not os.path.exists(session_path):
        conn.close()
        return jsonify({"error": "Session file not found"}), 404
    
    proxy_config = load_proxies()
    proxy_info = proxy_config['proxies'][0] if proxy_config.get('enabled') and proxy_config.get('proxies') else None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    update_result = loop.run_until_complete(update_profile_worker(session_path, field, value, proxy_info))
    loop.close()

    if not update_result["success"]:
        conn.close()
        return jsonify({"error": update_result["error"]}), 500

    conn.execute(
        "UPDATE session_metadata SET full_name = ?, username = ?, is_live = ?, status_text = ?, last_checked = CURRENT_TIMESTAMP WHERE group_id = ? AND filename = ?",
        (update_result["updated_full_name"], update_result["updated_username"], True, "Live", group_id, filename)
    )
    conn.commit()
    conn.close()

    return jsonify(update_result)


def manage_startup_shortcut(enable):
    """
    Creates or deletes the application's shortcut in the Windows Startup folder using winshell.
    """
    try:
        # Use winshell to reliably get the path to the user's Startup folder
        startup_folder = winshell.startup()
        
        # Define the path for our shortcut file
        shortcut_path = os.path.join(startup_folder, 'STool Dashboard.lnk')
        
        if enable:
            # --- Create Shortcut Logic ---
            if os.path.exists(shortcut_path):
                print("Startup shortcut already exists.")
                return True

            target_script = os.path.abspath(sys.argv[0])
            working_dir = os.path.dirname(target_script)
            
            print(f"Creating startup shortcut for: {target_script}")
            print(f"Startup folder: {startup_folder}")
            print(f"Shortcut path: {shortcut_path}")
            
            with winshell.shortcut(shortcut_path) as shortcut:
                # Use pythonw.exe instead of python.exe to avoid showing terminal
                python_dir = os.path.dirname(sys.executable)
                pythonw_path = os.path.join(python_dir, 'pythonw.exe')
                if os.path.exists(pythonw_path):
                    shortcut.path = pythonw_path
                else:
                    shortcut.path = sys.executable  # Fallback to regular python.exe
                shortcut.arguments = f'"{target_script}"' # The .pyw script to run
                shortcut.working_directory = working_dir
                shortcut.description = "Start STool Dashboard"
            
            print("Startup shortcut created successfully.")
            return True

        else:
            # --- Delete Shortcut Logic ---
            if os.path.exists(shortcut_path):
                print("Deleting startup shortcut.")
                os.remove(shortcut_path)
                print("Startup shortcut deleted.")
                return True
            else:
                print("Startup shortcut does not exist, nothing to delete.")
                return True

    except Exception as e:
        # Log any errors that occur during shortcut management
        print(f"ERROR managing startup shortcut: {e}")
        return False


# --- DASHBOARD SETTINGS MANAGER: BLUEPRINT & LOGIC ---
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

def load_dashboard_settings():
    if not os.path.exists(DASHBOARD_SETTINGS_FILE):
        with open(DASHBOARD_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"auto_start": False, "auto_open_dashboard": True}, f)
        return {"auto_start": False, "auto_open_dashboard": True}
    with open(DASHBOARD_SETTINGS_FILE, "r", encoding="utf-8") as f:
        try:
            settings = json.load(f)
            # Ensure auto_open_dashboard exists with default value
            if "auto_open_dashboard" not in settings:
                settings["auto_open_dashboard"] = True
            return settings
        except json.JSONDecodeError:
            return {"auto_start": False, "auto_open_dashboard": True}

def save_dashboard_settings(settings):
    with open(DASHBOARD_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)

def load_open_apps_settings():
    if not os.path.exists(OPEN_APPS_SETTINGS_FILE):
        with open(OPEN_APPS_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"enabled": False, "urls": []}, f)
        return {"enabled": False, "urls": []}
    with open(OPEN_APPS_SETTINGS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"enabled": False, "urls": []}

def save_open_apps_settings(settings):
    with open(OPEN_APPS_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)

@dashboard_bp.route("/api/settings", methods=["GET"])
def get_dashboard_settings():
    settings = load_dashboard_settings()
    return jsonify(settings)

@dashboard_bp.route("/api/settings", methods=["POST"])
def set_dashboard_settings():
    data = request.json
    settings = load_dashboard_settings()
    
    # Get the new auto_start value from the request
    new_auto_start_state = data.get("auto_start", False)
    settings["auto_start"] = new_auto_start_state
    
    # Get the new auto_open_dashboard value from the request
    new_auto_open_dashboard_state = data.get("auto_open_dashboard", True)
    settings["auto_open_dashboard"] = new_auto_open_dashboard_state
    
    # Save the setting to the JSON file first
    save_dashboard_settings(settings)
    
    # THEN, call the function to create or delete the shortcut based on the new state
    shortcut_result = manage_startup_shortcut(new_auto_start_state)
    
    if shortcut_result:
        message = "Đã bật khởi động cùng Windows." if new_auto_start_state else "Đã tắt khởi động cùng Windows."
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"success": False, "error": "Không thể tạo/xóa shortcut khởi động. Vui lòng chạy với quyền Administrator."})

@dashboard_bp.route("/api/open-apps", methods=["GET"])
def get_open_apps_settings():
    settings = load_open_apps_settings()
    return jsonify(settings)

@dashboard_bp.route("/api/open-apps", methods=["POST"])
def set_open_apps_settings():
    data = request.json
    settings = load_open_apps_settings()
    
    # Update enabled state if provided
    if "enabled" in data:
        settings["enabled"] = data.get("enabled", False)
    
    # Update URLs if provided
    if "urls" in data:
        new_urls = data.get("urls", [])
        # Validate URLs
        valid_urls = []
        for url in new_urls:
            url = url.strip()
            if url and (url.startswith("http://") or url.startswith("https://")):
                valid_urls.append(url)
        settings["urls"] = valid_urls
    
    # Save the settings
    save_open_apps_settings(settings)
    
    if "urls" in data:
        return jsonify({"success": True, "message": f"Đã lưu {len(settings['urls'])} URL apps."})
    else:
        return jsonify({"success": True, "message": "Đã cập nhật cài đặt apps."})


# --- UTILITIES MANAGER: BLUEPRINT & LOGIC ---
utilities_bp = Blueprint("utilities", __name__, url_prefix="/utilities")

@utilities_bp.route("/shutdown", methods=["POST"])
def schedule_shutdown():
    """Schedules a system shutdown on Windows."""
    data = request.json
    try:
        seconds = int(data.get("seconds", 0))
        if seconds <= 0:
            return jsonify({"error": "Số giây phải lớn hơn 0"}), 400

        # Command to cancel any existing shutdown timer first, then set a new one.
        os.system("shutdown /a") 
        command = f"shutdown /s /t {seconds}"
        os.system(command)
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        message = f"Đã hẹn giờ tắt máy sau {hours} giờ {minutes} phút."
        return jsonify({"success": True, "message": message})
    except (ValueError, TypeError):
        return jsonify({"error": "Dữ liệu không hợp lệ"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@utilities_bp.route("/cancel-shutdown", methods=["POST"])
def cancel_shutdown():
    """Cancels any pending system shutdown on Windows."""
    try:
        # The /a switch aborts a system shutdown.
        os.system("shutdown /a")
        return jsonify({"success": True, "message": "Đã hủy lệnh hẹn giờ tắt máy."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- AUTOMATIC SEEDING MANAGER: BLUEPRINT & LOGIC (SIMPLIFIED) ---

automatic_bp = Blueprint("automatic", __name__, url_prefix="/automatic")

# This is the background thread that checks the schedule.
def scheduler_thread_worker():
    """Background worker that checks if the current time is within the scheduled window and triggers the task once per day."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        try:
            conn = get_db_connection()
            settings = conn.execute("SELECT * FROM auto_seeding_settings WHERE id = 1").fetchone()
            
            if not settings or not settings['is_enabled'] or not settings['run_time'] or not settings['end_run_time']:
                conn.close()
                time.sleep(30)
                continue

            now = datetime.now()
            now_time = now.time()
            
            start_time = datetime.strptime(settings['run_time'], "%H:%M").time()
            end_time = datetime.strptime(settings['end_run_time'], "%H:%M").time()

            is_in_window = False
            if start_time <= end_time: # Normal case (e.g., 09:00 to 17:00)
                if start_time <= now_time < end_time:
                    is_in_window = True
            else: # Overnight case (e.g., 22:00 to 02:00)
                if now_time >= start_time or now_time < end_time:
                    is_in_window = True

            if is_in_window:
                last_run_str = settings['last_run_timestamp']
                should_run = False
                if not last_run_str:
                    should_run = True # Never run before
                else:
                    last_run_dt = datetime.fromisoformat(last_run_str)
                    # ROBUST FIX: Check if the last run was more than 22 hours ago.
                    # This reliably prevents re-triggering within the same 24-hour cycle for any schedule type.
                    if now - last_run_dt > timedelta(hours=22):
                        should_run = True
                
                if should_run:
                    print(f"[{datetime.now()}] Auto Seeding: Conditions met. Triggering task.")
                    loop.run_until_complete(trigger_auto_seeding_task())
                    
                    current_run_timestamp = now.isoformat()
                    conn.execute("UPDATE auto_seeding_settings SET last_run_timestamp = ? WHERE id = 1", (current_run_timestamp,))
                    conn.commit()

                    if not settings['run_daily']:
                        conn.execute("UPDATE auto_seeding_settings SET is_enabled = 0 WHERE id = 1")
                        conn.commit()
                        print("Auto Seeding: Run once completed, is_enabled set to false.")
            
            conn.close()
        except Exception as e:
            print(f"Error in Auto Seeding scheduler thread: {e}")
        
        time.sleep(30)

async def trigger_auto_seeding_task():
    """Fetches ALL configs from DB, prepares data, and starts the seeding task with the correct parameters."""
    print(f"[{datetime.now()}] Triggering Auto Seeding task...")
    
    conn = get_db_connection()
    # Fetch ALL settings for auto-seeding
    settings = conn.execute("SELECT * FROM auto_seeding_settings WHERE id = 1").fetchone()
    if not settings or not settings['target_session_group_id']:
        print("Auto Seeding Error: Target session group is not configured.")
        conn.close()
        return

    target_group_id = settings['target_session_group_id']
    group_info = conn.execute("SELECT folder_path FROM session_groups WHERE id = ?", (target_group_id,)).fetchone()
    if not group_info:
        print(f"Auto Seeding Error: Session group with ID {target_group_id} not found.")
        conn.close()
        return
    group_folder_path = group_info['folder_path']
    
    # Get the seedingGroup task config (messages, links, etc.)
    seeding_config_row = conn.execute("SELECT config_json FROM task_configs WHERE task_name = 'seedingGroup'").fetchone()
    if not seeding_config_row:
        print("Auto Seeding Error: 'seedingGroup' configuration card not found.")
        conn.close()
        return

    config = json.loads(seeding_config_row['config_json'])
    messages = config.get("messages", [])
    if not messages:
        print("Auto Seeding Error: No messages found in seeding config.")
        conn.close()
        return
        
    random.shuffle(messages)
    config["messages"] = messages
    
    session_files = [f for f in os.listdir(group_folder_path) if f.endswith(".session")]
    if not session_files:
        print(f"Auto Seeding Error: No session files found in the target group folder.")
        conn.close()
        return
    random.shuffle(session_files)
    conn.close()

    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "task_name": "seedingGroup", "group_id": target_group_id, "status": "running",
        "total": len(session_files), "processed": 0, "success": 0, "failed": 0,
        "results": [], "messages": []
    }
    
    # Use the parameters fetched from the settings table instead of hardcoded values
    thread = Thread(
        target=run_task_in_thread,
        args=(
            task_id, target_group_id, group_folder_path, session_files,
            settings['core'], settings['delay_per_session'], settings['delay_between_batches'],
            settings['admin_enabled'], settings['admin_delay'],
            seeding_group_worker, config
        ),
        kwargs={"proxies": []} # Auto seeding will not use proxy for now
    )
    thread.daemon = True
    thread.start()
    print(f"Auto Seeding task {task_id} started for group {target_group_id} with {len(session_files)} sessions.")

@automatic_bp.route("/api/seeding/settings", methods=["GET"])
def get_auto_seeding_settings():
    conn = get_db_connection()
    settings = conn.execute("SELECT * FROM auto_seeding_settings WHERE id = 1").fetchone()
    conn.close()
    
    # --- START: NEW DEBUG LOGIC ---
    settings_dict = dict(settings) if settings else {}
    print(f"DEBUG: Data fetched by GET request (on tab load): {settings_dict}")
    # --- END: NEW DEBUG LOGIC ---
    
    return jsonify(settings_dict)

@automatic_bp.route("/api/seeding/settings", methods=["POST"])
def save_auto_seeding_settings():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400

        conn = get_db_connection()
        conn.execute(
            """INSERT INTO auto_seeding_settings (id, is_enabled, run_time, end_run_time, run_daily, target_session_group_id, task_name, core, delay_per_session, delay_between_batches, admin_enabled, admin_delay)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 is_enabled = excluded.is_enabled,
                 run_time = excluded.run_time,
                 end_run_time = excluded.end_run_time,
                 run_daily = excluded.run_daily,
                 target_session_group_id = excluded.target_session_group_id,
                 task_name = excluded.task_name,
                 core = excluded.core,
                 delay_per_session = excluded.delay_per_session,
                 delay_between_batches = excluded.delay_between_batches,
                 admin_enabled = excluded.admin_enabled,
                 admin_delay = excluded.admin_delay;
            """,
            (
                data.get("is_enabled", False),
                data.get("run_time"),
                data.get("end_run_time"),
                data.get("run_daily", False),
                data.get("target_session_group_id"),
                data.get("task_name", "seedingGroup"),
                data.get("core", 5),
                data.get("delay_per_session", 10),
                data.get("delay_between_batches", 600),
                data.get("admin_enabled", False),
                data.get("admin_delay", 10)
            )
        )
        conn.commit()
        conn.close()
        return jsonify(data)

    except sqlite3.Error as e:
        print(f"CRITICAL (SAVE): Database error in save_auto_seeding_settings: {e}")
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        print(f"CRITICAL (SAVE): General error in save_auto_seeding_settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# --- KCAL FOODS MANAGER: BLUEPRINT & LOGIC ---
kcal_bp = Blueprint("kcal", __name__, url_prefix="/api")

@kcal_bp.route("/settings", methods=["GET"])
def get_body_settings():
    conn = get_db_connection()
    settings = conn.execute("SELECT * FROM body_settings WHERE id = 1").fetchone()
    conn.close()
    if settings:
        return jsonify(dict(settings))
    return jsonify({
        "initial_weight": None,
        "current_weight": None,
        "height": None,
        "age": None,
        "gender": "male",
        "activity_level": "moderate",
        "daily_calories_target": None
    })

@kcal_bp.route("/settings", methods=["POST"])
def save_body_settings():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Dữ liệu không hợp lệ"}), 400
        
        required_fields = ["initial_weight", "current_weight", "height", "age", "gender", "activity_level"]
        if not all(field in data and data[field] is not None for field in required_fields):
            missing_fields = [field for field in required_fields if field not in data or data[field] is None]
            return jsonify({"error": f"Thiếu thông tin: {', '.join(missing_fields)}"}), 400

        # Validate numeric values
        try:
            initial_weight = float(data["initial_weight"])
            weight = float(data["current_weight"])
            height = float(data["height"])
            age = int(data["age"])
            gender = data["gender"]
            activity_level = data["activity_level"]
            
            if weight <= 0 or height <= 0 or age <= 0 or initial_weight <= 0:
                return jsonify({"error": "Các thông số phải lớn hơn 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Lỗi định dạng số liệu"}), 400

        # Calculate BMR and daily calorie target
        if gender == "male":
            bmr = 66.47 + (13.75 * weight) + (5.003 * height) - (6.755 * age)
        else:
            bmr = 655.1 + (9.563 * weight) + (1.850 * height) - (4.676 * age)

        activity_multipliers = {
            "sedentary": 1.2, "light": 1.375, "moderate": 1.55, 
            "active": 1.725, "very_active": 1.9
        }
        daily_calories = bmr * activity_multipliers.get(activity_level, 1.55)

        conn = get_db_connection()
        try:
            # Check if a record for id=1 already exists
            existing_record = conn.execute("SELECT id FROM body_settings WHERE id = 1").fetchone()

            if existing_record:
                # If it exists, UPDATE the record. Do NOT change the start_date.
                conn.execute("""
                    UPDATE body_settings SET
                        initial_weight = ?, current_weight = ?, height = ?, age = ?, gender = ?,
                        activity_level = ?, daily_calories_target = ?, last_reset = datetime('now', 'localtime')
                    WHERE id = 1
                """, (initial_weight, weight, height, age, gender, activity_level, daily_calories))
            else:
                # If it does not exist, INSERT a new record, including the start_date.
                conn.execute("""
                    INSERT INTO body_settings (id, initial_weight, current_weight, height, age, gender, activity_level, daily_calories_target, last_reset, start_date)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                """, (initial_weight, weight, height, age, gender, activity_level, daily_calories))

            conn.commit()
            
            # Fetch the complete, updated record to send back to the client
            settings = conn.execute("SELECT * FROM body_settings WHERE id = 1").fetchone()
            if settings:
                return jsonify(dict(settings))
            else:
                # This case should ideally not be reached after a successful commit
                return jsonify({"error": "Không thể truy xuất dữ liệu sau khi lưu"}), 500

        except sqlite3.Error as e:
            print(f"DEBUG: Database error in save_body_settings: {e}")
            return jsonify({"error": "Lỗi cập nhật dữ liệu database"}), 500
        finally:
            conn.close()

    except Exception as e:
        print(f"DEBUG: General error in save_body_settings: {e}")
        return jsonify({"error": "Lỗi xử lý chung"}), 500

@kcal_bp.route("/foods", methods=["GET"])
def get_kcal_foods():
    conn = get_db_connection()
    foods = conn.execute("SELECT * FROM kcal_foods ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(row) for row in foods])

@kcal_bp.route("/foods", methods=["POST"])
def add_kcal_food():
    data = request.json
    required_fields = ["name", "category", "calories", "protein", "fat", "carbs"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Dữ liệu không hợp lệ"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO kcal_foods (name, category, calories, protein, fat, carbs) VALUES (?, ?, ?, ?, ?, ?)",
        (data["name"], data["category"], data["calories"], data["protein"], data["fat"], data["carbs"])
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    new_food = data.copy()
    new_food['id'] = new_id
    return jsonify(new_food), 201

@kcal_bp.route("/foods/<int:food_id>", methods=["DELETE"])
def delete_kcal_food(food_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM kcal_foods WHERE id = ?", (food_id,))
    conn.commit()
    conn.close()
    
    if cursor.rowcount > 0:
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Không tìm thấy thực phẩm"}), 404


# --- MAIN APP ROUTES & SETUP ---
app.register_blueprint(kcal_bp)
app.register_blueprint(facebook_bp)
app.register_blueprint(telegram_bp)
app.register_blueprint(notes_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(utilities_bp)
app.register_blueprint(automatic_bp)

# Global scheduler thread variable
scheduler_thread = None

# Start scheduler thread for automatic seeding
def start_scheduler_thread():
    """Start the scheduler thread for automatic seeding."""
    global scheduler_thread
    if scheduler_thread is None or not scheduler_thread.is_alive():
        scheduler_thread = Thread(target=scheduler_thread_worker, daemon=True)
        scheduler_thread.start()
        print("Auto seeding scheduler thread started")

# Disable caching để luôn reload static files
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/")
def main_dashboard():
    facebook_accounts = load_fb_accounts()

    return render_template(
        "index.html",
        facebook_accounts=sorted(
            facebook_accounts, key=lambda x: x.get("nickname", "").lower()
        ),
        request=request,
    )

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files với no-cache headers"""
    response = send_from_directory('static', filename)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def open_browser():
    """Mở trang dashboard trong trình duyệt web mặc định."""
    try:
        # Kiểm tra setting auto_open_dashboard
        settings = load_dashboard_settings()
        if settings.get("auto_open_dashboard", True):
            webbrowser.open_new("http://127.0.0.1:5000/")
            # Mở các apps startup sau khi mở dashboard
            open_startup_apps()
        else:
            print("Auto open dashboard is disabled. Dashboard will not open automatically.")
    except Exception as e:
        print(f"Could not open browser: {e}")

def open_startup_apps():
    """Mở các URL apps khi khởi động nếu được bật."""
    try:
        settings = load_open_apps_settings()
        if settings.get("enabled", False) and settings.get("urls"):
            print(f"Opening {len(settings['urls'])} startup apps...")
            for url in settings["urls"]:
                try:
                    webbrowser.open_new(url)
                    time.sleep(1)  # Delay between opening apps
                except Exception as e:
                    print(f"Could not open URL {url}: {e}")
    except Exception as e:
        print(f"Error opening startup apps: {e}")


def run_flask_app():
    """Hàm chạy Flask app trong một luồng riêng."""
    # Không mở trình duyệt tự động khi ở chế độ debug
    if not app.debug:
        Thread(target=lambda: (time.sleep(2), open_browser())).start()
    port = int(os.environ.get("PORT", 5000))
    print(f"STool Dashboard is running on http://127.0.0.1:{port}")
    print("Debug mode: ON - Auto reload when code changes")
    # Bật debug nhưng tắt reloader vì chạy trong thread
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)


def exit_action(icon, item):
    """Hàm xử lý khi nhấn nút thoát trên tray icon."""
    print("Exiting application...")
    icon.stop()
    # os._exit(0) là một cách để buộc thoát toàn bộ chương trình,
    # hữu ích khi các luồng con (như Flask) không tự dừng lại.
    os._exit(0)


def setup_and_run_tray():
    """Thiết lập và chạy icon trên khay hệ thống."""
    # Chạy Flask trong một luồng nền, daemon=True để nó tự tắt khi chương trình chính thoát
    flask_thread = Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    # Tải ảnh icon từ file bạn đã cung cấp
    try:
        image = Image.open(os.path.join(app.root_path, "static", "icontray.png"))
    except FileNotFoundError:
        print("Không tìm thấy file 'image_fe55d8.png'. Tạo icon mặc định.")
        width, height = 64, 64
        color1, color2 = (13, 110, 253), (255, 255, 255)
        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
        dc.rectangle((0, height // 2, width // 2, height), fill=color2)

    # Tạo menu cho icon (default=True nghĩa là nháy đúp sẽ thực hiện hành động này)
    menu = (pystray.MenuItem('Mở Dashboard', open_browser, default=True), pystray.MenuItem('Thoát', exit_action))
    
    # Tạo đối tượng icon
    icon = pystray.Icon("stool_dashboard", image, "STool Dashboard", menu)
    
    # Chạy icon trên luồng chính (lệnh này sẽ blocking, giữ chương trình sống)
    icon.run()



def migrate_legacy_telegram_db():
    """
    Performs a one-time migration of data from the old telegram_dashboard.db
    to the new consolidated Data.db.
    """
    legacy_db_path = os.path.join(DATA_DIR, "telegram_dashboard.db")
    main_db_path = DATABASE_PATH

    # If the old database doesn't exist, do nothing.
    if not os.path.exists(legacy_db_path):
        return

    print("--- Found legacy telegram_dashboard.db. Starting migration... ---")

    try:
        legacy_conn = sqlite3.connect(legacy_db_path)
        legacy_conn.row_factory = sqlite3.Row
        legacy_cursor = legacy_conn.cursor()

        main_conn = get_db_connection() # Uses the existing function to connect to Data.db
        main_cursor = main_conn.cursor()

        # --- Migrate Groups (Table: session_groups) ---
        legacy_groups = legacy_cursor.execute("SELECT id, name, folder_path FROM groups").fetchall()
        if legacy_groups:
            main_cursor.executemany(
                "INSERT OR IGNORE INTO session_groups (id, name, folder_path) VALUES (?, ?, ?)",
                [(g['id'], g['name'], g['folder_path']) for g in legacy_groups]
            )
            print(f"Migrated {len(legacy_groups)} groups.")

        # --- Migrate Sessions (Table: session_metadata) ---
        legacy_sessions = legacy_cursor.execute("SELECT group_id, filename, phone, full_name, username, is_live, status_text FROM sessions").fetchall()
        if legacy_sessions:
            # Prepare data for insertion into the new table structure
            sessions_to_insert = [
                (
                    s['group_id'], s['filename'], s.get('full_name'), s.get('username'),
                    s.get('is_live'), s.get('status_text'), datetime.now(timezone.utc).isoformat()
                ) for s in legacy_sessions
            ]
            main_cursor.executemany(
                "INSERT OR IGNORE INTO session_metadata (group_id, filename, full_name, username, is_live, status_text, last_checked) VALUES (?, ?, ?, ?, ?, ?, ?)",
                sessions_to_insert
            )
            print(f"Migrated {len(legacy_sessions)} session metadata records.")

        main_conn.commit()
        print("--- Migration successful. ---")

    except sqlite3.Error as e:
        # It's possible the old DB has a different schema. We'll catch the error.
        # This can happen if table 'groups' or 'sessions' does not exist.
        print(f"!!! MIGRATION SKIPPED: An error occurred while accessing telegram_dashboard.db: {e}")
        print("!!! This usually means the file is from an incompatible version or is empty/corrupt.")

    finally:
        if 'legacy_conn' in locals():
            legacy_conn.close()
        if 'main_conn' in locals():
            main_conn.close()

    # Rename the old file to prevent running this again. This is safer than deleting.
    try:
        os.rename(legacy_db_path, legacy_db_path + ".migrated")
        print(f"--- Renamed old database to {os.path.basename(legacy_db_path)}.migrated ---")
    except OSError as e:
        print(f"Could not rename legacy database file: {e}")


def migrate_auto_seeding_schema():
    """
    Performs a one-time, robust migration of the auto_seeding_settings table
    to clean up old/deprecated columns and ensure schema consistency.
    """
    migration_flag = os.path.join(DATA_DIR, 'auto_seeding_schema_v2.flag')
    if os.path.exists(migration_flag):
        return # Migration has already been performed.

    print("--- Checking for and running auto_seeding_settings schema migration... ---")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(auto_seeding_settings)")
        existing_columns = [row['name'] for row in cursor.fetchall()]

        # Define the clean, correct set of columns we want to keep.
        final_columns = ['id', 'is_enabled', 'run_time', 'end_run_time', 'run_daily', 'target_session_group_id', 'last_run_timestamp', 'task_name', 'core', 'delay_per_session', 'delay_between_batches', 'admin_enabled', 'admin_delay']
        
        # Determine which of the final columns actually exist in the old table to be copied.
        columns_to_copy = [col for col in final_columns if col in existing_columns]
        columns_to_copy_str = ", ".join(columns_to_copy)

        print(f"Schema Migration: The following columns will be preserved: {columns_to_copy_str}")

        # 1. Create a new table with the perfect, clean schema.
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

        # 2. Copy data from the old table to the new one, only selecting the valid columns that exist.
        if columns_to_copy:
            cursor.execute(f"""
                INSERT INTO auto_seeding_settings_new ({columns_to_copy_str})
                SELECT {columns_to_copy_str} FROM auto_seeding_settings
            """)
            print("Schema Migration: Data copied to new clean table.")

        # 3. Drop the old messy table.
        cursor.execute("DROP TABLE auto_seeding_settings")
        print("Schema Migration: Old table dropped.")

        # 4. Rename the new table to the original name.
        cursor.execute("ALTER TABLE auto_seeding_settings_new RENAME TO auto_seeding_settings")
        print("Schema Migration: New table renamed.")
        
        conn.commit()
        
        # 5. Create the flag file to prevent this migration from running again.
        with open(migration_flag, 'w') as f:
            f.write(datetime.now().isoformat())
        print("--- Schema migration for auto_seeding_settings complete. ---")

    except sqlite3.Error as e:
        print(f"!!! MIGRATION SKIPPED for auto_seeding_settings due to an error: {e}")
        # Rollback any partial changes if an error occurs.
        conn.rollback()
    finally:
        conn.close()


# --- MXH API ENDPOINTS ---
@app.route('/mxh/api/groups', methods=['GET', 'POST'])
def mxh_groups():
    conn = get_db_connection()
    try:
        if request.method == 'GET':
            groups = conn.execute('SELECT * FROM mxh_groups ORDER BY created_at DESC').fetchall()
            return jsonify([dict(group) for group in groups])
        
        elif request.method == 'POST':
            data = request.get_json()
            name = data.get('name')
            color = data.get('color')
            
            if not name or not color:
                return jsonify({'error': 'Name and color are required'}), 400
            
            # Auto-assign platform icons based on group name
            platform_icons = {
                'wechat': 'bi-wechat',
                'facebook': 'bi-facebook',
                'instagram': 'bi-instagram',
                'tiktok': 'bi-tiktok',
                'youtube': 'bi-youtube',
                'twitter': 'bi-twitter',
                'linkedin': 'bi-linkedin',
                'zalo': 'bi-chat-dots',
                'telegram': 'bi-telegram',
                'whatsapp': 'bi-whatsapp'
            }
            icon = platform_icons.get(name.lower(), 'bi-share-fill')
            
            try:
                cursor = conn.execute(
                    'INSERT INTO mxh_groups (name, color, icon, created_at) VALUES (?, ?, ?, ?)',
                    (name, color, icon, datetime.now().isoformat())
                )
                conn.commit()
                group_id = cursor.lastrowid
                return jsonify({
                    'id': group_id,
                    'name': name,
                    'color': color,
                    'icon': icon,
                    'message': 'Group created successfully'
                }), 201
            except sqlite3.IntegrityError:
                return jsonify({'error': f'Nhóm "{name}" đã tồn tại. Vui lòng chọn tên khác.'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/mxh/api/accounts', methods=['GET', 'POST'])
def mxh_accounts():
    conn = get_db_connection()
    try:
        if request.method == 'GET':
            try:
                accounts = conn.execute('''
                    SELECT a.*, g.name as group_name, g.color as group_color, g.icon as group_icon 
                    FROM mxh_accounts a 
                    LEFT JOIN mxh_groups g ON a.group_id = g.id 
                ''').fetchall()
                return jsonify([dict(account) for account in accounts])
            except sqlite3.OperationalError as e:
                if "no such column" in str(e):
                    # Fallback for old database without WeChat columns
                    accounts = conn.execute('''
                        SELECT a.*, g.name as group_name, g.color as group_color, g.icon as group_icon 
                        FROM mxh_accounts a 
                        LEFT JOIN mxh_groups g ON a.group_id = g.id 
                    ''').fetchall()
                    # Add default WeChat values
                    result = []
                    for account in accounts:
                        account_dict = dict(account)
                        account_dict.update({
                            'wechat_created_day': 1,
                            'wechat_created_month': 1,
                            'wechat_created_year': 2024,
                            'wechat_scan_create': 0,
                            'wechat_scan_rescue': 0,
                            'wechat_status': 'available'
                        })
                        result.append(account_dict)
                    return jsonify(result)
                else:
                    raise e
        
        elif request.method == 'POST':
            data = request.get_json()
            card_name = data.get('card_name')
            group_id = data.get('group_id')
            platform = data.get('platform')
            username = data.get('username')
            url = data.get('url', '')
            
            # WeChat specific fields
            now = datetime.now()
            wechat_created_day = data.get('wechat_created_day', now.day)
            wechat_created_month = data.get('wechat_created_month', now.month)
            wechat_created_year = data.get('wechat_created_year', now.year)
            wechat_scan_create = data.get('wechat_scan_create', 0)
            wechat_scan_rescue = data.get('wechat_scan_rescue', 0)
            wechat_status = data.get('wechat_status', 'available')
            
            if not all([card_name, group_id, platform, username]):
                return jsonify({'error': 'All fields are required'}), 400
            
            try:
                conn.execute(
                    '''INSERT INTO mxh_accounts 
                       (card_name, group_id, platform, username, url, created_at, 
                        wechat_created_day, wechat_created_month, wechat_created_year,
                        wechat_scan_create, wechat_scan_rescue, wechat_status) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (card_name, group_id, platform, username, url, datetime.now().isoformat(),
                     wechat_created_day, wechat_created_month, wechat_created_year,
                     wechat_scan_create, wechat_scan_rescue, wechat_status)
                )
            except sqlite3.OperationalError as e:
                if "no such column" in str(e):
                    # Fallback for old database without WeChat columns
                    conn.execute(
                        '''INSERT INTO mxh_accounts 
                           (card_name, group_id, platform, username, url, created_at) 
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        (card_name, group_id, platform, username, url, datetime.now().isoformat())
                    )
                else:
                    raise e
            conn.commit()
            return jsonify({'message': 'Account created successfully'}), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/mxh/api/accounts/<int:account_id>/mute', methods=['POST'])
def mute_mxh_account(account_id):
    conn = get_db_connection()
    try:
        data = request.get_json()
        is_secondary = data.get('is_secondary', False)
        
        # Calculate mute until date (30 days from now)
        from datetime import datetime, timedelta
        mute_until = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        
        if is_secondary:
            conn.execute(
                'UPDATE mxh_accounts SET secondary_muted_until = ? WHERE id = ?',
                (mute_until, account_id)
            )
        else:
            conn.execute(
                'UPDATE mxh_accounts SET muted_until = ? WHERE id = ?',
                (mute_until, account_id)
            )
        conn.commit()
        
        return jsonify({'message': 'Account muted successfully for 30 days', 'muted_until': mute_until})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/mxh/api/accounts/<int:account_id>/unmute', methods=['POST'])
def unmute_mxh_account(account_id):
    conn = get_db_connection()
    try:
        data = request.get_json()
        is_secondary = data.get('is_secondary', False)
        
        if is_secondary:
            conn.execute(
                'UPDATE mxh_accounts SET secondary_muted_until = NULL WHERE id = ?',
                (account_id,)
            )
        else:
            conn.execute(
                'UPDATE mxh_accounts SET muted_until = NULL WHERE id = ?',
                (account_id,)
            )
        conn.commit()
        
        return jsonify({'message': 'Account unmuted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/mxh/api/accounts/<int:account_id>', methods=['PUT', 'DELETE'])
def update_mxh_account(account_id):
    conn = get_db_connection()
    try:
        if request.method == 'PUT':
            data = request.get_json()
            is_secondary = data.get('is_secondary', False)

            fields_to_update = {
                'card_name': data.get('card_name'),
                'username': data.get('username'),
                'phone': data.get('phone'),
                'url': data.get('url'),
                'login_username': data.get('login_username'),
                'login_password': data.get('login_password'),
                'wechat_created_day': data.get('wechat_created_day'),
                'wechat_created_month': data.get('wechat_created_month'),
                'wechat_created_year': data.get('wechat_created_year'),
                'wechat_status': data.get('wechat_status'),
                'status': data.get('status')
            }
            
            # Use appropriate prefixes for secondary account
            if is_secondary:
                update_cols = {f"secondary_{key}": value for key, value in fields_to_update.items()}
            else:
                update_cols = fields_to_update

            # Filter out any keys with None values to avoid overwriting with null
            update_cols = {k: v for k, v in update_cols.items() if v is not None}
            
            if not update_cols:
                return jsonify({'message': 'No fields to update.'})
                
            set_clause = ", ".join([f"{key} = ?" for key in update_cols.keys()])
            params = list(update_cols.values()) + [account_id]

            try:
                conn.execute(f'UPDATE mxh_accounts SET {set_clause} WHERE id = ?', params)
                conn.commit()
                return jsonify({'message': 'Account updated successfully'})
            except sqlite3.OperationalError as e:
                return jsonify({'error': str(e)}), 500
        
        elif request.method == 'DELETE':
            conn.execute('DELETE FROM mxh_accounts WHERE id = ?', (account_id,))
            conn.commit()
            return jsonify({'message': 'Account deleted successfully'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/mxh/api/accounts/<int:account_id>/scan', methods=['POST'])
def mark_account_scanned(account_id):
    conn = get_db_connection()
    try:
        data = request.get_json() or {}
        is_secondary = data.get('is_secondary', False)
        
        if data.get('reset'):
            # Reset scan count and last scan date
            if is_secondary:
                conn.execute('''
                    UPDATE mxh_accounts SET 
                    secondary_wechat_scan_count = 0,
                    secondary_wechat_last_scan_date = NULL
                    WHERE id = ?
                ''', (account_id,))
            else:
                conn.execute('''
                    UPDATE mxh_accounts SET 
                    wechat_scan_count = 0,
                    wechat_last_scan_date = NULL
                    WHERE id = ?
                ''', (account_id,))
            conn.commit()
            return jsonify({'message': 'Scan count reset successfully'})
        else:
            # Update scan count and last scan date
            current_date = datetime.now().isoformat()
            if is_secondary:
                conn.execute('''
                    UPDATE mxh_accounts SET 
                    secondary_wechat_scan_count = secondary_wechat_scan_count + 1,
                    secondary_wechat_last_scan_date = ?
                    WHERE id = ?
                ''', (current_date, account_id))
            else:
                conn.execute('''
                    UPDATE mxh_accounts SET 
                    wechat_scan_count = wechat_scan_count + 1,
                    wechat_last_scan_date = ?
                    WHERE id = ?
                ''', (current_date, account_id))
            conn.commit()
            return jsonify({'message': 'Account marked as scanned successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/mxh/api/accounts/<int:account_id>/toggle-status', methods=['POST'])
def toggle_account_status(account_id):
    conn = get_db_connection()
    try:
        data = request.get_json() or {}
        is_secondary = data.get('is_secondary', False)
        
        if is_secondary:
            # Toggle secondary status
            conn.execute('''
                UPDATE mxh_accounts 
                SET secondary_status = CASE 
                    WHEN secondary_status = 'active' THEN 'disabled'
                    ELSE 'active'
                END,
                secondary_die_date = CASE 
                    WHEN secondary_status = 'active' THEN ?
                    ELSE NULL
                END
                WHERE id = ?
            ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), account_id))
        else:
            # Toggle primary status
            conn.execute('''
                UPDATE mxh_accounts 
                SET status = CASE 
                    WHEN status = 'disabled' THEN 'active'
                    ELSE 'disabled'
                END,
                die_date = CASE 
                    WHEN status = 'disabled' THEN ?
                    ELSE NULL
                END
                WHERE id = ?
            ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), account_id))
        
        conn.commit()
        return jsonify({'message': 'Account status toggled successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/mxh/api/accounts/<int:account_id>/rescue', methods=['POST'])
def rescue_account(account_id):
    conn = get_db_connection()
    try:
        data = request.get_json() or {}
        is_secondary = data.get('is_secondary', False)
        rescue_result = data.get('result')  # 'success' or 'failed'
        
        if rescue_result == 'success':
            # Cứu thành công - chuyển về available và tăng success count
            if is_secondary:
                conn.execute('''
                    UPDATE mxh_accounts 
                    SET secondary_status = 'active',
                        secondary_die_date = NULL,
                        secondary_rescue_success_count = secondary_rescue_success_count + 1
                    WHERE id = ?
                ''', (account_id,))
            else:
                conn.execute('''
                    UPDATE mxh_accounts 
                    SET status = 'active',
                        die_date = NULL,
                        rescue_success_count = rescue_success_count + 1
                    WHERE id = ?
                ''', (account_id,))
            message = 'Account rescued successfully!'
        elif rescue_result == 'failed':
            # Cứu thất bại - tăng rescue count
            if is_secondary:
                conn.execute('''
                    UPDATE mxh_accounts 
                    SET secondary_rescue_count = secondary_rescue_count + 1
                    WHERE id = ?
                ''', (account_id,))
            else:
                conn.execute('''
                    UPDATE mxh_accounts 
                    SET rescue_count = rescue_count + 1
                    WHERE id = ?
                ''', (account_id,))
            message = 'Rescue attempt failed. Rescue count increased.'
        else:
            return jsonify({'error': 'Invalid rescue result'}), 400
        
        conn.commit()
        return jsonify({'message': message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/mxh/api/accounts/<int:account_id>/mark-die', methods=['POST'])
def mark_account_die(account_id):
    conn = get_db_connection()
    try:
        data = request.get_json() or {}
        is_secondary = data.get('is_secondary', False)
        die_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if is_secondary:
            conn.execute('''
                UPDATE mxh_accounts 
                SET secondary_status = 'disabled',
                    secondary_die_date = ?,
                    secondary_rescue_count = 0
                WHERE id = ?
            ''', (die_date, account_id))
        else:
            conn.execute('''
                UPDATE mxh_accounts 
                SET status = 'disabled',
                    die_date = ?,
                    rescue_count = 0
                WHERE id = ?
            ''', (die_date, account_id))
        
        conn.commit()
        return jsonify({'message': 'Account marked as died', 'die_date': die_date})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/mxh/api/groups/<int:group_id>', methods=['DELETE'])
def delete_mxh_group(group_id):
    conn = get_db_connection()
    try:
        # Check if group has accounts
        accounts = conn.execute('SELECT COUNT(*) FROM mxh_accounts WHERE group_id = ?', (group_id,)).fetchone()[0]
        if accounts > 0:
            return jsonify({'error': 'Cannot delete group with existing accounts'}), 400
        
        conn.execute('DELETE FROM mxh_groups WHERE id = ?', (group_id,))
        conn.commit()
        return jsonify({'message': 'Group deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
    migrate_auto_seeding_schema() # <-- ADD THIS LINE
    migrate_legacy_telegram_db() # <-- ADD THIS LINE
    migrate_json_to_sqlite()  # Run migration once
    start_scheduler_thread()  # Start automatic seeding scheduler
    setup_and_run_tray()