# MXH (Mạng Xã Hội) - Social Media Management System

## � Unified Logging: Backend + Browser Console (F12)

### 📖 Overview

MonDashboard có hệ thống logging thống nhất, cho phép xem **cả log backend lẫn log F12 browser** trong cùng 1 terminal và file log.

### 🚀 Quick Start

#### Windows:
```powershell
# Cài đặt dependencies
pip install -r requirements.txt

# Chạy dev mode
.\scripts\run_dev.ps1
```

#### Linux/macOS:
```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Chạy dev mode
chmod +x scripts/run_dev.sh
bash scripts/run_dev.sh
```

### ⚙️ Configuration

Sử dụng **environment variables**:

```bash
# Bật/tắt console bridge
CONSOLE_BRIDGE_MODE=cdp        # CDP (Chrome DevTools Protocol) - default
CONSOLE_BRIDGE_MODE=inpage     # In-Page fallback (hook console.*)
CONSOLE_BRIDGE_MODE=off        # Tắt hoàn toàn

# CDP port (nếu dùng CDP mode)
CDP_PORT=9222                  # default: 9222

# Log level
LOG_LEVEL=INFO                 # DEBUG|INFO|WARNING|ERROR

# Environment
ENV=dev                        # dev|prod (/__console chỉ hoạt động ở dev)

# Security token (optional)
DEV_CONSOLE_TOKEN=your_secret  # Nếu set, client phải gửi X-Dev-Token header
```

### 📂 Log Files

- **`logs/app.log`**: Backend logs (Flask, Python code)
- **`logs/f12_console.log`**: Browser console logs (F12 console, errors, warnings)

Both files:
- Auto-rotate: 5 files × 5MB each
- Format: `[timestamp] [level] [logger] message`

### 🔍 How It Works

#### Mode 1: CDP (Chrome DevTools Protocol) - Preferred

1. Chrome chạy với `--remote-debugging-port=9222`
2. `web_console_bridge.py` kết nối qua WebSocket
3. Lắng nghe events:
   - `Runtime.consoleAPICalled` → console.log/warn/error
   - `Runtime.exceptionThrown` → JavaScript exceptions
   - `Log.entryAdded` → Other browser logs
4. Ghi vào `logs/f12_console.log` và terminal

**Ưu điểm**: Không cần sửa frontend, capture tất cả logs tự động

#### Mode 2: In-Page Fallback

1. `app/static/js/console-mirror.js` hook console methods
2. Hook `window.onerror` và `unhandledrejection`
3. Batch logs và gửi về Flask `POST /__console`
4. `console_endpoint.py` nhận và ghi log

**Ưu điểm**: Không cần Chrome với CDP, chạy được mọi browser

### 🛡️ Security

- `/__console` endpoint **chỉ hoạt động khi `ENV=dev`**
- Có thể set `DEV_CONSOLE_TOKEN` để yêu cầu token
- Auto-reject batch > 512KB
- Truncate messages/stacks quá dài
- Rate limiting (debounce 100ms, max 20 logs/batch)

### 🎨 Log Format Examples

**Backend log:**
```
[2025-10-20 15:30:45] [INFO] [app] User clicked MXH card #5
```

**F12 log (CDP):**
```
[2025-10-20 15:30:46] [ERROR] [f12] [F12-CDP] [Exception] TypeError: Cannot read property 'id' of undefined | mxh.html:2379:17
  at flipCardToAccount (mxh.html:2379:17)
  at HTMLDivElement.<anonymous> (mxh.html:1305:45)
```

**F12 log (In-Page):**
```
[2025-10-20 15:30:47] [WARNING] [f12] [F12-InPage] [console.warn] API response slow | http://localhost:5000/mxh:842:12
```

### 🐛 Troubleshooting

**CDP không kết nối được:**
- Kiểm tra Chrome có chạy với `--remote-debugging-port=9222` không
- Mở `http://localhost:9222` trên browser để xem có targets không
- Thử port khác: `CDP_PORT=9223`

