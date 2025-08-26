/**
 * TURFMAPP Utility Functions
 * 
 * Common utility functions following code.md standards.
 * Provides reusable helper functions for DOM manipulation, validation, and data handling.
 */

'use strict';

/**
 * DOM Utility Functions
 */
const DOMUtils = {
    /**
     * Safely get element by ID with error handling
     * @param {string} id - Element ID
     * @returns {HTMLElement|null} - Element or null if not found
     */
    getElementById(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Element with ID '${id}' not found`);
        }
        return element;
    },

    /**
     * Add CSS class with animation support
     * @param {HTMLElement} element - Target element
     * @param {string} className - CSS class name
     * @param {number} delay - Optional delay in milliseconds
     */
    addClass(element, className, delay = 0) {
        if (!element) return;
        
        if (delay > 0) {
            setTimeout(() => element.classList.add(className), delay);
        } else {
            element.classList.add(className);
        }
    },

    /**
     * Remove CSS class with animation support
     * @param {HTMLElement} element - Target element
     * @param {string} className - CSS class name
     * @param {number} delay - Optional delay in milliseconds
     */
    removeClass(element, className, delay = 0) {
        if (!element) return;
        
        if (delay > 0) {
            setTimeout(() => element.classList.remove(className), delay);
        } else {
            element.classList.remove(className);
        }
    },

    /**
     * Toggle CSS class
     * @param {HTMLElement} element - Target element
     * @param {string} className - CSS class name
     */
    toggleClass(element, className) {
        if (!element) return;
        element.classList.toggle(className);
    },

    /**
     * Set element text content safely
     * @param {HTMLElement} element - Target element
     * @param {string} text - Text content
     */
    setText(element, text) {
        if (!element) return;
        element.textContent = text;
    },

    /**
     * Clear element content
     * @param {HTMLElement} element - Target element
     */
    clearContent(element) {
        if (!element) return;
        element.innerHTML = '';
    }
};

/**
 * Validation Utility Functions
 */
const ValidationUtils = {
    /**
     * Validate username according to app rules
     * @param {string} username - Username to validate
     * @returns {Object} - Validation result with isValid boolean and message
     */
    validateUsername(username) {
        const rules = AppConfig.VALIDATION.USERNAME;
        
        if (!username || username.trim().length === 0) {
            return { isValid: false, message: 'Username is required' };
        }
        
        if (username.length < rules.MIN_LENGTH) {
            return { isValid: false, message: `Username must be at least ${rules.MIN_LENGTH} characters` };
        }
        
        if (username.length > rules.MAX_LENGTH) {
            return { isValid: false, message: `Username cannot exceed ${rules.MAX_LENGTH} characters` };
        }
        
        if (!rules.PATTERN.test(username)) {
            return { isValid: false, message: 'Username can only contain letters, numbers, underscore, and hyphen' };
        }
        
        return { isValid: true, message: '' };
    },

    /**
     * Validate password according to app rules
     * @param {string} password - Password to validate
     * @returns {Object} - Validation result with isValid boolean and message
     */
    validatePassword(password) {
        const rules = AppConfig.VALIDATION.PASSWORD;
        
        if (!password || password.length === 0) {
            return { isValid: false, message: 'Password is required' };
        }
        // In testing mode allow short passwords to support temporary creds
        if (!isFeatureEnabled('TESTING_MODE') && password.length < rules.MIN_LENGTH) {
            return { isValid: false, message: `Password must be at least ${rules.MIN_LENGTH} characters` };
        }
        
        if (password.length > rules.MAX_LENGTH) {
            return { isValid: false, message: `Password cannot exceed ${rules.MAX_LENGTH} characters` };
        }
        
        // TODO: Add stronger password validation when requirements are finalized
        // if (rules.REQUIRE_UPPERCASE && !/[A-Z]/.test(password)) {
        //     return { isValid: false, message: 'Password must contain at least one uppercase letter' };
        // }
        
        return { isValid: true, message: '' };
    },

    /**
     * Validate form inputs
     * @param {Object} formData - Form data to validate
     * @returns {Object} - Validation result with isValid boolean and errors object
     */
    validateForm(formData) {
        const errors = {};
        let isValid = true;
        
        // Validate username
        const usernameValidation = this.validateUsername(formData.username);
        if (!usernameValidation.isValid) {
            errors.username = usernameValidation.message;
            isValid = false;
        }
        
        // Validate password
        const passwordValidation = this.validatePassword(formData.password);
        if (!passwordValidation.isValid) {
            errors.password = passwordValidation.message;
            isValid = false;
        }
        
        return { isValid, errors };
    }
};

/**
 * Storage Utility Functions
 */
const StorageUtils = {
    /**
     * Safely set item in localStorage
     * @param {string} key - Storage key
     * @param {*} value - Value to store (will be JSON stringified)
     */
    setItem(key, value) {
        try {
            const serializedValue = JSON.stringify(value);
            localStorage.setItem(key, serializedValue);
        } catch (error) {
            console.error('Error saving to localStorage:', error);
        }
    },

    /**
     * Safely get item from localStorage
     * @param {string} key - Storage key
     * @returns {*} - Parsed value or null if not found
     */
    getItem(key) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch (error) {
            console.error('Error reading from localStorage:', error);
            return null;
        }
    },

    /**
     * Remove item from localStorage
     * @param {string} key - Storage key
     */
    removeItem(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('Error removing from localStorage:', error);
        }
    },

    /**
     * Clear all app-related items from localStorage
     */
    clearAppStorage() {
        try {
            Object.values(AppConfig.STORAGE_KEYS).forEach(key => {
                localStorage.removeItem(key);
            });
        } catch (error) {
            console.error('Error clearing app storage:', error);
        }
    }
};

/**
 * Network Utility Functions
 */
const NetworkUtils = {
    /**
     * Make HTTP request with proper error handling
     * @param {string} url - Request URL
     * @param {Object} options - Fetch options
     * @returns {Promise<Object>} - Response data or error
     */
    async makeRequest(url, options = {}) {
        try {
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            };
            
            const response = await fetch(url, defaultOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return { success: true, data };
        } catch (error) {
            console.error('Network request failed:', error);
            return { success: false, error: error.message };
        }
    }
};

/**
 * Animation Utility Functions
 */
const AnimationUtils = {
    /**
     * Debounce function execution
     * @param {Function} func - Function to debounce
     * @param {number} delay - Delay in milliseconds
     * @returns {Function} - Debounced function
     */
    debounce(func, delay = AppConfig.UI.DEBOUNCE_DELAY) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    },

    /**
     * Throttle function execution
     * @param {Function} func - Function to throttle
     * @param {number} limit - Time limit in milliseconds
     * @returns {Function} - Throttled function
     */
    throttle(func, limit) {
        let inThrottle;
        return function (...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * Wait for specified duration
     * @param {number} duration - Duration in milliseconds
     * @returns {Promise} - Promise that resolves after duration
     */
    wait(duration) {
        return new Promise(resolve => setTimeout(resolve, duration));
    }
};

/**
 * Error Handling Utility Functions
 */
const ErrorUtils = {
    /**
     * Log error with context
     * @param {string} context - Error context
     * @param {Error} error - Error object
     */
    logError(context, error) {
        console.error(`[${context}]`, error);
        
        // TODO: In production, send errors to monitoring service
        // if (AppConfig.ENVIRONMENT === 'production') {
        //     this.sendErrorToMonitoring(context, error);
        // }
    },

    /**
     * Show user-friendly error message
     * @param {string} message - Error message to display
     * @param {HTMLElement} element - Element to show error in
     */
    showError(message, element) {
        if (!element) return;
        
        DOMUtils.setText(element, message);
        DOMUtils.addClass(element, 'show');
        DOMUtils.addClass(element, 'error');
    },

    /**
     * Clear error message
     * @param {HTMLElement} element - Element to clear error from
     */
    clearError(element) {
        if (!element) return;
        
        DOMUtils.removeClass(element, 'show');
        DOMUtils.removeClass(element, 'error');
        setTimeout(() => DOMUtils.setText(element, ''), AppConfig.UI.ANIMATION_DURATION);
    }
};

// Export utilities for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        DOMUtils,
        ValidationUtils,
        StorageUtils,
        NetworkUtils,
        AnimationUtils,
        ErrorUtils
    };
}