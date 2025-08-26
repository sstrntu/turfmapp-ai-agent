/**
 * TURFMAPP Dashboard Controller
 * 
 * Handles dashboard page interactions following code.md standards.
 * Manages dashboard functionality, user interactions, and data display.
 */

'use strict';

/**
 * Dashboard Page Controller
 * Main controller for dashboard/home page functionality
 */
const DashboardController = {
    /**
     * DOM element references
     * @private
     */
    _elements: {
        userGreeting: null,
        welcomeTitle: null,
        getStartedBtn: null,
        dashboardContent: null,
        navLinks: null
    },

    /**
     * Dashboard state
     * @private
     */
    _state: {
        currentUser: null,
        isLoading: false,
        activeSection: 'dashboard'
    },

    /**
     * Initialize the dashboard controller
     */
    init() {
        this._initializeElements();
        this._loadUserData();
        this._attachEventListeners();
        this._updateUserInterface();
        this._checkAuthentication();
    },

    /**
     * Initialize DOM element references
     * @private
     */
    _initializeElements() {
        this._elements.userGreeting = DOMUtils.getElementById('user-greeting');
        this._elements.welcomeTitle = DOMUtils.getElementById('welcome-title');
        this._elements.getStartedBtn = document.querySelector('.primary-action-btn');
        this._elements.dashboardContent = document.querySelector('.dashboard-content');
        this._elements.navLinks = document.querySelectorAll('.nav-link:not(.logout-link)');

        // Log missing elements for debugging
        Object.entries(this._elements).forEach(([key, element]) => {
            if (!element && key !== 'navLinks') {
                console.warn(`Dashboard element '${key}' not found`);
            }
        });
    },

    /**
     * Load user data from authentication service
     * @private
     */
    _loadUserData() {
        this._state.currentUser = AuthService.getCurrentUser();
        
        if (!this._state.currentUser && isFeatureEnabled('TESTING_MODE')) {
            // Create mock user for testing
            this._state.currentUser = {
                id: 'test-user',
                username: 'testuser',
                email: 'test@turfmapp.com',
                role: 'user',
                loginTime: new Date().toISOString()
            };
        }
    },

    /**
     * Attach event listeners
     * @private
     */
    _attachEventListeners() {
        // Navigation links
        this._elements.navLinks?.forEach(link => {
            link.addEventListener('click', (event) => {
                this._handleNavigation(event);
            });
        });

        // Keyboard navigation
        document.addEventListener('keydown', (event) => {
            this._handleKeyboardNavigation(event);
        });

        // Window events
        window.addEventListener('beforeunload', () => {
            this._handlePageUnload();
        });

        // TODO: Add event listeners for future dashboard features
        /*
        // Widget interactions
        document.addEventListener('click', (event) => {
            if (event.target.matches('.widget-card')) {
                this._handleWidgetClick(event);
            }
        });

        // Search functionality
        const searchInput = document.querySelector('.search-input');
        if (searchInput) {
            searchInput.addEventListener('input', 
                AnimationUtils.debounce((event) => {
                    this._handleSearch(event.target.value);
                }, 300)
            );
        }
        */
    },

    /**
     * Update user interface with user data
     * @private
     */
    _updateUserInterface() {
        if (this._state.currentUser) {
            // Update greeting
            if (this._elements.userGreeting) {
                const greeting = this._generatePersonalizedGreeting();
                DOMUtils.setText(this._elements.userGreeting, greeting);
            }

            // Update welcome title
            if (this._elements.welcomeTitle) {
                const welcomeText = `Welcome back, ${this._state.currentUser.username}!`;
                DOMUtils.setText(this._elements.welcomeTitle, welcomeText);
            }
        }
    },

    /**
     * Generate personalized greeting based on time of day
     * @returns {string} - Personalized greeting
     * @private
     */
    _generatePersonalizedGreeting() {
        const hour = new Date().getHours();
        let timeGreeting;

        if (hour < 12) {
            timeGreeting = 'Good morning';
        } else if (hour < 18) {
            timeGreeting = 'Good afternoon';
        } else {
            timeGreeting = 'Good evening';
        }

        const username = this._state.currentUser?.username || 'User';
        return `${timeGreeting}, ${username}!`;
    },

    /**
     * Check authentication status
     * @private
     */
    _checkAuthentication() {
        if (!AuthService.isAuthenticated() && !isFeatureEnabled('TESTING_MODE')) {
            console.warn('User not authenticated, redirecting to login');
            window.location.href = AppConfig.ROUTES.LOGIN;
            return;
        }

        // TODO: Implement session timeout check
        /*
        this._startSessionTimeoutCheck();
        */
    },

    /**
     * Handle navigation clicks
     * @param {Event} event - Click event
     * @private
     */
    _handleNavigation(event) {
        event.preventDefault();
        
        const link = event.currentTarget;
        const href = link.getAttribute('href');
        const section = href?.replace('#', '') || 'dashboard';

        // Update active nav state
        this._setActiveNavigation(link);
        
        // Handle different navigation targets
        switch (section) {
            case 'dashboard':
                this._showDashboardSection();
                break;
            case 'analytics':
                this._showAnalyticsSection();
                break;
            case 'settings':
                this._showSettingsSection();
                break;
            default:
                console.warn(`Unknown navigation section: ${section}`);
        }

        this._state.activeSection = section;
    },

    /**
     * Set active navigation state
     * @param {HTMLElement} activeLink - The clicked navigation link
     * @private
     */
    _setActiveNavigation(activeLink) {
        // Remove active class from all nav links
        this._elements.navLinks?.forEach(link => {
            DOMUtils.removeClass(link, 'active');
            link.removeAttribute('aria-current');
        });

        // Add active class to clicked link
        DOMUtils.addClass(activeLink, 'active');
        activeLink.setAttribute('aria-current', 'page');
    },

    /**
     * Handle keyboard navigation
     * @param {KeyboardEvent} event - Keyboard event
     * @private
     */
    _handleKeyboardNavigation(event) {
        // ESC key handling
        if (event.key === 'Escape') {
            // TODO: Close modals, dropdowns, etc.
            console.log('Escape key pressed');
        }

        // Tab navigation enhancement
        if (event.key === 'Tab') {
            // TODO: Implement better focus management
        }
    },

    /**
     * Handle page unload
     * @private
     */
    _handlePageUnload() {
        // TODO: Save user preferences, clean up resources
        console.log('Dashboard page unloading');
    },

    /**
     * Handle Get Started button click
     */
    handleGetStarted() {
        console.log('Get Started clicked');
        
        // TODO: Implement actual onboarding flow
        /*
        // Show onboarding modal or redirect to tutorial
        this._showOnboardingFlow();
        */
        
        // For now, show a simple message
        this._showTemporaryMessage('Get Started functionality will be implemented here!');
    },

    /**
     * Show dashboard section
     * @private
     */
    _showDashboardSection() {
        console.log('Showing dashboard section');
        
        // TODO: Load dashboard widgets and data
        /*
        this._loadDashboardWidgets();
        this._refreshDashboardData();
        */
        
        this._showTemporaryMessage('Dashboard section selected');
    },

    /**
     * Show analytics section
     * @private
     */
    _showAnalyticsSection() {
        console.log('Showing analytics section');
        
        // TODO: Load analytics data and charts
        /*
        this._loadAnalyticsCharts();
        this._refreshAnalyticsData();
        */
        
        this._showTemporaryMessage('Analytics section selected - Charts and data will be shown here');
    },

    /**
     * Show settings section
     * @private
     */
    _showSettingsSection() {
        console.log('Showing settings section');
        
        // TODO: Load user settings interface
        /*
        this._loadUserSettings();
        this._showSettingsForm();
        */
        
        this._showTemporaryMessage('Settings section selected - User preferences will be shown here');
    },

    /**
     * Show temporary message (for testing/development)
     * @param {string} message - Message to display
     * @private
     */
    _showTemporaryMessage(message) {
        if (this._elements.dashboardContent) {
            const messageElement = document.createElement('div');
            messageElement.className = 'temp-message';
            messageElement.style.cssText = `
                background: rgba(76, 175, 80, 0.2);
                border: 1px solid rgba(76, 175, 80, 0.5);
                border-radius: 8px;
                padding: 16px;
                margin: 16px 0;
                color: #ffffff;
                text-align: center;
                font-weight: 500;
                letter-spacing: 1px;
            `;
            messageElement.textContent = message;

            // Remove existing temp messages
            const existing = this._elements.dashboardContent.querySelector('.temp-message');
            if (existing) {
                existing.remove();
            }

            // Add new message
            this._elements.dashboardContent.appendChild(messageElement);

            // Remove after 3 seconds
            setTimeout(() => {
                messageElement.remove();
            }, 3000);
        }
    },

    // TODO: Future dashboard methods to implement
    /*
    _loadDashboardWidgets() {
        // Load and render dashboard widgets
    },

    _refreshDashboardData() {
        // Refresh dashboard data from API
    },

    _loadAnalyticsCharts() {
        // Load analytics charts and visualizations
    },

    _refreshAnalyticsData() {
        // Refresh analytics data from API
    },

    _loadUserSettings() {
        // Load user settings and preferences
    },

    _showSettingsForm() {
        // Show settings form interface
    },

    _showOnboardingFlow() {
        // Show user onboarding tutorial
    },

    _startSessionTimeoutCheck() {
        // Start session timeout monitoring
    },

    _handleWidgetClick(event) {
        // Handle widget interactions
    },

    _handleSearch(query) {
        // Handle search functionality
    }
    */
};

/**
 * Dashboard utility functions
 */
const DashboardUtils = {
    /**
     * Format date for display
     * @param {Date|string} date - Date to format
     * @returns {string} - Formatted date string
     */
    formatDate(date) {
        const dateObj = typeof date === 'string' ? new Date(date) : date;
        return dateObj.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    },

    /**
     * Format time for display
     * @param {Date|string} date - Date/time to format
     * @returns {string} - Formatted time string
     */
    formatTime(date) {
        const dateObj = typeof date === 'string' ? new Date(date) : date;
        return dateObj.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    /**
     * Calculate time since login
     * @param {string} loginTime - Login timestamp
     * @returns {string} - Human-readable time difference
     */
    getTimeSinceLogin(loginTime) {
        const login = new Date(loginTime);
        const now = new Date();
        const diffMs = now - login;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
        
        const diffHours = Math.floor(diffMins / 60);
        return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    }
};

/**
 * Initialize dashboard when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', () => {
    DashboardController.init();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        DashboardController,
        DashboardUtils
    };
}