import sqlite3
import json
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, render_template
from app.database import get_db_connection

mxh_bp = Blueprint("mxh", __name__, url_prefix="/mxh")


# --- ALIAS: giữ tương thích FE cũ - tạo/xóa CARD qua /api/accounts ---

@mxh_bp.route("/api/accounts", methods=["POST"])
def alias_create_card_from_accounts():
    """
    FE cũ: POST /mxh/api/accounts
    Expect: tạo CARD + tạo luôn 1 ACCOUNT primary thuộc card đó.
    """
    conn = get_db_connection()
    try:
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        card_name = (data.get("card_name") or data.get("name") or "").strip()
        group_id  = int(data.get("group_id") or 0)
        platform  = (data.get("platform") or "wechat").strip().lower()
        if not card_name or not group_id:
            return jsonify({"error": "card_name và group_id là bắt buộc"}), 400

        now = datetime.now(timezone.utc).astimezone().isoformat()

        # 1) Tạo CARD
        cur = conn.execute("""
            INSERT INTO mxh_cards (card_name, group_id, platform, created_at, updated_at)
            VALUES (?,?,?,?,?)
        """, (card_name, group_id, platform, now, now))
        card_id = cur.lastrowid

        # 2) Tạo ACCOUNT primary (map đúng cột DB)
        acc_cols = (
            "card_id","is_primary","account_name","username","phone","url",
            "login_username","login_password","created_at","updated_at",
            "wechat_created_day","wechat_created_month","wechat_created_year",
            "wechat_status","status","muted_until","die_date","disabled_date",
            "wechat_scan_count","wechat_last_scan_date",
            "rescue_count","rescue_success_count","email_reset_date","notice"
        )
        acc_vals = (
            card_id, 1,
            data.get("account_name") or "Tài khoản chính",
            data.get("username") or ".",
            data.get("phone") or ".",
            data.get("url") or ".",
            data.get("login_username") or ".",
            data.get("login_password") or ".",
            now, now,
            data.get("wechat_created_day"),
            data.get("wechat_created_month"),
            data.get("wechat_created_year"),
            (data.get("wechat_status") or "available"),
            (data.get("status") or "active"),
            data.get("muted_until"),
            data.get("die_date"),
            data.get("disabled_date"),
            0, None,
            0, 0,
            data.get("email_reset_date"),
            json.dumps(data.get("notice")) if isinstance(data.get("notice"), dict) else data.get("notice")
        )
        q = f"INSERT INTO mxh_accounts ({','.join(acc_cols)}) VALUES ({','.join(['?']*len(acc_cols))})"
        cur2 = conn.execute(q, acc_vals)
        account_id = cur2.lastrowid

        conn.commit()

        new_card = conn.execute("SELECT * FROM mxh_cards WHERE id=?", (card_id,)).fetchone()
        new_acc  = conn.execute("SELECT * FROM mxh_accounts WHERE id=?", (account_id,)).fetchone()
        return jsonify({"card": dict(new_card), "account": dict(new_acc)}), 201
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_bp.route("/api/accounts/<int:any_id>", methods=["DELETE"])
def smart_delete_account_or_card(any_id: int):
    """
    FE cũ gọi /mxh/api/accounts/<id> để xóa.
    - Nếu <id> là account.id -> xóa ACCOUNT
    - Nếu <id> là mxh_cards.id -> xóa CARD + toàn bộ accounts con
    """
    conn = get_db_connection()
    try:
        conn.execute("BEGIN")

        acc = conn.execute("SELECT id FROM mxh_accounts WHERE id=?", (any_id,)).fetchone()
        if acc:
            conn.execute("DELETE FROM mxh_accounts WHERE id=?", (any_id,))
            conn.commit()
            return jsonify({"message": "Account deleted", "account_id": any_id})

        card = conn.execute("SELECT id FROM mxh_cards WHERE id=?", (any_id,)).fetchone()
        if card:
            conn.execute("DELETE FROM mxh_accounts WHERE card_id=?", (any_id,))
            conn.execute("DELETE FROM mxh_cards WHERE id=?", (any_id,))
            conn.commit()
            return jsonify({"message": "Card and its accounts deleted", "card_id": any_id})

        conn.rollback()
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_bp.route("")
def mxh_page():
    return render_template("mxh.html", title="Mạng Xã Hội")


