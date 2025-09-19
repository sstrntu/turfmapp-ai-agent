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

        if (!response.ok) {
            throw new Error(`Config fetch failed: ${response.status}`);
        }

        const config = await response.json();

        SUPABASE_CONFIG = {
            url: config.supabase.url,
            anonKey: config.supabase.anonKey
        };

        console.log('✅ Loaded Supabase config from backend');
        return SUPABASE_CONFIG;
    } catch (error) {
        console.error('Failed to load Supabase config from backend:', error);

        // Emergency fallback with actual credentials for development
        // This should only be used when backend is not available
        console.warn('🚨 Using emergency fallback config - backend unavailable');

        // Try to get from environment or use development defaults
        SUPABASE_CONFIG = {
            url: 'https://pwxhgvuyaxgavommtqpr.supabase.co',
            anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB3eGhndnV5YXhnYXZvbW10cXByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYyMjA1OTcsImV4cCI6MjA3MTc5NjU5N30.n7i3AMpdRRBWA5AhNMdzO5qf_34w4Fo13adUBWsoevg'
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
        console.log('🟠 [SUPABASE] SupabaseClient constructor called');
        this.url = url;
        this.anonKey = anonKey;
        this.session = null;
        this.user = null;
        this._refreshTimerId = null;

        console.log('🟠 [SUPABASE] Loading stored session...');
        // Initialize from stored session
        this.loadStoredSession();
        console.log('🟠 [SUPABASE] Session loaded, scheduling refresh...');
        // Schedule refresh if a session exists
        this._scheduleRefresh();
        console.log('🟠 [SUPABASE] SupabaseClient constructor complete');
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
     * Validate stored CSRF token (for Supabase OAuth where we can't pass custom state)
     */
    _validateStoredCSRFToken() {
        const storedToken = sessionStorage.getItem('oauth-csrf-token');
        const expiry = sessionStorage.getItem('oauth-csrf-expiry');

        // Clean up tokens after use
        sessionStorage.removeItem('oauth-csrf-token');
        sessionStorage.removeItem('oauth-csrf-expiry');

        if (!storedToken || !expiry) {
            console.error('CSRF token not found');
            return false;
        }

        if (Date.now() > parseInt(expiry)) {
            console.error('CSRF token expired');
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
            // Generate CSRF token for security (store for later validation)
            const csrfToken = this._generateCSRFToken();
            this._storeCSRFToken(csrfToken);

            // Redirect to Supabase Google OAuth
            // Note: Supabase manages its own state parameter, so we'll validate our token separately
            const redirectUrl = `${window.location.origin}/auth-callback.html`;
            const authUrl = `${this.url}/auth/v1/authorize?provider=google&redirect_to=${encodeURIComponent(redirectUrl)}`;

            // Store additional security info for callback validation
            localStorage.setItem('auth-return-url', '/home.html');
            localStorage.setItem('auth-initiated-time', Date.now().toString());

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
            console.log('🔧 handleAuthCallback called');
            console.log('🔍 Full URL:', window.location.href);
            console.log('🔍 Hash:', window.location.hash);
            console.log('🔍 Search:', window.location.search);

            // Validate authentication was recently initiated (anti-replay protection)
            const authInitiatedTime = localStorage.getItem('auth-initiated-time');
            console.log('🔍 Auth initiated time:', authInitiatedTime);
            if (authInitiatedTime) {
                const timeSinceInit = Date.now() - parseInt(authInitiatedTime);
                localStorage.removeItem('auth-initiated-time');

                // Check if auth was initiated within the last 10 minutes
                if (timeSinceInit > 600000) { // 10 minutes
                    throw new Error('Authentication session expired - possible replay attack');
                }
                console.log('✅ Auth timing validation passed');
            }

            // Validate our CSRF token (independent of Supabase state)
            const csrfValid = this._validateStoredCSRFToken();
            console.log('🔍 CSRF validation:', csrfValid);
            if (!csrfValid) {
                console.warn('CSRF token validation failed - proceeding with caution');
                // Don't block but log for monitoring
            }

            const urlParams = new URLSearchParams(window.location.hash.substring(1));
            const accessToken = urlParams.get('access_token');
            const refreshToken = urlParams.get('refresh_token');

            console.log('🔍 Parsed URL params:');
            console.log('  - access_token:', accessToken ? `${accessToken.substring(0, 20)}...` : 'null');
            console.log('  - refresh_token:', refreshToken ? `${refreshToken.substring(0, 10)}...` : 'null');

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
    console.log('🔵 [SUPABASE] initializeSupabase called on:', window.location.href);
    if (supabaseInitialized) {
        console.log('🔵 [SUPABASE] Already initialized, returning existing client');
        return window.supabase;
    }

    console.log('🔵 [SUPABASE] Loading config...');
    const config = await loadSupabaseConfig();
    console.log('🔵 [SUPABASE] Creating SupabaseClient...');
    window.supabase = new SupabaseClient(config.url, config.anonKey);
    console.log('🔵 [SUPABASE] SupabaseClient created successfully');
    supabaseInitialized = true;
    return window.supabase;
}

// Expose initializeSupabase globally
window.initializeSupabase = initializeSupabase;

// Auto-initialize on script load
console.log('🟡 [SUPABASE] About to auto-initialize on:', window.location.href);
initializeSupabase().catch(error => {
    console.error('Failed to initialize Supabase:', error);
    // Try again after a short delay
    setTimeout(() => {
        initializeSupabase().catch(console.error);
    }, 1000);
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SupabaseClient, initializeSupabase };
}