**In-Page không gửi logs:**
- Kiểm tra `ENV=dev` (/__console chỉ hoạt động ở dev mode)
- Mở F12 → Network → Xem có request `POST /__console` không
- Kiểm tra console có lỗi từ `console-mirror.js` không

**Logs không thấy trong file:**
- Kiểm tra folder `logs/` có tồn tại không
- Kiểm tra permissions ghi file
- Xem terminal có error message từ `logging_conf.py` không

---

## �📋 Kiến trúc hệ thống: Card và Account

### 🆚 So sánh MXH OLD vs MXH NEW

#### **MXH OLD** (thư mục `MXH_Old/`)
- **1 Card = 1 Account** (quan hệ 1-1)
- Đơn giản, trực tiếp
- Mỗi card hiển thị 1 tài khoản duy nhất
- Không hỗ trợ tài khoản phụ

#### **MXH NEW** (hiện tại - `app/mxh_routes.py`, `app/templates/mxh.html`)
- **1 Card = N Accounts** (quan hệ 1-N)
- Phức tạp hơn, linh hoạt hơn
- 1 Card có **1 tài khoản chính** (primary account) + **nhiều tài khoản phụ**
- Card có 2 mặt: **mặt trước** và **mặt sau** để hiển thị các tài khoản khác nhau

### 🗃️ Cấu trúc Database

```sql
-- Bảng MXH Cards (Cha)
CREATE TABLE mxh_cards (
    id INTEGER PRIMARY KEY,
    card_name TEXT NOT NULL,        -- Tên card (thường là số: "1", "2", "3"...)
    group_id INTEGER,               -- Nhóm (WeChat, Telegram, Facebook...)
    platform TEXT NOT NULL,         -- Nền tảng (wechat, telegram, facebook...)
    created_at TEXT,
    updated_at TEXT
);

-- Bảng MXH Accounts (Con)
CREATE TABLE mxh_accounts (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL,       -- FOREIGN KEY → mxh_cards.id
    is_primary INTEGER DEFAULT 0,   -- 1 = tài khoản chính (👑), 0 = tài khoản phụ
    account_name TEXT,              -- Tên tài khoản
    username TEXT,                  -- Username/tên hiển thị
    phone TEXT,                     -- Số điện thoại
    url TEXT,                       -- URL profile
    login_username TEXT,            -- Username đăng nhập
    login_password TEXT,            -- Password đăng nhập
    status TEXT,                    -- Trạng thái: 'active', 'disabled', 'die'
    wechat_status TEXT,             -- Trạng thái WeChat (available/disabled/die)
    -- ... các trường khác (wechat_created_day/month/year, notice, etc.) ...
    FOREIGN KEY(card_id) REFERENCES mxh_cards(id) ON DELETE CASCADE
);
```

**Quan hệ dữ liệu:**
- 1 Card có nhiều Accounts (1-N)
- Mỗi Card có đúng 1 Account với `is_primary = 1` (tài khoản chính - có icon 👑)
- Các Account còn lại là tài khoản phụ (`is_primary = 0`)
- Khi xóa Card → tất cả Accounts con bị xóa theo (CASCADE)

### 🎴 Cơ chế Card Flip

#### Luồng hoạt động:
1. **Mặc định**: Card hiển thị **tài khoản chính** (is_primary=1, có icon 👑)
2. **Click số card** hoặc **context menu "Tài Khoản"**: Chọn tài khoản khác
3. **Card flip**: Mặt card lật sang hiển thị tài khoản được chọn
4. **Số hiển thị**: `2/7` = đang hiển thị tài khoản thứ 2 trong tổng số 7 tài khoản

#### State Management:
```javascript
// State được lưu cho mỗi card trong memory (không lưu database)
const cardStates = new Map();

function getCardState(cardId) {
    if (!cardStates.has(cardId)) {
        cardStates.set(cardId, {
            isFlipped: false,           // Card đang mặt trước hay mặt sau?
            activeAccountId: null       // ID của account đang hiển thị
        });
    }
    return cardStates.get(cardId);
}
```