@mxh_bp.route("/api/groups", methods=["GET", "POST"])
def mxh_groups():
    conn = get_db_connection()
    try:
        if request.method == "GET":
            groups = conn.execute(
                "SELECT * FROM mxh_groups ORDER BY created_at DESC"
            ).fetchall()
            return jsonify([dict(g) for g in groups])
        elif request.method == "POST":
            data = request.get_json()
            name, color = data.get("name"), data.get("color")
            if not name or not color:
                return jsonify({"error": "Name and color are required"}), 400
            platform_icons = {
                "wechat": "bi-wechat",
                "facebook": "bi-facebook",
                "instagram": "bi-instagram",
                "tiktok": "bi-tiktok",
                "youtube": "bi-youtube",
                "twitter": "bi-twitter",
                "linkedin": "bi-linkedin",
                "zalo": "bi-chat-dots",
                "telegram": "bi-telegram",
                "whatsapp": "bi-whatsapp",
            }
            icon = platform_icons.get(name.lower(), "bi-share-fill")
            try:
                cursor = conn.execute(
                    "INSERT INTO mxh_groups (name, color, icon, created_at) VALUES (?, ?, ?, ?)",
                    (name, color, icon, datetime.now().isoformat()),
                )
                conn.commit()
                return (
                    jsonify(
                        {
                            "id": cursor.lastrowid,
                            "name": name,
                            "color": color,
                            "icon": icon,
                            "message": "Group created",
                        }
                    ),
                    201,
                )
            except sqlite3.IntegrityError:
                return jsonify({"error": f'Group "{name}" already exists.'}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_bp.route("/api/accounts", methods=["GET"])
def list_accounts_flat():
    """GET /mxh/api/accounts - trả danh sách account phẳng (join từ mxh_accounts + mxh_cards)"""
    conn = get_db_connection()
    try:
        last = request.args.get("last_updated_at")
        base_sql = """
            SELECT
                a.*,
                c.card_name,
                c.group_id,
                c.platform
            FROM mxh_accounts a
            JOIN mxh_cards   c ON a.card_id = c.id
        """
        args = []
        if last:
            base_sql += " WHERE a.updated_at > ?"
            args.append(last)
        base_sql += " ORDER BY a.is_primary DESC, c.group_id ASC, CAST(c.card_name AS INTEGER) ASC, a.id ASC"

        rows = conn.execute(base_sql, args).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_bp.route("/api/cards", methods=["GET", "POST"])
def mxh_cards_and_sub_accounts():
    """GET/POST /mxh/api/cards - quản lý cards và sub_accounts"""
    conn = get_db_connection()
    try:
        if request.method == "GET":
            cards = conn.execute(
                "SELECT c.*, g.name as group_name, g.color as group_color, g.icon as group_icon FROM mxh_cards c LEFT JOIN mxh_groups g ON c.group_id = g.id ORDER BY CAST(c.card_name AS INTEGER)"
            ).fetchall()
            result = [dict(c) for c in cards]
            card_ids = [c["id"] for c in result]

            if card_ids:
                placeholders = ",".join("?" for _ in card_ids)
                sub_accounts = conn.execute(
                    f"SELECT * FROM mxh_accounts WHERE card_id IN ({placeholders}) ORDER BY is_primary DESC, id ASC",
                    card_ids,
                ).fetchall()
                for card in result:
                    card["sub_accounts"] = [
                        dict(sa) for sa in sub_accounts if sa["card_id"] == card["id"]
                    ]
            return jsonify(result)

        elif request.method == "POST":
            data = request.get_json()
            now_iso = datetime.now().isoformat()

            cursor = conn.execute(
                "INSERT INTO mxh_cards (card_name, group_id, platform, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (
                    data.get("card_name"),
                    data.get("group_id"),
                    data.get("platform"),
                    now_iso,
                    now_iso,
                ),
            )
            card_id = cursor.lastrowid

            conn.execute(
                """INSERT INTO mxh_accounts (card_id, is_primary, account_name, username, phone, url, login_username, login_password, created_at, updated_at, wechat_created_day, wechat_created_month, wechat_created_year, status) 
                            VALUES (?, 1, 'Tài khoản chính', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    card_id,
                    data.get("username"),
                    data.get("phone"),
                    data.get("url"),
                    data.get("login_username"),
                    data.get("login_password"),
                    now_iso,
                    now_iso,
                    data.get("wechat_created_day"),
                    data.get("wechat_created_month"),
                    data.get("wechat_created_year"),
                    "active",
                ),
            )

            conn.commit()
            return jsonify({"message": "Card created", "card_id": card_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_bp.route("/api/cards/<int:card_id>", methods=["PUT", "DELETE"])
def mxh_update_or_delete_card(card_id):
    """PUT/DELETE /mxh/api/cards/<card_id> - cập nhật hoặc xóa card"""
    conn = get_db_connection()
    try:
        if request.method == "PUT":
            data = request.get_json()
            conn.execute(
                "UPDATE mxh_cards SET card_name = ?, updated_at = ? WHERE id = ?",
                (data.get("card_name"), datetime.now().isoformat(), card_id),
            )
            conn.commit()
            return jsonify({"message": "Card updated"})
        elif request.method == "DELETE":
            conn.execute("DELETE FROM mxh_cards WHERE id = ?", (card_id,))
            conn.commit()
            return jsonify({"message": "Card and sub-accounts deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# === NEW: PUT /api/accounts/<account_id> - Update Account (not card!) ===
@mxh_bp.route("/api/accounts/<int:account_id>", methods=["PUT"])
def update_account_direct(account_id):
    """
    PUT /mxh/api/accounts/<account_id> - Update account fields
    Used by frontend to update account status, username, phone, etc.
    Also handles card_name update (updates the card, not the account)
    """
    conn = get_db_connection()
    try:
        data = request.get_json() or {}
        
        # Handle card_name separately (it's in mxh_cards table)
        card_name = data.pop('card_name', None)
        
        # Build dynamic UPDATE query for account fields
        allowed_fields = {
            "status", "username", "phone", "url", "login_username", "login_password",
            "account_name", "wechat_created_day", "wechat_created_month", "wechat_created_year",
            "wechat_status", "die_date", "disabled_date", "wechat_scan_count", "wechat_last_scan_date",
            "rescue_count", "rescue_success_count", "email_reset_date", "notice", "muted_until",
            "email"  # Thêm trường email để cho phép cập nhật email từ modal WeChat
        }
        
        # 🔍 Debug: Kiểm tra dữ liệu nhận được từ frontend
        print(f"🔍 [update_account_direct] Received data: {data}")
        print(f"🔍 [update_account_direct] Email in data: {data.get('email', 'NOT FOUND')}")
        
        updates = {}
        for field in allowed_fields:
            if field in data:
                updates[field] = data[field]
        
        # 🔍 Debug: Kiểm tra các trường sẽ được cập nhật
        print(f"🔍 [update_account_direct] Fields to update: {list(updates.keys())}")
        print(f"🔍 [update_account_direct] Email in updates: {updates.get('email', 'NOT FOUND')}")
        
        # Update card_name if provided
        if card_name is not None:
            # Get card_id for this account
            account = conn.execute("SELECT card_id FROM mxh_accounts WHERE id = ?", (account_id,)).fetchone()
            if account:
                conn.execute(
                    "UPDATE mxh_cards SET card_name = ?, updated_at = ? WHERE id = ?",
                    (card_name, datetime.now().isoformat(), account['card_id'])
                )
        
        # Update account fields if any
        if updates:
            # Add updated_at
            updates["updated_at"] = datetime.now().isoformat()
            
            # Build SQL
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [account_id]
            
            # 🔍 Debug: Kiểm tra SQL query và giá trị
            sql_query = f"UPDATE mxh_accounts SET {set_clause} WHERE id = ?"
            print(f"🔍 [update_account_direct] SQL: {sql_query}")
            print(f"🔍 [update_account_direct] Values: {values}")
            
            conn.execute(sql_query, values)
        
        conn.commit()
        
        # Return updated account with joined data (card_name, group_id, platform)
        updated = conn.execute("""
            SELECT a.*, c.card_name, c.group_id, c.platform 
            FROM mxh_accounts a 
            JOIN mxh_cards c ON a.card_id = c.id 
            WHERE a.id = ?
        """, (account_id,)).fetchone()
        
        # 🔍 Debug: Kiểm tra kết quả sau khi cập nhật
        if updated:
            updated_dict = dict(updated)
            print(f"🔍 [update_account_direct] Updated account email: {updated_dict.get('email', 'NOT FOUND')}")
            return jsonify(updated_dict)
        return jsonify({"error": "Account not found after update"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_bp.route("/api/cards/<int:card_id>/accounts", methods=["POST"])
def mxh_create_sub_account(card_id):
    """POST /mxh/api/cards/<card_id>/accounts - tạo account con"""
    conn = get_db_connection()
    try:
        data = request.get_json() or {}
        now_iso = datetime.now().isoformat()
        
        # 🔍 Nhận các trường wechat_created_* từ request body
        wechat_created_day = data.get("wechat_created_day")
        wechat_created_month = data.get("wechat_created_month")
        wechat_created_year = data.get("wechat_created_year")
        
        # 🔍 Lưu đầy đủ các trường wechat_created_* vào database
        cursor = conn.execute(
            """INSERT INTO mxh_accounts 
               (card_id, is_primary, created_at, updated_at, account_name, 
                wechat_created_day, wechat_created_month, wechat_created_year) 
               VALUES (?, 0, ?, ?, ?, ?, ?, ?)""",
            (card_id, now_iso, now_iso, "Tài khoản phụ", 
             wechat_created_day, wechat_created_month, wechat_created_year),
        )
        sub_account_id = cursor.lastrowid
        conn.commit()
        
        # 🔍 Trả về đầy đủ thông tin account bao gồm created_at và wechat_created_*
        new_sub = conn.execute(
            "SELECT * FROM mxh_accounts WHERE id = ?", (sub_account_id,)
        ).fetchone()
        return jsonify(dict(new_sub)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# Alias để tương thích với route cũ
@mxh_bp.route("/api/accounts/<int:card_id>/sub_accounts", methods=["POST"])
def add_sub_account(card_id):
    """Alias cho route cũ - redirect đến /api/cards/<card_id>/accounts"""
    return mxh_create_sub_account(card_id)


@mxh_bp.route("/api/sub_accounts/<int:sub_account_id>", methods=["PUT", "DELETE"])
def manage_sub_account(sub_account_id):
    conn = get_db_connection()
    try:
        if request.method == "PUT":
            data = request.get_json()
            fields = {k: v for k, v in data.items() if v is not None}
            if "card_name" in fields:
                del fields["card_name"]
            if not fields:
                return jsonify({"message": "No fields to update."})
            fields["updated_at"] = datetime.now().isoformat()
            set_clause = ", ".join([f"{key} = ?" for key in fields.keys()])
            params = list(fields.values()) + [sub_account_id]
            conn.execute(
                f"UPDATE mxh_accounts SET {set_clause} WHERE id = ?", params
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM mxh_accounts WHERE id = ?", (sub_account_id,)
            ).fetchone()
            return jsonify(dict(updated))
        elif request.method == "DELETE":
            sub_account = conn.execute(
                "SELECT is_primary FROM mxh_accounts WHERE id = ?",
                (sub_account_id,),
            ).fetchone()
            if sub_account and sub_account["is_primary"]:
                return jsonify({"error": "Cannot delete primary sub-account"}), 400
            conn.execute("DELETE FROM mxh_accounts WHERE id = ?", (sub_account_id,))
            conn.commit()
            return jsonify({"message": "Sub-account deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# Alias cho các thao tác account mới (theo yêu cầu chuẩn hóa API)
def _now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()


# Các route cụ thể phải đặt TRƯỚC route chung để tránh conflict
@mxh_bp.route("/api/accounts/<int:account_id>/toggle-status", methods=["POST"])
def acc_toggle_status(account_id):
    """POST /mxh/api/accounts/<account_id>/toggle-status - toggle status của account"""
    conn = get_db_connection()
    try:
        now_iso = _now_iso()
        # active <-> inactive (tùy Sếp dùng status gì)
        conn.execute("""
            UPDATE mxh_accounts
            SET status = CASE
                WHEN status = 'active' THEN 'inactive'
                ELSE 'active'
            END,
            updated_at = ?
            WHERE id = ?
        """, (now_iso, account_id))
        conn.commit()
        return jsonify({"message": "Status toggled"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_bp.route("/api/accounts/<int:account_id>/scan", methods=["POST"])
def acc_scan(account_id):
    """POST /mxh/api/accounts/<account_id>/scan - ghi nhận hoặc reset scan"""
    conn = get_db_connection()
    try:
        # Đọc dữ liệu JSON từ body của request
        data = request.get_json(silent=True) or {}
        now_iso = _now_iso()

        if data.get("reset"):
            # Reset lượt quét
            conn.execute(
                """
                UPDATE mxh_accounts
                SET wechat_scan_count = 0,
                    wechat_last_scan_date = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (now_iso, account_id),
            )
            message = "Scan count reset"
        else:
            # Tăng lượt quét
            conn.execute(
                """
                UPDATE mxh_accounts
                SET wechat_scan_count = COALESCE(wechat_scan_count, 0) + 1,
                    wechat_last_scan_date = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (now_iso, now_iso, account_id),
            )
            message = "Scan recorded"

        conn.commit()
        
        # Return updated account data
        updated = conn.execute("""
            SELECT a.*, c.card_name, c.group_id, c.platform 
            FROM mxh_accounts a 
            JOIN mxh_cards c ON a.card_id = c.id 
            WHERE a.id = ?
        """, (account_id,)).fetchone()
        
        if updated:
            return jsonify(dict(updated))
        return jsonify({"message": message})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_bp.route("/api/accounts/<int:account_id>/rescue", methods=["POST"])
def acc_rescue(account_id):
    """POST /mxh/api/accounts/<account_id>/rescue - rescue account"""
    conn = get_db_connection()
    try:
        body = request.get_json(silent=True) or {}
        result = (body.get("result") or "").lower()
        now_iso = _now_iso()
        if result == "success":
            conn.execute("""
                UPDATE mxh_accounts
                SET status = 'active',
                    die_date = NULL,
                    disabled_date = NULL,
                    rescue_success_count = COALESCE(rescue_success_count,0) + 1,
                    updated_at = ?
                WHERE id = ?
            """, (now_iso, account_id))
            msg = "Rescued successfully"
        else:
            conn.execute("""
                UPDATE mxh_accounts
                SET rescue_count = COALESCE(rescue_count,0) + 1,
                    updated_at = ?
                WHERE id = ?
            """, (now_iso, account_id))
            msg = "Rescue attempt recorded"
        conn.commit()
        
        # Return updated account data as source of truth
        updated_account = conn.execute("""
            SELECT a.*, c.card_name, c.group_id, c.platform 
            FROM mxh_accounts a 
            JOIN mxh_cards c ON a.card_id = c.id 
            WHERE a.id = ?
        """, (account_id,)).fetchone()
        
        if updated_account:
            return jsonify(dict(updated_account))
        else:
            return jsonify({"message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_bp.route("/api/accounts/<int:account_id>/mark-die", methods=["POST"])
def acc_mark_die(account_id):
    """POST /mxh/api/accounts/<account_id>/mark-die - đánh dấu account chết"""
    conn = get_db_connection()
    try:
        now_iso = _now_iso()
        conn.execute("""
            UPDATE mxh_accounts
            SET status = 'die',
                die_date = ?,
                updated_at = ?
            WHERE id = ?
        """, (now_iso, now_iso, account_id))
        conn.commit()
        return jsonify({"message": "Account marked as die"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_bp.route("/api/accounts/<int:account_id>/reset", methods=["POST"])
def acc_reset(account_id):
    """POST /mxh/api/accounts/<account_id>/reset - reset account về trạng thái mặc định"""
    conn = get_db_connection()
    try:
        print(f"🔄 Resetting account {account_id}...")
        now_iso = _now_iso()
        
        # Check if account exists first
        existing = conn.execute("SELECT id, username, phone FROM mxh_accounts WHERE id = ?", (account_id,)).fetchone()
        if not existing:
            print(f"❌ Account {account_id} not found!")
            return jsonify({"error": "Account not found"}), 404
        
        print(f"📝 Before reset: user={existing['username']}, phone={existing['phone']}")
        
        cursor = conn.execute("""
            UPDATE mxh_accounts
            SET username = '.',
                phone = '.',
                status = 'active',
                die_date = NULL,
                disabled_date = NULL,
                wechat_scan_count = 0,
                wechat_last_scan_date = NULL,
                rescue_count = 0,
                rescue_success_count = 0,
                notice = NULL,
                muted_until = NULL,
                updated_at = ?
            WHERE id = ?
        """, (now_iso, account_id))
        
        rows_affected = cursor.rowcount
        print(f"📊 UPDATE affected {rows_affected} rows")
        
        conn.commit()
        print(f"✅ Committed transaction")
        
        # Return updated account data
        updated = conn.execute("""
            SELECT a.*, c.card_name, c.group_id, c.platform 
            FROM mxh_accounts a 
            JOIN mxh_cards c ON a.card_id = c.id 
            WHERE a.id = ?
        """, (account_id,)).fetchone()
        
        if updated:
            print(f"📤 After reset: user={updated['username']}, phone={updated['phone']}")
            return jsonify(dict(updated))
        return jsonify({"message": "Account reset successfully"})
    except Exception as e:
        print(f"❌ Error resetting account: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_bp.route("/api/accounts/<int:account_id>/notice", methods=["PUT", "DELETE"])
def acc_notice(account_id):
    """PUT/DELETE /mxh/api/accounts/<account_id>/notice - quản lý notice"""
    conn = get_db_connection()
    try:
        now_iso = _now_iso()
        if request.method == "DELETE":
            conn.execute("UPDATE mxh_accounts SET notice = NULL, updated_at = ? WHERE id = ?", (now_iso, account_id))
            conn.commit()
            return jsonify({"message": "Notice cleared"})
        data = request.get_json() or {}
        
        # Calculate due_date if not provided
        if 'due_date' not in data and 'days' in data:
            from datetime import timedelta
            start_date = datetime.now(timezone.utc).astimezone()
            due_date = start_date + timedelta(days=int(data['days']))
            data['due_date'] = due_date.isoformat()
            data['start_at'] = start_date.isoformat()
            data['enabled'] = True
        
        conn.execute("UPDATE mxh_accounts SET notice = ?, updated_at = ? WHERE id = ?", (json.dumps(data), now_iso, account_id))
        conn.commit()
        return jsonify({"message": "Notice saved", "notice": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()