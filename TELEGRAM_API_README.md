# 🚀 Telegram Manager API - Hướng Dẫn

## ✅ Đã Hoàn Thành

### 1. **Backend API Routes** (telegram_routes.py)
Tất cả các API endpoints cần thiết đã được tạo:

- ✅ `GET /telegram/api/groups` - Lấy danh sách nhóm session
- ✅ `POST /telegram/api/groups` - Tạo nhóm mới và upload sessions
- ✅ `DELETE /telegram/api/groups/<group_id>` - Xóa nhóm
- ✅ `GET /telegram/api/groups/<group_id>/sessions` - Lấy sessions trong nhóm
- ✅ `POST /telegram/api/run-task` - Chạy task (check-live, join, seeding)
- ✅ `GET /telegram/api/task-status/<task_id>` - Lấy tiến độ task
- ✅ `POST /telegram/api/stop-task/<task_id>` - Dừng task
- ✅ `GET /telegram/api/active-tasks` - Lấy danh sách task đang chạy
- ✅ `GET/POST /telegram/api/config/<task_id>` - Lưu/Load cấu hình task
- ✅ `POST /telegram/api/global-settings` - Lưu cài đặt Core/Delay/Admin
- ✅ `GET/POST /telegram/api/proxies` - Quản lý proxy
- ✅ `POST /telegram/api/upload-admin-sessions` - Upload admin sessions
- ✅ `POST /telegram/api/sessions/delete` - Xóa sessions
- ✅ `POST /telegram/api/update-session-info` - Cập nhật full_name/username

### 2. **Automatic Seeding Routes** (automatic_routes.py)
- ✅ `GET /automatic/api/seeding/settings` - Lấy cài đặt auto seeding
- ✅ `POST /automatic/api/seeding/settings` - Lưu cài đặt auto seeding

### 3. **Frontend** (telegram.html)
- ✅ Đã port 100% chức năng từ index.html
- ✅ Tất cả debug logs (🔍) để dễ troubleshoot
- ✅ Context menu, modals, event handlers đầy đủ

## 📁 Cấu Trúc Dữ Liệu

Tất cả dữ liệu được lưu trong `data/telegram/`:

```
data/telegram/
├── sessions/
│   ├── <group_id>/
│   │   ├── session1.session
│   │   ├── session2.session
│   │   └── ...
├── config/
│   ├── global_settings.json
│   ├── auto_seeding.json
│   ├── joinGroup.json
│   └── seedingGroup.json
├── groups.json
├── active_tasks.json
└── proxy_config.json
```

## 🔧 Cách Sử Dụng

### 1. Khởi động server
```bash
cd C:\Users\Mon\Desktop\Mon
python run.pyw
```

### 2. Truy cập Telegram Manager
Mở trình duyệt: `http://localhost:5000/telegram`

### 3. Upload Sessions
1. Click **"Add Session"**
2. Nhập tên nhóm (ví dụ: "Main Group")
3. Chọn các file `.session`
4. Click **"Lưu lại"**

### 4. Check Live Sessions
1. Chọn nhóm từ dropdown
2. Tick chọn sessions cần check
3. Click **"Check Live"**

### 5. Cấu hình Join Group
1. Click vào tab **"Group"**
2. Click vào card **"Join Group/Channel"**
3. Click **"Cấu hình"**
4. Nhập danh sách link (mỗi dòng một link)
5. Click **"Lưu"**
6. Chọn sessions và click **"Run"**

### 6. Cấu hình Seeding Group
1. Click vào card **"Seeding Group"**
2. Click **"Cấu hình"**
3. Nhập:
   - Link nhóm
   - Tin nhắn (Session thành viên)
   - Tin nhắn (Admin)
4. Upload Admin session (nếu cần)
5. Click **"Lưu"**
6. Click **"Run"**

## 🐛 Debug

Tất cả API calls đều có debug logs với prefix 🔍:

**Frontend (Browser Console):**
```javascript
🔍 Loading Telegram script...
🔍 Telegram pane found, initializing...
🔍 Loading Telegram groups...
🔍 Groups loaded: [...]
```

**Backend (Python Terminal):**
```python
🔍 DEBUG: Telegram routes module loaded
🔍 GET /telegram/api/groups
🔍 Returning 3 groups
🔍 POST /telegram/api/groups
🔍 Group name: Main Group, Files: 5
🔍 Created group Main Group with 5 sessions
```

## ⚠️ Lưu Ý

### Hiện Tại Chưa Implement:
1. **Logic thực tế cho tasks** - Các API chỉ trả về skeleton, bạn cần implement:
   - Check Live thực tế (kết nối Telegram)
   - Join Group thực tế
   - Seeding Group thực tế
   - Task progress tracking

2. **Auto Seeding Scheduler** - Cần implement cron job để chạy theo lịch

### Để Implement Logic Thực Tế:
Bạn cần thêm Telethon/Pyrogram vào `requirements.txt`:
```
telethon>=1.34.0
# hoặc
pyrogram>=2.0.0
```

Sau đó trong `telegram_routes.py`, thêm logic để:
1. Kết nối session files
2. Check live status
3. Join groups
4. Send messages

## 📊 Testing

### Test Upload Sessions:
1. Tạo file test: `test.session` (có thể là file rỗng để test)
2. Upload qua UI
3. Check console logs
4. Verify file xuất hiện trong `data/telegram/sessions/<group_id>/`

### Test API Trực Tiếp:
```bash
# Lấy danh sách groups
curl http://localhost:5000/telegram/api/groups

# Lấy sessions trong group
curl http://localhost:5000/telegram/api/groups/<group_id>/sessions
```

## 🎯 Next Steps

1. ✅ **DONE**: Backend API skeleton
2. ✅ **DONE**: Frontend integration
3. 🔄 **TODO**: Implement Telegram logic (Telethon/Pyrogram)
4. 🔄 **TODO**: Task queue system (Celery/RQ)
5. 🔄 **TODO**: Auto Seeding scheduler
6. 🔄 **TODO**: Session validation
7. 🔄 **TODO**: Error handling & retry logic
8. 🔄 **TODO**: Logging system

---

**Server đã được khởi động lại với các routes mới!** 🚀

Bây giờ bạn có thể:
1. Refresh trang `/telegram`
2. Thử upload sessions
3. Check console logs để verify API calls hoạt động

