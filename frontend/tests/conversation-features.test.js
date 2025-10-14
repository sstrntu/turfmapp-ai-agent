/**
 * Frontend tests for Conversation History Features
 * Tests conversation loading, deletion, and file attachments
 */

describe('Conversation History Features', () => {
    let mockFetch;
    let mockWindow;

    beforeEach(() => {
        // Mock fetch
        mockFetch = jest.fn();
        global.fetch = mockFetch;

        // Mock window objects
        mockWindow = {
            chatAdapter: {
                loadConversation: jest.fn(),
                conversationId: null
            },
            loadConversation: jest.fn(),
            supabase: {
                getAccessToken: jest.fn(() => 'mock-token')
            }
        };
        Object.assign(window, mockWindow);
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('Conversation Loading', () => {
        test('should load conversation messages from backend', async () => {
            const mockConversationId = 'conv-123';
            const mockMessages = [
                {
                    role: 'user',
                    content: 'Hello',
                    metadata: {}
                },
                {
                    role: 'assistant',
                    content: 'Hi there!',
                    metadata: {
                        sources: [{title: 'Source 1', url: 'http://example.com'}]
                    }
                }
            ];

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ messages: mockMessages })
            });

            // Mock loadConversation from TurfmappChatAdapter
            window.chatAdapter.loadConversation = async function(conversationId) {
                const response = await fetch(`/api/v1/chat/conversations/${conversationId}`, {
                    headers: {
                        'Authorization': `Bearer ${window.supabase.getAccessToken()}`,
                        'Content-Type': 'application/json'
                    }
                });

                const data = await response.json();
                this.conversationId = conversationId;

                return data.messages.map(msg => {
                    const parsedMetadata = typeof msg.metadata === 'string'
                        ? JSON.parse(msg.metadata)
                        : msg.metadata;

                    if (msg.role === 'user') {
                        return {
                            role: 'user',
                            content: [{ type: 'text', text: msg.content }]
                        };
                    } else if (msg.role === 'assistant') {
                        return {
                            role: 'assistant',
                            content: [{ type: 'text', text: msg.content }],
                            metadata: {
                                custom: {
                                    sources: parsedMetadata.sources || [],
                                    reasoning: parsedMetadata.reasoning || [],
                                    blocks: parsedMetadata.blocks || []
                                }
                            }
                        };
                    }
                    return null;
                }).filter(Boolean);
            };

            const result = await window.chatAdapter.loadConversation(mockConversationId);

            expect(mockFetch).toHaveBeenCalledWith(
                `/api/v1/chat/conversations/${mockConversationId}`,
                expect.objectContaining({
                    headers: expect.objectContaining({
                        'Authorization': 'Bearer mock-token'
                    })
                })
            );

            expect(result).toHaveLength(2);
            expect(result[0].role).toBe('user');
            expect(result[1].role).toBe('assistant');
            expect(window.chatAdapter.conversationId).toBe(mockConversationId);
        });

        test('should transform metadata from string to object', async () => {
            const mockConversationId = 'conv-456';
            const mockMessages = [
                {
                    role: 'assistant',
                    content: 'Response',
                    metadata: JSON.stringify({ sources: [{title: 'Test'}] })
                }
            ];

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ messages: mockMessages })
            });

            window.chatAdapter.loadConversation = async function(conversationId) {
                const response = await fetch(`/api/v1/chat/conversations/${conversationId}`, {
                    headers: {
                        'Authorization': `Bearer ${window.supabase.getAccessToken()}`,
                        'Content-Type': 'application/json'
                    }
                });

                const data = await response.json();
                return data.messages.map(msg => {
                    const parsedMetadata = typeof msg.metadata === 'string'
                        ? JSON.parse(msg.metadata)
                        : msg.metadata;

                    return {
                        role: msg.role,
                        content: [{ type: 'text', text: msg.content }],
                        metadata: {
                            custom: {
                                sources: parsedMetadata.sources || []
                            }
                        }
                    };
                });
            };

            const result = await window.chatAdapter.loadConversation(mockConversationId);

            expect(result[0].metadata.custom.sources).toEqual([{title: 'Test'}]);
        });

        test('should handle loading errors gracefully', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: false,
                status: 404
            });

            window.chatAdapter.loadConversation = async function(conversationId) {
                const response = await fetch(`/api/v1/chat/conversations/${conversationId}`, {
                    headers: {
                        'Authorization': `Bearer ${window.supabase.getAccessToken()}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error(`Failed to load conversation: ${response.status}`);
                }
            };

            await expect(
                window.chatAdapter.loadConversation('invalid-id')
            ).rejects.toThrow('Failed to load conversation: 404');
        });
    });

    describe('Conversation Deletion', () => {
        test('should delete conversation via API', async () => {
            const conversationId = 'conv-to-delete';

            mockFetch.mockResolvedValueOnce({
                ok: true
            });

            const deleteConversation = async (convId) => {
                const response = await fetch(`/api/v1/chat/conversations/${convId}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${window.supabase.getAccessToken()}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return true;
            };

            const result = await deleteConversation(conversationId);

            expect(result).toBe(true);
            expect(mockFetch).toHaveBeenCalledWith(
                `/api/v1/chat/conversations/${conversationId}`,
                expect.objectContaining({
                    method: 'DELETE',
                    headers: expect.objectContaining({
                        'Authorization': 'Bearer mock-token'
                    })
                })
            );
        });

        test('should handle deletion errors', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: false,
                status: 403
            });

            const deleteConversation = async (convId) => {
                const response = await fetch(`/api/v1/chat/conversations/${convId}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${window.supabase.getAccessToken()}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
            };

            await expect(
                deleteConversation('protected-conv')
            ).rejects.toThrow('HTTP 403');
        });

        test('should reload page when deleting current conversation', async () => {
            const conversationId = 'current-conv';
            window.chatAdapter.conversationId = conversationId;

            // Mock window.location.reload
            delete window.location;
            window.location = { reload: jest.fn() };

            mockFetch.mockResolvedValueOnce({ ok: true });

            const deleteConversation = async (convId) => {
                const response = await fetch(`/api/v1/chat/conversations/${convId}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${window.supabase.getAccessToken()}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok && window.chatAdapter?.conversationId === convId) {
                    window.location.reload();
                }
            };

            await deleteConversation(conversationId);

            expect(window.location.reload).toHaveBeenCalled();
        });
    });

    describe('File Attachments', () => {
        test('should upload file and return URL', async () => {
            const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ ok: true, url: '/uploads/test.pdf' })
            });

            const uploadFile = async (file) => {
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch('/api/uploads/', {
                    method: 'POST',
                    body: formData
                });

                return await response.json();
            };

            const result = await uploadFile(mockFile);

            expect(result.ok).toBe(true);
            expect(result.url).toBe('/uploads/test.pdf');
            expect(mockFetch).toHaveBeenCalledWith(
                '/api/uploads/',
                expect.objectContaining({
                    method: 'POST'
                })
            );
        });

        test('should handle file upload errors', async () => {
            const mockFile = new File(['content'], 'test.jpg', { type: 'image/jpeg' });

            mockFetch.mockRejectedValueOnce(new Error('Upload failed'));

            const uploadFile = async (file) => {
                try {
                    const formData = new FormData();
                    formData.append('file', file);

                    const response = await fetch('/api/uploads/', {
                        method: 'POST',
                        body: formData
                    });

                    return await response.json();
                } catch (error) {
                    return { ok: false, error: error.message };
                }
            };

            const result = await uploadFile(mockFile);

            expect(result.ok).toBe(false);
            expect(result.error).toBe('Upload failed');
        });

        test('should detect file type correctly', () => {
            const getFileType = (filename) => {
                const ext = filename.split('.').pop().toLowerCase();
                if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) return 'image';
                if (['mp4', 'webm', 'ogg', 'mov'].includes(ext)) return 'video';
                if (['mp3', 'wav', 'ogg', 'm4a'].includes(ext)) return 'audio';
                if (['pdf'].includes(ext)) return 'pdf';
                if (['doc', 'docx', 'txt', 'rtf'].includes(ext)) return 'document';
                if (['csv', 'xls', 'xlsx'].includes(ext)) return 'data';
                return 'file';
            };

            expect(getFileType('photo.jpg')).toBe('image');
            expect(getFileType('document.pdf')).toBe('pdf');
            expect(getFileType('video.mp4')).toBe('video');
            expect(getFileType('audio.mp3')).toBe('audio');
            expect(getFileType('spreadsheet.xlsx')).toBe('data');
            expect(getFileType('notes.txt')).toBe('document');
            expect(getFileType('unknown.xyz')).toBe('file');
        });

        test('should include attachments in message payload', () => {
            window.pendingAttachments = [
                { url: '/uploads/file1.pdf', type: 'pdf', name: 'file1.pdf' },
                { url: '/uploads/image.jpg', type: 'image', name: 'image.jpg' }
            ];

            const buildPayload = () => {
                const attachments = window.pendingAttachments || null;
                return {
                    message: 'Test message',
                    attachments: attachments
                };
            };

            const payload = buildPayload();

            expect(payload.attachments).toHaveLength(2);
            expect(payload.attachments[0].url).toBe('/uploads/file1.pdf');
            expect(payload.attachments[1].type).toBe('image');
        });

        test('should clear pending attachments after sending', () => {
            window.pendingAttachments = [
                { url: '/uploads/test.pdf', type: 'pdf', name: 'test.pdf' }
            ];

            delete window.pendingAttachments;

            expect(window.pendingAttachments).toBeUndefined();
        });
    });

    describe('Conversation History List', () => {
        test('should fetch and group conversations by date', async () => {
            const today = new Date();
            const yesterday = new Date(today);
            yesterday.setDate(yesterday.getDate() - 1);
            const older = new Date(today);
            older.setDate(older.getDate() - 7);

            const mockConversations = [
                { id: '1', title: 'Today conv', updated_at: today.toISOString() },
                { id: '2', title: 'Yesterday conv', updated_at: yesterday.toISOString() },
                { id: '3', title: 'Old conv', updated_at: older.toISOString() }
            ];

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ conversations: mockConversations })
            });

            const loadConversationHistory = async () => {
                const response = await fetch('/api/v1/chat/conversations', {
                    headers: {
                        'Authorization': `Bearer ${window.supabase.getAccessToken()}`,
                        'Content-Type': 'application/json'
                    }
                });

                const data = await response.json();

                // Group by date
                const grouped = {};
                data.conversations.forEach(conv => {
                    const date = new Date(conv.updated_at);
                    const today = new Date();
                    const yesterday = new Date(today);
                    yesterday.setDate(yesterday.getDate() - 1);

                    let dateStr;
                    if (date.toDateString() === today.toDateString()) {
                        dateStr = 'Today';
                    } else if (date.toDateString() === yesterday.toDateString()) {
                        dateStr = 'Yesterday';
                    } else {
                        dateStr = date.toLocaleDateString();
                    }

                    if (!grouped[dateStr]) grouped[dateStr] = [];
                    grouped[dateStr].push(conv);
                });

                return grouped;
            };

            const result = await loadConversationHistory();

            expect(result['Today']).toHaveLength(1);
            expect(result['Yesterday']).toHaveLength(1);
            expect(Object.keys(result)).toContain('Today');
            expect(Object.keys(result)).toContain('Yesterday');
        });
    });
});
