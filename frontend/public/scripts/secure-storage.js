/**
 * Secure Storage Module for TURFMAPP
 * Provides encrypted storage for sensitive data
 */

'use strict';

/**
 * Secure Storage Implementation
 * Uses sessionStorage for session data and encrypted localStorage for persistent data
 */
class SecureStorage {
    constructor() {
        this.prefix = 'tm_';
        this.sessionPrefix = 'tm_session_';
        this.encryptionKey = null;
        this.initEncryption();
    }

    /**
     * Initialize encryption key (simplified - in production use proper key derivation)
     */
    initEncryption() {
        // Generate or retrieve encryption key
        let key = localStorage.getItem(this.prefix + 'ek');
        if (!key) {
            // Generate a simple key (in production, use proper cryptographic methods)
            key = this.generateKey();
            localStorage.setItem(this.prefix + 'ek', key);
        }
        this.encryptionKey = key;
    }

    /**
     * Generate a simple encryption key
     */
    generateKey() {
        const array = new Uint8Array(32);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    }

    /**
     * Simple XOR encryption (for basic obfuscation - not cryptographically secure)
     */
    encrypt(data) {
        if (!data || !this.encryptionKey) return data;

        try {
            const jsonData = JSON.stringify(data);
            let encrypted = '';
            for (let i = 0; i < jsonData.length; i++) {
                const keyChar = this.encryptionKey[i % this.encryptionKey.length];
                encrypted += String.fromCharCode(jsonData.charCodeAt(i) ^ keyChar.charCodeAt(0));
            }
            return btoa(encrypted); // Base64 encode
        } catch (error) {
            return data; // Fallback to unencrypted
        }
    }

    /**
     * Simple XOR decryption
     */
    decrypt(encryptedData) {
        if (!encryptedData || !this.encryptionKey) return null;

        try {
            const encrypted = atob(encryptedData); // Base64 decode
            let decrypted = '';
            for (let i = 0; i < encrypted.length; i++) {
                const keyChar = this.encryptionKey[i % this.encryptionKey.length];
                decrypted += String.fromCharCode(encrypted.charCodeAt(i) ^ keyChar.charCodeAt(0));
            }
            return JSON.parse(decrypted);
        } catch (error) {
            return null; // Failed to decrypt
        }
    }

    /**
     * Store sensitive data securely (persistent)
     */
    setSecure(key, value) {
        try {
            const encrypted = this.encrypt(value);
            localStorage.setItem(this.prefix + key, encrypted);
            return true;
        } catch (error) {
            return false;
        }
    }

    /**
     * Retrieve sensitive data securely (persistent)
     */
    getSecure(key) {
        try {
            const encrypted = localStorage.getItem(this.prefix + key);
            return encrypted ? this.decrypt(encrypted) : null;
        } catch (error) {
            return null;
        }
    }

    /**
     * Store session-only data (cleared on browser close)
     */
    setSession(key, value) {
        try {
            sessionStorage.setItem(this.sessionPrefix + key, JSON.stringify(value));
            return true;
        } catch (error) {
            return false;
        }
    }

    /**
     * Retrieve session-only data
     */
    getSession(key) {
        try {
            const data = sessionStorage.getItem(this.sessionPrefix + key);
            return data ? JSON.parse(data) : null;
        } catch (error) {
            return null;
        }
    }

    /**
     * Remove sensitive data
     */
    removeSecure(key) {
        try {
            localStorage.removeItem(this.prefix + key);
            return true;
        } catch (error) {
            return false;
        }
    }

    /**
     * Remove session data
     */
    removeSession(key) {
        try {
            sessionStorage.removeItem(this.sessionPrefix + key);
            return true;
        } catch (error) {
            return false;
        }
    }

    /**
     * Clear all secure data
     */
    clearAll() {
        try {
            // Clear localStorage entries
            const keys = Object.keys(localStorage);
            keys.forEach(key => {
                if (key.startsWith(this.prefix)) {
                    localStorage.removeItem(key);
                }
            });

            // Clear sessionStorage entries
            const sessionKeys = Object.keys(sessionStorage);
            sessionKeys.forEach(key => {
                if (key.startsWith(this.sessionPrefix)) {
                    sessionStorage.removeItem(key);
                }
            });

            return true;
        } catch (error) {
            return false;
        }
    }

    /**
     * Check if storage is available
     */
    isAvailable() {
        try {
            const test = 'test';
            localStorage.setItem(test, test);
            localStorage.removeItem(test);
            return true;
        } catch (error) {
            return false;
        }
    }
}

// Initialize global secure storage instance
window.secureStorage = new SecureStorage();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SecureStorage };
}