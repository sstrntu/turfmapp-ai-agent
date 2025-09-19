/**
 * Supabase Client for TURFMAPP
 * Handles authentication and database operations
 */

'use strict';

/**
 * Supabase Configuration
 * Loads configuration from environment or backend
 */
let SUPABASE_CONFIG = {
    url: null,
    anonKey: null
};

// Load configuration from backend
async function loadSupabaseConfig() {
    try {
        const response = await fetch('/api/config/supabase');
        if (response.ok) {
            SUPABASE_CONFIG = await response.json();
        } else {
            throw new Error('Failed to load configuration');
        }
    } catch (error) {
        // Config loading failed - fallback for dev only
        if (window.location.hostname === 'localhost') {
            SUPABASE_CONFIG = {
                url: window.SUPABASE_URL || null,
                anonKey: window.SUPABASE_ANON_KEY || null
            };
        }
    }
}

/**
 * Simple Supabase Client Implementation
 * Using vanilla JS to match the existing codebase style
 */
class SupabaseClient {
    constructor(url, anonKey) {
        this.url = url;
        this.anonKey = anonKey;
        this.session = null;
        this.user = null;
        this._refreshTimerId = null;
        
        // Initialize from stored session
        this.loadStoredSession();
        // Schedule refresh if a session exists
        this._scheduleRefresh();
    }

    /**
     * Load stored session from secure storage
     */
    loadStoredSession() {
        try {
            // Use secure storage if available, fallback to localStorage
            let storedSession = null;
            if (window.secureStorage) {
                storedSession = window.secureStorage.getSecure('session');
            } else {
                const sessionData = localStorage.getItem('sb-session');
                storedSession = sessionData ? JSON.parse(sessionData) : null;
            }

            if (storedSession) {
                this.session = storedSession;
                this.user = this.session?.user || null;
            }
        } catch (error) {
            // Session loading failed - clear session
            this.clearSession();
        }
    }

    /**
     * Store session in secure storage
     */
    storeSession(session) {
        if (session) {
            // Use secure storage if available, fallback to localStorage
            if (window.secureStorage) {
                window.secureStorage.setSecure('session', session);
            } else {
                localStorage.setItem('sb-session', JSON.stringify(session));
            }

            this.session = session;
            this.user = session.user;
            this._scheduleRefresh();
        } else {
            this.clearSession();
        }
    }

    /**
     * Clear session
     */
    clearSession() {
        // Clear from both secure storage and localStorage
        if (window.secureStorage) {
            window.secureStorage.removeSecure('session');
        }
        localStorage.removeItem('sb-session');

        this.session = null;
        this.user = null;
        if (this._refreshTimerId) {
            clearTimeout(this._refreshTimerId);
            this._refreshTimerId = null;
        }
    }

    /**
     * Get current session
     */
    getSession() {
        return this.session;
    }

    /**
     * Get current user
     */
    getUser() {
        return this.user;
    }

    /**
     * Get access token
     */
    getAccessToken() {
        return this.session?.access_token || null;
    }

    /**
     * Sign in with Google
     */
    async signInWithGoogle() {
        try {
            // Redirect to Supabase Google OAuth
            // The redirect_to parameter tells Supabase where to redirect after successful auth
            const redirectUrl = `${window.location.origin}/auth-callback.html`;
            const authUrl = `${this.url}/auth/v1/authorize?provider=google&redirect_to=${encodeURIComponent(redirectUrl)}`;
            
            // Redirect directly to home after authentication
            localStorage.setItem('auth-return-url', '/home.html');
            
            window.location.href = authUrl;
        } catch (error) {
            throw new Error('Failed to initiate Google sign in');
        }
    }

