/**
 * Console Mirror - In-Page Fallback
 * Captures console.*, window.onerror, unhandledrejection
 * Sends logs to Flask backend via /__console
 */
(function() {
    'use strict';
    
    // Configuration
    const ENDPOINT = '/__console';
    const BATCH_SIZE = 20;
    const BATCH_INTERVAL = 100; // ms
    const MAX_BATCH_BYTES = 10 * 1024; // 10KB
    const MAX_STACK_LENGTH = 2000;
    const MAX_MESSAGE_LENGTH = 2000;
    
    // Store original console methods
    const origConsole = {
        debug: console.debug,
        log: console.log,
        info: console.info,
        warn: console.warn,
        error: console.error
    };
    
    // Log queue
    let logQueue = [];
    let flushTimer = null;
    
    /**
     * Truncate string if too long
     */
    function truncate(str, maxLen) {
        if (!str) return '';
        str = String(str);
        return str.length > maxLen ? str.substring(0, maxLen) + '... (truncated)' : str;
    }
    
    /**
     * Stringify arguments safely
     */
    function stringifyArgs(args) {
        return Array.from(args).map(arg => {
            if (arg === null) return 'null';
            if (arg === undefined) return 'undefined';
            if (typeof arg === 'object') {
                try {
                    return JSON.stringify(arg, null, 2);
                } catch (e) {
                    return String(arg);
                }
            }
            return String(arg);
        }).join(' ');
    }
    
    /**
     * Add log to queue
     */
    function queueLog(level, message, stack, error) {
        try {
            const logEntry = {
                level: level,
                message: truncate(message, MAX_MESSAGE_LENGTH),
                stack: stack ? truncate(stack, MAX_STACK_LENGTH) : '',
                url: window.location.href,
                line: error && error.lineno ? error.lineno : 0,
                col: error && error.colno ? error.colno : 0,
                ts: Date.now() / 1000
            };
            
            logQueue.push(logEntry);
            
            // Schedule flush if not already scheduled
            if (!flushTimer) {
                flushTimer = setTimeout(flushLogs, BATCH_INTERVAL);
            }
            
            // Immediate flush if queue is full
            if (logQueue.length >= BATCH_SIZE) {
                flushLogs();
            }
        } catch (e) {
            // Silent fail - don't break page
        }
    }
    
    /**
     * Flush logs to server
     */
    function flushLogs() {
        if (flushTimer) {
            clearTimeout(flushTimer);
            flushTimer = null;
        }
        
        if (logQueue.length === 0) return;
        
        const batch = logQueue.splice(0, BATCH_SIZE);
        const payload = JSON.stringify({ logs: batch });
        
        // Check size limit
        const payloadSize = new Blob([payload]).size;
        if (payloadSize > MAX_BATCH_BYTES) {
            console.warn('[Console Mirror] Batch too large, dropping:', payloadSize, 'bytes');
            return;
        }
        
        // Send using sendBeacon (preferred - doesn't block page unload)
        if (navigator.sendBeacon) {
            try {
                const blob = new Blob([payload], { type: 'application/json' });
                const sent = navigator.sendBeacon(ENDPOINT, blob);
                if (!sent) {
                    // Fallback to fetch
                    sendViaFetch(payload);
                }
                return;
            } catch (e) {
                // Fallback to fetch
            }
        }
        
        // Fallback: fetch with keepalive
        sendViaFetch(payload);
    }
    
    /**
     * Send via fetch (fallback)
     */
    function sendViaFetch(payload) {
        fetch(ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: payload,
            keepalive: true  // Don't cancel on page unload
        }).catch(err => {
            // Silent fail
        });
    }
    
    /**
     * Hook console methods
     */
    function hookConsole(level) {
        console[level] = function(...args) {
            // Call original first (preserve dev console)
            origConsole[level].apply(console, args);
            
            // Queue for server
            const message = stringifyArgs(args);
            queueLog(level, message, null, null);
        };
    }
    
    // Hook all console methods
    hookConsole('debug');
    hookConsole('log');
    hookConsole('info');
    hookConsole('warn');
    hookConsole('error');
    
    /**
     * Capture window.onerror
     */
    const origOnError = window.onerror;
    window.onerror = function(message, source, lineno, colno, error) {
        const stack = error && error.stack ? error.stack : '';
        queueLog('error', message, stack, { lineno, colno });
        
        // Call original handler if exists
        if (origOnError) {
            return origOnError.apply(this, arguments);
        }
        return false;
    };
    
    /**
     * Capture unhandledrejection (Promise errors)
     */
    window.addEventListener('unhandledrejection', function(event) {
        const reason = event.reason;
        const message = reason && reason.message ? reason.message : String(reason);
        const stack = reason && reason.stack ? reason.stack : '';
        queueLog('error', '[Promise] ' + message, stack, null);
    });
    
    /**
     * Flush on page unload
     */
    window.addEventListener('beforeunload', function() {
        flushLogs();
    });
    
    /**
     * Flush periodically (every 5 seconds if there are logs)
     */
    setInterval(function() {
        if (logQueue.length > 0) {
            flushLogs();
        }
    }, 5000);
    
    console.log('[Console Mirror] Initialized - logs will be sent to backend');
})();
