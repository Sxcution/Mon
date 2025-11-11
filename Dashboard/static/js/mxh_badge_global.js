// Global MXH Badge - robust selectors + CSS fallback, zero UI render
(function () {
    // ===== Config =====
    const FETCH_URL = '/mxh/api/accounts';
    const INTERVAL_MS = 15000; // 15s
    const SELECTOR_CANDIDATES = [
        // khuyến nghị: add data-tab="mxh" vào nav link để bắt chắc 100%
        '[data-tab="mxh"]',
        '[data-route="mxh"]',
        // id thường gặp
        '#nav-mxh', '#mxh-nav', '#tab-mxh', '#mxhTab', '#mxh-tab',
        // link và hash
        'a[href="/mxh"]', 'a[href*="/mxh"]', 'a[href="#mxh"]', 'a[href*="#mxh"]', 'a.nav-link[href*="mxh"]',
        // bootstrap tabs / aria
        '[data-bs-target="#mxh"]', '[data-bs-target*="mxh"]',
        '[aria-controls="mxh"]', '[aria-controls*="mxh"]',
        'button[role="tab"][data-target*="mxh"]',
        'button[role="tab"][data-bs-target*="mxh"]',
        '.nav-link[data-target="mxh"]'
    ];

    // ===== CSS fallback (nếu thiếu link CSS) =====
    (function ensureCss() {
        if (document.querySelector('link[href*="mxh_badge.css"]') || document.getElementById('__mxh_badge_css__')) return;
        const css = `
        .nav-badge-container{position:absolute;top:-4px;right:-8px;z-index:10;pointer-events:none}
        .nav-badge{background-color:#dc3545;color:#fff;border-radius:50%;width:20px;height:20px;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;line-height:20px;animation:pulse 2s infinite;user-select:none;will-change:transform}
        @keyframes pulse{0%{transform:scale(1);box-shadow:0 0 0 0 rgba(220,53,69,.55)}70%{transform:scale(1.05);box-shadow:0 0 0 10px rgba(220,53,69,0)}100%{transform:scale(1);box-shadow:0 0 0 0 rgba(220,53,69,0)}}
        `;
        const style = document.createElement('style');
        style.id = '__mxh_badge_css__';
        style.textContent = css;
        document.head.appendChild(style);
    })();

    // ===== State =====
    let intervalId = null;
    let inFlight = false;
    let controller = null;
    let observer = null;
    let currentText = null;
    let currentCritical = false;

    // ===== Utils =====
    const norm = s => (s || '').toLowerCase()
        .normalize('NFD').replace(/\p{Diacritic}/gu, '');

    function findNavAnchors() {
        const set = new Set();
        // 1) selectors trực tiếp
        for (const sel of SELECTOR_CANDIDATES) {
            document.querySelectorAll(sel).forEach(el => set.add(el));
        }
        // 2) fallback theo text (MXH / Mạng xã hội) trong vùng nav/menu/tablist
        const scopes = document.querySelectorAll('nav, .navbar, .nav, .menu, [role="tablist"]');
        scopes.forEach(scope => {
            scope.querySelectorAll('a,button,.nav-link,[role="tab"],.nav-item').forEach(el => {
                const t = norm(el.textContent || el.getAttribute('aria-label') || '');
                if (t === 'mxh' || t.includes('mang xa hoi')) set.add(el);
            });
        });
        return Array.from(set);
    }

    function ensureBadge(anchor) {
        if (!anchor) return null;
        const cs = getComputedStyle(anchor);
        if (cs.position === 'static') {
            // ép relative để absolute con định vị theo anchor
            anchor.style.position = 'relative';
        }
        let container = anchor.querySelector('.nav-badge-container');
        if (!container) {
            container = document.createElement('span');
            container.className = 'nav-badge-container';
            const badge = document.createElement('span');
            badge.className = 'nav-badge';
            container.appendChild(badge);
            anchor.appendChild(container);
        }
        return container.querySelector('.nav-badge');
    }

    function setBadgeText(text, isCritical) {
        const anchors = findNavAnchors();
        if (anchors.length === 0) return;
        for (const a of anchors) {
            if (text === null) {
                a.querySelector('.nav-badge-container')?.remove();
                continue;
            }
            const badge = ensureBadge(a);
            if (!badge) continue;
            if (badge.textContent !== text) badge.textContent = text;
            const label = isCritical ? 'MXH có thông báo hết hạn' : 'MXH có mục cần chú ý';
            badge.setAttribute('aria-label', label);
            badge.title = label;
        }
    }

    function formatBadgeText(state) {
        if (state.showExclamation) return '!';
        const n = state.totalAttention;
        if (!n || n <= 0) return null;
        return n > 9 ? '9+' : String(n);
    }

    function computeBadgeState(accounts) {
        const now = Date.now();
        let expiredNoticeCount = 0;
        let oneYearNoHKChangeCount = 0;

        for (const acc of accounts) {
            // 1) notice hết hạn
            const notice = acc?.notice ?? acc?.notice_info ?? acc?.noticeStatus;
            if (notice) {
                const expired =
                    notice.expired === true ||
                    notice.status === 'expired' ||
                    notice.state === 'expired' ||
                    (notice.expires_at && new Date(notice.expires_at).getTime() <= now) ||
                    (notice.expiresAt && new Date(notice.expiresAt).getTime() <= now);
                if (expired) expiredNoticeCount++;
            }
            // 2) WeChat >= 1 năm chưa đổi số HK
            const platform = (acc?.platform || acc?.type || '').toLowerCase();
            const isWeChat = platform.includes('wechat') || platform === 'wx' || platform === 'weixin';
            if (isWeChat) {
                const createdAt = acc?.created_at ?? acc?.createdAt ?? acc?.created ?? acc?.joined_at;
                let ageDays = acc?.age_days ?? acc?.ageDays;
                if (!ageDays && createdAt) {
                    const t = new Date(createdAt).getTime();
                    if (Number.isFinite(t)) ageDays = Math.floor((now - t) / 86400000);
                }
                const lastChange =
                    acc?.hk_changed_at ??
                    acc?.last_number_change_at ??
                    acc?.hkChangedAt ??
                    acc?.lastNumberChangeAt;

                let changedDaysAgo = null;
                if (lastChange) {
                    const lt = new Date(lastChange).getTime();
                    if (Number.isFinite(lt)) changedDaysAgo = Math.floor((now - lt) / 86400000);
                }

                const isAgeGte1y =
                    (typeof ageDays === 'number' && ageDays >= 365) ||
                    (!!createdAt && Number.isFinite(new Date(createdAt).getTime()) &&
                        (now - new Date(createdAt).getTime()) >= 365 * 86400000);

                if (isAgeGte1y && (changedDaysAgo === null || changedDaysAgo >= 365)) {
                    oneYearNoHKChangeCount++;
                }
            }
        }

        const totalAttention = expiredNoticeCount + oneYearNoHKChangeCount;
        const showExclamation = expiredNoticeCount > 0;
        return { totalAttention, showExclamation, expiredNoticeCount, oneYearNoHKChangeCount };
    }

    async function fetchAccountsMinimal(signal) {
        const res = await fetch(FETCH_URL, {
            method: 'GET',
            credentials: 'same-origin',
            cache: 'no-store',
            signal
        }).catch(() => null);
        if (!res || !res.ok) return null;
        const json = await res.json().catch(() => null);
        if (!json) return null;
        const accounts = Array.isArray(json?.accounts) ? json.accounts
                        : Array.isArray(json?.data)    ? json.data
                        : Array.isArray(json)          ? json
                        : null;
        return accounts || null;
    }

    async function updateGlobalMXHBadge() {
        if (document.hidden) return;
        if (inFlight) return;
        try {
            inFlight = true;
            controller?.abort();
            controller = new AbortController();

            const accounts = await fetchAccountsMinimal(controller.signal);
            if (!accounts) { setBadgeText(null, false); return; }

            const state = computeBadgeState(accounts);
            const nextText = formatBadgeText(state);
            const nextCritical = !!state.showExclamation;

            if (nextText !== currentText || nextCritical !== currentCritical) {
                setBadgeText(nextText, nextCritical);
                currentText = nextText;
                currentCritical = nextCritical;
            }
        } catch (_) {
            /* silent fail */
        } finally {
            inFlight = false;
        }
    }

    function start() {
        if (intervalId !== null) return;
        updateGlobalMXHBadge();
        intervalId = window.setInterval(updateGlobalMXHBadge, INTERVAL_MS);
    }
    function stop() { if (intervalId !== null) { clearInterval(intervalId); intervalId = null; } }
    function onVisibilityChange() { if (document.hidden) stop(); else start(); }

    function ensureAnchorsThenStart() {
        if (findNavAnchors().length > 0) {
            start();
            observer?.disconnect(); observer = null;
            return;
        }
        if (!observer) {
            observer = new MutationObserver(() => {
                if (findNavAnchors().length > 0) {
                    start();
                    observer.disconnect(); observer = null;
                }
            });
            observer.observe(document.documentElement, { childList: true, subtree: true });
        }
    }

    function cleanup() {
        stop();
        controller?.abort(); controller = null;
        document.removeEventListener('visibilitychange', onVisibilityChange, { passive: true });
        window.removeEventListener('pagehide', cleanup, { passive: true });
        window.removeEventListener('beforeunload', cleanup, { passive: true });
        observer?.disconnect(); observer = null;
    }

    // Boot
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', ensureAnchorsThenStart, { once: true, passive: true });
    } else {
        ensureAnchorsThenStart();
    }
    document.addEventListener('visibilitychange', onVisibilityChange, { passive: true });
    window.addEventListener('pagehide', cleanup, { passive: true });
    window.addEventListener('beforeunload', cleanup, { passive: true });

    // manual hook
    window.__MXH_BADGE__ = { update: updateGlobalMXHBadge, start, stop };
})();