/**
 * Google Authentication Module for TURFMAPP
 * Handles Google OAuth flow through Supabase
 */

'use strict';

/**
 * Google Authentication Controller
 */
const GoogleAuth = {
    /**
     * Initialize authentication state
     */
    async init() {
        // Ensure Supabase is initialized
        await initializeSupabase();

        // Check if user is already authenticated
        if (window.supabase.isSessionValid()) {
            this.handleAuthenticatedUser();
        }
    },

    /**
     * Sign in with Google
     */
    async signIn() {
        try {
            this.showStatus('Redirecting to Google...', 'info');

            // Initiate Google OAuth flow
            await window.supabase.signInWithGoogle();

        } catch (error) {
            console.error('Google sign in error:', error);
            this.showStatus('Failed to sign in with Google. Please try again.', 'error');
        }
    },

    /**
     * Development mode login (disabled for security)
     * This method is preserved for API compatibility but disabled
     */
    async devLogin() {
        console.warn('Development login is disabled for security reasons');
        this.showStatus('Development login is disabled. Please use Google authentication.', 'error');
    },

    /**
     * Handle authenticated user
     */
    async handleAuthenticatedUser() {
        const user = window.supabase.getUser();
        if (user) {
            this.showStatus(`Welcome back, ${user.name || user.email}!`, 'success');
            // Redirect to home - Google services will be managed in Settings
            setTimeout(() => window.location.replace('/home.html'), 1500);
        }
    },

    /**
     * Check Google services and prompt if needed
     */
    async checkAndPromptGoogleServices() {
        try {
            // Check if user has Google accounts connected
            const session = await window.supabase.getSession();
            const response = await fetch('/api/v1/google/auth/status', {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                const hasGoogleAccounts = data.data.total_accounts > 0;

                if (!hasGoogleAccounts) {
                    // Show Google services prompt
                    this.showGoogleServicesPrompt();
                } else {
                    // User already has Google accounts, go to home
                    this.showStatus('Google services connected!', 'success');
                    setTimeout(() => window.location.replace('/home.html'), 1500);
                }
            } else {
                // If Google auth check fails, still go to home (non-blocking)
                console.warn('Could not check Google auth status, proceeding to home');
                setTimeout(() => window.location.replace('/home.html'), 2000);
            }
        } catch (error) {
            console.error('Error checking Google services:', error);
            // On error, proceed to home after delay (non-blocking)
            setTimeout(() => window.location.replace('/home.html'), 2000);
        }
    },

    /**
     * Show Google services connection prompt
     */
    showGoogleServicesPrompt() {
        const statusElement = document.getElementById('login-status');
        const loginForm = document.querySelector('.login-form');

        if (statusElement && loginForm) {
            // Update the form to show Google services prompt
            loginForm.innerHTML = `
                <div class="google-services-prompt">
                    <h3 style="margin-bottom: 15px; color: #333;">🚀 Connect Google Services</h3>
                    <p style="margin-bottom: 20px; color: #666; line-height: 1.4;">
                        Connect your Gmail, Google Drive, and Calendar to unlock powerful AI features:
                    </p>
                    <ul style="text-align: left; margin: 15px 0; color: #555;">
                        <li>📧 Ask AI about your emails</li>
                        <li>📁 Manage Google Drive files</li>
                        <li>📅 Access your calendar events</li>
                    </ul>
                    <button type="button" id="connect-google-btn" class="google-signin-button"
                            style="margin: 15px 0;" onclick="GoogleAuth.connectGoogleServices()">
                        <svg class="google-icon" viewBox="0 0 24 24" width="20" height="20">
                            <path fill="#4285f4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#34a853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#fbbc05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                            <path fill="#ea4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                        </svg>
                        <span class="button-text">Connect Google Services</span>
                    </button>
                    <button type="button" style="background: #6c757d; color: white; padding: 10px 20px;
                                                  border: none; border-radius: 3px; margin: 5px; cursor: pointer;"
                            onclick="GoogleAuth.skipGoogleServices()">
                        Skip for Now
                    </button>
                </div>
            `;
        }
    },

    /**
     * Connect Google services
     */
    async connectGoogleServices() {
        try {
            this.showStatus('Connecting to Google services...', 'info');

            const session = await window.supabase.getSession();
            const response = await fetch('/api/v1/google/auth/url', {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Redirect to Google OAuth
                    window.location.href = data.data.auth_url;
                } else {
                    throw new Error(data.message || 'Failed to get Google auth URL');
                }
            } else {
                throw new Error('Failed to initiate Google connection');
            }
        } catch (error) {
            console.error('Error connecting Google services:', error);
            this.showStatus(`Failed to connect Google services: ${error.message}`, 'error');
        }
    },

    /**
     * Skip Google services connection
     */
    skipGoogleServices() {
        this.showStatus('Proceeding without Google services', 'info');
        setTimeout(() => {
            window.location.replace('/home.html');
        }, 1000);
    },

    /**
     * Sign out
     */
    async signOut() {
        try {
            // Clear admin cache on sign out
            this.clearAdminCache();

            await window.supabase.signOut();
            this.showStatus('Signed out successfully', 'success');

            // Redirect to login
            setTimeout(() => {
                window.location.href = '/portal.html';
            }, 1000);

        } catch (error) {
            console.error('Sign out error:', error);
            this.showStatus('Sign out failed', 'error');
        }
    },

    /**
     * Show status message
     */
    showStatus(message, type = 'info') {
        const statusElement = document.getElementById('login-status');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `status-message ${type}`;

            // Clear message after delay (except for errors)
            if (type !== 'error') {
                setTimeout(() => {
                    statusElement.textContent = '';
                    statusElement.className = 'status-message';
                }, 5000);
            }
        }
    },

    /**
     * Check authentication status
     */
    async checkAuthStatus() {
        try {
            const response = await window.supabase.apiRequest('/api/v1/auth/status');
            const data = await response.json();

            return data.authenticated ? data.user : null;
        } catch (error) {
            console.error('Auth status check error:', error);
            return null;
        }
    },

    /**
     * Get current access token for API requests
     */
    getToken() {
        try {
            // First try to get from initialized Supabase client
            if (window.supabase?.session) {
                return window.supabase.session.access_token || null;
            }

            // Fallback: try to get from stored session
            const encryptedSession = sessionStorage.getItem('sb-session-enc');
            if (encryptedSession && window.supabase) {
                // If we have Supabase client, use its decryption method
                try {
                    const sessionData = window.supabase._decryptSession(encryptedSession);
                    return sessionData?.access_token || null;
                } catch (e) {
                    console.error('Error decrypting session for token:', e);
                }
            }

            // Last resort: check legacy localStorage
            const legacySession = localStorage.getItem('sb-session');
            if (legacySession) {
                try {
                    const session = JSON.parse(legacySession);
                    return session.access_token || null;
                } catch (e) {
                    console.error('Error parsing legacy session for token:', e);
                }
            }

            return null;
        } catch (error) {
            console.error('Error getting token:', error);
            return null;
        }
    },

    /**
     * Check if current user is authenticated
     */
    isAuthenticated() {
        try {
            // First check if Supabase is initialized
            if (!window.supabase) {
                console.warn('Supabase not initialized yet, checking stored session...');

                // Check if we have a session in sessionStorage
                const encryptedSession = sessionStorage.getItem('sb-session-enc');
                const sessionExpiry = sessionStorage.getItem('sb-session-exp');

                if (encryptedSession && sessionExpiry) {
                    const expiry = parseInt(sessionExpiry);
                    const isValid = Date.now() < expiry;
                    //console.log('Found stored session, valid:', isValid);
                    return isValid;
                }

                // Fallback: check legacy localStorage session
                const legacySession = localStorage.getItem('sb-session');
                if (legacySession) {
                    try {
                        const session = JSON.parse(legacySession);
                        const isValid = session.expires_at ? Date.now() < session.expires_at : false;
                        //console.log('Found legacy session, valid:', isValid);
                        return isValid;
                    } catch (e) {
                        console.error('Error parsing legacy session:', e);
                    }
                }

                return false;
            }

            return window.supabase.isSessionValid() || false;
        } catch (error) {
            console.error('Error checking authentication:', error);
            return false;
        }
    },

    /**
     * Get current user information
     */
    getCurrentUser() {
        return window.supabase?.getUser() || null;
    },

    /**
     * Check if current user has admin privileges (cached for performance)
     */
    async isAdmin() {
        try {
            const token = this.getToken();
            if (!token) return false;

            // Check cache first (valid for 5 minutes)
            const cacheKey = 'tm_user_admin_status';
            const cached = localStorage.getItem(cacheKey);
            if (cached) {
                const { isAdmin, timestamp, userToken } = JSON.parse(cached);
                // Use cache if less than 5 minutes old and same token
                if (Date.now() - timestamp < 300000 && userToken === token) {
                    return isAdmin;
                }
            }

            const response = await fetch('/api/v1/settings/profile', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const user = await response.json();
                const isAdminUser = ['admin', 'super_admin'].includes(user.role);

                // Cache the result
                localStorage.setItem(cacheKey, JSON.stringify({
                    isAdmin: isAdminUser,
                    timestamp: Date.now(),
                    userToken: token
                }));

                return isAdminUser;
            }
            return false;
        } catch (error) {
            console.error('Error checking admin status:', error);
            return false;
        }
    },

    /**
     * Ensure user is authenticated and redirect if not
     */
    async requireAuth() {
        try {
            // Wait for Supabase to be initialized if it's not ready
            if (!window.supabase && typeof window.initializeSupabase === 'function') {
                //console.log('⏳ [AUTH] Waiting for Supabase initialization...');
                await window.initializeSupabase();
            }

            // Give it a moment to settle
            let attempts = 0;
            while (!window.supabase && attempts < 50) {
                await new Promise(resolve => setTimeout(resolve, 100));
                attempts++;
            }

            //console.log('🔍 [AUTH] Supabase ready:', !!window.supabase);
            //console.log('🔍 [AUTH] Session valid:', window.supabase?.isSessionValid());

            const isAuth = this.isAuthenticated();
            //console.log('🔍 [AUTH] Final authentication result:', isAuth);

            if (!isAuth) {
                //console.log('❌ [AUTH] Authentication failed, redirecting to portal');
                window.location.href = '/portal.html';
                return false;
            }

            //console.log('✅ [AUTH] Authentication successful');
            return true;
        } catch (error) {
            console.error('❌ [AUTH] Error in requireAuth:', error);
            window.location.href = '/portal.html';
            return false;
        }
    },

    /**
     * Show/hide elements based on admin status (optimized for loading screen)
     */
    async setupAdminUI() {
        // Get admin status (this will use cache if valid, or fetch fresh data)
        const isAdmin = await this.isAdmin();

        // Apply UI changes only once after verification completes
        this.applyAdminUI(isAdmin);

        return isAdmin;
    },

    /**
     * Apply admin UI changes
     */
    applyAdminUI(isAdmin) {
        const adminElements = document.querySelectorAll('[data-admin-only]');
        adminElements.forEach(element => {
            if (isAdmin) {
                element.style.display = element.dataset.adminDisplay || 'block';
            } else {
                element.style.display = 'none';
            }
        });
    },

    /**
     * Clear admin cache (useful when user logs out or role changes)
     */
    clearAdminCache() {
        localStorage.removeItem('tm_user_admin_status');
    }
};

// Initialize on page load - ONLY for login/portal pages
document.addEventListener('DOMContentLoaded', async function() {
    // Only initialize GoogleAuth on login/portal pages, not on home page
    if (window.location.pathname === '/portal.html' || window.location.pathname === '/login.html' || window.location.pathname === '/') {
        await GoogleAuth.init();
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { GoogleAuth };
}
