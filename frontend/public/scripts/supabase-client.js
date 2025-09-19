/**
 * Supabase Client for TURFMAPP
 * Handles authentication and database operations
 */

'use strict';

/**
 * Supabase Configuration
 * Loaded dynamically from backend to avoid hardcoding credentials
 */
let SUPABASE_CONFIG = null;

/**
 * Load configuration from backend
 */
async function loadSupabaseConfig() {
    if (SUPABASE_CONFIG) return SUPABASE_CONFIG;

    try {
        const backendUrl = window.location.origin.replace(':3005', ':8000');
        const response = await fetch(`${backendUrl}/api/v1/config/frontend`);
        const config = await response.json();

        SUPABASE_CONFIG = {
            url: config.supabase.url,
            anonKey: config.supabase.anonKey
        };

        return SUPABASE_CONFIG;
    } catch (error) {
        console.error('Failed to load Supabase config:', error);
        // Fallback to prevent app from breaking - but should not contain real credentials in production
        console.warn('Using fallback config - ensure backend is running');
        SUPABASE_CONFIG = {
            url: 'https://placeholder.supabase.co',
            anonKey: 'placeholder-key'
        };
        return SUPABASE_CONFIG;
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
     * Simple encryption for session data (client-side protection)
     * Note: This is not a substitute for server-side security
     */
    _encryptSession(sessionData) {
        try {
            // Simple XOR encryption with a dynamic key based on browser characteristics
            const key = this._getClientKey();
            const jsonStr = JSON.stringify(sessionData);
            let encrypted = '';

            for (let i = 0; i < jsonStr.length; i++) {
                encrypted += String.fromCharCode(jsonStr.charCodeAt(i) ^ key.charCodeAt(i % key.length));
            }

            return btoa(encrypted); // Base64 encode
        } catch (error) {
            console.error('Session encryption error:', error);
            return null;
        }
    }

    /**
     * Decrypt session data
     */
    _decryptSession(encryptedData) {
        try {
            const key = this._getClientKey();
            const encrypted = atob(encryptedData); // Base64 decode
            let decrypted = '';

            for (let i = 0; i < encrypted.length; i++) {
                decrypted += String.fromCharCode(encrypted.charCodeAt(i) ^ key.charCodeAt(i % key.length));
            }

            return JSON.parse(decrypted);
        } catch (error) {
            console.error('Session decryption error:', error);
            return null;
        }
    }

    /**
     * Generate a client-specific key for encryption
     */
    _getClientKey() {
        // Create a semi-persistent key based on browser characteristics
        const userAgent = navigator.userAgent.substring(0, 50);
        const language = navigator.language || 'en';
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

        return btoa(userAgent + language + timezone).substring(0, 32);
    }

    /**
     * Generate CSRF token for OAuth flows
     */
    _generateCSRFToken() {
        // Generate a cryptographically secure random token
        const array = new Uint8Array(32);
        crypto.getRandomValues(array);

        // Convert to base64url format (URL-safe)
        return btoa(String.fromCharCode.apply(null, array))
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=/g, '');
    }

    /**
     * Store CSRF token for validation
     */
    _storeCSRFToken(token) {
        sessionStorage.setItem('oauth-csrf-token', token);
        // Also set expiry (5 minutes for OAuth flow)
        sessionStorage.setItem('oauth-csrf-expiry', (Date.now() + 300000).toString());
    }

    /**
     * Validate CSRF token
     */
    _validateCSRFToken(token) {
        const storedToken = sessionStorage.getItem('oauth-csrf-token');
        const expiry = sessionStorage.getItem('oauth-csrf-expiry');

        // Clean up tokens after use
        sessionStorage.removeItem('oauth-csrf-token');
        sessionStorage.removeItem('oauth-csrf-expiry');

        if (!storedToken || !expiry) {
            console.error('CSRF token not found or expired');
            return false;
        }

        if (Date.now() > parseInt(expiry)) {
            console.error('CSRF token expired');
            return false;
        }

        if (storedToken !== token) {
            console.error('CSRF token mismatch');
            return false;
        }

        return true;
    }

    /**
     * Load stored session with decryption
     */
    loadStoredSession() {
        try {
            // Try encrypted storage first
            const encryptedSession = sessionStorage.getItem('sb-session-enc');
            if (encryptedSession) {
                const sessionData = this._decryptSession(encryptedSession);
                if (sessionData) {
                    this.session = sessionData;
                    this.user = this.session?.user || null;
                    return;
                }
            }

            // Fallback to legacy localStorage (for migration)
            const legacySession = localStorage.getItem('sb-session');
            if (legacySession) {
                console.warn('Migrating from legacy localStorage session');
                this.session = JSON.parse(legacySession);
                this.user = this.session?.user || null;

                // Migrate to secure storage and clean up
                this.storeSession(this.session);
                localStorage.removeItem('sb-session');
            }
        } catch (error) {
            console.error('Error loading stored session:', error);
            this.clearSession();
        }
    }

    /**
     * Store session with encryption
     */
    storeSession(session) {
        if (session) {
            // Store in encrypted sessionStorage (more secure than localStorage)
            const encryptedSession = this._encryptSession(session);
            if (encryptedSession) {
                sessionStorage.setItem('sb-session-enc', encryptedSession);

                // Store session expiry separately for quick access
                sessionStorage.setItem('sb-session-exp', session.expires_at?.toString() || '0');
            }

            this.session = session;
            this.user = session.user;
            this._scheduleRefresh();
        } else {
            this.clearSession();
        }
    }

    /**
     * Clear session securely
     */
    clearSession() {
        // Clear all possible session storage locations
        sessionStorage.removeItem('sb-session-enc');
        sessionStorage.removeItem('sb-session-exp');
        localStorage.removeItem('sb-session'); // Clean up legacy storage

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
            // Generate CSRF token for security
            const csrfToken = this._generateCSRFToken();
            this._storeCSRFToken(csrfToken);

            // Redirect to Supabase Google OAuth
            // The redirect_to parameter tells Supabase where to redirect after successful auth
            const redirectUrl = `${window.location.origin}/auth-callback.html`;
            const authUrl = `${this.url}/auth/v1/authorize?provider=google&redirect_to=${encodeURIComponent(redirectUrl)}&state=${encodeURIComponent(csrfToken)}`;

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

            // Validate CSRF token from state parameter
            const state = urlParams.get('state');
            if (state && !this._validateCSRFToken(state)) {
                throw new Error('Invalid authentication state - possible CSRF attack');
            }

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

// Initialize global Supabase client asynchronously
let supabaseInitialized = false;

async function initializeSupabase() {
    if (supabaseInitialized) return window.supabase;

    const config = await loadSupabaseConfig();
    window.supabase = new SupabaseClient(config.url, config.anonKey);
    supabaseInitialized = true;
    return window.supabase;
}

// Auto-initialize on script load
initializeSupabase().catch(console.error);

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SupabaseClient };
}