/**
 * Supabase Client for TURFMAPP
 * Handles authentication and database operations
 */

'use strict';

/**
 * Supabase Configuration
 * Replace these with your actual Supabase project credentials
 */
const SUPABASE_CONFIG = {
    url: 'https://pwxhgvuyaxgavommtqpr.supabase.co',  // Your project URL
    anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB3eGhndnV5YXhnYXZvbW10cXByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYyMjA1OTcsImV4cCI6MjA3MTc5NjU5N30.n7i3AMpdRRBWA5AhNMdzO5qf_34w4Fo13adUBWsoevg'  // Your anon/public key
};

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
     * Load stored session from localStorage
     */
    loadStoredSession() {
        try {
            const storedSession = localStorage.getItem('sb-session');
            if (storedSession) {
                this.session = JSON.parse(storedSession);
                this.user = this.session?.user || null;
            }
        } catch (error) {
            console.error('Error loading stored session:', error);
            this.clearSession();
        }
    }

    /**
     * Store session in localStorage
     */
    storeSession(session) {
        if (session) {
            localStorage.setItem('sb-session', JSON.stringify(session));
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
            console.error('Google sign in error:', error);
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
            console.error('Auth callback error:', error);
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
            console.error('Sign out error:', error);
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
            console.error('Session refresh error:', error);
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

// Initialize global Supabase client
window.supabase = new SupabaseClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.anonKey);

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SupabaseClient };
}