#### Hàm flip card:
```javascript
function flipCardToAccount(cardId, accountId) {
    const state = getCardState(cardId);
    const wrapper = document.getElementById(`card-wrapper-${cardId}`);
    
    if (!wrapper) return;

    // Toggle flip state
    const newFlipped = !state.isFlipped;
    state.isFlipped = newFlipped;
    state.activeAccountId = accountId;

    // Apply CSS flip class
    if (newFlipped) {
        wrapper.classList.add('flipped');
    } else {
        wrapper.classList.remove('flipped');
    }

    // Re-render mặt ẩn với account mới sau 300ms (đợi CSS animation)
    setTimeout(() => {
        const accounts = mxhAccounts.filter(acc => acc.card_id === cardId);
        const newActiveAccount = accounts.find(acc => acc.id === accountId);
        if (newActiveAccount) {
            const hiddenSide = newFlipped ? 'front' : 'back';
            const hiddenFace = wrapper.querySelector(`.mxh-card-face.${hiddenSide}`);
            if (hiddenFace) {
                hiddenFace.outerHTML = renderCardFace(newActiveAccount, accounts, hiddenSide);
            }
            // Update border color theo status của account mới
        }
    }, 300);
}
```

### 🎯 Context Menu - Chuyển đổi tài khoản

#### Context Menu Structure:
```
┌─────────────────────────────┐
│ Tài Khoản (7)          ▶    │──┐
│ Thông Tin                   │  │
│ Quét WeChat                 │  │
│ Trạng Thái             ▶    │  │
│ Copy SĐT                    │  │
│ Thông Báo                   │  │
│ ─────────────────────────── │  │
│ Xóa Card/Acc                │  │
└─────────────────────────────┘  │
                                 │
┌────────────────────────────────┘
│ ┌─────────────────────────┐
│ │ ✓ 1. Username1 👑       │ ← Tài khoản đang active
│ │   2. Username2          │
│ │   3. Username3          │
│ │   4. Username4          │
│ │   5. Username5          │
│ │   6. Username6          │
│ │   7. Username7          │
│ │   ───────────────────── │
│ │   + Thêm Tài Khoản      │
│ └─────────────────────────┘
└──
```

#### Context Menu Handler:
```javascript
// File: app/templates/mxh.html

// Khi click chuột phải vào card
window.handleCardContextMenu = function(event, cardId, accountId, platform) {
    event.preventDefault();
    event.stopPropagation();
    
    currentContextCardId = cardId;
    currentContextAccountId = accountId;
    
    // Lấy tất cả accounts thuộc card này
    const cardAccounts = mxhAccounts.filter(acc => acc.card_id === cardId);
    const state = getCardState(cardId);
    
    // Render menu động với danh sách tài khoản
    const menuHtml = `
        <div class="mxh-context-menu" id="card-context-menu">
            <div class="mxh-menu-item has-submenu">
                <span>Tài Khoản (${cardAccounts.length})</span>
                <div class="mxh-submenu">
                    ${cardAccounts.map((acc, idx) => {
                        const isActive = acc.id === state.activeAccountId;
                        const isPrimary = acc.is_primary;
                        return `
                        <div class="mxh-menu-item" 
                             data-action="switch-account" 
                             data-account-id="${acc.id}">
                            ${isActive ? '✓ ' : ''}${idx + 1}. ${acc.username || '...'} ${isPrimary ? '👑' : ''}
                        </div>
                    `;
                    }).join('')}
                    <div class="mxh-menu-item" data-action="add-sub-account">
                        <i class="bi bi-plus-circle me-2"></i>Thêm Tài Khoản
                    </div>
                </div>
            </div>
            <!-- ... menu items khác ... -->
        </div>
    `;
    
    // Append menu vào DOM và hiển thị
    document.body.insertAdjacentHTML('beforeend', menuHtml);
}

// Khi click vào "Tài Khoản X" trong menu
document.addEventListener('click', async function(e) {
    const menuItem = e.target.closest('.mxh-menu-item[data-action]');
    if (!menuItem) return;

    const action = menuItem.getAttribute('data-action');

    if (action === 'switch-account') {
        const accountId = parseInt(menuItem.getAttribute('data-account-id'));
        if (currentContextCardId && accountId) {
            flipCardToAccount(currentContextCardId, accountId);
            hideCardContextMenu();
        }
    } 
    // ... xử lý các action khác ...
});
```

