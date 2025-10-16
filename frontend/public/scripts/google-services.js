/**
 * Google Services Integration for TURFMAPP
 * Handles Gmail, Drive, and Calendar API interactions through backend
 */

'use strict';

/**
 * Google Services Controller
 */
const GoogleServices = {
    /**
     * Check if user has Google authentication
     */
    async checkGoogleAuth() {
        try {
            const response = await window.supabase.apiRequest('/api/v1/google/auth/status');
            const data = await response.json();

            if (response.ok) {
                return data.data;
            } else {
                console.error('Error checking Google auth status:', data);
                return { has_tokens: false };
            }
        } catch (error) {
            console.error('Error checking Google auth status:', error);
            return { has_tokens: false };
        }
    },

    /**
     * Initiate Google OAuth flow
     */
    async authenticateGoogle() {
        try {
            // Generate CSRF token for additional security
            const csrfToken = this._generateCSRFToken();
            this._storeCSRFToken(csrfToken);

            const response = await window.supabase.apiRequest('/api/v1/google/auth/url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    state: csrfToken
                })
            });
            const data = await response.json();

            if (response.ok && data.success) {
                // Redirect to Google OAuth
                window.location.href = data.data.auth_url;
            } else {
                throw new Error(data.message || 'Failed to get Google auth URL');
            }
        } catch (error) {
            console.error('Error authenticating with Google:', error);
            throw error;
        }
    },

    /**
     * Handle Google OAuth callback
     */
    async handleGoogleCallback(code, state) {
        try {
            // Validate CSRF token first
            if (state && !this._validateCSRFToken(state)) {
                throw new Error('Invalid authentication state - possible CSRF attack');
            }

            const response = await window.supabase.apiRequest('/api/v1/google/auth/callback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ code, state })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                return data.data;
            } else {
                throw new Error(data.message || 'Google authentication failed');
            }
        } catch (error) {
            console.error('Error handling Google callback:', error);
            throw error;
        }
    },

    /**
     * Refresh Google tokens
     */
    async refreshGoogleTokens() {
        try {
            const response = await window.supabase.apiRequest('/api/v1/google/auth/refresh', {
                method: 'POST'
            });

            const data = await response.json();

            if (response.ok && data.success) {
                return true;
            } else {
                throw new Error(data.message || 'Failed to refresh Google tokens');
            }
        } catch (error) {
            console.error('Error refreshing Google tokens:', error);
            return false;
        }
    },

    /**
     * Ensure valid tokens before API calls
     */
    async ensureValidTokens() {
        const authStatus = await this.checkGoogleAuth();
        if (authStatus.has_tokens && this.isTokenExpired(authStatus.expires_at)) {
            const refreshed = await this.refreshGoogleTokens();
            if (!refreshed) {
                await this.authenticateGoogle();
                throw new Error('Please re-authenticate with Google');
            }
        }
        return true;
    },

    /**
     * Check if token is expired
     */
    isTokenExpired(expiresAt) {
        if (!expiresAt) return true;
        return new Date(expiresAt) <= new Date();
    },

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
    },

    /**
     * Store CSRF token for validation
     */
    _storeCSRFToken(token) {
        sessionStorage.setItem('google-oauth-csrf-token', token);
        // Also set expiry (5 minutes for OAuth flow)
        sessionStorage.setItem('google-oauth-csrf-expiry', (Date.now() + 300000).toString());
    },

    /**
     * Validate CSRF token
     */
    _validateCSRFToken(token) {
        const storedToken = sessionStorage.getItem('google-oauth-csrf-token');
        const expiry = sessionStorage.getItem('google-oauth-csrf-expiry');

        // Clean up tokens after use
        sessionStorage.removeItem('google-oauth-csrf-token');
        sessionStorage.removeItem('google-oauth-csrf-expiry');

        if (!storedToken || !expiry) {
            console.error('Google OAuth CSRF token not found or expired');
            return false;
        }

        if (Date.now() > parseInt(expiry)) {
            console.error('Google OAuth CSRF token expired');
            return false;
        }

        if (storedToken !== token) {
            console.error('Google OAuth CSRF token mismatch');
            return false;
        }

        return true;
    },

    // Gmail Methods
    /**
     * Get Gmail messages
     */
    async getGmailMessages(query = '', maxResults = 10) {
        try {
            const params = new URLSearchParams({
                query,
                max_results: maxResults.toString()
            });

            const response = await window.supabase.apiRequest(`/api/v1/google/gmail/messages?${params}`);
            const data = await response.json();

            if (response.ok) {
                return data;
            } else {
                throw new Error(data.detail || 'Failed to get Gmail messages');
            }
        } catch (error) {
            console.error('Error getting Gmail messages:', error);
            throw error;
        }
    },

    /**
     * Get specific Gmail message
     */
    async getGmailMessage(messageId) {
        try {
            const response = await window.supabase.apiRequest(`/api/v1/google/gmail/messages/${messageId}`);
            const data = await response.json();

            if (response.ok) {
                return data;
            } else {
                throw new Error(data.detail || 'Failed to get Gmail message');
            }
        } catch (error) {
            console.error('Error getting Gmail message:', error);
            throw error;
        }
    },

    // Google Drive Methods
    /**
     * Get Google Drive files
     */
    async getDriveFiles(query = '', maxResults = 10) {
        try {
            const params = new URLSearchParams({
                query,
                max_results: maxResults.toString()
            });

            const response = await window.supabase.apiRequest(`/api/v1/google/drive/files?${params}`);
            const data = await response.json();

            if (response.ok) {
                return data;
            } else {
                throw new Error(data.detail || 'Failed to get Drive files');
            }
        } catch (error) {
            console.error('Error getting Drive files:', error);
            throw error;
        }
    },

    // Google Calendar Methods
    /**
     * Get Google Calendar events
     */
    async getCalendarEvents(calendarId = 'primary', maxResults = 10) {
        try {
            const params = new URLSearchParams({
                calendar_id: calendarId,
                max_results: maxResults.toString()
            });

            const response = await window.supabase.apiRequest(`/api/v1/google/calendar/events?${params}`);
            const data = await response.json();

            if (response.ok) {
                return data;
            } else {
                throw new Error(data.detail || 'Failed to get Calendar events');
            }
        } catch (error) {
            console.error('Error getting Calendar events:', error);
            throw error;
        }
    },

    // UI Helper Methods
    /**
     * Display Gmail messages in UI
     */
    displayGmailMessages(messages, containerId = 'gmail-messages') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container ${containerId} not found`);
            return;
        }

        if (!messages || messages.length === 0) {
            container.innerHTML = '<p>No messages found.</p>';
            return;
        }

        const messagesHtml = messages.map(message => `
            <div class="message-item" onclick="GoogleServices.showMessageDetails('${message.id}')">
                <div class="message-header">
                    <strong>${this.escapeHtml(message.subject || '(No Subject)')}</strong>
                    <span class="message-date">${this.formatDate(message.date)}</span>
                </div>
                <div class="message-from">${this.escapeHtml(message.from)}</div>
                <div class="message-snippet">${this.escapeHtml(message.snippet)}</div>
            </div>
        `).join('');

        container.innerHTML = `
            <h3>Gmail Messages</h3>
            <div class="messages-list">${messagesHtml}</div>
        `;
    },

    /**
     * Display Google Drive files in UI
     */
    displayDriveFiles(files, containerId = 'drive-files') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container ${containerId} not found`);
            return;
        }

        if (!files || files.length === 0) {
            container.innerHTML = '<p>No files found.</p>';
            return;
        }

        const filesHtml = files.map(file => `
            <div class="file-item">
                <div class="file-name">${this.escapeHtml(file.name)}</div>
                <div class="file-details">
                    <span class="file-type">${this.escapeHtml(file.mimeType || 'Unknown')}</span>
                    <span class="file-modified">${this.formatDate(file.modifiedTime)}</span>
                    ${file.size ? `<span class="file-size">${this.formatFileSize(file.size)}</span>` : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = `
            <h3>Google Drive Files</h3>
            <div class="files-list">${filesHtml}</div>
        `;
    },

    /**
     * Display Google Calendar events in UI
     */
    displayCalendarEvents(events, containerId = 'calendar-events') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container ${containerId} not found`);
            return;
        }

        if (!events || events.length === 0) {
            container.innerHTML = '<p>No events found.</p>';
            return;
        }

        const eventsHtml = events.map(event => `
            <div class="event-item">
                <div class="event-title">${this.escapeHtml(event.summary || '(No Title)')}</div>
                <div class="event-time">
                    ${this.formatEventTime(event.start, event.end)}
                </div>
                ${event.description ? `<div class="event-description">${this.escapeHtml(event.description)}</div>` : ''}
            </div>
        `).join('');

        container.innerHTML = `
            <h3>Calendar Events</h3>
            <div class="events-list">${eventsHtml}</div>
        `;
    },

    /**
     * Show message details (can be customized)
     */
    async showMessageDetails(messageId) {
        try {
            const message = await this.getGmailMessage(messageId);
            // You can customize this to show in a modal or dedicated area
            //console.log('Message details:', message);
            alert(`Message: ${message.snippet}`);
        } catch (error) {
            alert('Failed to load message details');
        }
    },

    // Advanced Drive Methods
    /**
     * Create folder structure in Google Drive
     */
    async createFolderStructure(folderPath, rootFolder = 'TURFMAPP') {
        try {
            await this.ensureValidTokens();

            const formData = new FormData();
            formData.append('folder_path', folderPath);
            formData.append('root_folder', rootFolder);

            const response = await window.supabase.apiRequest('/api/v1/google/drive/create-folder', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                return data;
            } else {
                throw new Error(data.detail || 'Failed to create folder structure');
            }
        } catch (error) {
            console.error('Error creating folder structure:', error);
            throw error;
        }
    },

    /**
     * Upload file to Google Drive
     */
    async uploadToDrive(file, folderPath = null) {
        try {
            await this.ensureValidTokens();

            const formData = new FormData();
            formData.append('file', file);
            if (folderPath) {
                formData.append('folder_path', folderPath);
            }

            const response = await window.supabase.apiRequest('/api/v1/google/drive/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                return data;
            } else {
                throw new Error(data.detail || 'Failed to upload file');
            }
        } catch (error) {
            console.error('Error uploading to Drive:', error);
            throw error;
        }
    },

    /**
     * Delete file from Google Drive
     */
    async deleteFromDrive(fileId) {
        try {
            await this.ensureValidTokens();

            const response = await window.supabase.apiRequest(`/api/v1/google/drive/files/${fileId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (response.ok) {
                return data;
            } else {
                throw new Error(data.detail || 'Failed to delete file');
            }
        } catch (error) {
            console.error('Error deleting from Drive:', error);
            throw error;
        }
    },

    /**
     * List files in specific folder
     */
    async listFilesInFolder(folderPath) {
        try {
            await this.ensureValidTokens();

            const response = await window.supabase.apiRequest(`/api/v1/google/drive/folder/${encodeURIComponent(folderPath)}/files`);
            const data = await response.json();

            if (response.ok) {
                return data;
            } else {
                throw new Error(data.detail || 'Failed to list files');
            }
        } catch (error) {
            console.error('Error listing files:', error);
            throw error;
        }
    },

    /**
     * Check if folder exists
     */
    async folderExists(folderPath) {
        try {
            await this.ensureValidTokens();

            const response = await window.supabase.apiRequest(`/api/v1/google/drive/folder-exists/${encodeURIComponent(folderPath)}`);
            const data = await response.json();

            if (response.ok) {
                return data.exists;
            } else {
                return false;
            }
        } catch (error) {
            console.error('Error checking folder:', error);
            return false;
        }
    },

    // UI Helper Methods
    /**
     * Display file upload progress
     */
    showUploadProgress(filename, progress) {
        // You can implement a progress UI here
        //console.log(`Uploading ${filename}: ${progress}%`);
    },

    // Utility Methods
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    formatDate(dateString) {
        if (!dateString) return '';
        try {
            return new Date(dateString).toLocaleDateString();
        } catch (e) {
            return dateString;
        }
    },

    formatFileSize(bytes) {
        if (!bytes) return '';
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    },

    formatEventTime(start, end) {
        if (!start) return '';

        const startTime = start.dateTime ? new Date(start.dateTime) : new Date(start.date);
        const endTime = end ? (end.dateTime ? new Date(end.dateTime) : new Date(end.date)) : null;

        let timeStr = startTime.toLocaleString();
        if (endTime && endTime.getTime() !== startTime.getTime()) {
            timeStr += ` - ${endTime.toLocaleString()}`;
        }

        return timeStr;
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { GoogleServices };
}
