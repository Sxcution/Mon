# Create README markdown file with the finalized content
content = """# ⚙️ GPS Patcher for Android (v6.0 – Precision Optimized)
Công cụ tự động vá `services.jar` (AOSP/One UI/MIUI/…) để **fake GPS mà không bị phát hiện**.
## 🎯 Mục tiêu
- **Bypass AppOps**: Không cần bật “Vị trí mô phỏng”.
- **Hợp pháp hóa vị trí giả**: Dữ liệu đi qua hệ thống trông như vị trí thật từ phần cứng.
---
## 🧠 Cách hoạt động (2 điểm vá)
### 1) Bypass AppOps (chính xác)
- **Class**: `SystemAppOpsHelper.smali`
- **Thao tác**: *Chỉ* stub 2 hàm trả **boolean**:
  - `noteOp(...)Z` → `const/4 v0, 0x1` → `return v0`
  - `noteOpNoThrow(...)Z` → `const/4 v0, 0x1` → `return v0`
- **Không đụng**: `checkOpNoThrow(...)Z` **và** mọi biến thể **trả int** (e.g. `checkOp`, `noteProxyOp`, …) để tránh phá permission flow/`clearCallingIdentity`.
**Kết quả**: Hệ thống luôn “OK” quyền gửi vị trí (không cần mock location).
---
### 2) Hợp pháp hóa dữ liệu vị trí
- **Class/Method**: `MockLocationProvider.smali` → `setProviderLocation(Location)V`
- **Thao tác**:
  - Tool tự phát hiện thanh ghi boolean trong lệnh  
    `invoke-virtual {v0, <reg>}, Landroid/location/Location;->setIsFromMockProvider(Z)V`
  - **Chèn trước invoke**: `const/4 <reg>, 0x0`  *(đặt flag “không phải mock”)*  
  - **Nếu `<reg>` dùng tiếp ngay sau đó (thường làm độ dài `new-array`)**: **phục hồi** `const/4 <reg>, 0x1`
- **Lưu ý**: Không hard-code `p1`. Mỗi ROM có thể dùng thanh ghi khác.
**Kết quả**: Dữ liệu vị trí giả mang nhãn “thật”, qua mặt kiểm tra mock location.
---
## ✨ Điểm mạnh
- 🎯 **Chính xác**: Chỉ chạm 2 hàm `Z` trong `SystemAppOpsHelper`; giữ nguyên `checkOpNoThrow`.
- 🔧 **Phục hồi thanh ghi thông minh** sau `setIsFromMockProvider` → tránh crash `new-array`.
- ⚡ **Nhanh**: Giải nén/biên dịch **song song** nhiều `classes*.dex`.
- 🧩 **Multi-Dex full**: Tự xử lý `classes.dex`, `classes2.dex`, …
- 🧱 **Build an toàn**: Mỗi `smali*` → `classes*.dex` tương ứng, tránh lỗi `Unsigned short value out of range`.
- 📦 **Repack chuẩn**: Giữ thứ tự `classes*.dex`, nén DEFLATED, không thêm file lạ.
- 🗂️ **Thư mục rõ ràng**: `bin/java/{baksmali.jar, smali.jar}`, đầu ra nằm trong `GPS_Patched/`.
- 🏷️ **Đặt tên thông minh**: ví dụ `services_S20.jar` → `services_S20_patched.jar`.
---
## ⚙️ Yêu cầu
1. **Java** (JDK/JRE) — kiểm tra `java -version`.
2. **Thư mục công cụ**:
GPS_Patcher_Tool/
├── bin/
│ └── java/
│ ├── baksmali.jar
│ └── smali.jar
└── main.pyw (hoặc main.py)
Tải smali/baksmali từ trang phát hành chính thức.
3. **Python**: `pip install PyQt6`.
---
## 🚀 Cách dùng nhanh
1. Mở `main.pyw`.
2. Kéo-thả `services.jar` vào app (hoặc bấm “Chọn file”).
3. Bấm **Bắt đầu vá** và chờ hoàn tất.
4. Lấy file trong `GPS_Patched/` (ví dụ `services_S20_patched.jar`) và thay cho file gốc (Magisk/TWRP/chép đè – cần root).
---
## 🧪 Kiểm tra kết quả
- **Hệ thống**: `adb shell dumpsys location`  
→ xác nhận providers hoạt động bình thường (không crash, request cập nhật đều).
- **Ứng dụng**: mở app fake GPS, đặt tọa độ → Google Maps/game/bank nhận đúng vị trí.
- **So sánh smali (tuỳ chọn)**:
- `SystemAppOpsHelper.smali`: chỉ 2 hàm `noteOp/ noteOpNoThrow` trả `true`.
- `MockLocationProvider.smali`: trước `setIsFromMockProvider(Z)` gán `false`, sau đó **phục hồi** thanh ghi nếu còn dùng.
---
## 🛠️ Ghi chú kỹ thuật
- Không thay `.registers` trừ khi bắt buộc (cần ≥1 cho `v0`).
- Regex của tool **chỉ** áp vào đúng class `SystemAppOpsHelper` (tránh trúng `$$ExternalSyntheticLambda*`).
- Chênh lệch `.line` là bình thường, không ảnh hưởng hành vi.
---

⚙️ Android ROM Patcher v6.0
Một bộ công cụ GUI đa năng, giúp tự động hóa quá trình vá lỗi và tùy chỉnh các file hệ thống quan trọng trong các bản ROM Android (unpacked).

✨ Các chức năng chính
Tool được chia làm 3 tab với các mục đích sử dụng khác nhau:

⚙️ Tab 1: Auto Rom (Chế độ tự động)
Đây là chức năng chính và được khuyến nghị sử dụng để vá toàn diện một bản ROM.
Mục đích: Tự động quét, xác thực và vá lỗi đồng thời các file services.jar, build.prop, và init.rc trong một thư mục ROM.
Cách hoạt động:
Kéo và thả thư mục ROM (ví dụ 
system/) vào giao diện.
Tool sử dụng logic quét thông minh để tìm đúng file hệ thống quan trọng nhất, bỏ qua các file không liên quan (ví dụ 
init.rc trong apex/) và ưu tiên file init.rc chứa block on charger.
Cho phép xem trước nội dung file, vá lỗi riêng lẻ và mở thư mục chứa file trực tiếp từ giao diện.
Nhấn 
"Auto Patch" để vá tất cả các file đã tìm thấy trong một lần.
⚠️ Kết quả: Các file gốc sẽ bị ghi đè trực tiếp trong thư mục ROM của bạn để tiết kiệm thời gian
🛰️ Tab 2: GPS Patcher (Vá thủ công)
Mục đích: Chỉ vá riêng lẻ file services.jar để bypass mock location mà không bị các ứng dụng phát hiện.
Cách hoạt động: Kéo thả file services.jar và nhấn nút vá lỗi.
Kết quả: Tạo ra file _patched.jar và lưu vào thư mục Patched. 
Không ghi đè file gốc.
🔌 Tab 3: Auto Start & ADB (Vá thủ công)
Mục đích: Vá riêng lẻ các file build.prop và/hoặc init.rc để tự động kích hoạt ADB, các thuộc tính hệ thống khác, hoặc thêm tính năng tự khởi động khi cắm sạc.
Cách hoạt động: Kéo thả file build.prop và/hoặc init.rc rồi nhấn nút phân tích.
Kết quả: Tạo ra các file _mod, lưu vào thư mục Patched. 
Không ghi đè file gốc.
🛠️ Yêu cầu
Java (JDK/JRE): Cần thiết để chạy các tác vụ baksmali và smali.
Python 3 & PyQt6: Cài đặt bằng lệnh pip install PyQt6.
Cấu trúc thư mục: Tool cần được đặt trong cấu trúc thư mục đúng để có thể tìm thấy các thư viện Java.
ModAndroid/
├── GPS_Tool/
│   ├── bin/
│   │   └── java/
│   │       ├── baksmali.jar
│   │       └── smali.jar
│   └── ModAndroid.pyw
└── ... (các file khác)
🚀 Hướng dẫn sử dụng
Chế độ Auto Rom (Khuyến nghị)
Mở tool và chọn tab 
"Auto Rom".
Kéo và thả thư mục ROM của bạn vào cửa sổ ứng dụng.
Chờ tool quét xong. Các nút 
"Xem..." và "Auto Patch" sẽ sáng lên nếu tìm thấy file hợp lệ.
(Tùy chọn) Nhấn "Xem build.prop" hoặc "Xem init.rc" để kiểm tra nội dung, vá riêng lẻ hoặc mở thư mục chứa file.
Nhấn "🚀 Auto Patch" để vá tất cả các file đã tìm thấy. Các file gốc trong thư mục ROM của bạn sẽ được cập nhật.
Chế độ Thủ công (GPS Patcher / Auto Start & ADB)
Chọn tab chức năng tương ứng.
Kéo và thả các file cần vá (
services.jar, build.prop, init.rc) vào cửa sổ.
Nhấn nút 
"Bắt đầu vá lỗi" hoặc "Phân tích và Tự động lưu".
Vào thư mục 
Patched (được tạo cùng cấp với tool) để lấy các file đã vá và tự thay thế thủ công vào ROM của bạn.
🧠 Chi tiết kỹ thuật vá GPS
Bypass AppOps: Tool chỉ sửa 2 phương thức trả về kiểu boolean (noteOp, noteOpNoThrow) trong SystemAppOpsHelper.smali để luôn trả về true, trong khi giữ nguyên các phương thức checkOp để không phá vỡ logic quyền của hệ thống.
Hợp pháp hóa Vị trí: Trong MockLocationProvider.smali, tool tìm đến lệnh gọi setIsFromMockProvider(Z)V và chèn một lệnh để ép giá trị boolean thành false (0x0), đánh dấu vị trí là "thật". Tool cũng có khả năng khôi phục giá trị của thanh ghi ngay sau đó để tránh gây lỗi cho các logic liền kề.
## ⚠️ Miễn trừ trách nhiệm
Mod hệ thống có rủi ro **bootloop**. Sao lưu trước khi làm. Bạn tự chịu trách nhiệm khi sử dụng công cụ này.

