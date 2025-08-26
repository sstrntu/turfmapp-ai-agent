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
        function scrollToBottom() {
            try {
                // Keep the message list pinned to bottom
                list.scrollTop = list.scrollHeight;
            } catch (e) { /* no-op */ }
        }
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
            
            scrollToBottom();
        }

        function createAssistantPlaceholder() {
            const msg = document.createElement('div');
            // Start as a compact typing bubble; promote to full-width on finish()
            msg.className = 'typing-bubble message-initial';
            
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
            
            scrollToBottom();

            return {
                finish(answer, reasoning, sources) {
                    // Promote to full-width assistant panel and render content
                    msg.classList.remove('typing-bubble');
                    msg.classList.add('assistant-message');
                    msg.innerHTML = '';

                    let content = String(answer || '');
                    content = this.normalizeMarkdown(content);

                    const looksLikeNews = Array.isArray(sources) && sources.length > 0 || /\bBreakdown:\b/i.test(content);

                    if (looksLikeNews) {
                        this.renderStructuredMessage(msg, content, sources);
                        this.renderReasoning(msg, reasoning);
                        scrollToBottom();
                    } else {
                        // Always render full answer without collapsing
                        this.typewriterEffect(msg, content, () => {
                            this.renderSources(msg, sources);
                            this.renderReasoning(msg, reasoning);
                            scrollToBottom();
                        });
                    }
                },
                error() {
                    msg.classList.remove('typing-bubble');
                    msg.innerHTML = '';
                    this.typewriterEffect(msg, 'Sorry, there was an error.', () => {
                        scrollToBottom();
                    });
                },
                sanitize(text) {
                    return String(text)
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;');
                },
                linkify(text) {
                    const escaped = this.sanitize(text);
                    return escaped.replace(/(https?:\/\/[^\s)]+)([\.)]?)/g, function(_, url, trail) {
                        const clean = url.replace(/[\.,);\]]+$/,'');
                        const t = trail || '';
                        try {
                            const u = new URL(clean);
                            const host = u.hostname.replace(/^www\./,'');
                            return '<a href="' + clean + '" target="_blank" rel="noopener noreferrer">' + host + '</a>' + t;
                        } catch (_) {
                            return url + (trail || '');
                        }
                    });
                },
                normalizeMarkdown(text) {
                    let out = String(text).replace(/\[([^\]]+)\]\(([^)]+)\)/g, function(_, _label, raw) {
                        let href = raw.trim();
                        if (!/^https?:\/\//i.test(href)) {
                            href = 'https://' + href.replace(/^\/*/, '');
                        }
                        try {
                            const host = new URL(href).hostname.replace(/^www\./, '');
                            return host;
                        } catch (_) {
                            return raw;
                        }
                    });
                    // Remove domain-only parentheticals like "(en.wikipedia.org, jleague.jp)"
                    out = this.stripDomainParentheticals(out);
                    return out;
                },
                stripDomainParentheticals(text) {
                    if (!text) return text;
                    // Match one or more domain names separated by commas inside parentheses
                    const domainGroup = /\s*\(((?:https?:\/\/)?[a-z0-9.-]+\.[a-z]{2,}(?:\/[^(\s)]*)?(?:\s*,\s*(?:https?:\/\/)?[a-z0-9.-]+\.[a-z]{2,}(?:\/[^(\s)]*)?)*)\)/gi;
                    // Replace repeatedly in case there are multiple groups
                    let prev;
                    let cleaned = String(text);
                    do {
                        prev = cleaned;
                        cleaned = cleaned.replace(domainGroup, '');
                    } while (cleaned !== prev);
                    return cleaned;
                },
                renderStructuredMessage(container, content, sources) {
                    content = this.normalizeMarkdown(content);
                    const root = document.createElement('div');
                    root.className = 'structured-answer';

                    // Split into logical sections by double newlines
                    const blocks = content.split(/\n\s*\n/);
                    const first = (blocks[0] || '').trim();

                    // Headline block
                    if (first) {
                        const headline = document.createElement('div');
                        headline.className = 'headline';
                        headline.style.fontWeight = '700';
                        headline.style.fontSize = '18px';
                        headline.style.lineHeight = '1.4';
                        headline.style.marginBottom = '10px';
                        headline.innerHTML = this.linkify(first);
                        root.appendChild(headline);
                    }

                    // Find Breakdown section and render bullets
                    const rest = blocks.slice(1).join('\n\n');
                    const text = (rest || content).trim();
                    const lines = text.split(/\n/);
                    let i = 0;
                    let inList = false;
                    let listEl = null;

                    function startList() {
                        if (!inList) {
                            listEl = document.createElement('ul');
                            listEl.style.paddingLeft = '22px';
                            listEl.style.margin = '0 0 10px 0';
                            inList = true;
                        }
                    }
                    function endList() {
                        if (inList && listEl) {
                            root.appendChild(listEl);
                            inList = false;
                            listEl = null;
                        }
                    }

                    for (; i < lines.length; i++) {
                        const raw = lines[i];
                        const line = raw.trim();
                        if (!line) { endList(); continue; }

                        if (/^Breakdown:\s*$/i.test(line)) {
                            endList();
                            const h = document.createElement('div');
                            h.style.fontWeight = '700';
                            h.style.margin = '8px 0 6px';
                            h.textContent = 'Breakdown:';
                            root.appendChild(h);
                            continue;
                        }

                        // Numbered bullets like "1) ..." or "- ..." or "• ..."
                        if (/^(?:[-*•]\s+|\d+\)\s+)/.test(line)) {
                            startList();
                            const li = document.createElement('li');
                            li.style.marginBottom = '6px';
                            li.innerHTML = this.linkify(line.replace(/^(?:[-*•]\s+|\d+\)\s+)/, ''));
                            listEl.appendChild(li);
                            continue;
                        }

                        // Paragraph fallback
                        endList();
                        const p = document.createElement('p');
                        p.style.margin = '0 0 8px 0';
                        p.innerHTML = this.linkify(line);
                        root.appendChild(p);
                    }
                    endList();

                    container.appendChild(root);
                    this.renderSources(container, sources);
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
                            scrollToBottom();
                        } else {
                            // Remove cursor after typing is complete
                            cursor.remove();
                            if (callback) callback();
                        }
                    }
                    
                    typeChar();
                },
                renderSources(container, sources) {
                    if (!Array.isArray(sources) || sources.length === 0) return;

                    // Toggle button with popover
                    const toggleWrap = document.createElement('div');
                    toggleWrap.className = 'sources-toggle-wrap';
                    const toggle = document.createElement('button');
                    toggle.type = 'button';
                    toggle.className = 'sources-toggle';
                    const stack = document.createElement('span');
                    stack.className = 'favicon-stack';
                    (sources.slice(0, 3)).forEach(function(s){
                        const img = document.createElement('img');
                        img.src = s.favicon || '';
                        img.alt = '';
                        img.width = 16; img.height = 16;
                        img.loading = 'lazy';
                        stack.appendChild(img);
                    });
                    const labelSpan = document.createElement('span');
                    labelSpan.textContent = 'Sources';
                    toggle.appendChild(stack);
                    toggle.appendChild(labelSpan);
                    toggle.setAttribute('aria-expanded', 'false');

                    const pop = document.createElement('div');
                    pop.className = 'sources-popover';
                    pop.setAttribute('role', 'dialog');
                    pop.setAttribute('aria-label', 'Citations');
                    pop.style.display = 'none';

                    const listEl = document.createElement('ul');
                    listEl.className = 'sources-list';
                    sources.slice(0, 10).forEach(function(s) {
                        const li = document.createElement('li');
                        const a = document.createElement('a');
                        a.href = s.url;
                        a.target = '_blank';
                        a.rel = 'noopener noreferrer';
                        const title = s.title || s.site || new URL(s.url).hostname;
                        a.textContent = title;
                        const meta = document.createElement('div');
                        meta.className = 'source-meta';
                        const fav = document.createElement('img');
                        fav.src = s.favicon || '';
                        fav.width = 16; fav.height = 16; fav.alt = '';
                        const host = document.createElement('span');
                        host.textContent = s.site || new URL(s.url).hostname;
                        meta.appendChild(fav);
                        meta.appendChild(host);
                        li.appendChild(a);
                        li.appendChild(meta);
                        listEl.appendChild(li);
                    });
                    pop.appendChild(listEl);

                    function positionPopover() {
                        // Use fixed positioning to escape scroll container clipping
                        pop.style.position = 'fixed';
                        // Temporarily show to measure
                        pop.style.visibility = 'hidden';
                        pop.style.display = 'block';
                        const rect = toggle.getBoundingClientRect();
                        const spacing = 8;
                        let left = rect.left;
                        let top = rect.top - pop.offsetHeight - spacing; // place above by default
                        // If off top, place below
                        if (top < 8) top = rect.bottom + spacing;
                        // Constrain horizontally
                        const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
                        const maxLeft = vw - pop.offsetWidth - 8;
                        if (left > maxLeft) left = Math.max(8, maxLeft);
                        if (left < 8) left = 8;
                        pop.style.left = left + 'px';
                        pop.style.top = top + 'px';
                        pop.style.visibility = 'visible';
                    }

                    function closeOnOutside(event) {
                        if (!pop.contains(event.target) && !toggle.contains(event.target)) {
                            pop.style.display = 'none';
                            toggle.setAttribute('aria-expanded', 'false');
                            window.removeEventListener('scroll', positionPopover, true);
                            window.removeEventListener('resize', positionPopover, true);
                            document.removeEventListener('mousedown', closeOnOutside, true);
                        }
                    }

                    toggle.addEventListener('click', function() {
                        const isOpen = window.getComputedStyle(pop).display !== 'none';
                        if (isOpen) {
                            pop.style.display = 'none';
                            toggle.setAttribute('aria-expanded', 'false');
                            window.removeEventListener('scroll', positionPopover, true);
                            window.removeEventListener('resize', positionPopover, true);
                            document.removeEventListener('mousedown', closeOnOutside, true);
                        } else {
                            // Ensure popover is attached to body to avoid clipping/stacking contexts
                            if (!pop.__attachedToBody) {
                                document.body.appendChild(pop);
                                pop.__attachedToBody = true;
                            }
                            positionPopover();
                            toggle.setAttribute('aria-expanded', 'true');
                            window.addEventListener('scroll', positionPopover, true);
                            window.addEventListener('resize', positionPopover, true);
                            document.addEventListener('mousedown', closeOnOutside, true);
                        }
                    });

                    toggleWrap.appendChild(toggle);
                    toggleWrap.appendChild(pop);
                    container.appendChild(toggleWrap);

                    // Remove thumbnail grid per request
                },
                renderReasoning(container, reasoning) {
                    if (!reasoning) return;

                    const group = document.createElement('div');
                    group.className = 'assistant-group';

                    const chip = document.createElement('button');
                    chip.type = 'button';
                    chip.className = 'reason-chip';
                    chip.textContent = 'Reasoning';
                    chip.setAttribute('aria-expanded', 'false');

                    const panel = document.createElement('div');
                    panel.className = 'reason-panel';
                    panel.style.display = 'none';
                    panel.textContent = String(reasoning);

                    chip.addEventListener('click', function () {
                        const isOpen = panel.style.display !== 'none';
                        panel.style.display = isOpen ? 'none' : 'block';
                        chip.setAttribute('aria-expanded', (!isOpen).toString());
                    });

                    group.appendChild(chip);
                    group.appendChild(panel);
                    container.appendChild(group);
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
                    developerInstructions: '',
                    assistantContext: '',
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
                developerInstructions: '',
                assistantContext: '',
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
                        placeholder.finish(res.message || '', res.reasoning || '', res.sources || []);
                        
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
