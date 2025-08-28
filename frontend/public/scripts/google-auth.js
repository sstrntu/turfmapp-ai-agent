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
    init() {
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
     * Development mode login (fallback for testing)
     */
    async devLogin() {
        try {
            this.showStatus('Signing in with development credentials...', 'info');

            // Use the legacy auth system for development
            const response = await fetch('/api/auth/dev-login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: 'test',
                    password: '123'
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.showStatus('Development login successful!', 'success');
                
                // Redirect after short delay
                setTimeout(() => {
                    window.location.href = '/home.html';
                }, 1000);
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Development login failed');
            }

        } catch (error) {
            console.error('Development login error:', error);
            this.showStatus(`Development login failed: ${error.message}`, 'error');
        }
    },

    /**
     * Handle authenticated user
     */
    handleAuthenticatedUser() {
        const user = window.supabase.getUser();
        if (user) {
            this.showStatus(`Welcome back, ${user.name || user.email}!`, 'success');
            // Redirect immediately to home if user opens portal while already authenticated
            window.location.replace('/home.html');
        }
    },

    /**
     * Sign out
     */
    async signOut() {
        try {
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
    }
};

// Initialize on page load - ONLY for login/portal pages
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize GoogleAuth on login/portal pages, not on home page
    if (window.location.pathname === '/portal.html' || window.location.pathname === '/login.html' || window.location.pathname === '/') {
        GoogleAuth.init();
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { GoogleAuth };
}