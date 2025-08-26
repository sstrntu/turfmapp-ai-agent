// Minimal Chat Controller
// Keeps UI simple, uses existing font/background

(function () {
    'use strict';

    const list = document.getElementById('chat-list');
    const form = document.getElementById('chat-form');
    let input = document.getElementById('chat-input');
    const menuToggle = document.getElementById('menu-toggle');
    const menuPanel = document.getElementById('top-menu');
    const hasChat = !!(list && form && input);

    if (hasChat) {
        function appendMessage(role, text) {
            const bubble = document.createElement('div');
            bubble.className = 'chat-bubble ' + (role === 'user' ? 'user' : 'assistant') + ' message-initial';
            bubble.textContent = text;
            list.appendChild(bubble);
            
            // Animate message appearance
            requestAnimationFrame(() => {
                bubble.classList.remove('message-initial');
                bubble.classList.add('message-appear');
            });
            
            list.scrollTop = list.scrollHeight;
        }

        function createAssistantPlaceholder() {
            const msg = document.createElement('div');
            msg.className = 'chat-bubble assistant typing-bubble message-initial';
            
            // Create ChatGPT-style typing indicator with three bouncing dots
            const typingIndicator = document.createElement('div');
            typingIndicator.className = 'typing-indicator';
            for (let i = 0; i < 3; i++) {
                const dot = document.createElement('div');
                dot.className = 'typing-dot';
                dot.style.animationDelay = `${i * 0.2}s`;
                typingIndicator.appendChild(dot);
            }
            msg.appendChild(typingIndicator);
            
            list.appendChild(msg);
            
            // Animate message appearance
            requestAnimationFrame(() => {
                msg.classList.remove('message-initial');
                msg.classList.add('message-appear');
            });
            
            list.scrollTop = list.scrollHeight;

            return {
                finish(answer, reasoning) {
                    // Remove typing indicator and add typewriter effect
                    msg.classList.remove('typing-bubble');
                    msg.innerHTML = '';
                    
                    // Start typewriter effect
                    this.typewriterEffect(msg, answer || '', () => {
                        list.scrollTop = list.scrollHeight;
                    });
                },
                error() {
                    msg.classList.remove('typing-bubble');
                    msg.innerHTML = '';
                    this.typewriterEffect(msg, 'Sorry, there was an error.', () => {
                        list.scrollTop = list.scrollHeight;
                    });
                },
                typewriterEffect(element, text, callback) {
                    let i = 0;
                    const speed = 20; // milliseconds per character
                    
                    // Add cursor
                    const cursor = document.createElement('span');
                    cursor.className = 'typing-cursor';
                    cursor.textContent = '|';
                    element.appendChild(cursor);
                    
                    function typeChar() {
                        if (i < text.length) {
                            element.textContent = text.substring(0, i + 1);
                            element.appendChild(cursor);
                            i++;
                            setTimeout(typeChar, speed + Math.random() * 20); // Add slight randomness
                            list.scrollTop = list.scrollHeight;
                        } else {
                            // Remove cursor after typing is complete
                            cursor.remove();
                            if (callback) callback();
                        }
                    }
                    
                    typeChar();
                }
            };
        }

        // File attachment management
        let attachments = [];
        const attachmentArea = document.getElementById('attachment-area');
        const fileInput = document.getElementById('file-input');

        function addAttachment(file, url) {
            const attachment = {
                file: file,
                url: url,
                type: getFileType(file.name),
                id: Date.now() + Math.random()
            };
            attachments.push(attachment);
            renderAttachments();
        }

        function removeAttachment(id) {
            attachments = attachments.filter(a => a.id !== id);
            renderAttachments();
        }

        // Make removeAttachment globally accessible
        window.removeAttachment = removeAttachment;

        function renderAttachments() {
            if (attachments.length === 0) {
                attachmentArea.innerHTML = '';
                return;
            }

            attachmentArea.innerHTML = attachments.map(att => `
                <div class="attachment-item">
                    <span class="file-icon">${getFileIcon(att.type)}</span>
                    <span class="file-name">${att.file.name}</span>
                    <button type="button" class="remove-btn" onclick="removeAttachment(${att.id})">×</button>
                </div>
            `).join('');
        }

        function getFileType(filename) {
            const ext = filename.toLowerCase().split('.').pop();
            if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'].includes(ext)) return 'image';
            if (['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm'].includes(ext)) return 'video';
            if (['mp3', 'wav', 'ogg', 'm4a', 'flac'].includes(ext)) return 'audio';
            if (['pdf', 'doc', 'docx', 'txt', 'rtf'].includes(ext)) return 'document';
            if (['json', 'csv', 'xml', 'xlsx'].includes(ext)) return 'data';
            return 'unknown';
        }

        function getFileIcon(type) {
            const icons = {
                image: '🖼️',
                video: '🎥',
                audio: '🎵',
                document: '📄',
                data: '📊',
                unknown: '📁'
            };
            return icons[type] || '📁';
        }

        // Tool button handlers
        document.getElementById('attach-file-btn')?.addEventListener('click', function() {
            fileInput?.click();
        });

        document.getElementById('image-gen-btn')?.addEventListener('click', function() {
            this.classList.toggle('active');
            const isActive = this.classList.contains('active');
            if (isActive) {
                input.placeholder = 'Describe an image to generate...';
            } else {
                input.placeholder = 'Type your message...';
            }
        });

        document.getElementById('web-search-btn')?.addEventListener('click', function() {
            this.classList.toggle('active');
            const isActive = this.classList.contains('active');
            if (isActive) {
                input.placeholder = 'Search the web for...';
            } else {
                input.placeholder = 'Type your message...';
            }
        });

        // File input handler
        fileInput?.addEventListener('change', function(e) {
            for (const file of e.target.files) {
                // Upload file first
                uploadFile(file).then(response => {
                    if (response.ok) {
                        addAttachment(file, response.url);
                    }
                });
            }
            this.value = ''; // Clear input
        });

        async function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/uploads/', {
                    method: 'POST',
                    body: formData
                });
                return await response.json();
            } catch (error) {
                console.error('Upload failed:', error);
                return { ok: false, error: error.message };
            }
        }

        // Load all settings from localStorage
        function loadAllSettings() {
            try {
                return {
                    model: localStorage.getItem('tm_model') || 'gpt-5-mini',
                    developerInstructions: localStorage.getItem('tm_developer_instructions') || 
                        'Tone: To the point with easy to understand language.\nTool Usage: If need to use tools that is not available, ask the user for tool or data access.\nResponse Style: Make sure you have all the available information first before answering. If user ask a question and you do not have good background or context to come up with a good answer, always ask the user back first.',
                    assistantContext: localStorage.getItem('tm_assistant_context') || 
                        'You are an assistant to Turfmapp agency employees. Turfmapp is a sports media marketing and strategy agency. We do a lot of graphics, analytics, technical, and also run businesses such as the coffee shop, space rental, game room, gym, streetwear sports clothing store, etc. Majority of the employees are Thai. They can read/write English but they are more comfortable in Thai.',
                    textFormat: localStorage.getItem('tm_text_format') || 'text',
                    textVerbosity: localStorage.getItem('tm_text_verbosity') || 'medium',
                    reasoningEffort: localStorage.getItem('tm_reasoning_effort') || 'medium',
                    reasoningSummary: localStorage.getItem('tm_reasoning_summary') || 'auto',
                    toolWebSearch: localStorage.getItem('tm_tool_web_search') !== 'false',
                    webSearchContext: localStorage.getItem('tm_web_search_context') || 'medium',
                    toolImageGen: localStorage.getItem('tm_tool_image_generation') === 'true',
                    imageQuality: localStorage.getItem('tm_image_quality') || 'auto',
                    toolMcp: localStorage.getItem('tm_tool_mcp') === 'true',
                    mcpServerLabel: localStorage.getItem('tm_mcp_server_label') || '',
                    mcpConnectorId: localStorage.getItem('tm_mcp_connector_id') || '',
                    storeResponses: localStorage.getItem('tm_store_responses') !== 'false'
                };
            } catch (e) {
                console.error('Error loading settings:', e);
                return getDefaultSettings();
            }
        }

        function getDefaultSettings() {
            return {
                model: 'gpt-5-mini',
                developerInstructions: 'Tone: To the point with easy to understand language.\nTool Usage: If need to use tools that is not available, ask the user for tool or data access.\nResponse Style: Make sure you have all the available information first before answering. If user ask a question and you do not have good background or context to come up with a good answer, always ask the user back first.',
                assistantContext: 'You are an assistant to Turfmapp agency employees. Turfmapp is a sports media marketing and strategy agency. We do a lot of graphics, analytics, technical, and also run businesses such as the coffee shop, space rental, game room, gym, streetwear sports clothing store, etc. Majority of the employees are Thai. They can read/write English but they are more comfortable in Thai.',
                textFormat: 'text',
                textVerbosity: 'medium',
                reasoningEffort: 'medium',
                reasoningSummary: 'auto',
                toolWebSearch: true,
                webSearchContext: 'medium',
                toolImageGen: false,
                imageQuality: 'auto',
                toolMcp: false,
                mcpServerLabel: '',
                mcpConnectorId: '',
                storeResponses: true
            };
        }

        function buildToolsArray(settings, forceImageGen = false, forceWebSearch = false) {
            const tools = [];

            // Web search tool
            if (settings.toolWebSearch || forceWebSearch) {
                tools.push({
                    type: 'web_search_preview',
                    user_location: { type: 'approximate' },
                    search_context_size: settings.webSearchContext
                });
            }

            // Image generation tool
            if (settings.toolImageGen || forceImageGen) {
                tools.push({
                    type: 'image_generation',
                    size: 'auto',
                    quality: settings.imageQuality,
                    output_format: 'png',
                    background: 'auto',
                    moderation: 'auto',
                    partial_images: 3
                });
            }

            // MCP tool
            if (settings.toolMcp && settings.mcpServerLabel && settings.mcpConnectorId) {
                tools.push({
                    type: 'mcp',
                    server_label: settings.mcpServerLabel,
                    connector_id: settings.mcpConnectorId,
                    allowed_tools: ['fetch', 'get_profile', 'list_drives', 'recent_documents', 'search'],
                    require_approval: 'always'
                });
            }

            return tools;
        }

        // Auto-resize textarea functionality
        function autoResizeTextarea(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        }

        if (input) {
            input.addEventListener('input', function() {
                autoResizeTextarea(this);
            });

            // Handle keyboard shortcuts
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    form.dispatchEvent(new Event('submit'));
                } else if (e.key === 'Enter' && e.shiftKey) {
                    // Allow line break on Shift+Enter
                    setTimeout(() => autoResizeTextarea(this), 0);
                }
            });
        }

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const value = input.value.trim();
            if (!value) return;

            // Check for special tool modes
            const imageGenBtn = document.getElementById('image-gen-btn');
            const webSearchBtn = document.getElementById('web-search-btn');
            const isImageGen = imageGenBtn?.classList.contains('active');
            const isWebSearch = webSearchBtn?.classList.contains('active');

            appendMessage('user', value);
            input.value = '';
            autoResizeTextarea(input);

            // Load all settings from localStorage
            const settings = loadAllSettings();
            
            // create live placeholder with thinking dots
            var placeholder = createAssistantPlaceholder();

            // Build tools array based on settings and active modes
            const tools = buildToolsArray(settings, isImageGen, isWebSearch);

            // Build request payload
            const requestBody = {
                model: settings.model,
                messages: [{ role: 'user', content: value }],
                developer_instructions: settings.developerInstructions,
                assistant_context: settings.assistantContext,
                text_format: settings.textFormat,
                text_verbosity: settings.textVerbosity,
                reasoning_effort: settings.reasoningEffort,
                reasoning_summary: settings.reasoningSummary,
                tools: tools.length > 0 ? tools : null,
                store: settings.storeResponses,
                attachments: attachments.length > 0 ? attachments.map(att => ({
                    type: att.type,
                    url: att.url,
                    filename: att.file.name
                })) : null
            };
            
            console.log('Sending request:', requestBody);

            fetch('/api/chat/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            })
                .then(function (r) { return r.json(); })
                .then(function (res) {
                    if (res && res.ok) {
                        placeholder.finish(res.message || '', res.reasoning || '');
                        
                        // Clear attachments and reset tool buttons after successful response
                        attachments = [];
                        renderAttachments();
                        
                        // Reset tool button states
                        imageGenBtn?.classList.remove('active');
                        webSearchBtn?.classList.remove('active');
                        input.placeholder = 'Type your message...';
                    } else {
                        placeholder.error();
                    }
                })
                .catch(function () {
                    placeholder.error();
                });
        });
    }

    // Menu interactions
    if (menuToggle && menuPanel) {
        menuToggle.addEventListener('click', function () {
            const open = menuPanel.classList.toggle('open');
            menuToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            menuPanel.setAttribute('aria-hidden', open ? 'false' : 'true');
        });

        document.addEventListener('click', function (e) {
            if (!menuPanel.classList.contains('open')) return;
            const target = e.target;
            if (!menuPanel.contains(target) && target !== menuToggle) {
                menuPanel.classList.remove('open');
                menuToggle.setAttribute('aria-expanded', 'false');
                menuPanel.setAttribute('aria-hidden', 'true');
            }
        });
    }
})();
