/**
 * TURFMAPP Configuration Module
 * 
 * Centralized configuration management following code.md standards.
 * Contains application constants, API endpoints, and environment-specific settings.
 */

'use strict';

const AppConfig = {
    // Application information
    APP_NAME: 'TURFMAPP',
    APP_VERSION: '1.0.0',
    
    // Environment settings
    ENVIRONMENT: 'development', // development | production | testing
    
    // API Configuration
    API_BASE_URL: window.location.origin,
    API_ENDPOINTS: {
        // TODO: Implement actual API endpoints when backend is ready
        LOGIN: '/api/auth/login',
        LOGOUT: '/api/auth/logout',
        REFRESH: '/api/auth/refresh',
        USER_PROFILE: '/api/user/profile',
        // Commented out - not implemented yet
        // REGISTER: '/api/auth/register',
        // FORGOT_PASSWORD: '/api/auth/forgot-password',
        // RESET_PASSWORD: '/api/auth/reset-password'
    },
    
    // UI Configuration
    UI: {
        ANIMATION_DURATION: 300, // milliseconds
        DEBOUNCE_DELAY: 500,     // milliseconds
        MAX_LOGIN_ATTEMPTS: 3,
        SESSION_TIMEOUT: 30 * 60 * 1000, // 30 minutes in milliseconds
    },
    
    // Page routes
    ROUTES: {
        HOME: 'home.html',
        LOGIN: 'index.html',
        // TODO: Add more routes as pages are developed
        // DASHBOARD: 'dashboard.html',
        // PROFILE: 'profile.html',
        // SETTINGS: 'settings.html'
    },
    
    // Local storage keys
    STORAGE_KEYS: {
        USER_TOKEN: 'turfmapp_token',
        USER_PREFERENCES: 'turfmapp_preferences',
        LAST_LOGIN: 'turfmapp_last_login',
        // Commented out - not implemented yet
        // REMEMBER_ME: 'turfmapp_remember_me',
        // THEME_PREFERENCE: 'turfmapp_theme'
    },
    
    // Feature flags for development
    FEATURES: {
        // Currently enabled features
        TESTING_MODE: true,
        AUTO_LOGIN: true, // For testing - bypasses authentication
        
        // TODO: Enable when ready
        // REAL_AUTHENTICATION: false,
        // FORGOT_PASSWORD: false,
        // USER_REGISTRATION: false,
        // MULTI_FACTOR_AUTH: false,
        // REMEMBER_ME: false
    },
    
    // Error messages
    MESSAGES: {
        LOGIN_SUCCESS: 'Login successful! Redirecting...',
        LOGIN_ERROR: 'Invalid credentials. Please try again.',
        NETWORK_ERROR: 'Network error. Please check your connection.',
        SESSION_EXPIRED: 'Your session has expired. Please log in again.',
        VALIDATION_ERROR: 'Please fill in all required fields.',
        // TODO: Add more messages as features are implemented
        // REGISTRATION_SUCCESS: 'Account created successfully!',
        // PASSWORD_RESET_SENT: 'Password reset email sent.',
    },
    
    // Validation rules
    VALIDATION: {
        USERNAME: {
            MIN_LENGTH: 3,
            MAX_LENGTH: 50,
            PATTERN: /^[a-zA-Z0-9_-]+$/, // Alphanumeric, underscore, hyphen only
        },
        PASSWORD: {
            MIN_LENGTH: 8,
            MAX_LENGTH: 128,
            // TODO: Implement stronger password requirements
            // REQUIRE_UPPERCASE: true,
            // REQUIRE_LOWERCASE: true,
            // REQUIRE_NUMBERS: true,
            // REQUIRE_SPECIAL_CHARS: true,
        }
    }
};

// Freeze the configuration object to prevent modification
Object.freeze(AppConfig);
Object.freeze(AppConfig.API_ENDPOINTS);
Object.freeze(AppConfig.UI);
Object.freeze(AppConfig.ROUTES);
Object.freeze(AppConfig.STORAGE_KEYS);
Object.freeze(AppConfig.FEATURES);
Object.freeze(AppConfig.MESSAGES);
Object.freeze(AppConfig.VALIDATION);

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AppConfig;
}

/**
 * Environment-specific configuration override
 * Allows for different settings in production vs development
 */
function getEnvironmentConfig() {
    const envConfigs = {
        production: {
            FEATURES: {
                TESTING_MODE: false,
                AUTO_LOGIN: false,
                // REAL_AUTHENTICATION: true
            }
        },
        testing: {
            UI: {
                ANIMATION_DURATION: 0 // Disable animations in tests
            }
        }
    };
    
    return envConfigs[AppConfig.ENVIRONMENT] || {};
}

/**
 * Utility function to check if a feature is enabled
 * @param {string} featureName - Name of the feature to check
 * @returns {boolean} - Whether the feature is enabled
 */
function isFeatureEnabled(featureName) {
    return AppConfig.FEATURES[featureName] || false;
}

/**
 * Utility function to get API endpoint URL
 * @param {string} endpointName - Name of the endpoint
 * @returns {string} - Full URL for the endpoint
 */
function getApiUrl(endpointName) {
    const endpoint = AppConfig.API_ENDPOINTS[endpointName];
    if (!endpoint) {
        console.error(`API endpoint '${endpointName}' not found in configuration`);
        return '';
    }
    return `${AppConfig.API_BASE_URL}${endpoint}`;
}