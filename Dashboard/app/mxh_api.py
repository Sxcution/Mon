import sqlite3
import json
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from app.database import get_db_connection

mxh_api_bp = Blueprint("mxh_api", __name__, url_prefix="/mxh/api")


@mxh_api_bp.route("/accounts", methods=["GET"])
def get_accounts():
    """
    GET /mxh/api/accounts
    Get all accounts with optional last_updated_at filter for incremental updates.
    """
    conn = get_db_connection()
    try:
        last_updated_at = request.args.get('last_updated_at')
        
        if last_updated_at:
            # Get accounts updated after the specified timestamp
            query = """
                SELECT a.*, c.card_name, c.platform, c.group_id, g.name as group_name, g.color as group_color, g.icon as group_icon
                FROM mxh_accounts a
                JOIN mxh_cards c ON a.card_id = c.id
                JOIN mxh_groups g ON c.group_id = g.id
                WHERE a.updated_at > ?
                ORDER BY a.updated_at DESC
            """
            accounts = conn.execute(query, (last_updated_at,)).fetchall()
        else:
            # Get all accounts
            query = """
                SELECT a.*, c.card_name, c.platform, c.group_id, g.name as group_name, g.color as group_color, g.icon as group_icon
                FROM mxh_accounts a
                JOIN mxh_cards c ON a.card_id = c.id
                JOIN mxh_groups g ON c.group_id = g.id
                ORDER BY a.updated_at DESC
            """
            accounts = conn.execute(query).fetchall()
        
        # Convert to list of dictionaries
        accounts_list = []
        for account in accounts:
            account_dict = dict(account)
            # Parse notice JSON if it exists
            if account_dict.get('notice'):
                try:
                    account_dict['notice'] = json.loads(account_dict['notice'])
                except (json.JSONDecodeError, TypeError):
                    account_dict['notice'] = None
            accounts_list.append(account_dict)
        
        return jsonify(accounts_list)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_api_bp.route("/cards", methods=["POST"])
