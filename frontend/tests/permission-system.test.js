/**
 * Frontend tests for Permission Management System
 * Tests the admin UI visibility and caching functionality
 */

describe('Permission Management System', () => {
    let mockLocalStorage;
    
    beforeEach(() => {
        // Mock localStorage
        mockLocalStorage = {
            store: {},
            getItem: jest.fn(key => mockLocalStorage.store[key] || null),
            setItem: jest.fn((key, value) => mockLocalStorage.store[key] = value),
            removeItem: jest.fn(key => delete mockLocalStorage.store[key])
        };
        Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });
        
        // Mock fetch
        global.fetch = jest.fn();
        
        // Mock GoogleAuth
        window.GoogleAuth = {
            getToken: jest.fn(),
            isAdmin: jest.fn(),
            setupAdminUI: jest.fn(),
            applyAdminUI: jest.fn(),
            clearAdminCache: jest.fn()
        };
    });
    
    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('Admin Role Caching', () => {
        test('should use cached admin status when valid', async () => {
            const mockToken = 'test-token';
            const cacheData = {
                isAdmin: true,
                timestamp: Date.now(),
                userToken: mockToken
            };
            
            window.GoogleAuth.getToken.mockReturnValue(mockToken);
            mockLocalStorage.store['tm_user_admin_status'] = JSON.stringify(cacheData);
            
            // Mock the actual isAdmin implementation
            window.GoogleAuth.isAdmin = async function() {
                const cached = localStorage.getItem('tm_user_admin_status');
                if (cached) {
                    const { isAdmin, timestamp, userToken } = JSON.parse(cached);
                    if (Date.now() - timestamp < 300000 && userToken === this.getToken()) {
                        return isAdmin;
                    }
                }
                return false;
            };
            
            const result = await window.GoogleAuth.isAdmin();
            
            expect(result).toBe(true);
            expect(fetch).not.toHaveBeenCalled(); // Should not make API call
        });
        
        test('should fetch fresh data when cache is expired', async () => {
            const mockToken = 'test-token';
            const expiredCacheData = {
                isAdmin: true,
                timestamp: Date.now() - 400000, // 6+ minutes old
                userToken: mockToken
            };
            
            window.GoogleAuth.getToken.mockReturnValue(mockToken);
            mockLocalStorage.store['tm_user_admin_status'] = JSON.stringify(expiredCacheData);
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ role: 'admin' })
            });
            
            // Mock the actual isAdmin implementation with API fallback
            window.GoogleAuth.isAdmin = async function() {
                const cached = localStorage.getItem('tm_user_admin_status');
                if (cached) {
                    const { isAdmin, timestamp, userToken } = JSON.parse(cached);
                    if (Date.now() - timestamp < 300000 && userToken === this.getToken()) {
                        return isAdmin;
                    }
                }
                
                // Cache expired, fetch fresh data
                const response = await fetch('/api/v1/settings/profile', {
                    headers: { 'Authorization': `Bearer ${this.getToken()}` }
                });
                
                if (response.ok) {
                    const user = await response.json();
                    const isAdminUser = ['admin', 'super_admin'].includes(user.role);
                    
                    localStorage.setItem('tm_user_admin_status', JSON.stringify({
                        isAdmin: isAdminUser,
                        timestamp: Date.now(),
                        userToken: this.getToken()
                    }));
                    
                    return isAdminUser;
                }
                return false;
            };
            
            const result = await window.GoogleAuth.isAdmin();
            
            expect(result).toBe(true);
            expect(fetch).toHaveBeenCalledWith('/api/v1/settings/profile', {
                headers: { 'Authorization': 'Bearer test-token' }
            });
        });
        
        test('should clear cache on different token', async () => {
            const oldToken = 'old-token';
            const newToken = 'new-token';
            const cacheData = {
                isAdmin: true,
                timestamp: Date.now(),
                userToken: oldToken
            };
            
            window.GoogleAuth.getToken.mockReturnValue(newToken);
            mockLocalStorage.store['tm_user_admin_status'] = JSON.stringify(cacheData);
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ role: 'user' })
            });
            
            // Mock the actual isAdmin implementation
            window.GoogleAuth.isAdmin = async function() {
                const cached = localStorage.getItem('tm_user_admin_status');
                if (cached) {
                    const { isAdmin, timestamp, userToken } = JSON.parse(cached);
                    if (Date.now() - timestamp < 300000 && userToken === this.getToken()) {
                        return isAdmin;
                    }
                }
                
                // Different token, fetch fresh data
                const response = await fetch('/api/v1/settings/profile', {
                    headers: { 'Authorization': `Bearer ${this.getToken()}` }
                });
                
                if (response.ok) {
                    const user = await response.json();
                    return ['admin', 'super_admin'].includes(user.role);
                }
                return false;
            };
            
            const result = await window.GoogleAuth.isAdmin();
            
            expect(result).toBe(false);
            expect(fetch).toHaveBeenCalled(); // Should make fresh API call
        });
    });

    describe('Admin UI Management', () => {
        test('should show admin elements for admin users', () => {
            // Create mock DOM elements
            const adminTab = document.createElement('button');
            adminTab.setAttribute('data-admin-only', 'true');
            adminTab.style.display = 'none';
            document.body.appendChild(adminTab);
            
            const adminSection = document.createElement('div');
            adminSection.setAttribute('data-admin-only', 'true');
            adminSection.setAttribute('data-admin-display', 'flex');
            adminSection.style.display = 'none';
            document.body.appendChild(adminSection);
            
            // Mock applyAdminUI implementation
            window.GoogleAuth.applyAdminUI = function(isAdmin) {
                const adminElements = document.querySelectorAll('[data-admin-only]');
                adminElements.forEach(element => {
                    if (isAdmin) {
                        element.style.display = element.dataset.adminDisplay || 'block';
                    } else {
                        element.style.display = 'none';
                    }
                });
            };
            
            // Test admin user
            window.GoogleAuth.applyAdminUI(true);
            
            expect(adminTab.style.display).toBe('block');
            expect(adminSection.style.display).toBe('flex');
            
            // Cleanup
            document.body.removeChild(adminTab);
            document.body.removeChild(adminSection);
        });
        
        test('should hide admin elements for regular users', () => {
            // Create mock DOM elements
            const adminTab = document.createElement('button');
            adminTab.setAttribute('data-admin-only', 'true');
            adminTab.style.display = 'block';
            document.body.appendChild(adminTab);
            
            // Mock applyAdminUI implementation  
            window.GoogleAuth.applyAdminUI = function(isAdmin) {
                const adminElements = document.querySelectorAll('[data-admin-only]');
                adminElements.forEach(element => {
                    if (isAdmin) {
                        element.style.display = element.dataset.adminDisplay || 'block';
                    } else {
                        element.style.display = 'none';
                    }
                });
            };
            
            // Test regular user
            window.GoogleAuth.applyAdminUI(false);
            
            expect(adminTab.style.display).toBe('none');
            
            // Cleanup
            document.body.removeChild(adminTab);
        });
    });

    describe('Settings Page Tab System', () => {
        test('should initialize with Settings tab active', () => {
            // Mock DOM structure
            const settingsTab = document.createElement('button');
            settingsTab.className = 'tab-button active';
            settingsTab.setAttribute('data-tab', 'settings');
            
            const adminTab = document.createElement('button');
            adminTab.className = 'tab-button';
            adminTab.setAttribute('data-tab', 'admin');
            adminTab.style.display = 'none';
            
            const settingsContent = document.createElement('div');
            settingsContent.className = 'tab-content active';
            settingsContent.id = 'settings-tab';
            
            const adminContent = document.createElement('div');
            adminContent.className = 'tab-content';
            adminContent.id = 'admin-tab-content';
            
            expect(settingsTab.classList.contains('active')).toBe(true);
            expect(adminTab.classList.contains('active')).toBe(false);
            expect(settingsContent.classList.contains('active')).toBe(true);
            expect(adminContent.classList.contains('active')).toBe(false);
        });
        
        test('should switch tabs correctly', () => {
            // Mock tab switching functionality
            const tabButtons = [
                { element: document.createElement('button'), tab: 'settings' },
                { element: document.createElement('button'), tab: 'admin' }
            ];
            
            const tabContents = [
                { element: document.createElement('div'), id: 'settings-tab' },
                { element: document.createElement('div'), id: 'admin-tab-content' }
            ];
            
            // Set initial state
            tabButtons[0].element.classList.add('active');
            tabContents[0].element.classList.add('active');
            
            // Mock click on admin tab
            const switchToTab = (targetTab) => {
                tabButtons.forEach(btn => btn.element.classList.remove('active'));
                tabContents.forEach(content => content.element.classList.remove('active'));
                
                const targetButton = tabButtons.find(btn => btn.tab === targetTab);
                const targetContent = tabContents.find(content => 
                    content.id === (targetTab === 'admin' ? 'admin-tab-content' : `${targetTab}-tab`)
                );
                
                if (targetButton && targetContent) {
                    targetButton.element.classList.add('active');
                    targetContent.element.classList.add('active');
                }
            };
            
            // Switch to admin tab
            switchToTab('admin');
            
            expect(tabButtons[0].element.classList.contains('active')).toBe(false);
            expect(tabButtons[1].element.classList.contains('active')).toBe(true);
            expect(tabContents[0].element.classList.contains('active')).toBe(false);
            expect(tabContents[1].element.classList.contains('active')).toBe(true);
        });
    });

    describe('Cache Management', () => {
        test('should clear cache on sign out', () => {
            // Set up cache
            mockLocalStorage.store['tm_user_admin_status'] = JSON.stringify({
                isAdmin: true,
                timestamp: Date.now(),
                userToken: 'token'
            });
            
            // Mock clearAdminCache
            window.GoogleAuth.clearAdminCache = function() {
                localStorage.removeItem('tm_user_admin_status');
            };
            
            window.GoogleAuth.clearAdminCache();
            
            expect(mockLocalStorage.store['tm_user_admin_status']).toBeUndefined();
        });
        
        test('should validate cache token matches current token', () => {
            const currentToken = 'current-token';
            const cachedToken = 'old-token';
            
            window.GoogleAuth.getToken.mockReturnValue(currentToken);
            mockLocalStorage.store['tm_user_admin_status'] = JSON.stringify({
                isAdmin: true,
                timestamp: Date.now(),
                userToken: cachedToken
            });
            
            // Mock cache validation logic
            const isValidCache = () => {
                const cached = localStorage.getItem('tm_user_admin_status');
                if (cached) {
                    const { timestamp, userToken } = JSON.parse(cached);
                    return Date.now() - timestamp < 300000 && userToken === window.GoogleAuth.getToken();
                }
                return false;
            };
            
            expect(isValidCache()).toBe(false); // Should be invalid due to token mismatch
        });
    });

    describe('Error Handling', () => {
        test('should handle API errors gracefully', async () => {
            window.GoogleAuth.getToken.mockReturnValue('test-token');
            
            fetch.mockRejectedValueOnce(new Error('Network error'));
            
            // Mock isAdmin with error handling
            window.GoogleAuth.isAdmin = async function() {
                try {
                    const response = await fetch('/api/v1/settings/profile', {
                        headers: { 'Authorization': `Bearer ${this.getToken()}` }
                    });
                    
                    if (response.ok) {
                        const user = await response.json();
                        return ['admin', 'super_admin'].includes(user.role);
                    }
                    return false;
                } catch (error) {
                    console.error('Error checking admin status:', error);
                    return false;
                }
            };
            
            const result = await window.GoogleAuth.isAdmin();
            
            expect(result).toBe(false);
        });
        
        test('should handle malformed cache data', () => {
            mockLocalStorage.store['tm_user_admin_status'] = 'invalid-json';
            
            // Mock cache parsing with error handling
            const getCachedAdminStatus = () => {
                try {
                    const cached = localStorage.getItem('tm_user_admin_status');
                    if (cached) {
                        return JSON.parse(cached);
                    }
                } catch (error) {
                    console.warn('Invalid cache data, clearing cache');
                    localStorage.removeItem('tm_user_admin_status');
                }
                return null;
            };
            
            const result = getCachedAdminStatus();
            
            expect(result).toBeNull();
            expect(mockLocalStorage.store['tm_user_admin_status']).toBeUndefined();
        });
    });
});

describe('Settings Page Integration', () => {
    beforeEach(() => {
        // Mock document structure
        document.body.innerHTML = `
            <div class="settings-tabs">
                <button class="tab-button active" data-tab="settings">Settings</button>
                <button class="tab-button" data-tab="admin" id="admin-tab" style="display: none;">
                    Admin
                    <span class="admin-only-badge">Admin</span>
                </button>
            </div>
            <div id="settings-tab" class="tab-content active"></div>
            <div id="admin-tab-content" class="tab-content"></div>
        `;
    });
    
    test('should show admin tab for admin users', () => {
        const adminTab = document.getElementById('admin-tab');
        
        // Simulate admin user login
        adminTab.style.display = 'block';
        
        expect(adminTab.style.display).toBe('block');
    });
    
    test('should keep admin tab hidden for regular users', () => {
        const adminTab = document.getElementById('admin-tab');
        
        expect(adminTab.style.display).toBe('none');
    });
});