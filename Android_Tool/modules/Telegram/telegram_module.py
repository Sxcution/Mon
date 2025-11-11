"""
Telegram Tools Module - Seeding automation for Telegram groups
Port from TelegramSeedingTool.py with PyQt6 and native theme
"""

import os
import sys
import logging
import json
import random
import sqlite3
import re
from datetime import datetime

# Get logger for this module (will be configured by Main.pyw)
logger = logging.getLogger('telegram_module')

from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QObject, QTimer, QRect, QPoint
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTextEdit, QLabel, QFileDialog, QMessageBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QComboBox, QMenu, QStyle, QStyledItemDelegate
)
from PyQt6.QtGui import QFont, QAction, QCursor, QPainter, QPen, QColor


class CheckBoxHeader(QHeaderView):
    """Custom header with checkbox in first column and button in last column."""
    
    checkbox_clicked = pyqtSignal(bool)
    check_live_clicked = pyqtSignal()
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.is_checked = False
        self.button_hovered = False
        self.button_pressed = False
        self.setSectionsClickable(True)
        self.sectionClicked.connect(self.on_section_clicked)
        self.setMouseTracking(True)
    
    def paintSection(self, painter, rect, logicalIndex):
        """Override paint to draw checkbox in first column and button in last column."""
        painter.save()
        super().paintSection(painter, rect, logicalIndex)
        painter.restore()
        
        if logicalIndex == 0:
            # Draw checkbox
            option_rect = QRect(rect.x() + rect.width()//2 - 9, rect.y() + rect.height()//2 - 9, 18, 18)
            
            # Draw checkbox border
            painter.setPen(QPen(QColor("#555555"), 2))
            painter.setBrush(QColor("#1a1a1a"))
            painter.drawRoundedRect(option_rect, 4, 4)
            
            # Draw checkmark if checked
            if self.is_checked:
                painter.setPen(QPen(QColor("#00ff00"), 2))
                painter.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
                painter.drawText(option_rect, Qt.AlignmentFlag.AlignCenter, "✓")
        
        elif logicalIndex == 7:  # Last column - Live
            # Draw button
            button_rect = QRect(rect.x() + 5, rect.y() + 5, rect.width() - 10, rect.height() - 10)
            
            # Button color based on state
            if self.button_pressed:
                bg_color = QColor("#0d0d0d")
            elif self.button_hovered:
                bg_color = QColor("#2a2a2a")
            else:
                bg_color = QColor("#1a1a1a")
            
            painter.setPen(QPen(QColor("#333333"), 1))
            painter.setBrush(bg_color)
            painter.drawRoundedRect(button_rect, 3, 3)
            
            # Draw button text
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont('Segoe UI', 8))
            painter.drawText(button_rect, Qt.AlignmentFlag.AlignCenter, "🔍 Check Live")
    
    def mouseMoveEvent(self, event):
        """Track mouse movement for button hover effect."""
        logical_index = self.logicalIndexAt(event.pos())
        if logical_index == 7:
            rect = self.sectionViewportPosition(7)
            section_rect = QRect(rect, 0, self.sectionSize(7), self.height())
            self.button_hovered = section_rect.contains(event.pos().x(), event.pos().y())
            self.viewport().update()
        else:
            if self.button_hovered:
                self.button_hovered = False
                self.viewport().update()
        super().mouseMoveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press for button."""
        logical_index = self.logicalIndexAt(event.pos())
        if logical_index == 7:
            self.button_pressed = True
            self.viewport().update()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release for button."""
        logical_index = self.logicalIndexAt(event.pos())
        if logical_index == 7 and self.button_pressed:
            self.check_live_clicked.emit()
        self.button_pressed = False
        self.viewport().update()
        super().mouseReleaseEvent(event)
    
    def on_section_clicked(self, logicalIndex):
        """Handle section click."""
        if logicalIndex == 0:
            self.is_checked = not self.is_checked
            self.checkbox_clicked.emit(self.is_checked)
            self.viewport().update()
    
    def set_checked(self, checked):
        """Set checkbox state."""
        self.is_checked = checked
        self.viewport().update()

# Icon path
ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "icons")


