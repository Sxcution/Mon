# Cấu Trúc Thư Mục Modules

Mỗi module có thư mục riêng với cấu trúc như sau:

```
modules/
├── ModAndroid/
│   ├── ModAndroid.pyw          # Main script
│   ├── bin/                     # Thư viện binary (Java tools, v.v.)
│   │   └── java/
│   │       ├── baksmali.jar
│   │       ├── smali.jar
│   │       ├── apktool_2.12.0.jar
│   │       └── ...
│   ├── config/                  # Cấu hình module
│   │   └── config.json         # Settings (device serial, v.v.)
│   └── data/                    # Dữ liệu runtime
│       ├── Patched/            # Files đã patch
│       ├── Decompiled/         # Files đã decompile
│       └── Rebuilt/            # Files đã rebuild
│
├── Telegram/
│   ├── telegram_module.py      # Main script
│   ├── config/                 # Cấu hình module
│   │   ├── seeding_config.json
│   │   ├── admin_responses.txt
│   │   ├── session_folder_path.txt
│   │   └── ...
│   └── data/                   # Dữ liệu runtime
│       └── (sessions, logs, v.v.)
│
├── HOW_TO_ADD_MODULE.md        # Hướng dẫn thêm module mới
└── README.md                   # Thông tin chung về modules
```

## Nguyên Tắc Tổ Chức

### 1. **Thư mục gốc module** (`modules/ModuleName/`)
   - Chứa file script chính (`ModuleName.pyw` hoặc `module_name.py`)
   - Mỗi module hoàn toàn độc lập

### 2. **Thư mục `bin/`** (nếu cần)
   - Chứa các công cụ binary, thư viện JAR, executables
   - Ví dụ: `baksmali.jar`, `smali.jar`, `apktool.jar`

### 3. **Thư mục `config/`**
   - Chứa tất cả files cấu hình của module
   - Ví dụ: `config.json`, `settings.txt`, `api_keys.json`
   - **Persistence:** Config được lưu lại sau khi tool tắt

### 4. **Thư mục `data/`**
   - Chứa dữ liệu runtime, output, cache
   - Ví dụ: files đã patch, decompiled, logs tạm
   - **Temporary/Output:** Có thể xóa mà không ảnh hưởng tool

## Lợi Ích

✅ **Tổ chức rõ ràng:** Mỗi module có không gian riêng  
✅ **Dễ maintain:** Config và data được tách biệt  
✅ **Portable:** Di chuyển/backup module dễ dàng  
✅ **Scalable:** Thêm module mới không ảnh hưởng modules cũ  

## Import trong Main.pyw

```python
# Load ModAndroid
modandroid_path = os.path.join(modules_dir, "ModAndroid", "ModAndroid.pyw")
spec = importlib.util.spec_from_file_location("ModAndroid", modandroid_path)
modandroid_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(modandroid_module)

# Load Telegram
telegram_path = os.path.join(modules_dir, "Telegram", "telegram_module.py")
spec = importlib.util.spec_from_file_location("telegram_module", telegram_path)
telegram_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(telegram_module)
```

## Thêm Module Mới

1. Tạo thư mục `modules/ModuleName/`
2. Tạo `modules/ModuleName/config/` và `modules/ModuleName/data/`
3. Tạo script chính `modules/ModuleName/module_name.py`
4. Update `Main.pyw` để import module mới
5. (Optional) Thêm `modules/ModuleName/bin/` nếu cần binary tools

Xem thêm: `HOW_TO_ADD_MODULE.md`