    /**
     * Handle OAuth callback
     */
    async handleAuthCallback() {
        try {
            const urlParams = new URLSearchParams(window.location.hash.substring(1));
            const accessToken = urlParams.get('access_token');
            const refreshToken = urlParams.get('refresh_token');
            
            if (accessToken) {
                // Get user info from Supabase
                const userResponse = await fetch(`${this.url}/auth/v1/user`, {
                    headers: {
                        'Authorization': `Bearer ${accessToken}`,
                        'apikey': this.anonKey
                    }
                });

                if (userResponse.ok) {
                    const userData = await userResponse.json();
                    
                    const session = {
                        access_token: accessToken,
                        refresh_token: refreshToken,
                        user: userData,
                        expires_at: Date.now() + (3600 * 1000) // 1 hour
                    };

                    this.storeSession(session);
                    return session;
                }
            }
            
            throw new Error('Invalid callback parameters');
        } catch (error) {
            throw error;
        }
    }

    /**
     * Sign out
     */
    async signOut() {
        try {
            if (this.session) {
                // Call Supabase sign out endpoint
                await fetch(`${this.url}/auth/v1/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.session.access_token}`,
                        'apikey': this.anonKey
                    }
                });
            }
        } catch (error) {
            // Sign out error - continue with cleanup
        } finally {
            this.clearSession();
        }
    }

    /**
     * Check if session is valid
     */
    isSessionValid() {
        if (!this.session || !this.session.access_token) {
            return false;
        }

        // Check if token is expired
        if (this.session.expires_at && Date.now() > this.session.expires_at) {
            return false;
        }

        return true;
    }

    /**
     * Refresh session if needed
     */
    async refreshSession() {
        if (!this.session?.refresh_token) {
            return null;
        }

        try {
            const response = await fetch(`${this.url}/auth/v1/token?grant_type=refresh_token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'apikey': this.anonKey
                },
                body: JSON.stringify({
                    refresh_token: this.session.refresh_token
                })
            });

            if (response.ok) {
                const data = await response.json();
                const newSession = {
                    access_token: data.access_token,
                    refresh_token: data.refresh_token || this.session.refresh_token,
                    user: data.user,
                    expires_at: Date.now() + (3600 * 1000)
                };

                this.storeSession(newSession);
                return newSession;
            }
        } catch (error) {
            // Session refresh failed
        }

        // Refresh failed, clear session
        this.clearSession();
        return null;
    }

    /**
     * Schedule token refresh shortly before expiry
     */
    _scheduleRefresh() {
        if (!this.session?.expires_at) return;

        // Refresh 60 seconds before expiry (minimum 10s from now)
        const msUntilRefresh = Math.max(this.session.expires_at - Date.now() - 60_000, 10_000);

        if (this._refreshTimerId) clearTimeout(this._refreshTimerId);
        this._refreshTimerId = setTimeout(async () => {
            try {
                await this.refreshSession();
            } catch (_) {
                // ignore; isSessionValid will fail and guards will redirect as needed
            }
        }, msUntilRefresh);
    }

    /**
     * Make authenticated API request to backend
     */
    async apiRequest(endpoint, options = {}) {
        // Ensure session is valid
        if (!this.isSessionValid()) {
            await this.refreshSession();
        }

        if (!this.isSessionValid()) {
            throw new Error('Not authenticated');
        }

        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAccessToken()}`
            }
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        const response = await fetch(endpoint, mergedOptions);
        
        if (response.status === 401) {
            // Token expired, try refresh
            await this.refreshSession();
            if (this.isSessionValid()) {
                // Retry with new token
                mergedOptions.headers.Authorization = `Bearer ${this.getAccessToken()}`;
                return fetch(endpoint, mergedOptions);
            } else {
                throw new Error('Authentication failed');
            }
        }

        return response;
    }
}

// Initialize global Supabase client after config loads
window.supabase = null;

// Initialize client once config is loaded
async function initializeSupabaseClient() {
    await loadSupabaseConfig();
    if (SUPABASE_CONFIG.url && SUPABASE_CONFIG.anonKey) {
        window.supabase = new SupabaseClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.anonKey);
    } else {
        throw new Error('Supabase configuration not available');
    }
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', initializeSupabaseClient);

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SupabaseClient };
}