class CustomCheckBox(QCheckBox):
    """Custom checkbox with green checkmark."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def paintEvent(self, event):
        """Override paint to draw custom checkmark."""
        super().paintEvent(event)
        
        if self.isChecked():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw green checkmark (✓)
            pen = QPen(QColor("#00ff00"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setFont(QFont('Segoe UI', 12, QFont.Weight.Bold))
            
            # Calculate center position
            rect = self.rect()
            text_rect = QRect(0, 0, 18, 18)  # Checkbox indicator size
            
            # Draw checkmark
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "✓")


def get_icon(icon_name):
    """Get QIcon from icons folder."""
    from PyQt6.QtGui import QIcon
    icon_path = os.path.join(ICONS_DIR, f"{icon_name}.png")
    if os.path.exists(icon_path):
        return QIcon(icon_path)
    return None

try:
    from telethon.sync import TelegramClient
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.tl.functions.messages import SendMessageRequest
    from telethon.network import ConnectionTcpAbridged
    import asyncio
    import socket
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    logger.warning("Telethon not installed. Telegram features will be disabled.")

# Configuration paths
tool_dir = os.path.dirname(os.path.abspath(__file__))
config_dir = os.path.join(tool_dir, "config")
data_dir = os.path.join(tool_dir, "data")

# Ensure directories exist
os.makedirs(config_dir, exist_ok=True)
os.makedirs(data_dir, exist_ok=True)

# Config files
seeding_config_file = os.path.join(config_dir, "seeding_config.json")
session_folder_path_file = os.path.join(config_dir, "session_folder_path.txt")
session_groups_file = os.path.join(config_dir, "session_groups.json")
admin_session_file_path = os.path.join(config_dir, "admin_session_path.txt")
admin_responses_file = os.path.join(config_dir, "admin_responses.txt")
sample_script_file = os.path.join(config_dir, "sample_script.txt")
session_cache_file = os.path.join(data_dir, "session_cache.json")  # Cache persistent cho sessions

# API ID và API Hash cố định
SCENARIO_API_ID = 28610130
SCENARIO_API_HASH = "eda4079a5b9d4f3f88b67dacd799f902"

# Default admin responses
DEFAULT_ADMIN_RESPONSES = [
    "Dạ anh check inbox ạ",
    "Dạ a kiểm tra tin nhắn nhé",
    "Anh xem tin nhắn giúp em với ạ",
    "Dạ anh vào inbox xem thông tin nhé"
]

# Emoji list for random message variation
EMOJI_LIST = ["😊", "👍", "🔥", "💥", "🚀", "💎"]

# Sample scripts
SAMPLE_SCRIPTS = [
    "Chào mọi người, mình mới tham gia nhóm, rất vui được gặp mọi người! 😊",
    "Có ai biết cách làm việc này không ạ? Mình cần hỗ trợ chút xíu! 🙏",
    "Nhóm mình đông vui quá, có ai muốn giao lưu không nhỉ? 🔥",
    "Mình vừa tìm được một mẹo hay, ai muốn mình chia sẻ không? 🚀"
]

def save_seeding_config(group_links, delay_time, admin_delay_time, random_delay, scenario_text="", group_join_links="", 
                        auto_schedule=False, schedule_time="18:00", selected_group="Tất cả sessions"):
    config = {
        "group_links": group_links,
        "delay_time": delay_time,
        "admin_delay_time": admin_delay_time,
        "random_delay": random_delay,
        "scenario_text": scenario_text,
        "group_join_links": group_join_links,
        "auto_schedule": auto_schedule,
        "schedule_time": schedule_time,
        "selected_group": selected_group  # Lưu nhóm đã chọn
    }
    try:
        with open(seeding_config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        # Removed auto-save log to reduce spam
    except Exception as e:
        logger.error(f"Lỗi khi lưu seeding config: {str(e)}")

def save_session_groups(session_groups):
    """Save session groups to file."""
    try:
        with open(session_groups_file, "w", encoding="utf-8") as f:
            json.dump(session_groups, f, indent=4, ensure_ascii=False)
        logger.info(f"💾 Đã lưu {len(session_groups)} nhóm session")
    except Exception as e:
        logger.error(f"❌ Lỗi khi lưu session groups: {str(e)}")

def load_session_groups():
    """Load session groups from file."""
    if os.path.exists(session_groups_file):
        try:
            with open(session_groups_file, "r", encoding="utf-8") as f:
                groups = json.load(f)
            logger.info(f"📂 Đã load {len(groups)} nhóm session")
            return groups
        except Exception as e:
            logger.error(f"❌ Lỗi khi load session groups: {str(e)}")
    return {}

def load_seeding_config():
    default_config = {
        "group_links": [], 
        "delay_time": "600", 
        "admin_delay_time": "20", 
        "random_delay": False,
        "scenario_text": "",
        "group_join_links": "",
        "auto_schedule": False,
        "schedule_time": "18:00",
        "selected_group": "Tất cả sessions"  # Lưu nhóm đã chọn
    }
    if not os.path.exists(seeding_config_file):
        return default_config
    try:
        with open(seeding_config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        for key in default_config:
            if key not in config:
                config[key] = default_config[key]
        return config
    except Exception as e:
        logger.error(f"Lỗi khi đọc seeding config: {str(e)}")
        return default_config

def save_admin_responses(responses):
    try:
        with open(admin_responses_file, "w", encoding="utf-8") as f:
            f.write(responses)
    except Exception as e:
        logger.error(f"Lỗi khi lưu admin responses: {str(e)}")

def save_session_cache(session_cache):
    """Save session cache to file."""
    try:
        with open(session_cache_file, "w", encoding="utf-8") as f:
            json.dump(session_cache, f, indent=4, ensure_ascii=False)
        # logger.debug(f"💾 Đã lưu cache cho {len(session_cache)} sessions")
    except Exception as e:
        logger.error(f"❌ Lỗi khi lưu session cache: {str(e)}")

def load_session_cache():
    """Load session cache from file."""
    if os.path.exists(session_cache_file):
        try:
            with open(session_cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
            logger.info(f"📂 Đã load cache cho {len(cache)} sessions")
            return cache
        except Exception as e:
            logger.error(f"❌ Lỗi khi load session cache: {str(e)}")
    return {}

# Worker QThread: Joining Groups
class JoinGroupWorker(QObject):
    update_message = pyqtSignal(str, str)  # (message, color)
    finished = pyqtSignal(int, int)  # (successful_joins, failed_joins)
    progress = pyqtSignal(int, int)  # (current, total)
    update_session_status = pyqtSignal(int, str, str, str, str, str, str)  # row, phone, full_name, username, message, status, session_path

    def __init__(self, session_paths, group_links, delay_time, random_delay):
        super().__init__()
        self.session_paths = session_paths  # List of full session paths
        self.group_links = group_links
        self.delay_time = delay_time
        self.random_delay = random_delay
        self.is_running = False
        self.should_stop = False

    def get_delay(self, base_delay):
        if self.random_delay:
            return random.uniform(base_delay * 0.8, base_delay * 1.2)
        return base_delay

    async def join_group(self, session_path, api_id, api_hash, group_link):
        client = TelegramClient(session_path, api_id, api_hash, connection=ConnectionTcpAbridged)
        await client.connect()

        if not await client.is_user_authorized():
            logger.error(f"Session {session_path} không hợp lệ!")
            return False

        try:
            await client(JoinChannelRequest(group_link))
            logger.info(f"Đã tham gia nhóm {group_link} từ session {session_path}")
            await client.disconnect()
            return True
        except Exception as e:
            logger.error(f"Không thể tham gia nhóm {group_link}: {str(e)}")
            return False

    async def run_async(self):
        if self.is_running:
            return
        self.is_running = True

        try:
            if not self.session_paths:
                self.update_message.emit("Không có session nào được chọn!", "red")
                self.is_running = False
                return

            if not self.group_links:
                self.update_message.emit("Không có link nhóm nào hợp lệ!", "red")
                self.is_running = False
                return

            self.update_message.emit(f"Đang tham gia các nhóm với {len(self.session_paths)} sessions...", "blue")

            api_id = SCENARIO_API_ID
            api_hash = SCENARIO_API_HASH

            successful_joins = 0
            failed_joins = 0
            total_joins_needed = len(self.group_links) * len(self.session_paths)
            current_join = 0

            for idx, session_path in enumerate(self.session_paths):
                if self.should_stop:
                    break

                # Lấy thông tin thật từ Telegram
                try:
                    client = TelegramClient(session_path, api_id, api_hash, connection=ConnectionTcpAbridged)
                    await client.connect()
                    
                    if await client.is_user_authorized():
                        me = await client.get_me()
                        phone_number = me.phone if me.phone else "N/A"
                        full_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "N/A"
                        username = f"@{me.username}" if me.username else ""
                    else:
                        phone_number = "N/A"
                        full_name = "N/A"
                        username = ""
                    
                    await client.disconnect()
                except Exception as e:
                    logger.error(f"Lỗi lấy thông tin session: {e}")
                    phone_number = "N/A"
                    full_name = "N/A"
                    username = ""

                for group_link in self.group_links:
                    if self.should_stop:
                        break

                    current_join += 1
                    self.progress.emit(current_join, total_joins_needed)
                    self.update_session_status.emit(
                        idx, phone_number, full_name, username,
                        "Tham gia nhóm", "Đang xử lý...", session_path
                    )

                    result = await self.join_group(session_path, api_id, api_hash, group_link)

                    if result:
                        successful_joins += 1
                        self.update_session_status.emit(
                            idx, phone_number, full_name, username,
                            "Tham gia nhóm", "Hoàn Thành!", session_path
                        )
                    else:
                        failed_joins += 1
                        self.update_session_status.emit(
                            idx, phone_number, full_name, username,
                            "Tham gia nhóm", "Thất bại!", session_path
                        )

                    # Apply delay
                    if current_join < total_joins_needed and not self.should_stop:
                        delay = self.get_delay(self.delay_time)
                        remaining_delay = delay
                        while remaining_delay > 0 and not self.should_stop:
                            self.update_message.emit(f"Chờ tham gia tiếp theo... Còn {int(remaining_delay)} giây", "blue")
                            await asyncio.sleep(1)
                            remaining_delay -= 1

            self.update_message.emit(f"Hoàn tất tham gia nhóm! Thành công: {successful_joins}, Thất bại: {failed_joins}", "green")
            self.finished.emit(successful_joins, failed_joins)
        finally:
            self.is_running = False

    @pyqtSlot()
    def run(self):
        asyncio.run(self.run_async())

    @pyqtSlot()
    def stop(self):
        self.should_stop = True


# Worker QThread: Seeding Process
class SeedingWorker(QObject):
    update_message = pyqtSignal(str, str)
    finished = pyqtSignal(int, int)
    progress = pyqtSignal(int, int)
    update_session_status = pyqtSignal(int, str, str, str, str, str, str)  # row, phone, full_name, username, message, status, session_path

    def __init__(self, session_paths, admin_session_path, group_links, scenario_lines, 
                 delay_time, admin_delay_time, admin_response_lines, random_delay, randomize_message):
        super().__init__()
        self.session_paths = session_paths  # List of full session paths
        self.admin_session_path = admin_session_path
        self.group_links = group_links
        self.scenario_lines = scenario_lines
        self.delay_time = delay_time
        self.admin_delay_time = admin_delay_time
        self.admin_response_lines = admin_response_lines
        self.random_delay = random_delay
        self.randomize_message = randomize_message
        self.is_running = False
        self.should_stop = False
        self.current_session_index = 0

    async def run_session(self, session_path, api_id, api_hash, group_link, message):
        client = TelegramClient(session_path, api_id, api_hash, connection=ConnectionTcpAbridged)
        await client.connect()

        if not await client.is_user_authorized():
            logger.error(f"Session {session_path} không hợp lệ!")
            return None

        try:
            await client(JoinChannelRequest(group_link))
            result = await client.send_message(group_link, message)
            message_id = result.id
            logger.info(f"Đã gửi tin nhắn '{message}' tới nhóm {group_link}")
            await client.disconnect()
            return message_id
        except Exception as e:
            logger.error(f"Không thể gửi tin nhắn tới nhóm {group_link}: {str(e)}")
            return None

    async def run_admin_session(self, session_path, api_id, api_hash, group_link, message):
        """Admin task - giống tool cũ: mở, gửi, đóng"""
        client = None
        try:
            client = TelegramClient(session_path, api_id, api_hash)
            await client.connect()

            if not await client.is_user_authorized():
                logger.error(f"Session Admin không hợp lệ!")
                return False

            # Ensure admin is in the group
            try:
                await client(JoinChannelRequest(group_link))
            except Exception as join_error:
                # Might be already in channel
                logger.info(f"Admin join error (might be already in): {join_error}")
            
            await client.send_message(group_link, message)
            logger.info(f"Admin đã gửi tin nhắn '{message}' tới nhóm {group_link}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi chạy session Admin: {str(e)}")
            return False
        finally:
            if client and client.is_connected():
                await client.disconnect()
    
    async def seeding_worker(self, row_index, session_path, group_link, message, api_id, api_hash):
        """Seeding worker - giống tool cũ: mở, join, gửi, đóng"""
        client = None
        status = {
            "is_live": False,
            "full_name": "Lỗi",
            "username": "",
            "status_text": "Lỗi seeding",
            "phone": "N/A"
        }
        
        try:
            client = TelegramClient(session_path, api_id, api_hash, connection=ConnectionTcpAbridged)
            await client.connect()
            
            if not await client.is_user_authorized():
                status["status_text"] = "Session die"
                self.update_session_status.emit(
                    row_index, status["phone"], status["full_name"], status["username"],
                    "Gửi tin nhắn", status["status_text"], session_path
                )
                return False
            
            # Lấy thông tin user
            me = await client.get_me()
            status["is_live"] = True
            status["phone"] = me.phone if me.phone else "N/A"
            status["full_name"] = f"{me.first_name or ''} {me.last_name or ''}".strip() or "N/A"
            status["username"] = f"@{me.username}" if me.username else ""
            
            # Update UI: Đang xử lý
            self.update_session_status.emit(
                row_index, status["phone"], status["full_name"], status["username"],
                "Gửi tin nhắn", "Đang xử lý...", session_path
            )
            
            # Join group
            try:
                await client(JoinChannelRequest(group_link))
            except Exception:
                pass  # Continue even if join fails
            
            # Send message
            await client.send_message(group_link, message)
            status["status_text"] = "Đã gửi tin nhắn"
            
            # Update UI: Hoàn thành
            self.update_session_status.emit(
                row_index, status["phone"], status["full_name"], status["username"],
                "Gửi tin nhắn", "Hoàn Thành!", session_path
            )
            return True
            
        except Exception as e:
            status["status_text"] = str(e)[:50]
            # Update UI: Thất bại
            self.update_session_status.emit(
                row_index, status["phone"], status["full_name"], status["username"],
                "Gửi tin nhắn", f"Thất bại: {status['status_text']}", session_path
            )
            return False
        finally:
            if client and client.is_connected():
                await client.disconnect()

    def get_delay(self, base_delay):
        if self.random_delay:
            return random.uniform(base_delay * 0.8, base_delay * 1.2)
        return base_delay

    def randomize_message_content(self, message):
        if random.random() < 0.5:
            message += " " + random.choice(EMOJI_LIST)
        if random.random() < 0.3:
            message = message.replace("ạ", "a").replace("A", "a")
        return message

    async def run_async(self):
        if self.is_running:
            return
        self.is_running = True

        try:
            if not self.session_paths:
                self.update_message.emit("Không có session nào được chọn!", "red")
                self.is_running = False
                return

            if not self.scenario_lines:
                self.update_message.emit("Không có dòng kịch bản nào hợp lệ!", "red")
                self.is_running = False
                return

            if not self.group_links:
                self.update_message.emit("Không có link nhóm nào hợp lệ!", "red")
                self.is_running = False
                return

            # Verify admin session (giống tool cũ)
            admin_session_path = None
            if self.admin_session_path:
                try:
                    # Verify admin session is valid
                    test_client = TelegramClient(self.admin_session_path, SCENARIO_API_ID, SCENARIO_API_HASH)
                    await test_client.connect()
                    if not await test_client.is_user_authorized():
                        await test_client.disconnect()
                        self.update_message.emit("Session Admin không hợp lệ!", "red")
                        self.is_running = False
                        return
                    await test_client.disconnect()
                    admin_session_path = self.admin_session_path
                    self.update_message.emit("✅ Admin session đã sẵn sàng", "green")
                except Exception as e:
                    self.update_message.emit(f"Lỗi khi khởi tạo session Admin: {str(e)}", "red")
                    self.is_running = False
                    return

            # ===== LOGIC GIỐNG 100% TOOL CŨ =====
            self.update_message.emit(f"Đang chạy seeding với {len(self.session_paths)} sessions...", "blue")

            api_id = SCENARIO_API_ID
            api_hash = SCENARIO_API_HASH
            
            # Batch theo SỐ GROUPS (giống tool cũ)
            concurrency = len(self.group_links)
            successful_runs = 0
            failed_runs = 0
            
            # Shuffle sessions
            session_paths_shuffled = self.session_paths.copy()
            random.shuffle(session_paths_shuffled)
            
            # Cycler for groups and scenarios (giống tool cũ)
            from itertools import cycle
            group_cycler = cycle(self.group_links)
            scenario_cycler = cycle(self.scenario_lines)
            admin_group_index = 0
            
            # Chia sessions thành batches (giống tool cũ)
            total_batches = (len(session_paths_shuffled) + concurrency - 1) // concurrency
            
            for batch_idx in range(total_batches):
                if self.should_stop:
                    break
                
                # Lấy batch sessions
                start_idx = batch_idx * concurrency
                end_idx = min(start_idx + concurrency, len(session_paths_shuffled))
                batch_sessions = session_paths_shuffled[start_idx:end_idx]
                
                self.progress.emit(end_idx, len(session_paths_shuffled))
                
                # Tạo tasks với delay giữa sessions (staggered start - giống tool cũ)
                async_tasks = []
                for i, session_path in enumerate(batch_sessions):
                    if self.should_stop:
                        break
                    
                    # Lấy group và message cho session này
                    group_link = next(group_cycler)
                    message = next(scenario_cycler)
                    if self.randomize_message:
                        message = self.randomize_message_content(message)
                    
                    # Tạo task
                    task = self.seeding_worker(
                        start_idx + i, session_path, group_link, message, 
                        api_id, api_hash
                    )
                    async_tasks.append(asyncio.create_task(task))
                    
                    # Delay giữa sessions TRONG batch (staggered start)
                    if self.delay_time > 0 and i < len(batch_sessions) - 1:
                        delay = self.get_delay(self.delay_time / concurrency)
                        await asyncio.sleep(delay)
                
                # Chờ TẤT CẢ tasks trong batch hoàn thành (giống tool cũ)
                results = await asyncio.gather(*async_tasks, return_exceptions=True)
                
                # Count results
                for result in results:
                    if isinstance(result, Exception) or result is False:
                        failed_runs += 1
                    else:
                        successful_runs += 1
                
                # Admin logic sau mỗi batch (giống tool cũ)
                if admin_session_path and not self.should_stop:
                    admin_target_group = self.group_links[admin_group_index]
                    admin_response = random.choice(self.admin_response_lines)
                    
                    # Admin delay countdown
                    if self.admin_delay_time > 0:
                        admin_delay = self.get_delay(self.admin_delay_time)
                        remaining = int(admin_delay)
                        while remaining > 0 and not self.should_stop:
                            self.update_message.emit(f"Admin trả lời sau... {remaining}s", "blue")
                            await asyncio.sleep(1)
                            remaining -= 1
                    
                    if not self.should_stop:
                        try:
                            await self.run_admin_session(
                                admin_session_path, SCENARIO_API_ID, SCENARIO_API_HASH,
                                admin_target_group, admin_response
                            )
                            self.update_message.emit(f"✅ Admin đã gửi tin nhắn tới {admin_target_group}", "green")
                            admin_group_index = (admin_group_index + 1) % len(self.group_links)
                        except Exception as e:
                            self.update_message.emit(f"❌ Admin gửi thất bại: {str(e)}", "red")
                
                # Delay giữa các batches
                if batch_idx < total_batches - 1 and not self.should_stop:
                    delay = self.get_delay(self.delay_time)
                    remaining_delay = int(delay)
                    while remaining_delay > 0 and not self.should_stop:
                        self.update_message.emit(f"Đang chờ đợt tiếp... {remaining_delay}s", "blue")
                        await asyncio.sleep(1)
                        remaining_delay -= 1
            
            # Kết thúc
            self.update_message.emit(
                f"=============================="
                f"\n🎉 HOÀN TẤT SEEDING"
                f"\n✅ Thành công: {successful_runs}/{len(session_paths_shuffled)}"
                f"\n❌ Thất bại: {failed_runs}/{len(session_paths_shuffled)}"
                f"\n📊 Tỷ lệ thành công: {successful_runs/len(session_paths_shuffled)*100:.1f}%"
                f"\n==============================", 
                "green"
            )
            self.finished.emit(successful_runs, failed_runs)
        finally:
            self.is_running = False

    @pyqtSlot()
    def run(self):
        asyncio.run(self.run_async())

    @pyqtSlot()
    def stop(self):
        self.should_stop = True


# Worker QThread: Check Live Sessions
class CheckLiveWorker(QObject):
    update_session_info = pyqtSignal(int, str, str, str, str, str)  # row, phone, full_name, username, status, session_path
    finished = pyqtSignal(int, int)  # live_count, die_count
    progress_update = pyqtSignal(int, int)  # current, total
    
    def __init__(self, session_data_list):
        super().__init__()
        self.session_data_list = session_data_list  # List of (row, session_data) tuples
        self.should_stop = False
    
    def stop(self):
        self.should_stop = True
    
    async def check_single_session(self, row, session_data):
        """Check a single session."""
        session_path = session_data['session_path']
        
        client = TelegramClient(session_path, SCENARIO_API_ID, SCENARIO_API_HASH, connection=ConnectionTcpAbridged)
        try:
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                phone = me.phone if me.phone else "N/A"
                full_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "N/A"
                username = f"@{me.username}" if me.username else ""
                return row, phone, full_name, username, "✅ Live", session_path
            else:
                return row, "N/A", "N/A", "", "❌ Die", session_path
        except Exception as e:
            return row, "N/A", "N/A", "", f"❌ Die", session_path
        finally:
            await client.disconnect()
    
    def run(self):
        """Check all sessions."""
        import asyncio
        
        live_count = 0
        die_count = 0
        total = len(self.session_data_list)
        
        for idx, (row, session_data) in enumerate(self.session_data_list):
            if self.should_stop:
                break
            
            try:
                # Create new event loop for each session
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Check session
                row_result, phone, full_name, username, status, session_path = loop.run_until_complete(
                    self.check_single_session(row, session_data)
                )
                
                loop.close()
                
                # Emit result
                self.update_session_info.emit(row_result, phone, full_name, username, status, session_path)
                
                # Update counters
                if "Live" in status:
                    live_count += 1
                    logger.info(f"✅ Session {idx+1}/{total}: Live - {phone} ({full_name}) {username}" if username else f"✅ Session {idx+1}/{total}: Live - {phone} ({full_name})")
                else:
                    die_count += 1
                    logger.info(f"❌ Session {idx+1}/{total}: Die")
                
                # Emit progress
                self.progress_update.emit(idx + 1, total)
                
            except Exception as e:
                logger.error(f"❌ Lỗi khi check session {session_data.get('session_file', 'unknown')}: {str(e)}")
                die_count += 1
        
        # Emit finished
        self.finished.emit(live_count, die_count)


# Main Telegram Widget with Seeding tab
class TelegramToolWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Initialize variables
        self.session_folder_path = None
        self.admin_session_path = None
        self.session_data = []
        
        # Cache để lưu trạng thái session (key = session_path, value = dict với phone, username, live, etc.)
        # Load từ file persistent
        self.session_cache = load_session_cache()
        
        self.seeding_thread = QThread()
        self.join_group_thread = QThread()
        self.check_live_thread = QThread()
        self.seeding_worker = None
        self.join_group_worker = None
        self.check_live_worker = None
        
        # Auto scheduler variables
        self.scheduler_timer = None
        self.scheduler_enabled = False
        self.last_run_date = None  # Track last run to avoid running multiple times
        
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Input field style
        input_style = "QLineEdit, QTextEdit { border: 1px solid #555; padding: 4px; border-radius: 3px; }"
        
        # ===== MAIN TABS (Manager, Seeding, Group) - Ngay dưới tab chính =====
        self.tabs = QTabWidget()
        
        # Tăng chiều cao tab con +10% bằng padding (từ 8px -> 9px) + Modern styling với viền xeon
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 9px 16px;
                margin-right: 3px;
                margin-top: 2px;
                border-radius: 6px;
                background-color: #2d2d2d;
                color: #aaaaaa;
                border: 2px solid #404040;
                outline: none !important;
            }
            
            QTabBar::tab:selected {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 2px solid #00aaff !important;
                box-shadow: 0 0 10px #00aaff, inset 0 0 5px #00aaff;
                outline: none !important;
            }
            
            QTabBar::tab:hover:!selected {
                background-color: #353535;
                color: #dddddd;
                border: 2px solid #555555;
            }
            
            QTabBar::tab:focus {
                outline: none !important;
            }
        """)
        
        # Manager Tab
        self.manager_tab = QWidget()
        self.init_manager_tab()
        manager_icon = get_icon('manager')
        if manager_icon:
            self.tabs.addTab(self.manager_tab, manager_icon, "Manager")
        else:
            self.tabs.addTab(self.manager_tab, "📊 Manager")
        
        # Seeding Tab
        self.seeding_content_tab = QWidget()
        self.init_seeding_content_tab(input_style)
        # Try message.png first, fallback to messenger.png
        seeding_icon = get_icon('message') or get_icon('messenger')
        if seeding_icon:
            self.tabs.addTab(self.seeding_content_tab, seeding_icon, "Seeding")
        else:
            self.tabs.addTab(self.seeding_content_tab, "🌱 Seeding")
        
        # Group Tab
        self.group_tab = QWidget()
        self.init_group_tab(input_style)
        group_icon = get_icon('group')
        if group_icon:
            self.tabs.addTab(self.group_tab, group_icon, "Group")
        else:
            self.tabs.addTab(self.group_tab, "👥 Group")
        
        layout.addWidget(self.tabs)
        
        # ===== CONTROL BAR (Single row) - Dưới tabs =====
        control_row = QHBoxLayout()
        
        # Left side: Run button + Delay settings
        self.run_stop_btn = QPushButton("▶️ Run")
        self.run_stop_btn.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        self.run_stop_btn.clicked.connect(self.toggle_run_stop)
        self.run_stop_btn.setMinimumWidth(100)
        control_row.addWidget(self.run_stop_btn)
        
        control_row.addWidget(QLabel("|"))
        
        control_row.addWidget(QLabel("Delay (s):"))
        self.delay_time_line = QLineEdit()
        self.delay_time_line.setPlaceholderText("600")
        self.delay_time_line.setMaximumWidth(60)
        self.delay_time_line.setStyleSheet(input_style)
        control_row.addWidget(self.delay_time_line)
        
        control_row.addWidget(QLabel("Admin Delay:"))
        self.admin_delay_time_line = QLineEdit()
        self.admin_delay_time_line.setPlaceholderText("20")
        self.admin_delay_time_line.setMaximumWidth(60)
        self.admin_delay_time_line.setStyleSheet(input_style)
        control_row.addWidget(self.admin_delay_time_line)
        
        self.random_delay_checkbox = QCheckBox("☐ Random ±20%")
        control_row.addWidget(self.random_delay_checkbox)
        
        control_row.addWidget(QLabel("|"))
        
        # Right side: Session management (after Random)
        self.session_btn = QPushButton("📁 Session")
        self.session_btn.setMinimumWidth(100)
        self.session_btn.clicked.connect(self.show_session_menu)
        control_row.addWidget(self.session_btn)
        
        control_row.addWidget(QLabel("Nhóm:"))
        self.session_group_combo = QComboBox()
        self.session_group_combo.setMinimumWidth(120)
        self.session_group_combo.addItem("Tất cả sessions")
        self.session_group_combo.setStyleSheet("QComboBox { border: 1px solid #555; padding: 4px; border-radius: 3px; }")
        self.session_group_combo.currentTextChanged.connect(self.on_group_changed)
        control_row.addWidget(self.session_group_combo)
        
        # Spacer at the end
        control_row.addStretch()
        
        layout.addLayout(control_row)
        
        # Status label (shared)
        self.status_label = QLabel("")
        self.status_label.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        layout.addWidget(self.status_label)
        
        # Initialize state
        self.is_running = False
        self.session_folder_path = ""
        self.admin_session_path = ""
        self.session_groups = {}  # {group_name: [session_files]}
    
    def init_manager_tab(self):
        """Tab Manager - Hiển thị session table."""
        layout = QVBoxLayout(self.manager_tab)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Session table
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(8)  # Checkbox + STT + 6 columns
        
        # Set custom header with checkbox and Check Live button
        self.custom_header = CheckBoxHeader(Qt.Orientation.Horizontal, self.session_table)
        self.session_table.setHorizontalHeader(self.custom_header)
        self.custom_header.checkbox_clicked.connect(self.on_header_checkbox_clicked)
        self.custom_header.check_live_clicked.connect(self.check_live_sessions)
        
        self.session_table.setHorizontalHeaderLabels(["", "STT", "SĐT", "Name", "Username", "Message", "Status", "Live"])
        
        # Hide vertical header (row numbers on the left)
        self.session_table.verticalHeader().setVisible(False)
        
        # Set column widths
        self.session_table.setColumnWidth(0, 30)  # Checkbox column (giảm xuống 30px)
        self.session_table.setColumnWidth(1, 50)  # STT column (fixed width)
        self.custom_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.custom_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.custom_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.custom_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.custom_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.custom_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.custom_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.custom_header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        
        # Add table and make it expand to fill all space
        layout.addWidget(self.session_table, 1)  # stretch factor = 1
    
    def init_seeding_content_tab(self, input_style):
        """Tab Seeding - Scenario, Group links, Admin responses."""
        layout = QVBoxLayout(self.seeding_content_tab)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Group links
        layout.addWidget(QLabel("Link nhóm Telegram (mỗi dòng một link):"))
        self.group_links_text = QTextEdit()
        self.group_links_text.setPlaceholderText("https://t.me/...\nhttps://t.me/...")
        self.group_links_text.setMaximumHeight(60)
        self.group_links_text.setStyleSheet(input_style)
        layout.addWidget(self.group_links_text)
        
        # ===== HEADERS ROW (Kịch bản + buttons | Admin + button) =====
        headers_row = QHBoxLayout()
        
        # Left side: Scenario header + buttons
        scenario_header = QHBoxLayout()
        scenario_header.addWidget(QLabel("Kịch bản (mỗi dòng một nội dung):"))
        gen_btn = QPushButton("🎲 Tạo Kịch Bản")
        gen_btn.setMaximumWidth(130)
        gen_btn.clicked.connect(self.generate_scenario)
        scenario_header.addWidget(gen_btn)
        save_btn = QPushButton("💾 Lưu Mẫu")
        save_btn.setMaximumWidth(100)
        save_btn.clicked.connect(self.save_scenario)
        scenario_header.addWidget(save_btn)
        scenario_header.addStretch()
        headers_row.addLayout(scenario_header, 5)
        
        # Right side: Admin header + button
        admin_header = QHBoxLayout()
        admin_header.addWidget(QLabel("Nội dung Admin trả lời:"))
        save_admin_btn = QPushButton("💾 Lưu")
        save_admin_btn.setMaximumWidth(80)
        save_admin_btn.clicked.connect(self.save_admin_responses)
        admin_header.addWidget(save_admin_btn)
        admin_header.addStretch()
        headers_row.addLayout(admin_header, 5)
        
        layout.addLayout(headers_row)
        
        # ===== TEXT AREAS ROW (Scenario | Admin Response) =====
        text_areas_row = QHBoxLayout()
        
        # Left: Scenario text
        self.scenario_text = QTextEdit()
        self.scenario_text.setPlaceholderText("Nhập nội dung...")
        self.scenario_text.setStyleSheet(input_style)
        text_areas_row.addWidget(self.scenario_text, 5)
        
        # Right: Admin response text
        self.admin_response_text = QTextEdit()
        self.admin_response_text.setPlaceholderText("Mỗi dòng một nội dung trả lời...")
        self.admin_response_text.setStyleSheet(input_style)
        text_areas_row.addWidget(self.admin_response_text, 5)
        
        layout.addLayout(text_areas_row)
        
        # Options
        options_layout = QHBoxLayout()
        self.randomize_message_checkbox = QCheckBox("☐ Random tin nhắn (thêm emoji)")
        options_layout.addWidget(self.randomize_message_checkbox)
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # ===== AUTO SCHEDULER =====
        scheduler_box = QHBoxLayout()
        scheduler_box.addWidget(QLabel("⏰ Lịch tự động:"))
        
        self.auto_schedule_checkbox = QCheckBox("Bật lịch tự động")
        self.auto_schedule_checkbox.stateChanged.connect(self.toggle_scheduler)
        scheduler_box.addWidget(self.auto_schedule_checkbox)
        
        scheduler_box.addWidget(QLabel("Giờ chạy:"))
        self.schedule_time_edit = QLineEdit()
        self.schedule_time_edit.setPlaceholderText("18:00")
        self.schedule_time_edit.setMaximumWidth(60)
        self.schedule_time_edit.setStyleSheet(input_style)
        self.schedule_time_edit.textChanged.connect(self.save_config)
        scheduler_box.addWidget(self.schedule_time_edit)
        
        self.schedule_status_label = QLabel("Chưa kích hoạt")
        self.schedule_status_label.setStyleSheet("color: #888;")
        scheduler_box.addWidget(self.schedule_status_label)
        
        scheduler_box.addStretch()
        layout.addLayout(scheduler_box)
        
        layout.addStretch()
    
    def init_group_tab(self, input_style):
        """Tab Group - Join group functionality."""
        layout = QVBoxLayout(self.group_tab)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        layout.addWidget(QLabel("Link nhóm Telegram để tham gia (mỗi dòng một link):"))
        self.group_join_links_text = QTextEdit()
        self.group_join_links_text.setPlaceholderText("https://t.me/...\nhttps://t.me/...")
        self.group_join_links_text.setMaximumHeight(150)
        self.group_join_links_text.setStyleSheet(input_style)
        layout.addWidget(self.group_join_links_text)
        
        info_label = QLabel("💡 Tip: Nhập link nhóm và nhấn Run để tự động tham gia nhóm bằng tất cả session.")
        info_label.setStyleSheet("padding: 10px; border: 1px solid #555; border-radius: 5px; color: #888;")
        layout.addWidget(info_label)
        
        layout.addStretch()
    
    def show_session_menu(self):
        """Show session management menu."""
        menu = QMenu(self)
        
        add_folder_action = QAction("📂 Thêm Thư Mục Session", self)
        add_folder_action.triggered.connect(self.select_session_folder)
        menu.addAction(add_folder_action)
        
        admin_session_action = QAction("👤 Session Admin", self)
        admin_session_action.triggered.connect(self.select_admin_session)
        menu.addAction(admin_session_action)
        
        menu.addSeparator()
        
        manage_groups_action = QAction("⚙️ Quản lý Nhóm Session", self)
        manage_groups_action.triggered.connect(self.manage_session_groups)
        menu.addAction(manage_groups_action)
        
        menu.exec(QCursor.pos())
    
    def toggle_run_stop(self):
        """Toggle between Run and Stop."""
        if self.is_running:
            # Currently running → Stop
            self.stop_current_task()
        else:
            # Currently stopped → Run based on active tab
            self.run_current_tab()
    
    def run_current_tab(self):
        """Run task based on currently active tab."""
        current_tab_index = self.tabs.currentIndex()
        current_tab_text = self.tabs.tabText(current_tab_index)
        
        if "Manager" in current_tab_text:
            logger.info("ℹ️ Tab Manager chỉ để xem thông tin session, không có tác vụ để chạy")
            QMessageBox.information(self, "Manager", "Tab Manager chỉ để xem thông tin session.")
            return
        elif "Seeding" in current_tab_text:
            logger.info("▶️ Bắt đầu chạy Seeding...")
            self.run_seeding()
        elif "Group" in current_tab_text:
            logger.info("▶️ Bắt đầu chạy Join Group...")
            self.run_join_group()
    
    def stop_current_task(self):
        """Stop current running task."""
        self.stop_seeding()
        self.is_running = False
        self.run_stop_btn.setText("▶️ Run")
        self.run_stop_btn.setStyleSheet("")
    
    def select_session_folder(self):
        """Add session folder to a group."""
        folder_path = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Session")
        if not folder_path:
            return
        
        # Ask for group name
        from PyQt6.QtWidgets import QInputDialog
        group_name, ok = QInputDialog.getText(
            self, "Tên Nhóm Session", 
            "Nhập tên nhóm (ví dụ: M1, M2, VIP...):",
            text=os.path.basename(folder_path)
        )
        
        if ok and group_name:
            # Add sessions from folder to group
            try:
                session_files = [f for f in os.listdir(folder_path) if f.endswith(".session")]
                if not session_files:
                    QMessageBox.warning(self, "Lỗi", "Thư mục không chứa file .session nào!")
                    return
                
                # Store full paths
                session_paths = [os.path.join(folder_path, f) for f in session_files]
                self.session_groups[group_name] = session_paths
                
                # Save session groups to file
                save_session_groups(self.session_groups)
                
                # Update combo box
                if self.session_group_combo.findText(group_name) == -1:
                    self.session_group_combo.addItem(group_name)
                
                # Save to file (for backward compatibility)
                self.session_folder_path = folder_path
                with open(session_folder_path_file, "w", encoding="utf-8") as f:
                    f.write(folder_path)
                
                # Reload table
                self.load_sessions_to_table()
                
                logger.info(f"✅ Đã thêm nhóm '{group_name}' với {len(session_files)} sessions")
                QMessageBox.information(self, "Thành công", 
                    f"Đã thêm {len(session_files)} sessions vào nhóm '{group_name}'!")
                    
            except Exception as e:
                logger.error(f"❌ Lỗi khi tải session: {str(e)}")
                QMessageBox.critical(self, "Lỗi", f"Lỗi khi tải session: {str(e)}")
    
    def manage_session_groups(self):
        """Manage session groups - view/delete groups."""
        if not self.session_groups:
            QMessageBox.information(self, "Thông báo", "Chưa có nhóm session nào. Hãy thêm thư mục session trước!")
            return
        
        # Create dialog
        from PyQt6.QtWidgets import QDialog, QListWidget, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle("📂 Quản lý Nhóm Session")
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(300)
        
        layout = QVBoxLayout(dialog)
        
        # Info label
        info_label = QLabel(f"📊 Tổng số nhóm: {len(self.session_groups)}")
        info_label.setStyleSheet("padding: 8px; font-weight: bold;")
        layout.addWidget(info_label)
        
        # List widget
        list_widget = QListWidget()
        for group_name, sessions in self.session_groups.items():
            list_widget.addItem(f"📁 {group_name} ({len(sessions)} sessions)")
        layout.addWidget(list_widget)
        
        # Delete button
        delete_btn = QPushButton("❌ Xóa Nhóm Đã Chọn")
        delete_btn.clicked.connect(lambda: self.delete_selected_group(list_widget, dialog))
        layout.addWidget(delete_btn)
        
        # Close button
        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()
    
    def delete_selected_group(self, list_widget, dialog):
        """Delete selected session group."""
        current_item = list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(dialog, "Lỗi", "Vui lòng chọn nhóm cần xóa!")
            return
        
        # Extract group name from list item text
        item_text = current_item.text()  # "📁 GroupName (5 sessions)"
        group_name = item_text.split("📁 ")[1].split(" (")[0]
        
        # Confirm deletion
        reply = QMessageBox.question(
            dialog, "Xác nhận xóa",
            f"Bạn có chắc muốn xóa nhóm '{group_name}'?\n\n⚠️ Lưu ý: Chỉ xóa nhóm, không xóa file session gốc.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from session_groups
            del self.session_groups[group_name]
            
            # Save to file
            save_session_groups(self.session_groups)
            
            # Remove from combo box
            index = self.session_group_combo.findText(group_name)
            if index != -1:
                self.session_group_combo.removeItem(index)
            
            # Remove from list widget
            list_widget.takeItem(list_widget.currentRow())
            
            # Reload table
            self.load_sessions_to_table()
            
            logger.info(f"🗑️ Đã xóa nhóm session: {group_name}")
            QMessageBox.information(dialog, "Thành công", f"Đã xóa nhóm '{group_name}'!")
    
    def on_header_checkbox_clicked(self, checked):
        """Handle header checkbox click - toggle all session checkboxes."""
        for row in range(self.session_table.rowCount()):
            checkbox_widget = self.session_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(CustomCheckBox)
                if checkbox:
                    checkbox.setChecked(checked)
    
    def toggle_all_sessions(self, state):
        """Toggle all session checkboxes (deprecated - kept for compatibility)."""
        for row in range(self.session_table.rowCount()):
            checkbox_widget = self.session_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(CustomCheckBox)
                if checkbox:
                    checkbox.setChecked(state == Qt.CheckState.Checked.value)
    
    def get_selected_sessions(self):
        """Get only selected sessions (with checkbox checked)."""
        selected = []
        for row in range(self.session_table.rowCount()):
            checkbox_widget = self.session_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(CustomCheckBox)
                if checkbox and checkbox.isChecked() and row < len(self.session_data):
                    selected.append(self.session_data[row])
        return selected
    
    def check_live_sessions(self):
        """Check live status of selected sessions using QThread."""
        if not TELETHON_AVAILABLE:
            QMessageBox.warning(self, "Lỗi", "Telethon chưa được cài đặt!")
            return
        
        # Get selected sessions with their row indices
        session_data_list = []
        for row in range(self.session_table.rowCount()):
            checkbox_widget = self.session_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(CustomCheckBox)
                if checkbox and checkbox.isChecked() and row < len(self.session_data):
                    session_data_list.append((row, self.session_data[row]))
        
        if not session_data_list:
            logger.warning("⚠️ Chưa chọn session nào để check live")
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất 1 session để check live!")
            return
        
        logger.info("=" * 30)
        logger.info("🔍 BẮT ĐẦU CHECK LIVE SESSIONS")
        logger.info(f"📊 Số sessions đã chọn: {len(session_data_list)}")
        logger.info("=" * 30)
        
        # Create worker
        self.check_live_worker = CheckLiveWorker(session_data_list)
        self.check_live_worker.moveToThread(self.check_live_thread)
        
        # Connect signals
        self.check_live_thread.started.connect(self.check_live_worker.run)
        self.check_live_worker.update_session_info.connect(self.on_check_live_update)
        self.check_live_worker.finished.connect(self.on_check_live_finished)
        
        # Start thread
        self.check_live_thread.start()
    
    def on_check_live_update(self, row, phone, full_name, username, status, session_path):
        """Update UI when a session is checked - với full_name."""
        # Update phone number (column 2)
        if phone and phone != "N/A":
            phone_item = QTableWidgetItem(phone)
            phone_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.session_table.setItem(row, 2, phone_item)
        
        # Update full name (column 3 - Name column)
        if full_name and full_name != "N/A":
            self.session_table.setItem(row, 3, QTableWidgetItem(full_name))
        
        # Update username (column 4 - Username column)
        if username:
            self.session_table.setItem(row, 4, QTableWidgetItem(username))
        
        # Update Live status - centered (column 7)
        live_item = QTableWidgetItem(status)
        live_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.session_table.setItem(row, 7, live_item)
        
        # Update persistent cache
        if session_path:
            if session_path not in self.session_cache:
                self.session_cache[session_path] = {}
            self.session_cache[session_path].update({
                'phone': phone,
                'full_name': full_name,
                'username': username,
                'live_status': status
            })
            
            # Save cache to file
            save_session_cache(self.session_cache)
        
        # Update session_data cache
        if row < len(self.session_data):
            self.session_data[row].update({
                'phone': phone,
                'full_name': full_name,
                'username': username
            })
    
    def on_check_live_finished(self, live_count, die_count):
        """Handle check live completion."""
        self.check_live_thread.quit()
        
        total = live_count + die_count
        rate = (live_count / total * 100) if total > 0 else 0
        
        logger.info("=" * 30)
        logger.info("🎉 HOÀN TẤT CHECK LIVE")
        logger.info(f"✅ Live: {live_count}/{total}")
        logger.info(f"❌ Die: {die_count}/{total}")
        logger.info(f"📊 Tỷ lệ Live: {rate:.1f}%")
        logger.info("=" * 30)
        
        QMessageBox.information(self, "Hoàn tất", 
            f"Check Live hoàn tất!\n\n✅ Live: {live_count}\n❌ Die: {die_count}\n📊 Tỷ lệ: {rate:.1f}%")
    
    def extract_phone_from_session(self, session_path, session_file):
        """
        Extract phone number from session file.
        Try multiple methods:
        1. Read from .session SQLite database
        2. Parse from filename if it contains phone number
        3. Return filename as fallback
        """
        # Method 1: Try to read from .session database
        if TELETHON_AVAILABLE:
            try:
                conn = sqlite3.connect(session_path)
                cursor = conn.cursor()
                # Telethon stores DC info in sessions table
                cursor.execute("SELECT * FROM sessions")
                row = cursor.fetchone()
                conn.close()
                
                # If we have data, try to extract phone from the session
                # This is a simplified approach - full parsing would need telethon's internal format
                if row:
                    # Try to find phone in session data using regex
                    session_str = str(row)
                    phone_match = re.search(r'\+?\d{10,15}', session_str)
                    if phone_match:
                        return phone_match.group(0)
            except Exception:
                pass
        
        # Method 2: Try to parse from filename
        # Remove .session extension
        name_without_ext = session_file.replace('.session', '')
        
        # Check if filename is or contains a phone number
        # Pattern: numbers, possibly with + at start
        phone_pattern = r'\+?\d{10,15}'
        phone_match = re.search(phone_pattern, name_without_ext)
        if phone_match:
            return phone_match.group(0)
        
        # Method 3: Fallback - return filename without extension
        return name_without_ext
    
    def on_group_changed(self):
        """Handle group selection change - load sessions and save config."""
        self.load_sessions_to_table()
        self.save_config()  # Auto save selected group
    
    def load_sessions_to_table(self):
        """Load sessions to table based on selected group."""
        selected_group = self.session_group_combo.currentText()
        
        if selected_group == "Tất cả sessions":
            # Show all sessions from all groups
            all_sessions = []
            for group_name, session_paths in self.session_groups.items():
                for path in session_paths:
                    all_sessions.append((path, os.path.basename(path), group_name))
            logger.info(f"📊 Hiển thị tất cả {len(all_sessions)} sessions từ {len(self.session_groups)} nhóm")
        else:
            # Show sessions from selected group only
            if selected_group not in self.session_groups:
                self.session_table.setRowCount(0)
                logger.warning(f"⚠️ Nhóm '{selected_group}' không tồn tại")
                return  # Return chỉ khi nhóm KHÔNG tồn tại
            all_sessions = [(p, os.path.basename(p), selected_group) for p in self.session_groups[selected_group]]
            logger.info(f"📊 Hiển thị nhóm '{selected_group}' với {len(all_sessions)} sessions")
        
        # Sort sessions by filename to maintain consistent order
        all_sessions.sort(key=lambda x: x[1].lower())
        
        try:
            self.session_table.setRowCount(len(all_sessions))
            self.session_data = []
            
            for i, (session_path, session_file, group_name) in enumerate(all_sessions):
                # Check if session has cached data
                cached_data = self.session_cache.get(session_path, {})
                
                # Extract phone from cache or session filename
                phone_number = cached_data.get('phone') or self.extract_phone_from_session(session_path, session_file)
                full_name = cached_data.get('full_name', "")
                username = cached_data.get('username', "")
                live_status = cached_data.get('live_status', "Chưa check")
                
                self.session_data.append({
                    "phone": phone_number,
                    "full_name": full_name,
                    "username": username,
                    "session_file": session_file,
                    "session_path": session_path,
                    "group": group_name
                })
                
                # Add checkbox to column 0 - compact layout
                checkbox = CustomCheckBox()
                checkbox.setChecked(False)  # Default unchecked
                checkbox.setFixedSize(18, 18)  # Fix size để không có khoảng trống
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                checkbox_layout.setSpacing(0)
                checkbox_layout.addWidget(checkbox)
                self.session_table.setCellWidget(i, 0, checkbox_widget)
                
                # Add STT (số thứ tự) to column 1 - centered
                stt_item = QTableWidgetItem(str(i + 1))
                stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.session_table.setItem(i, 1, stt_item)
                
                # Add other columns (shift by 1)
                # SĐT - centered (restore from cache)
                phone_item = QTableWidgetItem(phone_number)
                phone_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.session_table.setItem(i, 2, phone_item)
                
                # Name - Full Name (restore from cache)
                self.session_table.setItem(i, 3, QTableWidgetItem(full_name if full_name else ""))
                
                # Username - @username (restore from cache)
                self.session_table.setItem(i, 4, QTableWidgetItem(username if username else ""))
                
                # Message
                self.session_table.setItem(i, 5, QTableWidgetItem("Chưa chạy"))
                
                # Status - empty (chỉ hiển thị khi chạy)
                self.session_table.setItem(i, 6, QTableWidgetItem(""))
                
                # Live status - centered (restore from cache)
                live_item = QTableWidgetItem(live_status)
                live_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.session_table.setItem(i, 7, live_item)
        except Exception as e:
            logger.error(f"❌ Lỗi khi tải session: {str(e)}")
    
    def select_admin_session(self):
        """Select admin session file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn File Session Admin", "", "Session files (*.session)")
        if file_path:
            self.admin_session_path = file_path
            try:
                with open(admin_session_file_path, "w", encoding="utf-8") as f:
                    f.write(file_path)
                logger.info(f"👤 Đã chọn Admin session: {os.path.basename(file_path)}")
                QMessageBox.information(self, "Thành công", 
                    f"Đã chọn admin session: {os.path.basename(file_path)}")
            except Exception as e:
                logger.error(f"❌ Lỗi khi lưu admin session path: {str(e)}")
    
    def load_config(self):
        # Load session groups
        self.session_groups = load_session_groups()
        for group_name in self.session_groups.keys():
            if self.session_group_combo.findText(group_name) == -1:
                self.session_group_combo.addItem(group_name)
        
        # Load session folder path (for backward compatibility)
        if os.path.exists(session_folder_path_file):
            try:
                with open(session_folder_path_file, "r", encoding="utf-8") as f:
                    self.session_folder_path = f.read().strip()
                # Note: No auto-load to table - user must manually add via Session menu
            except Exception as e:
                logger.error(f"Lỗi khi đọc session folder path: {str(e)}")
        
        # Load admin session path
        if os.path.exists(admin_session_file_path):
            try:
                with open(admin_session_file_path, "r", encoding="utf-8") as f:
                    self.admin_session_path = f.read().strip()
            except Exception as e:
                logger.error(f"Lỗi khi đọc admin session path: {str(e)}")
        
        # Load admin responses
        if os.path.exists(admin_responses_file):
            try:
                with open(admin_responses_file, "r", encoding="utf-8") as f:
                    self.admin_response_text.setPlainText(f.read().strip())
            except:
                pass
        else:
            self.admin_response_text.setPlainText("\n".join(DEFAULT_ADMIN_RESPONSES))
        
        # Load seeding config
        config = load_seeding_config()
        self.group_links_text.setPlainText("\n".join(config.get("group_links", [])))
        self.delay_time_line.setText(config.get("delay_time", "600"))
        self.admin_delay_time_line.setText(config.get("admin_delay_time", "20"))
        self.random_delay_checkbox.setChecked(config.get("random_delay", False))
        self.scenario_text.setPlainText(config.get("scenario_text", ""))
        self.group_join_links_text.setPlainText(config.get("group_join_links", ""))
        
        # Load scheduler config
        self.schedule_time_edit.setText(config.get("schedule_time", "18:00"))
        auto_schedule_enabled = config.get("auto_schedule", False)
        if auto_schedule_enabled:
            # Set checkbox (will trigger toggle_scheduler via signal)
            self.auto_schedule_checkbox.setChecked(True)
        
        # Restore selected group
        selected_group = config.get("selected_group", "Tất cả sessions")
        index = self.session_group_combo.findText(selected_group)
        if index >= 0:
            self.session_group_combo.setCurrentIndex(index)
            logger.info(f"📂 Restore nhóm đã chọn: {selected_group}")
        
        # Load sessions to table
        if self.session_groups:
            self.load_sessions_to_table()
            logger.info(f"📱 Đã load {len(self.session_groups)} nhóm session")
    
    def save_config(self):
        group_links = [line.strip() for line in self.group_links_text.toPlainText().split("\n") if line.strip() and line.startswith("https://t.me/")]
        scenario_text = self.scenario_text.toPlainText()
        group_join_links = self.group_join_links_text.toPlainText()
        selected_group = self.session_group_combo.currentText()
        save_seeding_config(group_links, self.delay_time_line.text(), self.admin_delay_time_line.text(), 
                           self.random_delay_checkbox.isChecked(), scenario_text, group_join_links,
                           self.auto_schedule_checkbox.isChecked(), self.schedule_time_edit.text().strip(), selected_group)
    
    def save_admin_responses(self):
        responses = self.admin_response_text.toPlainText().strip()
        if responses:
            save_admin_responses(responses)
            num_responses = len([line for line in responses.split("\n") if line.strip()])
            logger.info(f"💾 Đã lưu {num_responses} nội dung Admin response")
            QMessageBox.information(self, "Thành công", "Đã lưu nội dung Admin!")
        else:
            logger.warning("⚠️ Nội dung Admin trống, không thể lưu")
            QMessageBox.warning(self, "Lỗi", "Nội dung Admin trống!")
    
    def generate_scenario(self):
        try:
            if os.path.exists(sample_script_file):
                with open(sample_script_file, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                if lines:
                    random.shuffle(lines)
                    self.scenario_text.setPlainText("\n".join(lines))
                    logger.info(f"🎲 Đã tạo kịch bản ngẫu nhiên với {len(lines)} dòng")
                else:
                    logger.warning("⚠️ File sample_script.txt trống!")
                    self.status_label.setText("File sample_script.txt trống!")
            else:
                logger.warning("⚠️ Không tìm thấy file sample_script.txt!")
                self.status_label.setText("Không tìm thấy file sample_script.txt!")
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo kịch bản: {str(e)}")
            self.status_label.setText(f"Lỗi: {str(e)}")
    
    def save_scenario(self):
        content = self.scenario_text.toPlainText().strip()
        if content:
            try:
                with open(sample_script_file, "w", encoding="utf-8") as f:
                    f.write(content)
                num_lines = len([line for line in content.split("\n") if line.strip()])
                logger.info(f"💾 Đã lưu kịch bản mẫu với {num_lines} dòng")
                QMessageBox.information(self, "Thành công", "Đã lưu kịch bản!")
            except Exception as e:
                logger.error(f"❌ Lỗi khi lưu kịch bản: {str(e)}")
                QMessageBox.critical(self, "Lỗi", f"Lỗi khi lưu: {str(e)}")
        else:
            logger.warning("⚠️ Kịch bản trống, không thể lưu")
            QMessageBox.warning(self, "Lỗi", "Kịch bản trống!")
    
    def run_join_group(self):
        if not TELETHON_AVAILABLE:
            QMessageBox.warning(self, "Lỗi", "Telethon chưa được cài đặt!")
            return
        
        # Check for selected sessions
        selected_sessions = self.get_selected_sessions()
        if not selected_sessions:
            self.status_label.setText("❌ Chưa chọn session nào! Hãy tick checkbox ở tab Manager.")
            logger.warning("❌ Không có session nào được chọn để chạy")
            return
        
        # Use group_join_links_text from Group tab
        group_links = [line.strip() for line in self.group_join_links_text.toPlainText().split("\n") 
                      if line.strip() and line.startswith("https://t.me/")]
        if not group_links:
            self.status_label.setText("❌ Danh sách link nhóm trống!")
            logger.warning("❌ Danh sách link nhóm trống")
            return
        
        try:
            delay_time = float(self.delay_time_line.text().strip())
        except:
            self.status_label.setText("❌ Thời gian delay không hợp lệ!")
            logger.error("❌ Thời gian delay không hợp lệ")
            return
        
        # Save config before running
        self.save_config()
        
        # Get selected session paths
        selected_session_paths = [s['session_path'] for s in selected_sessions]
        
        logger.info("=" * 30)
        logger.info("🚀 BẮT ĐẦU THAM GIA NHÓM")
        logger.info(f"📊 Số sessions đã chọn: {len(selected_session_paths)}")
        logger.info(f"🔗 Số nhóm cần join: {len(group_links)}")
        logger.info(f"⏱️ Delay: {delay_time}s")
        logger.info("=" * 30)
        
        self.join_group_worker = JoinGroupWorker(selected_session_paths, group_links, delay_time, 
                                                  self.random_delay_checkbox.isChecked())
        self.join_group_worker.moveToThread(self.join_group_thread)
        self.join_group_thread.started.connect(self.join_group_worker.run)
        self.join_group_worker.update_message.connect(self.show_message)
        self.join_group_worker.finished.connect(self.on_join_finished)
        self.join_group_worker.update_session_status.connect(self.update_session_status)
        self.join_group_thread.start()
        
        # Update button state
        self.is_running = True
        self.run_stop_btn.setText("⏹ Stop")
        self.run_stop_btn.setStyleSheet("background-color: #F44336; color: white;")
    
    def run_seeding(self):
        if not TELETHON_AVAILABLE:
            QMessageBox.warning(self, "Lỗi", "Telethon chưa được cài đặt!")
            return
        
        # Check for selected sessions
        selected_sessions = self.get_selected_sessions()
        if not selected_sessions:
            self.status_label.setText("❌ Chưa chọn session nào! Hãy tick checkbox ở tab Manager.")
            logger.warning("❌ Không có session nào được chọn để chạy")
            return
        
        group_links = [line.strip() for line in self.group_links_text.toPlainText().split("\n") 
                      if line.strip() and line.startswith("https://t.me/")]
        if not group_links:
            self.status_label.setText("❌ Danh sách link nhóm trống!")
            logger.warning("❌ Danh sách link nhóm trống")
            return
        
        scenario_lines = [line.strip() for line in self.scenario_text.toPlainText().split("\n") if line.strip()]
        if not scenario_lines:
            self.status_label.setText("❌ Kịch bản trống!")
            logger.warning("❌ Kịch bản trống")
            return
        
        admin_lines = [line.strip() for line in self.admin_response_text.toPlainText().split("\n") if line.strip()] or DEFAULT_ADMIN_RESPONSES
        
        try:
            delay_time = float(self.delay_time_line.text().strip())
            admin_delay_time = float(self.admin_delay_time_line.text().strip())
        except:
            self.status_label.setText("❌ Thời gian delay không hợp lệ!")
            logger.error("❌ Thời gian delay không hợp lệ")
            return
        
        self.save_config()
        
        # Get selected session paths
        selected_session_paths = [s['session_path'] for s in selected_sessions]
        
        logger.info("=" * 30)
        logger.info("🌱 BẮT ĐẦU SEEDING")
        logger.info(f"📊 Số sessions đã chọn: {len(selected_session_paths)}")
        logger.info(f"🔗 Số nhóm cần seeding: {len(group_links)}")
        logger.info(f"📝 Số kịch bản: {len(scenario_lines)}")
        logger.info(f"⏱️ Delay: {delay_time}s | Admin Delay: {admin_delay_time}s")
        logger.info("=" * 30)
        
        self.seeding_worker = SeedingWorker(
            selected_session_paths, self.admin_session_path, group_links, scenario_lines,
            delay_time, admin_delay_time, admin_lines, 
            self.random_delay_checkbox.isChecked(), 
            self.randomize_message_checkbox.isChecked()
        )
        self.seeding_worker.moveToThread(self.seeding_thread)
        self.seeding_thread.started.connect(self.seeding_worker.run)
        self.seeding_worker.update_message.connect(self.show_message)
        self.seeding_worker.finished.connect(self.on_seeding_finished)
        self.seeding_worker.update_session_status.connect(self.update_session_status)
        self.seeding_thread.start()
        
        # Update button state
        self.is_running = True
        self.run_stop_btn.setText("⏹ Stop")
        self.run_stop_btn.setStyleSheet("background-color: #F44336; color: white;")
    
    def show_message(self, message, color):
        self.status_label.setText(message)
        if color == "red":
            self.status_label.setStyleSheet("color: #F44336;")
        elif color == "green":
            self.status_label.setStyleSheet("color: #4CAF50;")
        else:
            self.status_label.setStyleSheet("")
    
    def update_session_status(self, row, phone, full_name, username, message, status, session_path):
        """Update session status in UI - CORRECT column mapping."""
        if row >= self.session_table.rowCount():
            return  # Row không tồn tại
        
        # Lưu vào cache
        if session_path not in self.session_cache:
            self.session_cache[session_path] = {}
        self.session_cache[session_path].update({
            'phone': phone,
            'full_name': full_name,
            'username': username
        })
        
        # Save cache to file
        save_session_cache(self.session_cache)
        
        # Update UI - ĐÚNG mapping các cột
        # Col 0: Checkbox (không update)
        # Col 1: STT (không update)
        # Col 2: SĐT
        phone_item = QTableWidgetItem(phone)
        phone_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.session_table.setItem(row, 2, phone_item)
        
        # Col 3: Name (Full Name từ Telegram)
        self.session_table.setItem(row, 3, QTableWidgetItem(full_name))
        
        # Col 4: Username (@username từ Telegram)
        self.session_table.setItem(row, 4, QTableWidgetItem(username))
        
        # Col 5: Message (hành động: Tham gia nhóm, Gửi tin nhắn)
        self.session_table.setItem(row, 5, QTableWidgetItem(message))
        
        # Col 6: Status (trạng thái: Đang xử lý, Hoàn Thành, Thất bại)
        self.session_table.setItem(row, 6, QTableWidgetItem(status))
        
        # Col 7: Live (KHÔNG update - giữ nguyên trạng thái check live)
    
    def on_join_finished(self, success, failed):
        self.join_group_thread.quit()
        total = success + failed
        rate = (success / total * 100) if total > 0 else 0
        self.status_label.setText(f"✅ Hoàn tất tham gia! Thành công: {success}, Thất bại: {failed}, Tỷ lệ: {rate:.1f}%")
        
        logger.info("=" * 30)
        logger.info("🎉 HOÀN TẤT THAM GIA NHÓM")
        logger.info(f"✅ Thành công: {success}/{total}")
        logger.info(f"❌ Thất bại: {failed}/{total}")
        logger.info(f"📊 Tỷ lệ thành công: {rate:.1f}%")
        logger.info("=" * 30)
        
        # Reset button state
        self.is_running = False
        self.run_stop_btn.setText("▶️ Run")
        self.run_stop_btn.setStyleSheet("")
    
    def on_seeding_finished(self, success, failed):
        self.seeding_thread.quit()
        total = success + failed
        rate = (success / total * 100) if total > 0 else 0
        self.status_label.setText(f"✅ Hoàn tất seeding! Thành công: {success}, Thất bại: {failed}, Tỷ lệ: {rate:.1f}%")
        
        logger.info("=" * 30)
        logger.info("🎉 HOÀN TẤT SEEDING")
        logger.info(f"✅ Thành công: {success}/{total}")
        logger.info(f"❌ Thất bại: {failed}/{total}")
        logger.info(f"📊 Tỷ lệ thành công: {rate:.1f}%")
        logger.info("=" * 30)
        
        # Reset button state
        self.is_running = False
        self.run_stop_btn.setText("▶️ Run")
        self.run_stop_btn.setStyleSheet("")
    
    def toggle_scheduler(self):
        """Toggle auto scheduler on/off."""
        self.scheduler_enabled = self.auto_schedule_checkbox.isChecked()
        
        if self.scheduler_enabled:
            # Validate time format
            schedule_time = self.schedule_time_edit.text().strip()
            if not schedule_time or ':' not in schedule_time:
                QMessageBox.warning(self, "Lỗi", "Vui lòng nhập giờ hợp lệ (VD: 18:00)")
                self.auto_schedule_checkbox.setChecked(False)
                return
            
            try:
                hour, minute = schedule_time.split(':')
                hour = int(hour)
                minute = int(minute)
                if not (0 <= hour < 24 and 0 <= minute < 60):
                    raise ValueError
            except:
                QMessageBox.warning(self, "Lỗi", "Giờ không hợp lệ! Định dạng: HH:MM (VD: 18:00)")
                self.auto_schedule_checkbox.setChecked(False)
                return
            
            # Start timer - check every 60 seconds
            if self.scheduler_timer is None:
                self.scheduler_timer = QTimer(self)
                self.scheduler_timer.timeout.connect(self.check_schedule)
            
            self.scheduler_timer.start(60000)  # 60 seconds
            self.schedule_status_label.setText(f"✅ Kích hoạt - Chạy lúc {schedule_time}")
            self.schedule_status_label.setStyleSheet("color: #00ff00;")
            logger.info(f"⏰ Lịch tự động đã BẬT - Sẽ chạy lúc {schedule_time} mỗi ngày")
            
            # Save config
            self.save_config()
        else:
            # Stop timer
            if self.scheduler_timer:
                self.scheduler_timer.stop()
            
            self.schedule_status_label.setText("❌ Đã tắt")
            self.schedule_status_label.setStyleSheet("color: #ff0000;")
            logger.info("⏰ Lịch tự động đã TẮT")
            
            # Save config
            self.save_config()
    
    def check_schedule(self):
        """Check if it's time to run auto seeding."""
        if not self.scheduler_enabled:
            return
        
        schedule_time = self.schedule_time_edit.text().strip()
        if not schedule_time or ':' not in schedule_time:
            return
        
        try:
            hour, minute = schedule_time.split(':')
            hour = int(hour)
            minute = int(minute)
        except:
            return
        
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')
        
        # Check if current time matches schedule time
        if now.hour == hour and now.minute == minute:
            # Avoid running multiple times in the same minute
            if self.last_run_date == current_date:
                return
            
            logger.info("=" * 30)
            logger.info("⏰ ĐẾN GIỜ CHẠY LỊCH TỰ ĐỘNG!")
            logger.info(f"⏰ Thời gian: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 30)
            
            self.last_run_date = current_date
            self.run_auto_seeding()
    
    def run_auto_seeding(self):
        """Auto run seeding: Generate scenario -> Save -> Run."""
        logger.info("🤖 BẮT ĐẦU SEEDING TỰ ĐỘNG")
        
        # Step 1: Generate scenario
        logger.info("📝 Bước 1/3: Tạo kịch bản ngẫu nhiên...")
        self.generate_scenario()
        
        # Step 2: Save scenario
        logger.info("💾 Bước 2/3: Lưu kịch bản...")
        self.save_scenario()
        
        # Step 3: Switch to Seeding tab and run
        logger.info("▶️ Bước 3/3: Chạy Seeding...")
        
        # Find and switch to Seeding tab
        for i in range(self.tabs.count()):
            if "Seeding" in self.tabs.tabText(i):
                self.tabs.setCurrentIndex(i)
                break
        
        # Run seeding
        self.run_seeding()
        
        logger.info("🤖 ĐÃ KÍCH HOẠT SEEDING TỰ ĐỘNG")
    
    def stop_seeding(self):
        logger.info("⏹️ Đang dừng tác vụ...")
        if self.seeding_worker:
            self.seeding_worker.stop()
            self.seeding_thread.quit()
        if self.join_group_worker:
            self.join_group_worker.stop()
            self.join_group_thread.quit()
        self.status_label.setText("⏹️ Đã dừng!")
        logger.warning("⏹️ Tác vụ đã bị dừng bởi người dùng")


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    widget = TelegramToolWidget()
    widget.show()
    sys.exit(app.exec())