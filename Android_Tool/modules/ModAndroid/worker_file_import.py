"""
Worker Module cho File I/O Operations
Xử lý các thao tác copy, unzip, scan file nặng trên background thread
Tránh "Not Responding" khi xử lý file lớn

Author: Mon
AI Assistant: Claude Sonnet 4.5
"""

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from pathlib import Path
import os
import zipfile
import time


class FileImportWorker(QObject):
    """
    Worker để import file lớn (copy + unzip) mà không block UI thread
    
    Signals:
        progress: int (0-100) - Tiến độ công việc
        log: str - Log message để hiển thị
        finished: str - Đường dẫn file đích khi hoàn thành
        error: str - Thông báo lỗi
        cancelled: void - Báo hiệu đã hủy
    """
    
    progress = pyqtSignal(int)      # 0..100
    log = pyqtSignal(str)           # Log message
    finished = pyqtSignal(str)      # Destination path
    error = pyqtSignal(str)         # Error message
    cancelled = pyqtSignal()        # Cancelled signal
    
    def __init__(self, src_path: str, dst_dir: str, *, unzip=False, chunk_mb: int = 16):
        """
        Args:
            src_path: Đường dẫn file nguồn
            dst_dir: Thư mục đích
            unzip: True nếu cần giải nén file .zip sau khi copy
            chunk_mb: Kích thước chunk đọc/ghi (MB), mặc định 16MB
        """
        super().__init__()
        self.src = Path(src_path)
        self.dst_dir = Path(dst_dir)
        self.unzip = unzip
        self.chunk = max(1, chunk_mb) * 1024 * 1024  # Convert to bytes
        self._cancel = False
        
    @pyqtSlot()
    def run(self):
        """Main worker logic - chạy trên background thread"""
        try:
            # 🔍 DEBUG: Bắt đầu import
            self.log.emit(f"🔍 [FileImportWorker] Bắt đầu import: {self.src.name}")
            self.log.emit(f"🔍 [FileImportWorker] Chunk size: {self.chunk // 1024 // 1024}MB")
            
            # Tạo thư mục đích nếu chưa có
            self.dst_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy file với progress
            dst = self.dst_dir / self.src.name
            total = os.path.getsize(self.src)
            done = 0
            
            self.log.emit(f"🔍 [FileImportWorker] File size: {total / 1024 / 1024:.2f}MB")
            self.log.emit(f"📋 Đang copy {self.src.name}...")
            
            start_time = time.time()
            
            with open(self.src, "rb", buffering=self.chunk) as rf, \
                 open(dst, "wb", buffering=self.chunk) as wf:
                
                while True:
                    # Check cancel flag
                    if self._cancel:
                        self.log.emit("🔍 [FileImportWorker] Cancel detected, cleaning up...")
                        try:
                            dst.unlink()
                        except Exception:
                            pass
                        self.cancelled.emit()
                        return
                    
                    # Read chunk
                    buf = rf.read(self.chunk)
                    if not buf:
                        break
                    
                    # Write chunk
                    wf.write(buf)
                    done += len(buf)
                    
                    # Update progress (emit mỗi chunk để không spam)
                    if total:
                        progress_pct = int(done * 100 / total)
                        self.progress.emit(progress_pct)
            
            elapsed = time.time() - start_time
            speed_mbps = (total / 1024 / 1024) / elapsed if elapsed > 0 else 0
            self.log.emit(f"✅ Copy hoàn thành → {dst.name} ({speed_mbps:.2f} MB/s)")
            
            # Unzip nếu cần
            if self.unzip and dst.suffix.lower() == ".zip":
                self.log.emit(f"🔍 [FileImportWorker] Bắt đầu giải nén...")
                self.log.emit(f"📦 Đang giải nén {dst.name}...")
                
                with zipfile.ZipFile(dst) as zf:
                    members = zf.infolist()
                    total_members = len(members)
                    
                    self.log.emit(f"🔍 [FileImportWorker] Tổng số file: {total_members}")
                    
                    for i, m in enumerate(members, 1):
                        # Check cancel
                        if self._cancel:
                            self.log.emit("🔍 [FileImportWorker] Cancel during unzip")
                            self.cancelled.emit()
                            return
                        
                        # Extract file
                        zf.extract(m, self.dst_dir)
                        
                        # Update progress (emit mỗi 10 file hoặc 5% để giảm spam)
                        if i % 10 == 0 or i == total_members:
                            progress_pct = int(i * 100 / total_members)
                            self.progress.emit(progress_pct)
                            
                            # Log mỗi 100 file để không spam
                            if i % 100 == 0:
                                self.log.emit(f"🔍 [FileImportWorker] Đã giải nén {i}/{total_members} file...")
                
                self.log.emit(f"✅ Giải nén hoàn thành: {total_members} file")
            
            # Emit finished signal
            self.log.emit("🔍 [FileImportWorker] Hoàn thành thành công")
            self.finished.emit(str(dst))
            
        except Exception as e:
            self.log.emit(f"🔍 [FileImportWorker] Exception: {type(e).__name__}: {e}")
            self.error.emit(f"Lỗi: {repr(e)}")
    
    @pyqtSlot()
    def cancel(self):
        """Đánh dấu để hủy công việc"""
        self.log.emit("🔍 [FileImportWorker] Cancel requested")
        self._cancel = True


