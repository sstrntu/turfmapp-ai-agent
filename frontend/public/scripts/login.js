/**
 * TURFMAPP Login Controller
 * 
 * Handles login page interactions following code.md standards.
 * Manages form validation, submission, and user feedback.
 */

'use strict';

/**
 * Login Page Controller
 * Main controller for login page functionality
 */
const LoginController = {
    /**
     * DOM element references
     * @private
     */
    _elements: {
        form: null,
        usernameInput: null,
        passwordInput: null,
        submitButton: null,
        usernameError: null,
        passwordError: null,
        statusMessage: null
    },

    /**
     * Form state
     * @private
     */
    _state: {
        isSubmitting: false,
        validationErrors: {}
    },

    /**
     * Initialize the login controller
     */
    init() {
        this._initializeElements();
        this._attachEventListeners();
        this._setupFormValidation();
        
        // Set initial focus to username field
        if (this._elements.usernameInput) {
            this._elements.usernameInput.focus();
        }
    },

    /**
     * Initialize DOM element references
     * @private
     */
    _initializeElements() {
        this._elements.form = DOMUtils.getElementById('login-form') || document.querySelector('.login-form');
        this._elements.usernameInput = DOMUtils.getElementById('username');
        this._elements.passwordInput = DOMUtils.getElementById('password');
        this._elements.submitButton = document.querySelector('.login-button');
        this._elements.usernameError = DOMUtils.getElementById('username-error');
        this._elements.passwordError = DOMUtils.getElementById('password-error');
        this._elements.statusMessage = DOMUtils.getElementById('login-status');

        // Log missing elements for debugging
        Object.entries(this._elements).forEach(([key, element]) => {
            if (!element) {
                console.warn(`Login element '${key}' not found`);
            }
        });
    },

    /**
     * Attach event listeners to form elements
     * @private
     */
    _attachEventListeners() {
        // Form submission
        if (this._elements.form) {
            this._elements.form.addEventListener('submit', (event) => {
                this.handleSubmit(event);
            });
        }

        // Real-time validation on input blur
        if (this._elements.usernameInput) {
            this._elements.usernameInput.addEventListener('blur', 
                AnimationUtils.debounce(() => this._validateField('username'), 300)
            );
            
            // Clear error on input
            this._elements.usernameInput.addEventListener('input', () => {
                this._clearFieldError('username');
            });
        }

        if (this._elements.passwordInput) {
            this._elements.passwordInput.addEventListener('blur',
                AnimationUtils.debounce(() => this._validateField('password'), 300)
            );
            
            // Clear error on input
            this._elements.passwordInput.addEventListener('input', () => {
                this._clearFieldError('password');
            });
        }

        // Handle Enter key in form fields
        [this._elements.usernameInput, this._elements.passwordInput].forEach(input => {
            if (input) {
                input.addEventListener('keypress', (event) => {
                    if (event.key === 'Enter') {
                        event.preventDefault();
                        this.handleSubmit(event);
                    }
                });
            }
        });
    },

    /**
     * Set up form validation rules
     * @private
     */
    _setupFormValidation() {
        // Add HTML5 validation attributes programmatically
        if (this._elements.usernameInput) {
            this._elements.usernameInput.setAttribute('minlength', AppConfig.VALIDATION.USERNAME.MIN_LENGTH);
            this._elements.usernameInput.setAttribute('maxlength', AppConfig.VALIDATION.USERNAME.MAX_LENGTH);
            this._elements.usernameInput.setAttribute('pattern', AppConfig.VALIDATION.USERNAME.PATTERN.source);
        }

        if (this._elements.passwordInput) {
            this._elements.passwordInput.setAttribute('minlength', AppConfig.VALIDATION.PASSWORD.MIN_LENGTH);
            this._elements.passwordInput.setAttribute('maxlength', AppConfig.VALIDATION.PASSWORD.MAX_LENGTH);
        }
    },

    /**
     * Handle form submission
     * @param {Event} event - Form submit event
     * @returns {boolean} - Always false to prevent default form submission
     */
    async handleSubmit(event) {
        event.preventDefault();

        // Prevent multiple submissions
        if (this._state.isSubmitting) {
            return false;
        }

        try {
            this._state.isSubmitting = true;
            this._setSubmitButtonState(true);

            // Get form data
            const formData = this._getFormData();

            // Validate form
            const validation = ValidationUtils.validateForm(formData);
            if (!validation.isValid) {
                this._displayValidationErrors(validation.errors);
                return false;
            }

            // Clear any previous errors
            this._clearAllErrors();

            // Show loading state
            this._showStatusMessage('Authenticating...', 'info');

            // Attempt authentication
            const authResult = await AuthService.authenticate(formData);

            if (authResult.success) {
                this._showStatusMessage(authResult.message, 'success');
                
                // Redirect to home page after short delay
                await AnimationUtils.wait(1000);
                window.location.href = AppConfig.ROUTES.HOME;
            } else {
                this._showStatusMessage(authResult.message, 'error');
                
                // Handle account lockout
                if (authResult.locked) {
                    this._setSubmitButtonState(true, 'Account Locked');
                }
            }

        } catch (error) {
            ErrorUtils.logError('LoginController.handleSubmit', error);
            this._showStatusMessage(AppConfig.MESSAGES.NETWORK_ERROR, 'error');
        } finally {
            this._state.isSubmitting = false;
            if (!this._state.isLocked) {
                this._setSubmitButtonState(false);
            }
        }

        return false;
    },

    /**
     * Get form data
     * @returns {Object} - Form data object
     * @private
     */
    _getFormData() {
        return {
            username: this._elements.usernameInput?.value.trim() || '',
            password: this._elements.passwordInput?.value || ''
        };
    },

    /**
     * Validate individual form field
     * @param {string} fieldName - Name of field to validate
     * @private
     */
    _validateField(fieldName) {
        const formData = this._getFormData();
        
        if (fieldName === 'username') {
            const validation = ValidationUtils.validateUsername(formData.username);
            if (!validation.isValid) {
                this._showFieldError('username', validation.message);
            } else {
                this._clearFieldError('username');
            }
        } else if (fieldName === 'password') {
            const validation = ValidationUtils.validatePassword(formData.password);
            if (!validation.isValid) {
                this._showFieldError('password', validation.message);
            } else {
                this._clearFieldError('password');
            }
        }
    },

    /**
     * Display validation errors
     * @param {Object} errors - Validation errors object
     * @private
     */
    _displayValidationErrors(errors) {
        Object.entries(errors).forEach(([field, message]) => {
            this._showFieldError(field, message);
        });
        
        // Focus first error field
        const firstErrorField = Object.keys(errors)[0];
        if (firstErrorField && this._elements[firstErrorField + 'Input']) {
            this._elements[firstErrorField + 'Input'].focus();
        }
    },

    /**
     * Show field-specific error message
     * @param {string} fieldName - Field name
     * @param {string} message - Error message
     * @private
     */
    _showFieldError(fieldName, message) {
        const errorElement = this._elements[fieldName + 'Error'];
        if (errorElement) {
            ErrorUtils.showError(message, errorElement);
        }
        
        this._state.validationErrors[fieldName] = message;
    },

    /**
     * Clear field-specific error message
     * @param {string} fieldName - Field name
     * @private
     */
    _clearFieldError(fieldName) {
        const errorElement = this._elements[fieldName + 'Error'];
        if (errorElement) {
            ErrorUtils.clearError(errorElement);
        }
        
        delete this._state.validationErrors[fieldName];
    },

    /**
     * Clear all error messages
     * @private
     */
    _clearAllErrors() {
        ['username', 'password'].forEach(field => {
            this._clearFieldError(field);
        });
        
        if (this._elements.statusMessage) {
            DOMUtils.removeClass(this._elements.statusMessage, 'show');
        }
    },

    /**
     * Show status message
     * @param {string} message - Status message
     * @param {string} type - Message type ('info', 'success', 'error')
     * @private
     */
    _showStatusMessage(message, type = 'info') {
        if (!this._elements.statusMessage) return;
        
        // Clear previous classes
        ['info', 'success', 'error'].forEach(cls => {
            DOMUtils.removeClass(this._elements.statusMessage, cls);
        });
        
        // Set message and type
        DOMUtils.setText(this._elements.statusMessage, message);
        DOMUtils.addClass(this._elements.statusMessage, type);
        DOMUtils.addClass(this._elements.statusMessage, 'show');
    },

    /**
     * Set submit button state
     * @param {boolean} disabled - Whether button should be disabled
     * @param {string} text - Optional button text override
     * @private
     */
    _setSubmitButtonState(disabled, text = null) {
        if (!this._elements.submitButton) return;
        
        this._elements.submitButton.disabled = disabled;
        
        if (text) {
            const buttonTextElement = this._elements.submitButton.querySelector('.button-text');
            if (buttonTextElement) {
                DOMUtils.setText(buttonTextElement, text);
            }
        } else if (!disabled) {
            // Reset to original text
            const buttonTextElement = this._elements.submitButton.querySelector('.button-text');
            if (buttonTextElement) {
                DOMUtils.setText(buttonTextElement, 'LOGIN');
            }
        }
    }
};

/**
 * Initialize login controller when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', () => {
    LoginController.init();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LoginController;
}