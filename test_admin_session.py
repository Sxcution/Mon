#!/usr/bin/env python3
"""Test admin session authorization"""
import asyncio
from telethon import TelegramClient

API_ID = 28610130
API_HASH = "eda4079a5b9d4f3f88b67dacd799f902"
ADMIN_SESSION_PATH = r"C:\Users\Mon\Desktop\Mon\data\uploaded_sessions\Adminsession\84928551330.session"

async def test_admin():
    client = TelegramClient(ADMIN_SESSION_PATH, API_ID, API_HASH)
    
    try:
        await client.connect()
        print(f"Connected: {client.is_connected()}")
        
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"[OK] Admin session AUTHORIZED")
            print(f"Phone: {me.phone}")
            print(f"Name: {me.first_name} {me.last_name or ''}")
            print(f"Username: @{me.username or 'N/A'}")
        else:
            print(f"[ERROR] Admin session NOT AUTHORIZED")
            print("Session needs to be logged in again!")
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_admin())