class ZipExtractWorker(QObject):
    """
    Worker chuyên dụng cho giải nén file .zip lớn
    Xử lý theo từng file, emit progress chi tiết
    """
    
    progress = pyqtSignal(int)      # 0..100
    log = pyqtSignal(str)
    finished = pyqtSignal(str)      # Extract directory
    error = pyqtSignal(str)
    cancelled = pyqtSignal()
    
    def __init__(self, zip_path: str, extract_dir: str):
        super().__init__()
        self.zip_path = Path(zip_path)
        self.extract_dir = Path(extract_dir)
        self._cancel = False
    
    @pyqtSlot()
    def run(self):
        """Extract zip file với progress chi tiết"""
        try:
            self.log.emit(f"🔍 [ZipExtractWorker] Bắt đầu giải nén: {self.zip_path.name}")
            
            # Tạo thư mục extract nếu chưa có
            self.extract_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                members = zf.infolist()
                total = len(members)
                
                self.log.emit(f"🔍 [ZipExtractWorker] Tổng số file: {total}")
                
                for i, member in enumerate(members, 1):
                    if self._cancel:
                        self.log.emit("🔍 [ZipExtractWorker] Cancelled")
                        self.cancelled.emit()
                        return
                    
                    # Extract file
                    zf.extract(member, self.extract_dir)
                    
                    # Update progress mỗi file hoặc mỗi 5%
                    if i % 10 == 0 or i == total:
                        progress_pct = int(i * 100 / total)
                        self.progress.emit(progress_pct)
                    
                    # Log mỗi 100 file
                    if i % 100 == 0:
                        self.log.emit(f"  Đã giải nén {i}/{total} file...")
            
            self.log.emit(f"✅ Giải nén hoàn thành: {total} file → {self.extract_dir}")
            self.finished.emit(str(self.extract_dir))
            
        except Exception as e:
            self.log.emit(f"🔍 [ZipExtractWorker] Error: {e}")
            self.error.emit(f"Lỗi giải nén: {repr(e)}")
    
    @pyqtSlot()
    def cancel(self):
        """Request cancel"""
        self._cancel = True


class FileScanWorker(QObject):
    """
    Worker để scan thư mục tìm file (không block UI)
    Dùng cho File Manager hoặc scan ROM directory
    """
    
    progress = pyqtSignal(int)      # Số file đã scan
    log = pyqtSignal(str)
    finished = pyqtSignal(list)     # Danh sách file tìm thấy
    error = pyqtSignal(str)
    cancelled = pyqtSignal()
    
    def __init__(self, root_dir: str, pattern: str = "*", recursive: bool = True):
        """
        Args:
            root_dir: Thư mục gốc để scan
            pattern: Pattern file cần tìm (vd: "*.jar", "*.prop")
            recursive: True nếu scan đệ quy vào subfolder
        """
        super().__init__()
        self.root_dir = Path(root_dir)
        self.pattern = pattern
        self.recursive = recursive
        self._cancel = False
    
    @pyqtSlot()
    def run(self):
        """Scan directory để tìm file"""
        try:
            self.log.emit(f"🔍 [FileScanWorker] Bắt đầu scan: {self.root_dir}")
            
            results = []
            count = 0
            
            if self.recursive:
                # Scan đệ quy
                for root, dirs, files in os.walk(self.root_dir):
                    if self._cancel:
                        self.cancelled.emit()
                        return
                    
                    for file in files:
                        if self._cancel:
                            self.cancelled.emit()
                            return
                        
                        count += 1
                        full_path = os.path.join(root, file)
                        
                        # Check pattern match
                        if Path(file).match(self.pattern):
                            results.append(full_path)
                        
                        # Update progress mỗi 100 file
                        if count % 100 == 0:
                            self.progress.emit(count)
            else:
                # Scan chỉ trong thư mục hiện tại
                for item in self.root_dir.iterdir():
                    if self._cancel:
                        self.cancelled.emit()
                        return
                    
                    if item.is_file() and item.match(self.pattern):
                        results.append(str(item))
                        count += 1
            
            self.log.emit(f"✅ Scan hoàn thành: Tìm thấy {len(results)}/{count} file match")
            self.finished.emit(results)
            
        except Exception as e:
            self.log.emit(f"🔍 [FileScanWorker] Error: {e}")
            self.error.emit(f"Lỗi scan: {repr(e)}")
    
    @pyqtSlot()
    def cancel(self):
        """Request cancel"""
        self._cancel = True









