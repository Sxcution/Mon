/**
 * STool Dashboard - Global JavaScript Functions
 * File này chứa các functions dùng chung cho toàn bộ ứng dụng
 */

// ===== TOAST NOTIFICATION FUNCTION =====
/**
 * Hiển thị toast notification (Bootstrap Toast)
 * @param {string} message - Nội dung thông báo
 * @param {string} type - Loại thông báo ('success', 'error', 'info')
 * @param {string} title - Tiêu đề tùy chỉnh (optional)
 */
function showToast(message, type = 'success', title = 'Thông báo') {
    const toastEl = document.getElementById('liveToast');
    const toastHeader = document.getElementById('toastHeader');
    const toastTitle = document.getElementById('toastTitle');
    const toastBody = document.getElementById('toastBody');
    
    if (!toastEl) {
        console.warn('Toast element not found!');
        return;
    }
    
    // Set message
    toastBody.textContent = message;
    
    // Reset header classes
    toastHeader.className = 'toast-header';
    
    // Apply styling based on type
    if (type === 'success') {
        toastHeader.classList.add('bg-success', 'text-white');
        toastTitle.textContent = '✅ Thành công';
    } else if (type === 'error') {
        toastHeader.classList.add('bg-danger', 'text-white');
        toastTitle.textContent = '❌ Lỗi';
    } else if (type === 'warning') {
        toastHeader.classList.add('bg-warning', 'text-dark');
        toastTitle.textContent = '⚠️ Cảnh báo';
    } else {
        toastHeader.classList.add('bg-info', 'text-white');
        toastTitle.textContent = title;
    }
    
    // Show toast
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}

// ===== GLOBAL HELPERS =====
// Bạn có thể thêm các helper functions khác vào đây
// Ví dụ: formatDate, formatNumber, debounce, throttle, etc.


// ===== MODAL KEYBOARD SHORTCUTS =====
/**
 * Xử lý phím Enter và Esc cho tất cả modal
 * - Enter: Kích hoạt nút primary/danger trong modal
 * - Esc: Đóng modal (Bootstrap tự xử lý, nhưng có thể custom)
 */
document.addEventListener('DOMContentLoaded', function() {
    // Lắng nghe sự kiện khi modal được hiển thị
    document.addEventListener('shown.bs.modal', function(event) {
        const modal = event.target;
        
        // Tìm nút primary hoặc danger trong modal (ưu tiên danger cho modal xóa)
        const dangerBtn = modal.querySelector('.modal-footer .btn-danger');
        const primaryBtn = modal.querySelector('.modal-footer .btn-primary');
        const actionBtn = dangerBtn || primaryBtn;
        
        // Handler cho phím Enter
        const enterHandler = function(e) {
            if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.altKey) {
                // Không áp dụng nếu đang focus vào textarea
                if (document.activeElement.tagName === 'TEXTAREA') {
                    return;
                }
                
                e.preventDefault();
                if (actionBtn && !actionBtn.disabled) {
                    actionBtn.click();
                }
            }
        };
        
        // Thêm event listener
        modal.addEventListener('keydown', enterHandler);
        
        // Cleanup khi modal bị đóng
        modal.addEventListener('hidden.bs.modal', function() {
            modal.removeEventListener('keydown', enterHandler);
        }, { once: true });
    });
});

/* === Smart Token Feature === */

/**
 * 📋 Hàm copy text vào clipboard
 * @param {string} textToCopy - Đoạn text cần copy
 */
async function copyToClipboard(textToCopy) {
    try {
        await navigator.clipboard.writeText(textToCopy);
        
        // 🔍 Tạo thông báo "Đã copy"
        const tempDiv = document.createElement('div');
        tempDiv.textContent = `Đã copy: ${textToCopy}`;
        tempDiv.style.cssText = `
            position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
            background-color: rgba(0, 0, 0, 0.7); color: white; padding: 8px 15px;
            border-radius: 5px; font-size: 14px; z-index: 1000;
            transition: opacity 0.5s ease-out;
        `;
        document.body.appendChild(tempDiv);
        setTimeout(() => {
            tempDiv.style.opacity = '0';
            setTimeout(() => tempDiv.remove(), 500);
        }, 1500);

    } catch (err) {
        console.error('🔍 Không thể copy:', err);
    }
}

/**
 * 🚀 Hàm chính để tìm và thay thế các token
 * @param {HTMLElement} container - Phần tử HTML (ví dụ: div) chứa nội dung cần xử lý
 */