**Code đã sửa:** Xóa case 'switch-account' và 'add-new-account' trong unified-context-menu listener

---

## 🔑 Key Components

| Component | File | Mô tả |
|-----------|------|-------|
| **Database Schema** | `app/database.py` | Định nghĩa bảng mxh_cards và mxh_accounts với quan hệ 1-N |
| **Backend API** | `app/mxh_routes.py` | REST API xử lý CRUD cards/accounts, hỗ trợ FE cũ qua alias routes |
| **Frontend Render** | `app/templates/mxh.html` | Render cards với flip animation, context menu động |
| **Card State** | `cardStates Map` | Lưu trạng thái flip và active account cho mỗi card (in-memory) |
| **Context Menu Handler** | `handleCardContextMenu()` | Menu chuột phải để chuyển account, xem thông tin, xóa |
| **Flip Function** | `flipCardToAccount()` | Toggle flip state và re-render mặt ẩn với account mới |

---

## 🎨 Card Layout System

### Container và Grid
```html
<!-- Container chính -->
<div id="mxh-accounts-container">
    <div class="row g-2">
        <!-- Mỗi card là 1 col -->
        <div class="col" style="padding: 2px;" data-card-id="123">
            <!-- Card wrapper với flip animation -->
            <div class="mxh-card-wrapper" id="card-wrapper-123">
                <div class="mxh-card-inner">
                    <!-- Mặt trước -->
                    <div class="mxh-card-face front">...</div>
                    <!-- Mặt sau -->
                    <div class="mxh-card-face back">...</div>
                </div>
            </div>
        </div>
    </div>
</div>
```

### Chế độ xem (Cards per row)
- User có thể chọn số cards mỗi hàng (1-20) qua modal "Chế Độ Xem"
- Giá trị được lưu vào `localStorage` và CSS variable `--cardsPerRow`
- Mặc định: 12 cards/hàng

---

## ⚠️ Lưu ý cho AI Developer

### ✅ Điều cần nhớ:
1. **Card ≠ Account**: 1 card có thể có nhiều accounts
2. **Primary account luôn tồn tại**: Mỗi card có đúng 1 account primary
3. **State chỉ lưu ở client**: `cardStates` không sync với database
4. **Context menu là động**: Render lại mỗi lần chuột phải, không cache
5. **Flip animation 300ms**: Phải đợi animation xong mới re-render mặt ẩn

### ❌ Điều không nên làm:
1. Không xóa hoặc sửa `flipCardToAccount()` - hàm core của hệ thống
2. Không dùng `showUnifiedContextMenu()` cho card mới - đã deprecated
3. Không thay đổi cấu trúc `mxh-card-wrapper` / `mxh-card-inner` - CSS flip phụ thuộc vào nó
4. Không lưu `isFlipped` vào database - chỉ là UI state tạm thời
5. Không render tất cả accounts cùng lúc - chỉ render active account + hidden side

### 🔍 Debug tips:
- Check console logs: `console.log(cardStates)` để xem state hiện tại
- Check DOM: `document.querySelectorAll('.mxh-card-wrapper.flipped')` để xem cards đang flip
- Check data: `mxhAccounts.filter(acc => acc.card_id === X)` để xem accounts của card X

---

**Version:** MXH NEW (1-N model)  
**Last Updated:** 2025-10-20