def create_card():
    """
    POST /mxh/api/cards
    Create a new card with validation for unique card_name within group_id.
    """
    conn = get_db_connection()
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate required fields
        card_name = data.get("card_name")
        group_id = data.get("group_id")
        platform = data.get("platform")
        
        if not card_name:
            return jsonify({"error": "card_name is required", "field": "card_name"}), 400
        if not group_id:
            return jsonify({"error": "group_id is required", "field": "group_id"}), 400
        if not platform:
            return jsonify({"error": "platform is required", "field": "platform"}), 400
        
        # Check if card_name is unique within the same group_id
        existing_card = conn.execute(
            "SELECT id FROM mxh_cards WHERE card_name = ? AND group_id = ?",
            (card_name, group_id)
        ).fetchone()
        
        if existing_card:
            return jsonify({
                "error": f"Card name '{card_name}' already exists in group {group_id}",
                "field": "card_name"
            }), 400
        
        # Start transaction
        conn.execute("BEGIN")
        
        # Create the card
        now = datetime.now(timezone.utc).astimezone().isoformat()
        cursor = conn.execute(
            "INSERT INTO mxh_cards (card_name, group_id, platform, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (card_name, group_id, platform, now, now)
        )
        card_id = cursor.lastrowid
        
        # Create the primary account
        conn.execute(
            """INSERT INTO mxh_accounts (
                card_id, is_primary, account_name, username, phone, url, 
                login_username, login_password, wechat_created_day, wechat_created_month, 
                wechat_created_year, wechat_status, status, created_at, updated_at
            ) VALUES (?, 1, 'Primary Account', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
            (
                card_id,
                data.get("username", ""),
                data.get("phone", ""),
                data.get("url", ""),
                data.get("login_username", data.get("username", "")),  # Fallback login username
                data.get("login_password", ""),
                data.get("wechat_created_day"),
                data.get("wechat_created_month"),
                data.get("wechat_created_year"),
                "available",  # Default wechat_status
                now,  # created_at
                now   # updated_at
            )
        )
        
        conn.commit()
        
        # Return success message
        return jsonify({"message": "Card and primary account created successfully", "card_id": card_id}), 201
        
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return jsonify({"error": f"Database constraint violation: {str(e)}"}), 400
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_api_bp.route("/cards", methods=["GET"])
def get_cards():
    """
    GET /mxh/api/cards?group_id=&platform=
    Return a list of cards with accounts_summary.
    """
    conn = get_db_connection()
    try:
        group_id = request.args.get("group_id")
        platform = request.args.get("platform")
        
        # Build query with optional filters
        query = "SELECT * FROM mxh_cards WHERE 1=1"
        params = []
        
        if group_id:
            query += " AND group_id = ?"
            params.append(group_id)
        
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        
        query += " ORDER BY card_name"
        
        cards = conn.execute(query, params).fetchall()
        
        # Convert to list of dictionaries with nested sub_accounts
        result = [dict(card) for card in cards]
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
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_api_bp.route("/cards/<int:card_id>/accounts", methods=["POST"])
def create_account(card_id):
    """
    POST /mxh/api/cards/<card_id>/accounts
    Create a new account under the specified card.
    """
    conn = get_db_connection()
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Check if card exists and get card info
        card = conn.execute("SELECT * FROM mxh_cards WHERE id = ?", (card_id,)).fetchone()
        if not card:
            return jsonify({"error": "Card not found"}), 404
        
        # Get or set default values
        account_name = data.get("account_name", "Sub Account")
        username = data.get("username", "...")
        phone = data.get("phone", "...")
        
        # Create the account
        now = datetime.now(timezone.utc).astimezone().isoformat()
        cursor = conn.execute(
            """INSERT INTO mxh_accounts (
                card_id, is_primary, account_name, username, phone, url, 
                login_username, login_password, wechat_created_day, wechat_created_month, 
                wechat_created_year, wechat_status, status, die_date, disabled_date, wechat_scan_count, 
                wechat_last_scan_date, rescue_count, rescue_success_count, email_reset_date, 
                notice, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                card_id,
                data.get("is_primary", 0),
                account_name,
                username,
                phone,
                data.get("url", ""),
                data.get("login_username", ""),
                data.get("login_password", ""),
                data.get("wechat_created_day"),
                data.get("wechat_created_month"),
                data.get("wechat_created_year"),
                data.get("wechat_status", "available"),
                data.get("status", "active"),
                data.get("die_date"),
                data.get("disabled_date"),
                0,  # wechat_scan_count
                data.get("wechat_last_scan_date"),
                0,  # rescue_count
                0,  # rescue_success_count
                data.get("email_reset_date"),
                data.get("notice"),
                now,
                now
            )
        )
        account_id = cursor.lastrowid
        
        conn.commit()
        
        # Return the created account with card info
        new_account = conn.execute("""
            SELECT a.*, c.card_name, c.platform, c.group_id
            FROM mxh_accounts a
            JOIN mxh_cards c ON a.card_id = c.id
            WHERE a.id = ?
        """, (account_id,)).fetchone()
        return jsonify(dict(new_account)), 201
        
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return jsonify({"error": f"Database constraint violation: {str(e)}"}), 400
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_api_bp.route("/accounts/<int:account_id>/quick-update", methods=["POST"])
def quick_update_account(account_id):
    """
    POST /mxh/api/accounts/<id>/quick-update
    Quick update for inline editing of account fields.
    """
    conn = get_db_connection()
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Get the field and value to update
        field = data.get("field")
        value = data.get("value")
        
        if not field:
            return jsonify({"error": "field is required"}), 400
        
        # Validate field name to prevent SQL injection
        allowed_fields = [
            'account_name', 'username', 'phone', 'url', 'login_username', 
            'login_password', 'wechat_status', 'status', 'notice'
        ]
        
        if field not in allowed_fields:
            return jsonify({"error": f"Invalid field: {field}"}), 400
        
        # Update the field
        now = datetime.now(timezone.utc).astimezone().isoformat()
        conn.execute(
            f"UPDATE mxh_accounts SET {field} = ?, updated_at = ? WHERE id = ?",
            (value, now, account_id)
        )
        
        if conn.total_changes == 0:
            return jsonify({"error": "Account not found"}), 404
        
        conn.commit()
        return jsonify({"message": "Account updated successfully"}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_api_bp.route("/groups", methods=["GET", "POST"])
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


@mxh_api_bp.route("/accounts/<int:account_id>", methods=["PUT"])
def update_account(account_id):
    """
    PUT /mxh/api/accounts/<account_id>
    Cập nhật toàn diện thông tin cho một account.
    """
    conn = get_db_connection()
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        account = conn.execute("SELECT card_id FROM mxh_accounts WHERE id = ?", (account_id,)).fetchone()
        if not account:
            return jsonify({"error": "Account not found"}), 404

        now = datetime.now(timezone.utc).astimezone().isoformat()
        
        conn.execute("BEGIN")

        # --- Update mxh_accounts table ---
        account_fields = {}
        allowed_account_fields = [
            "username", "phone", "email", "wechat_created_day", "wechat_created_month",
            "wechat_created_year", "status", "muted_until", "wechat_status", "die_date", "disabled_date"
        ]
        
        for field in allowed_account_fields:
            if field in data:
                account_fields[field] = data[field]
        
        print(f"🔍 Account fields to update: {account_fields}")
        
        if account_fields:
            account_fields["updated_at"] = now
            set_clause = ", ".join([f"{key} = ?" for key in account_fields.keys()])
            params = list(account_fields.values()) + [account_id]
            sql = f"UPDATE mxh_accounts SET {set_clause} WHERE id = ?"
            print(f"🔍 SQL: {sql}")
            print(f"🔍 Params: {params}")
            conn.execute(sql, params)

        # --- Update mxh_cards table (for card_name) ---
        if "card_name" in data:
            conn.execute(
                "UPDATE mxh_cards SET card_name = ?, updated_at = ? WHERE id = ?",
                (data["card_name"], now, account['card_id'])
            )

        conn.commit()
        
        updated_account = conn.execute("SELECT a.*, c.card_name, c.platform, c.group_id FROM mxh_accounts a JOIN mxh_cards c ON a.card_id = c.id WHERE a.id = ?", (account_id,)).fetchone()
        result = dict(updated_account)
        print(f"🔍 Returning updated account: {result}")
        print(f"🔍 Email in result: {result.get('email', 'NOT FOUND')}")
        return jsonify(result)

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_api_bp.route("/notice", methods=["GET"])
def get_notice():
    """
    GET /mxh/api/notice?account_id=...
    Get notice data for a specific account.
    """
    conn = get_db_connection()
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            return jsonify({"error": "account_id is required"}), 400
        
        # Get account with notice data
        account = conn.execute(
            "SELECT * FROM mxh_accounts WHERE id = ?", 
            (account_id,)
        ).fetchone()
        
        if not account:
            return jsonify({"error": "Account not found"}), 404
        
        # Parse notice JSON
        notice_data = {}
        if account['notice']:
            try:
                notice_obj = json.loads(account['notice'])
                if notice_obj and notice_obj.get('enabled'):
                    notice_data = {
                        "title": notice_obj.get('title', 'Thông báo đến hạn'),
                        "message": notice_obj.get('note', 'Không có nội dung'),
                        "due_human": notice_obj.get('due_date', ''),
                        "due_at": notice_obj.get('due_date'),
                        "notice_id": account_id
                    }
            except json.JSONDecodeError:
                pass
        
        return jsonify(notice_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@mxh_api_bp.route("/notice/disable", methods=["POST"])
def disable_notice():
    """
    POST /mxh/api/notice/disable
    Disable notice for an account.
    Body: {"account_id": "..."} or {"notice_id": "..."}
    """
    conn = get_db_connection()
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        account_id = data.get('account_id') or data.get('notice_id')
        if not account_id:
            return jsonify({"error": "account_id or notice_id is required"}), 400
        
        # Update notice to disabled
        disabled_notice = json.dumps({
            "enabled": False,
            "title": "",
            "days": 0,
            "note": "",
            "start_at": None
        })
        
        conn.execute(
            "UPDATE mxh_accounts SET notice = ?, updated_at = ? WHERE id = ?",
            (disabled_notice, datetime.now().isoformat(), account_id)
        )
        
        conn.commit()
        
        return jsonify({"ok": True, "message": "Notice disabled successfully"})
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()