function processSmartTokens(container) {
    if (!container) return;

    // 🔍 Định nghĩa Regular Expressions
    const mentionRegex = /(^|\s|[\.,;!?()])(@[a-zA-Z0-9_]{3,32})(?![a-zA-Z0-9_])/g;
    const numberRegex = /(?<![a-zA-Z0-9])(\d{4,})(?![a-zA-Z0-9])/g; // >= 4 chữ số

    // 🔍 Dùng TreeWalker để chỉ duyệt qua các Text Node (hiệu quả nhất)
    const walker = document.createTreeWalker(
        container,
        NodeFilter.SHOW_TEXT,
        {
            acceptNode: function(node) {
                // 🔍 Bỏ qua các node đã xử lý hoặc trong script/style
                if (node.parentElement.closest('script, style, .smart-token')) {
                    return NodeFilter.FILTER_REJECT;
                }
                // 🔍 Chỉ xử lý node có ký tự @ hoặc số (tối ưu)
                if (node.nodeValue.includes('@') || /\d{4,}/.test(node.nodeValue)) {
                    return NodeFilter.FILTER_ACCEPT;
                }
                return NodeFilter.FILTER_REJECT;
            }
        }
    );

    const nodesToProcess = [];
    while (walker.nextNode()) {
        nodesToProcess.push(walker.currentNode);
    }

    // 🔍 Xử lý các node (phải làm sau khi duyệt xong để tránh lỗi)
    nodesToProcess.forEach(textNode => {
        const parent = textNode.parentNode;
        const text = textNode.nodeValue;
        const fragment = document.createDocumentFragment();
        let lastIndex = 0;

        // 🔍 Tạo mảng chứa tất cả các vị trí khớp (@ và số)
        const matches = [];
        let match;

        // 🔍 Tìm @username
        while ((match = mentionRegex.exec(text)) !== null) {
            const startIndex = match.index + match[1].length;
            matches.push({
                start: startIndex,
                end: startIndex + match[2].length,
                text: match[2]
            });
        }
        mentionRegex.lastIndex = 0; // Reset

        // 🔍 Tìm số
        while ((match = numberRegex.exec(text)) !== null) {
            matches.push({
                start: match.index,
                end: match.index + match[1].length,
                text: match[1]
            });
        }
        numberRegex.lastIndex = 0; // Reset

        // 🔍 Sắp xếp các match theo vị trí bắt đầu
        matches.sort((a, b) => a.start - b.start);

        // 🔍 Bọc các match bằng <span>
        matches.forEach(m => {
            if (m.start > lastIndex) {
                fragment.appendChild(document.createTextNode(text.substring(lastIndex, m.start)));
            }
            const span = document.createElement('span');
            span.className = 'smart-token';
            span.textContent = m.text;
            span.dataset.copyValue = m.text; // Lưu giá trị vào data- attribute
            fragment.appendChild(span);
            lastIndex = m.end;
        });

        // 🔍 Thêm phần text còn lại
        if (lastIndex < text.length) {
            fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
        }

        // 🔍 Thay thế text node cũ bằng fragment mới
        if (fragment.childNodes.length > 0) {
            parent.replaceChild(fragment, textNode);
        }
    });
}

/* === Kết thúc Smart Token Feature === */

/* === Kích hoạt Smart Token (Chỉ áp dụng cho tab Ghi chú) === */

document.addEventListener('DOMContentLoaded', () => {
    // Chỉ chạy Smart Token nếu đang ở trang Ghi chú (/notes)
    if (window.location.pathname === '/notes' || window.location.pathname.startsWith('/notes/')) {
        console.log('🔍 Smart Token: Activating for Notes tab.');

        // Xác định vùng chứa nội dung cho Notes
        const notesContainer = document.getElementById('notes-container');
        const notesDetailContent = document.getElementById('notes-detail-content');
        
        // ⚠️ CHỈ chạy nếu tìm thấy Notes container
        if (!notesDetailContent && !notesContainer) {
            console.log('🔍 Smart Token: Notes container not found, skipping.');
            return;
        }
        
        const containerToProcess = notesDetailContent || notesContainer;

        // Chạy hàm xử lý ban đầu
        processSmartTokens(containerToProcess);

        // Thêm trình nghe sự kiện Click (dùng event delegation)
        containerToProcess.addEventListener('click', (event) => {
            const target = event.target;
            // Kiểm tra xem có click đúng vào .smart-token không
            if (target.classList.contains('smart-token') && target.dataset.copyValue) {
                event.preventDefault();
                copyToClipboard(target.dataset.copyValue);
            }
        });

        // ❌ DISABLED MutationObserver - Notes đã có auto-detect riêng
        // MutationObserver gây conflict với auto-detect trong editor
        console.log('🔍 Smart Token: MutationObserver disabled (Notes has its own auto-detection).');
        
        /* COMMENTED OUT TO PREVENT CONFLICTS
        // Observer để xử lý nội dung được load động (AJAX) trong Ghi chú
        if (window.MutationObserver) {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach((node) => {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                // Chỉ xử lý nếu node được thêm vào trong container của Notes
                                if (containerToProcess.contains(node)) {
                                    console.log('🔍 Smart Token: Processing dynamically added content in Notes.');
                                    processSmartTokens(node);
                                }
                            }
                        });
                    }
                });
            });

            // Quan sát thay đổi trong container của Notes
            observer.observe(containerToProcess, {
                childList: true,
                subtree: true
            });
        }
        */
    }
});

/* === Kết thúc Kích hoạt Smart Token === */

