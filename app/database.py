import os
import sqlite3
from datetime import datetime

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_DIR = os.path.join(APP_ROOT, "data")
DATABASE_PATH = os.path.join(DATA_DIR, "Data.db")

def get_db_connection():
    """
    Thiết lập kết nối đến cơ sở dữ liệu SQLite.
    Bật hỗ trợ khóa ngoại (foreign key).
    """
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # Bắt buộc để ON DELETE CASCADE hoạt động
    return conn

def init_database():
    """
    Khởi tạo tất cả các bảng trong cơ sở dữ liệu nếu chúng chưa tồn tại.
    Hàm này đảm bảo cấu trúc schema luôn đúng theo thiết kế 1-N mới.
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"INFO: Created data directory at: {DATA_DIR}")

    conn = get_db_connection()
    cursor = conn.cursor()
    print("INFO: Starting database initialization...")

    # Bảng ghi chú
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY, 
            title_html TEXT, 
            content_html TEXT, 
            due_time TEXT, 
            status TEXT, 
            modified_at TEXT, 
            is_marked INTEGER DEFAULT 0
        )
    """)

    # Bảng nhóm MXH
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mxh_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            name TEXT NOT NULL UNIQUE, 
            color TEXT NOT NULL, 
            icon TEXT, 
            created_at TEXT NOT NULL
        )
    """)
    
    # Groups will be created dynamically by the frontend for each platform
    
    # Bảng thẻ MXH (cha) - corrected table name
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mxh_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_name TEXT NOT NULL,
            group_id INTEGER,
            platform TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Bảng tài khoản MXH (con) - exact structure as requested
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mxh_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL,
            is_primary INTEGER DEFAULT 0,
            account_name TEXT,
            username TEXT,
            phone TEXT,
            url TEXT,
            login_username TEXT,
            login_password TEXT,
            wechat_created_day INTEGER,
            wechat_created_month INTEGER,
            wechat_created_year INTEGER,
            wechat_status TEXT,
            status TEXT,
            die_date TEXT,
            disabled_date TEXT,
            wechat_scan_count INTEGER DEFAULT 0,
            wechat_last_scan_date TEXT,
            rescue_count INTEGER DEFAULT 0,
            rescue_success_count INTEGER DEFAULT 0,
            email_reset_date TEXT,
            notice TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(card_id) REFERENCES mxh_cards(id) ON DELETE CASCADE
        )
    """)

    # --- TẠO INDEX ĐỂ TĂNG TỐC ĐỘ TRUY VẤN ---
    # Exact index names as requested
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_acc_card ON mxh_accounts(card_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cards_group ON mxh_cards(group_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cards_platform ON mxh_cards(platform)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_acc_status ON mxh_accounts(wechat_status, status)")
    
    # --- MIGRATION: Add disabled_date column if not exists ---
    try:
        cursor.execute("SELECT disabled_date FROM mxh_accounts LIMIT 1")
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        print("INFO: Adding disabled_date column to mxh_accounts table...")
        cursor.execute("ALTER TABLE mxh_accounts ADD COLUMN disabled_date TEXT")
        print("INFO: disabled_date column added successfully.")
    
    conn.commit()
    conn.close()
    print("SUCCESS: Database initialization complete. Ready for 1-N model.")