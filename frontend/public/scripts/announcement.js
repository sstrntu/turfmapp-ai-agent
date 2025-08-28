'use strict';

/**
 * Shared Announcement utility
 * - Reads/writes the announcement message from localStorage
 * - Initializes a header display and keeps it in sync via the storage event
 */
const Announcement = {
    get() {
        try { return localStorage.getItem('announcement') || ''; } catch (_) { return ''; }
    },
    save(text) {
        try {
            const value = (text || '').trim();
            localStorage.setItem('announcement', value);
            // Notify open tabs
            window.dispatchEvent(new StorageEvent('storage', { key: 'announcement', newValue: value }));
        } catch (_) {}
    },
    clear() { this.save(''); },
    /**
     * Bind a header display container and text span by id
     */
    initHeader(containerId, textId) {
        function render() {
            const el = document.getElementById(containerId);
            const txt = document.getElementById(textId);
            if (!el || !txt) return;
            const value = Announcement.get();
            if (value) {
                txt.textContent = value;
                el.style.display = 'flex';
            } else {
                el.style.display = 'none';
            }
        }
        document.addEventListener('DOMContentLoaded', render);
        window.addEventListener('storage', function(e){ if (e.key === 'announcement') render(); });
        // Also expose manual refresh
        Announcement.refresh = render;
    }
};

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Announcement };
}


