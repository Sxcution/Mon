#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 DEBUG: Telegram Workers
Worker functions cho các task Telegram (Check Live, Join Group, Seeding)
Ported from Main.pyw
"""

import os
import asyncio
import random
import sqlite3
from itertools import cycle
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import JoinChannelRequest

# Telegram API credentials
API_ID = 28610130
API_HASH = "eda4079a5b9d4f3f88b67dacd799f902"
ADMIN_SESSION_FOLDER = "Adminsession"

print('🔍 DEBUG: Telegram workers module loaded')


def parse_proxy_string(proxy_str):
    """🔍 Parse proxy string to dict for Telethon"""
    if not proxy_str:
        return None
    
    try:
        # Format: socks5://user:pass@host:port or socks5://host:port
        if proxy_str.startswith('socks5://'):
            proxy_str = proxy_str[9:]
        
        if '@' in proxy_str:
            auth, addr = proxy_str.split('@')
            username, password = auth.split(':')
            host, port = addr.split(':')
            return {
                'proxy_type': 'socks5',
                'addr': host,
                'port': int(port),
                'username': username,
                'password': password
            }
        else:
            host, port = proxy_str.split(':')
            return {
                'proxy_type': 'socks5',
                'addr': host,
                'port': int(port)
            }
    except Exception as e:
        print(f'🔍 ERROR parsing proxy {proxy_str}: {e}')
        return None


def get_db_connection():
    """🔍 Get database connection"""
    from pathlib import Path
    BASE_DIR = Path(__file__).parent.parent
    DATABASE_PATH = BASE_DIR / 'data' / 'Data.db'
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


async def check_single_session_worker(session_path, *args, **kwargs):
    """🔍 Worker to check if a single session is live"""
    proxy_info = kwargs.get("proxy_info")
    status = {"is_live": False, "full_name": "Lỗi", "username": "", "status_text": "Error"}
    client = None
    
    print(f'🔍 Checking session: {os.path.basename(session_path)}')
    
    try:
        proxy_dict = parse_proxy_string(proxy_info)
        client = TelegramClient(session_path, API_ID, API_HASH, proxy=proxy_dict)
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            full_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
            status = {
                "is_live": True,
                "full_name": full_name or "No Name",
                "username": me.username or "",
                "status_text": "Live"
            }
            print(f'🔍 ✅ Live: {full_name} (@{me.username})')
        else:
            status["status_text"] = "Dead"
            print(f'🔍 ❌ Dead: Not authorized')
            
    except SessionPasswordNeededError:
        status["status_text"] = "2FA Enabled"
        print(f'🔍 ⚠️  2FA Enabled')
    except Exception as e:
        status["status_text"] = str(e)[:50]
        print(f'🔍 ❌ Error: {str(e)[:50]}')
    finally:
        if client and client.is_connected():
            await client.disconnect()
    
    return status


async def join_group_worker(session_path, group_links, *args, **kwargs):
    """🔍 Worker to join groups"""
    proxy_info = kwargs.get("proxy_info")
    status = {"is_live": False, "full_name": "Lỗi", "username": "", "status_text": "Error"}
    client = None
    
    print(f'🔍 Joining groups with session: {os.path.basename(session_path)}')
    
    try:
        proxy_dict = parse_proxy_string(proxy_info)
        client = TelegramClient(session_path, API_ID, API_HASH, proxy=proxy_dict)
        await client.connect()
        
        if not await client.is_user_authorized():
            status["status_text"] = "Dead"
            return status
        
        me = await client.get_me()
        full_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
        
        # Join all groups
        joined = 0
        for link in group_links:
            try:
                await client(JoinChannelRequest(link))
                joined += 1
                await asyncio.sleep(2)
            except Exception as e:
                print(f'🔍 Failed to join {link}: {e}')
        
        status = {
            "is_live": True,
            "full_name": full_name or "No Name",
            "username": me.username or "",
            "status_text": f"Joined {joined}/{len(group_links)}"
        }
        print(f'🔍 ✅ Joined {joined} groups')
        
    except Exception as e:
        status["status_text"] = str(e)[:50]
        print(f'🔍 ❌ Error: {str(e)[:50]}')
    finally:
        if client and client.is_connected():
            await client.disconnect()
    
    return status


async def seeding_group_worker(session_path, group_link, message_scenario, send_silent, *args, **kwargs):
    """🔍 Worker to seed messages to groups"""
    proxy_info = kwargs.get("proxy_info")
    status = {"is_live": False, "full_name": "Lỗi", "username": "", "status_text": "Error"}
    client = None
    
    print(f'🔍 Seeding group with session: {os.path.basename(session_path)} to {group_link}')
    
    try:
        proxy_dict = parse_proxy_string(proxy_info)
        client = TelegramClient(session_path, API_ID, API_HASH, proxy=proxy_dict)
        await client.connect()
        
        if not await client.is_user_authorized():
            status["status_text"] = "Dead"
            return status
        
        me = await client.get_me()
        full_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
        
        # 🔍 FIX: Simple join without get_entity() (match telegram_module.py line 559-563)
        try:
            await client(JoinChannelRequest(group_link))
        except Exception:
            pass  # Continue even if join fails (might already be in channel)
        
        # Send message - handle both dict and string format
        if isinstance(message_scenario, dict):
            message = message_scenario.get('text', '')
        else:
            message = str(message_scenario)
        
        print(f'🔍 Sending message: {message[:30]}...')
        await client.send_message(group_link, message, silent=send_silent)
        
        status = {
            "is_live": True,
            "full_name": full_name or "No Name",
            "username": me.username or "",
            "status_text": "Seeded"
        }
        print(f'🔍 ✅ Seeded message to {group_link}')
        
    except Exception as e:
        status["status_text"] = str(e)[:50]
        print(f'🔍 ❌ Error: {str(e)[:50]}')
    finally:
        if client and client.is_connected():
            await client.disconnect()
    
    return status


async def run_admin_task(admin_session_path, group_link, message):
    """🔍 Admin task to send message (match Main.pyw logic)"""
    print(f'🔍 Admin sending message to {group_link}')
    client = None
    
    try:
        # 🔍 IMPORTANT: Admin does not use proxy (match Main.pyw)
        client = TelegramClient(admin_session_path, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f'🔍 ❌ Admin session not authorized')
            return
        
        # 🔍 FIX: Simple join without get_entity() to avoid session lock (match Main.pyw)
        try:
            await client(JoinChannelRequest(group_link))
        except Exception as join_error:
            # Log but continue - might already be in channel
            print(f'🔍 Admin join error (might be already in channel): {join_error}')
        
        # Send message
        print(f'🔍 Admin sending: {message[:50]}...')
        await client.send_message(group_link, message)
        print(f'🔍 ✅ Admin sent message to {group_link}')
        
    except Exception as e:
        print(f'🔍 ❌ Admin task failed for group {group_link}: {e}')
    finally:
        if client and client.is_connected():
            await client.disconnect()


async def task_worker(task_id, group_id, session_path, filename, coro_func, *args, **kwargs):
    """🔍 Generic task worker that wraps the actual worker function"""
    proxy_info = kwargs.get("proxy_info")
    
    print(f'🔍 Task worker processing: {filename}')
    
    # Run the actual worker
    status_result = await coro_func(session_path, *args, proxy_info=proxy_info)
    
    # Update database with result
    conn = get_db_connection()
    try:
        conn.execute(
            """INSERT INTO session_metadata 
               (group_id, filename, full_name, username, is_live, status_text, last_checked) 
               VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) 
               ON CONFLICT(group_id, filename) 
               DO UPDATE SET 
                 full_name=excluded.full_name, 
                 username=excluded.username, 
                 is_live=excluded.is_live, 
                 status_text=excluded.status_text, 
                 last_checked=CURRENT_TIMESTAMP""",
            (
                group_id,
                filename,
                status_result.get("full_name"),
                status_result.get("username"),
                status_result.get("is_live"),
                status_result.get("status_text")
            )
        )
        conn.commit()
        print(f'🔍 ✅ Updated database for {filename}')
    except Exception as e:
        print(f'🔍 ❌ Database error for {filename}: {e}')
    finally:
        conn.close()
    
    # Update task status
    from app.telegram_routes import TASKS
    task = TASKS.get(task_id)
    if task:
        task["processed"] += 1
        if status_result.get("is_live"):
            task["success"] += 1
        else:
            task["failed"] += 1
        task["results"].append({"filename": filename, **status_result})
        print(f'🔍 Task progress: {task["processed"]}/{task["total"]}')


def run_task_in_thread(
    task_id, group_id, folder_path, filenames,
    core, delay_per_session, delay_between_batches,
    admin_enabled, admin_delay,
    worker_coro_func, upload_folder, *args, **kwargs
):
    """🔍 Run task in thread with asyncio (ported from Main.pyw)"""
    print(f'🔍 Starting task thread: {task_id}')
    print(f'🔍 Upload folder: {upload_folder}')
    
    async def main():
        from app.telegram_routes import TASKS
        
        task = TASKS.get(task_id)
        if not task or not folder_path:
            if task:
                task["status"] = "failed"
            print(f'🔍 ❌ Task failed: No task or folder_path')
            return
        
        proxies = kwargs.get("proxies", [])
        config = args[0] if args else {}
        
        print(f'🔍 Task config: {config}')
        print(f'🔍 Using {len(proxies)} proxies')
        
        # Prepare list of tasks to run
        tasks_to_run = []
        for f in filenames:
            if not f:
                task["total"] = max(0, task["total"] - 1)
                continue
            session_file_path = os.path.join(folder_path, f)
            if os.path.exists(session_file_path):
                tasks_to_run.append((session_file_path, f))
            else:
                print(f'🔍 ⚠️  Session file not found: {f}')
        
        print(f'🔍 Tasks to run: {len(tasks_to_run)}')
        
        # Determine concurrency and batching logic based on task type
        is_seeding_task = task.get("task_name") == "seedingGroup"
        if is_seeding_task:
            group_links = config.get("group_links", [])
            if not group_links:
                task["status"] = "failed"
                task["messages"].append("Lỗi: Seeding cần ít nhất 1 link nhóm.")
                return
            concurrency = len(group_links)
            group_cycler = cycle(group_links)
            scenario_cycler = cycle(config.get("messages", []))
        else:
            concurrency = core
        
        print(f'🔍 Concurrency: {concurrency}')
        
        proxy_cycler = cycle(proxies) if proxies else cycle([None])
        admin_group_index = 0
        
        # Main execution loop, iterating in batches
        for i in range(0, len(tasks_to_run), concurrency):
            if task.get("status") == "stopped":
                print(f'🔍 ⚠️  Task stopped by user')
                break
            
            batch_files = tasks_to_run[i : i + concurrency]
            async_tasks = []
            
            print(f'🔍 Processing batch {i // concurrency + 1}, size: {len(batch_files)}')
            
            # Staggered start loop for tasks within the batch
            for session_path, filename in batch_files:
                if task.get("status") == "stopped":
                    break
                
                worker_args = []
                if is_seeding_task:
                    worker_args = [
                        next(group_cycler),
                        next(scenario_cycler),
                        config.get('send_silent', False)
                    ]
                elif args:  # For other tasks like joinGroup
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
            print(f'🔍 ✅ Batch completed')
            
            # Admin Logic after each batch (match Main.pyw line 886-904)
            if is_seeding_task and admin_enabled and task.get("status") != "stopped":
                admin_session_file = config.get("admin_session_file")
                admin_messages = config.get("admin_messages", [])
                
                # Use upload_folder parameter (match Main.pyw line 889)
                admin_folder = os.path.join(upload_folder, ADMIN_SESSION_FOLDER)
                admin_session_path = os.path.join(admin_folder, admin_session_file) if admin_session_file else None
                
                if admin_session_path and os.path.exists(admin_session_path) and admin_messages:
                    admin_target_group = group_links[admin_group_index]
                    admin_response = random.choice(admin_messages)
                    
                    if admin_delay > 0:
                        for j in range(admin_delay, 0, -1):
                            if task.get("status") == "stopped":
                                break
                            task["messages"].append(f"Admin trả lời sau... {j}s")
                            await asyncio.sleep(1)
                    
                    if task.get("status") != "stopped":
                        await run_admin_task(admin_session_path, admin_target_group, admin_response)
                        admin_group_index = (admin_group_index + 1) % len(group_links)
            
            # Delay between batches
            if i + concurrency < len(tasks_to_run) and task.get("status") != "stopped" and delay_between_batches > 0:
                for j in range(delay_between_batches, 0, -1):
                    if task.get("status") == "stopped":
                        break
                    task["messages"].append(f"Đang chờ đợt tiếp... {j}s")
                    await asyncio.sleep(1)
        
        print(f'🔍 ✅ Task completed: {task_id}')
    
    # Run in new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        from app.telegram_routes import TASKS
        task = TASKS.get(task_id)
        if task and task.get("status") != "stopped":
            task["status"] = "completed"
        loop.close()
        print(f'🔍 Task thread finished: {task_id}')

