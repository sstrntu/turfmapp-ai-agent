'use strict';

/**
 * Shared Announcement utility
 * - Fetches active announcements from backend API
 * - Caches in localStorage for offline access
 * - Initializes a header display and keeps it in sync via the storage event
 */
const Announcement = {
    /**
     * Fetch active announcements from backend API
     */
    async fetch() {
        try {
            const response = await fetch('/api/v1/admin/announcements/active', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const announcements = await response.json();
                // Get the most recent active announcement
                if (announcements && announcements.length > 0) {
                    const announcement = announcements[0].content;
                    // Cache in localStorage
                    localStorage.setItem('announcement', announcement);
                    return announcement;
                } else {
                    // No active announcements
                    localStorage.setItem('announcement', '');
                    return '';
                }
            } else {
                // API error, fall back to cache
                return this.getFromCache();
            }
        } catch (error) {
            console.warn('Failed to fetch announcements from API:', error);
            // Fall back to cached value
            return this.getFromCache();
        }
    },

    /**
     * Get announcement from localStorage cache
     */
    getFromCache() {
        try { return localStorage.getItem('announcement') || ''; } catch (_) { return ''; }
    },

    /**
     * Get announcement (tries API first, falls back to cache)
     */
    async get() {
        return await this.fetch();
    },

    /**
     * Get announcement synchronously from cache only
     */
    getSync() {
        return this.getFromCache();
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
        async function render() {
            const el = document.getElementById(containerId);
            const txt = document.getElementById(textId);
            if (!el || !txt) return;

            // First show cached value immediately for fast loading
            const cachedValue = Announcement.getFromCache();
            if (cachedValue) {
                txt.textContent = cachedValue;
                el.style.display = 'flex';
            }

            // Then fetch from API to get latest
            const value = await Announcement.get();
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


