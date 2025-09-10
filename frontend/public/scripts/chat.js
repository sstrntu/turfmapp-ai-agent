// Minimal Chat Controller
// Keeps UI simple, uses existing font/background

(function () {
    'use strict';

    // Ensure the shared sphere animation matches login page styling
    (function ensureSphereAnimation() {
        try {
            var sphere = document.querySelector('.sphere');
            if (!sphere) return;
            // Restart the CSS-defined animation 'rot' without overriding z-index/position
            sphere.style.animation = 'none';
            // trigger reflow
            void sphere.offsetWidth;
            sphere.style.animation = 'rot 16s linear infinite reverse';
        } catch (_) {}
    })();

    const list = document.getElementById('chat-list');
    const form = document.getElementById('chat-form');
    let input = document.getElementById('chat-input');
    const menuToggle = document.getElementById('menu-toggle');
    const menuPanel = document.getElementById('top-menu');
    const hasChat = !!(list && form && input);
    
    // Conversation tracking
    let currentConversationId = null;

    // Make these functions globally accessible for conversation loading
    function scrollToBottom() {
        try {
            // Keep the message list pinned to bottom
            if (list) list.scrollTop = list.scrollHeight;
        } catch (e) { /* no-op */ }
    }
    
    function appendMessage(role, text) {
        if (!list) return;
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

        // Helper to robustly extract sources from metadata
        function extractSources(meta) {
            try {
                if (!meta || typeof meta !== 'object') return [];
                if (Array.isArray(meta.sources)) return meta.sources;
                if (typeof meta.sources === 'string') {
                    try {
                        const parsed = JSON.parse(meta.sources);
                        if (Array.isArray(parsed)) return parsed;
                    } catch (_) {}
                }
                // Fallback: find case-insensitive key that equals "sources"
                const key = Object.keys(meta).find(function(k){ return k && k.trim().toLowerCase() === 'sources'; });
                if (key) {
                    const val = meta[key];
                    if (Array.isArray(val)) return val;
                    if (typeof val === 'string') {
                        try {
                            const parsedVal = JSON.parse(val);
                            if (Array.isArray(parsedVal)) return parsedVal;
                        } catch (_) {}
                    }
                }
            } catch (_) {}
            return [];
        }

        // Function to properly render loaded messages with formatting
        function renderLoadedMessage(role, content, metadata = {}) {
            if (role === 'user') {
                // User messages can use simple append
                appendMessage(role, content);
            } else if (role === 'assistant') {
                console.log('Rendering assistant message with metadata:', metadata);
                
                // Assistant messages need the full assistant message structure
                const msg = document.createElement('div');
                msg.className = 'assistant-message message-appear';
                
                // Process content with markdown and formatting into blocks
                renderRichAssistantContent(msg, content);
                
                list.appendChild(msg);
                
                // Add sources if available
                var extracted = extractSources(metadata);
                console.log('Sources check:', {
                    sources: metadata.sources,
                    isArray: Array.isArray(metadata.sources),
                    length: metadata.sources?.length,
                    truthy: !!metadata.sources,
                    keys: (metadata && typeof metadata === 'object') ? Object.keys(metadata) : null,
                    extractedLength: extracted.length
                });
                
                // Render reasoning first (if any), then sources last
                if (metadata.reasoning) {
                    console.log('Adding reasoning to loaded message');
                    renderReasoning(msg, metadata.reasoning);
                }

                if (Array.isArray(extracted) && extracted.length > 0) {
                    console.log('Adding sources to bottom of loaded message:', extracted);
                    renderSources(msg, extracted);
                } else {
                    console.log('No valid sources found in metadata for assistant message');
                }
                
                scrollToBottom();
            }
        }
        
        // Helper functions for message processing
        function normalizeMarkdown(text) {
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
            out = stripDomainParentheticals(out);
            return out;
        }
        
        function linkifyText(text) {
            const escaped = sanitizeText(text);
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
        }

        // Render rich blocks (paragraphs and lists) similar to ChatGPT output
        function renderRichAssistantContent(container, rawContent) {
            const root = document.createElement('div');
            root.className = 'assistant-content';

            const content = linkifyText(normalizeMarkdown(String(rawContent || '')));

            // Split into blocks by blank lines
            const blocks = content.split(/\n\s*\n/);

            // Helpers to build lists
            function appendParagraph(text) {
                const p = document.createElement('p');
                p.style.margin = '0 0 10px 0';
                p.innerHTML = text;
                root.appendChild(p);
            }
            function parseList(lines, startIndex) {
                // Decide if ordered or unordered
                const isOrdered = /^\d+[\.)]\s+/.test(lines[startIndex]);
                const list = document.createElement(isOrdered ? 'ol' : 'ul');
                list.style.margin = '0 0 10px 18px';
                list.style.paddingLeft = '18px';
                let i = startIndex;
                while (i < lines.length) {
                    const l = lines[i];
                    if (!l || !(isOrdered ? /^\d+[\.)]\s+/.test(l) : /^(?:[-*•]\s+)/.test(l))) break;
                    const li = document.createElement('li');
                    li.style.marginBottom = '6px';
                    const itemText = l.replace(isOrdered ? /^\d+[\.)]\s+/ : /^(?:[-*•]\s+)/, '');
                    li.innerHTML = itemText;
                    list.appendChild(li);
                    i++;
                }
                root.appendChild(list);
                return i - 1; // last consumed index
            }

            // Add table parsing function
            function parseTable(lines, startIndex) {
                // Find table rows (lines with | separators)
                let i = startIndex;
                const tableRows = [];
                
                while (i < lines.length) {
                    const line = lines[i].trim();
                    if (!line || !line.includes('|')) break;
                    
                    // Skip separator rows (like |----|----|)
                    if (!/^[\|\s\-:]+$/.test(line)) {
                        // Split by | and clean up cells
                        const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell);
                        if (cells.length > 0) {
                            tableRows.push(cells);
                        }
                    }
                    i++;
                }
                
                if (tableRows.length > 0) {
                    const table = document.createElement('table');
                    table.style.cssText = `
                        border-collapse: collapse;
                        margin: 10px 0;
                        width: 100%;
                        background: rgba(255,255,255,0.05);
                        border-radius: 8px;
                        overflow: hidden;
                    `;
                    
                    // First row as header
                    const thead = document.createElement('thead');
                    const headerRow = document.createElement('tr');
                    headerRow.style.background = 'rgba(255,255,255,0.1)';
                    
                    tableRows[0].forEach(cellText => {
                        const th = document.createElement('th');
                        th.style.cssText = `
                            padding: 8px 12px;
                            text-align: left;
                            border-bottom: 1px solid rgba(255,255,255,0.1);
                            font-weight: 600;
                        `;
                        th.innerHTML = cellText;
                        headerRow.appendChild(th);
                    });
                    thead.appendChild(headerRow);
                    table.appendChild(thead);
                    
                    // Data rows
                    if (tableRows.length > 1) {
                        const tbody = document.createElement('tbody');
                        for (let rowIndex = 1; rowIndex < tableRows.length; rowIndex++) {
                            const tr = document.createElement('tr');
                            tr.style.cssText = `
                                border-bottom: 1px solid rgba(255,255,255,0.05);
                            `;
                            
                            tableRows[rowIndex].forEach(cellText => {
                                const td = document.createElement('td');
                                td.style.cssText = `
                                    padding: 8px 12px;
                                    border-bottom: 1px solid rgba(255,255,255,0.05);
                                `;
                                td.innerHTML = cellText;
                                tr.appendChild(td);
                            });
                            tbody.appendChild(tr);
                        }
                        table.appendChild(tbody);
                    }
                    
                    root.appendChild(table);
                }
                
                return i - 1; // last consumed index
            }

            blocks.forEach(function(block){
                const lines = block.split(/\n/).map(function(s){ return s.trim(); });
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    if (!line) continue;
                    
                    // Check for table (line contains |)
                    if (line.includes('|') && !line.startsWith('//')) {
                        i = parseTable(lines, i);
                        continue;
                    }
                    
                    // Check for lists
                    if (/^(?:[-*•]\s+|\d+[\.)]\s+)/.test(line)) {
                        i = parseList(lines, i);
                        continue;
                    }
                    
                    // Default to paragraph
                    appendParagraph(line);
                }
            });

            container.innerHTML = '';
            container.appendChild(root);
        }
        
        function sanitizeText(text) {
            return String(text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
        }
        
        function stripDomainParentheticals(text) {
            return text.replace(/\s*\([^)]*\b(?:\.com|\.org|\.net|\.edu|\.gov|\.co\.uk|\.jp)\b[^)]*\)/g, '');
        }

        // Function to render reasoning section
        function renderReasoning(container, reasoning) {
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

        // Function to add sources to the last message (for loading conversation history)
        function addSourcesToLastMessage(sources) {
            if (!list || !sources) return;
            
            const lastMessage = list.lastElementChild;
            if (lastMessage && lastMessage.classList.contains('assistant')) {
                renderSources(lastMessage, sources);
            }
        }

        // Extract renderSources function to be globally accessible
        function renderSources(container, sources) {
            console.log('🔍 renderSources called with:', sources);
            console.log('🔍 Sources is array:', Array.isArray(sources));
            console.log('🔍 Sources length:', sources?.length);
            
            if (!Array.isArray(sources) || sources.length === 0) {
                console.log('⚠️ renderSources early return - no sources');
                return;
            }
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
                img.alt = '';
                img.width = 16; img.height = 16;
                img.loading = 'lazy';
                
                // Handle favicon loading with fallbacks
                function loadFavicon(faviconUrl, fallbackIndex = 0) {
                    if (!faviconUrl) return;
                    
                    img.onerror = function() {
                        // Try fallback URLs if available
                        if (s.favicon_fallbacks && s.favicon_fallbacks[fallbackIndex]) {
                            loadFavicon(s.favicon_fallbacks[fallbackIndex], fallbackIndex + 1);
                        } else {
                            // Use a default icon if all fallbacks fail
                            img.style.display = 'none';
                        }
                    };
                    
                    img.onload = function() {
                        img.style.display = 'block';
                    };
                    
                    img.src = faviconUrl;
                }
                
                loadFavicon(s.favicon);
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
                fav.width = 16; fav.height = 16; fav.alt = '';
                
                // Handle favicon loading with fallbacks for sources list
                function loadSourceFavicon(faviconUrl, fallbackIndex = 0) {
                    if (!faviconUrl) return;
                    
                    fav.onerror = function() {
                        // Try fallback URLs if available
                        if (s.favicon_fallbacks && s.favicon_fallbacks[fallbackIndex]) {
                            loadSourceFavicon(s.favicon_fallbacks[fallbackIndex], fallbackIndex + 1);
                        } else {
                            // Use a default icon if all fallbacks fail
                            fav.style.display = 'none';
                        }
                    };
                    
                    fav.onload = function() {
                        fav.style.display = 'block';
                    };
                    
                    fav.src = faviconUrl;
                }
                
                loadSourceFavicon(s.favicon);
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
        }

    if (hasChat) {
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
                        renderSources(msg, sources);  // Use global function
                        scrollToBottom();
                    } else {
                        // Always render full answer without collapsing
                        this.typewriterEffect(msg, content, () => {
                            this.renderReasoning(msg, reasoning);
                            renderSources(msg, sources);  // Use global function
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
                // renderSources function removed - using the global one above instead
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

        document.getElementById('image-gen-btn')?.addEventListener('click', function() {
            this.classList.toggle('active');
            const isActive = this.classList.contains('active');
            if (isActive) {
                input.placeholder = 'Describe an image to generate...';
                // Deactivate other tools
                deactivateOtherTools('image-gen-btn');
            } else {
                input.placeholder = 'Type your message...';
            }
        });

        document.getElementById('web-search-btn')?.addEventListener('click', function() {
            this.classList.toggle('active');
            const isActive = this.classList.contains('active');
            if (isActive) {
                input.placeholder = 'Search the web for...';
                // Deactivate other Google tools
                deactivateGoogleTools();
            } else {
                input.placeholder = 'Type your message...';
            }
        });

        // Google tool button handlers
        document.getElementById('gmail-btn')?.addEventListener('click', function() {
            this.classList.toggle('active');
            const isActive = this.classList.contains('active');
            if (isActive) {
                input.placeholder = 'Ask about your Gmail...';
                // Deactivate other tools
                deactivateOtherTools('gmail-btn');
            } else {
                input.placeholder = 'Type your message...';
            }
        });

        document.getElementById('calendar-btn')?.addEventListener('click', function() {
            this.classList.toggle('active');
            const isActive = this.classList.contains('active');
            if (isActive) {
                input.placeholder = 'Ask about your Calendar...';
                // Deactivate other tools
                deactivateOtherTools('calendar-btn');
            } else {
                input.placeholder = 'Type your message...';
            }
        });

        document.getElementById('drive-btn')?.addEventListener('click', function() {
            this.classList.toggle('active');
            const isActive = this.classList.contains('active');
            if (isActive) {
                input.placeholder = 'Ask about your Drive files...';
                // Deactivate other tools
                deactivateOtherTools('drive-btn');
            } else {
                input.placeholder = 'Type your message...';
            }
        });

        // Helper function to deactivate Google tools
        function deactivateGoogleTools() {
            ['gmail-btn', 'calendar-btn', 'drive-btn'].forEach(id => {
                const btn = document.getElementById(id);
                if (btn) {
                    btn.classList.remove('active');
                    btn.setAttribute('aria-pressed', 'false');
                }
            });
        }

        // Helper function to deactivate other tools except the active one
        function deactivateOtherTools(activeId) {
            ['gmail-btn', 'calendar-btn', 'drive-btn', 'web-search-btn', 'image-gen-btn', 'sound-effects-btn'].forEach(id => {
                if (id !== activeId) {
                    const btn = document.getElementById(id);
                    if (btn) {
                        btn.classList.remove('active');
                        btn.setAttribute('aria-pressed', 'false');
                    }
                }
            });
        }

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
                    // Make tools available by default; user can explicitly disable via settings
                    toolWebSearch: (localStorage.getItem('tm_tool_web_search') ?? 'true') === 'true',
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
                // Default off to avoid unnecessary latency
                toolWebSearch: false,
                webSearchContext: 'medium',
                toolImageGen: false,
                imageQuality: 'auto',
                toolMcp: false,
                mcpServerLabel: '',
                mcpConnectorId: '',
                storeResponses: true
            };
        }

        function buildToolsArray(settings, forceImageGen = false, forceWebSearch = false, forceGoogleTools = {}) {
            const tools = [];

            // Web search tool
            if (settings.toolWebSearch || forceWebSearch) {
                tools.push({
                    type: 'web_search_preview',
                    user_location: { type: 'approximate' },
                    search_context_size: settings.webSearchContext || 'medium'
                });
            }

            // Image generation tool
            if (settings.toolImageGen || forceImageGen) {
                tools.push({
                    type: 'image_generation',
                    size: 'auto',
                    quality: settings.imageQuality || 'auto',
                    output_format: 'png',
                    background: 'auto',
                    moderation: 'auto',
                    partial_images: 3
                });
            }

            // Google MCP tools - activate individually when buttons are clicked
            if (forceGoogleTools.gmail || forceGoogleTools.calendar || forceGoogleTools.drive) {
                tools.push({
                    type: 'google_mcp',
                    enabled_tools: {
                        gmail: forceGoogleTools.gmail || false,
                        calendar: forceGoogleTools.calendar || false,
                        drive: forceGoogleTools.drive || false
                    }
                });
            }

            // Original MCP tool (from original repo)
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

        // Enhanced system instructions to help LLM understand when to use tools
        function buildSystemInstructions(settings, isWebSearchForced = false) {
            let instructions = [];
            
            // Base instructions for tool usage
            if (settings.toolWebSearch) {
                instructions.push(
                    "Use web search for current information: sports scores, news, weather, current season data, latest facts, or when users ask 'who is', 'what is the latest', 'this season', 'this year'."
                );
            }
            
            if (settings.toolImageGen) {
                instructions.push(
                    "Generate images for creative requests or when users explicitly ask for images."
                );
            }
            
            if (instructions.length > 0) {
                instructions.unshift("You have tools available. Use them when they would provide better, more current information than your training data.");
            }
            
            return instructions.join(" ");
        }

        // FAL Tools System
        const falToolMode = {
            active: false,
            currentTool: null,
            step: 0,
            parameters: {},
            parameterConfig: []
        };

        let availableTools = {};

        // Load available tools from backend
        async function loadAvailableTools() {
            try {
                const response = await fetch('/api/v1/fal-tools/available');
                if (response.ok) {
                    availableTools = await response.json();
                    console.log('Loaded available tools:', availableTools);
                } else {
                    console.error('Failed to load available tools:', response.status, response.statusText);
                }
            } catch (error) {
                console.error('Error loading available tools:', error);
            }
        }

        // Initialize tool buttons
        function initializeFALTools() {
            const toolButtons = document.querySelectorAll('.fal-tool');
            console.log('Found FAL tool buttons:', toolButtons.length);
            toolButtons.forEach(button => {
                console.log('Initializing button:', button.id, button.dataset.tool);
                button.addEventListener('click', function() {
                    console.log('FAL tool button clicked:', this.id, this.dataset.tool);
                    const toolId = this.dataset.tool;
                    if (toolId && availableTools[toolId]) {
                        console.log('Activating FAL tool:', toolId);
                        activateFALTool(toolId);
                    } else {
                        console.error('Tool not available:', toolId, 'Available tools:', availableTools);
                    }
                });
            });
        }

        // Activate a FAL tool
        function activateFALTool(toolId) {
            const tool = availableTools[toolId];
            if (!tool) return;

            falToolMode.active = true;
            falToolMode.currentTool = toolId;
            falToolMode.step = 0;
            falToolMode.parameters = {};
            falToolMode.parameterConfig = tool.parameters;

            // Update button states
            updateToolButtonStates(toolId);

            // Start parameter collection
            startParameterCollection();
        }

        // Deactivate FAL tool
        function deactivateFALTool() {
            falToolMode.active = false;
            falToolMode.currentTool = null;
            falToolMode.step = 0;
            falToolMode.parameters = {};
            falToolMode.parameterConfig = [];

            // Reset button states
            updateToolButtonStates(null);
        }

        // Update tool button visual states
        function updateToolButtonStates(activeToolId) {
            const toolButtons = document.querySelectorAll('.fal-tool');
            toolButtons.forEach(button => {
                const toolId = button.dataset.tool;
                const isActive = toolId === activeToolId;
                button.setAttribute('aria-pressed', isActive);
                button.classList.toggle('active', isActive);
            });
        }

        // Start collecting parameters from user
        function startParameterCollection() {
            const tool = availableTools[falToolMode.currentTool];
            if (!tool) return;

            // Show first parameter prompt
            showNextParameterPrompt();
        }

        // Show the next parameter prompt
        function showNextParameterPrompt() {
            const config = falToolMode.parameterConfig[falToolMode.step];
            if (!config) {
                // All parameters collected, execute the tool
                executeFALTool();
                return;
            }

            // Create assistant message asking for parameter
            appendMessage('assistant', config.prompt + (config.placeholder ? `\n\nExample: ${config.placeholder}` : ''));
        }

        // Process user input for FAL tool parameters
        function processFALToolInput(userInput) {
            if (!falToolMode.active || !falToolMode.parameterConfig[falToolMode.step]) {
                return false;
            }

            const config = falToolMode.parameterConfig[falToolMode.step];
            const paramName = config.name;

            // Validate and process input based on parameter type
            let processedValue;
            let isValid = true;
            let errorMessage = '';

            try {
                switch (config.type) {
                    case 'string':
                        processedValue = userInput.trim();
                        if (config.required && !processedValue) {
                            isValid = false;
                            errorMessage = 'This field is required.';
                        }
                        break;

                    case 'integer':
                        processedValue = parseInt(userInput.trim());
                        if (isNaN(processedValue)) {
                            isValid = false;
                            errorMessage = 'Please enter a valid number.';
                        } else if (config.min !== undefined && processedValue < config.min) {
                            isValid = false;
                            errorMessage = `Value must be at least ${config.min}.`;
                        } else if (config.max !== undefined && processedValue > config.max) {
                            isValid = false;
                            errorMessage = `Value must be at most ${config.max}.`;
                        }
                        break;

                    case 'float':
                        processedValue = parseFloat(userInput.trim());
                        if (isNaN(processedValue)) {
                            isValid = false;
                            errorMessage = 'Please enter a valid number.';
                        }
                        break;

                    case 'boolean':
                        const lowerInput = userInput.trim().toLowerCase();
                        if (['true', 'yes', '1', 'on'].includes(lowerInput)) {
                            processedValue = true;
                        } else if (['false', 'no', '0', 'off'].includes(lowerInput)) {
                            processedValue = false;
                        } else {
                            isValid = false;
                            errorMessage = 'Please enter true/false or yes/no.';
                        }
                        break;

                    default:
                        processedValue = userInput.trim();
                }
            } catch (error) {
                isValid = false;
                errorMessage = 'Invalid input format.';
            }

            if (!isValid) {
                appendMessage('assistant', `❌ ${errorMessage}\n\n${config.prompt}`);
                return true; // Still handled by FAL tool system
            }

            // Store the parameter
            falToolMode.parameters[paramName] = processedValue;
            falToolMode.step++;

            // Show confirmation and continue
            appendMessage('assistant', `✅ ${config.name}: ${processedValue}`);

            // Move to next parameter or execute
            showNextParameterPrompt();

            return true; // Input was handled by FAL tool system
        }

        // Execute the FAL tool with collected parameters
        async function executeFALTool() {
            const toolId = falToolMode.currentTool;
            const tool = availableTools[toolId];

            if (!tool) {
                appendMessage('assistant', '❌ Tool configuration not found.');
                deactivateFALTool();
                return;
            }

            // Show execution message
            // Show a compact status message (not a full assistant bubble yet)
            appendMessage('assistant', `🔧 Generating ${tool.name.toLowerCase()}...`);

            try {
                // Make API call to backend
                const response = await fetch(`/api/v1/fal-tools/${toolId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(falToolMode.parameters)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();

                if (result.success) {
                    // Display results
                    displayFALToolResult(result, tool);
                } else {
                    appendMessage('assistant', `❌ Error: ${result.error || 'Unknown error occurred'}`);
                }

            } catch (error) {
                console.error('FAL Tool execution error:', error);
                appendMessage('assistant', `❌ Failed to execute tool: ${error.message}`);
            }

            // Deactivate tool mode
            deactivateFALTool();
        }

        // Display FAL tool results in chat
        function displayFALToolResult(result, tool) {
            const resultDiv = document.createElement('div');
            resultDiv.className = 'chat-bubble assistant message-appear fal-result';

            let content = `✅ ${tool.name} completed!\n\n`;

            if (result.processing_time) {
                content += `⏱️ Processing time: ${result.processing_time}s\n\n`;
            }

            // Handle different result types
            if (result.result) {
                const data = result.result;

                switch (tool.output_type) {
                    case 'audio':
                        if (data.audio_file) {
                            content += '🎵 Generated audio:\n';
                            
                            // Create audio player
                            const audioContainer = document.createElement('div');
                            audioContainer.className = 'media-container audio-container';
                            
                            const audio = document.createElement('audio');
                            audio.controls = true;
                            audio.src = data.audio_file;
                            
                            const downloadBtn = document.createElement('a');
                            downloadBtn.href = data.audio_file;
                            downloadBtn.download = data.filename || 'generated-audio.wav';
                            downloadBtn.className = 'download-btn';
                            downloadBtn.textContent = '⬇️ Download';
                            
                            audioContainer.appendChild(audio);
                            audioContainer.appendChild(downloadBtn);
                            
                            resultDiv.innerHTML = content;
                            resultDiv.appendChild(audioContainer);
                        }
                        break;

                    case 'image':
                        if (data.image_url) {
                            content += '🖼️ Generated image:\n';
                            
                            const imageContainer = document.createElement('div');
                            imageContainer.className = 'media-container image-container';
                            
                            const img = document.createElement('img');
                            img.src = data.image_url;
                            img.alt = 'Generated image';
                            img.className = 'generated-image';
                            
                            const downloadBtn = document.createElement('a');
                            downloadBtn.href = data.image_url;
                            downloadBtn.download = data.filename || 'generated-image.png';
                            downloadBtn.className = 'download-btn';
                            downloadBtn.textContent = '⬇️ Download';
                            
                            imageContainer.appendChild(img);
                            imageContainer.appendChild(downloadBtn);
                            
                            resultDiv.innerHTML = content;
                            resultDiv.appendChild(imageContainer);
                        }
                        break;

                    default:
                        // Text or other result
                        content += JSON.stringify(data, null, 2);
                        resultDiv.textContent = content;
                }
            } else {
                resultDiv.textContent = content + 'Result generated successfully.';
            }

            list.appendChild(resultDiv);
            scrollToBottom();
        }

        // Initialize FAL tools on page load
        if (!window.__falToolsInit) {
            window.__falToolsInit = true;
            loadAvailableTools().then(() => {
                initializeFALTools();
            });
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

            // Check if FAL tool mode is active and handle parameter collection
            if (falToolMode.active && falToolMode.parameterConfig[falToolMode.step]) {
                // Show the user's input first
                appendMessage('user', value);
                input.value = '';
                autoResizeTextarea(input);
                // Then process the parameter so confirmations/prompts appear after
                setTimeout(function(){ processFALToolInput(value); }, 0);
                return;
            }

            // Check for special tool modes
            const imageGenBtn = document.getElementById('image-gen-btn');
            const webSearchBtn = document.getElementById('web-search-btn');
            const gmailBtn = document.getElementById('gmail-btn');
            const calendarBtn = document.getElementById('calendar-btn');
            const driveBtn = document.getElementById('drive-btn');
            
            const isImageGen = imageGenBtn?.classList.contains('active');
            const isWebSearch = webSearchBtn?.classList.contains('active');
            const isGmail = gmailBtn?.classList.contains('active');
            const isCalendar = calendarBtn?.classList.contains('active');
            const isDrive = driveBtn?.classList.contains('active');

            appendMessage('user', value);
            input.value = '';
            autoResizeTextarea(input);

            // Load all settings from localStorage
            const settings = loadAllSettings();
            
            // create live placeholder with thinking dots
            var placeholder = createAssistantPlaceholder();

            // Make tools available by default; if user clicks the toggles, force-include those
            const googleTools = {
                gmail: isGmail,
                calendar: isCalendar,
                drive: isDrive
            };
            const tools = buildToolsArray(settings, isImageGen, isWebSearch, googleTools);
            
            // Build enhanced system instructions to guide tool usage
            const systemInstructions = buildSystemInstructions(settings, isWebSearch);
            
            // Build request payload for v1 API
            const requestBody = {
                message: value,
                conversation_id: currentConversationId, // Use current conversation or null for new
                model: settings.model || "gpt-5-mini",
                tools: tools.length > 0 ? tools : null,
                tool_choice: isWebSearch ? 'required' : 'auto',
                assistant_context: systemInstructions, // Add system instructions to guide tool usage
                attachments: attachments.length > 0 ? attachments.map(att => ({
                    type: att.type,
                    url: att.url,
                    filename: att.file.name
                })) : null
            };
            
            // Get auth token for API request
            const session = window.supabase?.getSession();
            
            // Check if session is valid first
            if (!window.supabase || !window.supabase.isSessionValid()) {
                console.error('Session invalid or expired');
                placeholder.error();
                return;
            }
            
            const authToken = window.supabase.getAccessToken();
            if (!authToken) {
                console.error('No authentication token available');
                window.location.href = '/portal.html';
                return;
            }
            
            console.log('Sending chat request with tools:', tools?.map?.(t => t.type), 'tool_choice:', requestBody.tool_choice);
            fetch('/api/v1/chat/send', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify(requestBody)
            })
                .then(function (r) { 
                    if (!r.ok) {
                        throw new Error(`HTTP ${r.status}: ${r.statusText}`);
                    }
                    return r.json(); 
                })
                .then(function (res) {
                    if (res && res.assistant_message) {
                        // Update conversation ID from response
                        if (res.conversation_id) {
                            currentConversationId = res.conversation_id;
                            
                            // Refresh conversation history in sidebar
                            if (window.refreshConversationHistory) {
                                window.refreshConversationHistory();
                            }
                        }
                        
                        // Extract message content from the assistant_message
                        const messageContent = res.assistant_message.content || '';
                        // Sources and reasoning are at the top level of the response
                        const sources = res.sources || [];
                        const reasoning = res.reasoning || '';
                        
                        // Debug logging for sources
                        console.log('🔍 Frontend received sources:', sources);
                        console.log('🔍 Sources type:', typeof sources);
                        console.log('🔍 Sources length:', Array.isArray(sources) ? sources.length : 'Not array');
                        
                        placeholder.finish(messageContent, reasoning, sources);
                        
                        // Clear attachments and reset tool buttons after successful response
                        attachments = [];
                        renderAttachments();
                        
                        // Reset tool button states
                        imageGenBtn?.classList.remove('active');
                        webSearchBtn?.classList.remove('active');
                        gmailBtn?.classList.remove('active');
                        calendarBtn?.classList.remove('active');
                        driveBtn?.classList.remove('active');
                        
                        // Reset aria-pressed attributes
                        imageGenBtn?.setAttribute('aria-pressed', 'false');
                        webSearchBtn?.setAttribute('aria-pressed', 'false');
                        gmailBtn?.setAttribute('aria-pressed', 'false');
                        calendarBtn?.setAttribute('aria-pressed', 'false');
                        driveBtn?.setAttribute('aria-pressed', 'false');
                        
                        input.placeholder = 'Type your message...';
                    } else {
                        console.error('Invalid response format:', res);
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

    // Left panel toggle
    const lpToggle = document.getElementById('left-panel-toggle');
    const lp = document.getElementById('left-panel');
    const lpClose = document.getElementById('left-panel-close');
    if (lpToggle && lp) {
        function setLeftPanel(open) {
            lp.classList.toggle('open', open);
            lp.setAttribute('aria-hidden', open ? 'false' : 'true');
            lpToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            // Toggle body class to shift main content like ChatGPT
            document.body.classList.toggle('panel-open', open);
        }
        lpToggle.addEventListener('click', function(e){ 
            e.preventDefault();
            e.stopPropagation();
            const isCurrentlyOpen = lp.classList.contains('open');
            setLeftPanel(!isCurrentlyOpen); 
        });
        lpClose?.addEventListener('click', function(){ setLeftPanel(false); });
        document.addEventListener('keydown', function(e){ if (e.key === 'Escape') setLeftPanel(false); });
        
        // Add global click handler to close panel when clicking outside
        document.addEventListener('click', function(e) {
            if (!lp.classList.contains('open')) return;
            const target = e.target;
            if (!lp.contains(target) && target !== lpToggle && !lpToggle.contains(target)) {
                setLeftPanel(false);
            }
        });
    }

    // Panel actions: New chat + conversation history
    (function(){
        const newBtn = document.getElementById('btn-new-chat');
        const histList = document.getElementById('history-list');
        
        if (newBtn) {
            newBtn.addEventListener('click', function(){
                // Start new conversation
                currentConversationId = null;
                const chatList = document.getElementById('chat-list');
                if (chatList) chatList.innerHTML = '';
                const textarea = document.getElementById('chat-input');
                if (textarea) textarea.value = '';
                // Remove focus before hiding sidebar
                this.blur();
                if (lp) { 
                    lp.classList.remove('open'); 
                    lp.setAttribute('aria-hidden','true'); 
                    lpToggle?.setAttribute('aria-expanded','false'); 
                    document.body.classList.remove('panel-open'); 
                }
            });
        }
        
        // Debounced/single-flight state for history loads to prevent loops
        const historyLoadState = { inProgress: false, lastAt: 0 };

        async function loadConversationHistory() {
            console.log('loadConversationHistory called');
            // Prevent re-entrant or overly-frequent calls
            const now = Date.now();
            if (historyLoadState.inProgress) {
                console.log('History load already in progress, skipping');
                return;
            }
            if (now - historyLoadState.lastAt < 5000) { // 5s minimum interval
                console.log('History load throttled (5s cooldown)');
                return;
            }
            historyLoadState.inProgress = true;
            historyLoadState.lastAt = now;
            if (!histList) return;
            
            try {
                
                // Check if session is valid first
                if (!window.supabase || !window.supabase.isSessionValid()) {
                    histList.innerHTML = '<li class="empty">Please log in to see recent conversations</li>';
                    return;
                }
                
                const token = window.supabase.getAccessToken();
                if (!token) {
                    histList.innerHTML = '<li class="empty">Authentication required</li>';
                    return;
                }
                
                const response = await fetch('/api/v1/chat/conversations', {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    console.error('❌ Failed to load conversation history:', response.status);
                    histList.innerHTML = '<li class="error">Failed to load history</li>';
                    return;
                }
                
                const data = await response.json();
                renderHistory(data.conversations || []);
            } catch (error) {
                console.error('Error loading conversation history:', error);
                histList.innerHTML = '<li class="error">Failed to load history</li>';
            } finally {
                historyLoadState.inProgress = false;
            }
        }
        
        function renderHistory(conversations) {
            if (!histList) {
                return;
            }
            
            histList.innerHTML = '';
            
            if (!conversations.length) {
                histList.innerHTML = '<li class="empty">No recent conversations</li>';
                return;
            }
            
            // Group conversations by date
            const groupedByDate = {};
            conversations.forEach(conv => {
                const date = new Date(conv.updated_at);
                const dateStr = date.toLocaleDateString();
                if (!groupedByDate[dateStr]) {
                    groupedByDate[dateStr] = [];
                }
                groupedByDate[dateStr].push(conv);
            });
            
            // Sort dates (most recent first) and render
            const sortedDates = Object.keys(groupedByDate).sort((a, b) => {
                return new Date(b).getTime() - new Date(a).getTime();
            });
            
            sortedDates.forEach(dateStr => {
                // Create date header
                const dateHeader = document.createElement('li');
                dateHeader.className = 'date-group-header';
                dateHeader.textContent = dateStr;
                histList.appendChild(dateHeader);
                
                // Sort conversations within this date by most recent first
                const dateConversations = groupedByDate[dateStr].sort((a, b) => {
                    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
                });
                
                // Render conversations for this date
                dateConversations.forEach(conv => {
                    const li = document.createElement('li');
                    li.className = 'conversation-item';
                    
                    // Create main conversation button
                    const button = document.createElement('button');
                    button.className = 'conversation-btn';
                    button.textContent = conv.title || 'Untitled';
                    button.title = conv.title || 'Untitled';
                    
                    button.addEventListener('click', async function() {
                        await loadConversation(conv.id);
                        // Remove focus before hiding sidebar to fix accessibility issue
                        this.blur();
                        // Close sidebar after loading
                        if (lp) { 
                            lp.classList.remove('open'); 
                            lp.setAttribute('aria-hidden','true'); 
                            lpToggle?.setAttribute('aria-expanded','false'); 
                            document.body.classList.remove('panel-open'); 
                        }
                    });
                    
                    // Create delete button
                    const deleteBtn = document.createElement('button');
                    deleteBtn.className = 'conversation-delete-btn';
                    deleteBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 6h18m-2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6m4-6v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
                    deleteBtn.title = 'Delete conversation';
                    
                    deleteBtn.addEventListener('click', async function(e) {
                        e.stopPropagation(); // Prevent triggering the conversation load
                        
                        console.log('Delete button clicked for conversation:', conv.id);
                        if (confirm('Are you sure you want to delete this conversation? This action cannot be undone.')) {
                            console.log('User confirmed deletion, calling deleteConversation...');
                            await deleteConversation(conv.id);
                        } else {
                            console.log('User cancelled deletion');
                        }
                    });
                    
                    // Create conversation header with button and delete (no individual date since it's grouped)
                    const header = document.createElement('div');
                    header.className = 'conversation-header';
                    header.appendChild(button);
                    header.appendChild(deleteBtn);
                    
                    li.appendChild(header);
                    histList.appendChild(li);
                });
            });
        }
        
        async function loadConversation(conversationId) {
            try {
                const token = window.supabase?.getAccessToken();
                if (!token) return;
                
                const response = await fetch(`/api/v1/chat/conversations/${conversationId}`, {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    console.error('Failed to load conversation:', response.status);
                    return;
                }
                
                const data = await response.json();
                
                // Set current conversation ID
                currentConversationId = conversationId;
                
                // Clear current chat
                const chatList = document.getElementById('chat-list');
                if (chatList) chatList.innerHTML = '';
                
                // Render messages with proper formatting
                data.messages.forEach(msg => {
                    if (msg.role === 'user' || msg.role === 'assistant') {
                        // Parse metadata if it's a string
                        let parsedMetadata = {};
                        if (msg.metadata) {
                            try {
                                parsedMetadata = typeof msg.metadata === 'string' 
                                    ? JSON.parse(msg.metadata) 
                                    : msg.metadata;
                            } catch (e) {
                                console.error('Failed to parse metadata:', e, msg.metadata);
                                parsedMetadata = {};
                            }
                        }
                        
                        console.log('Loading message:', {
                            role: msg.role,
                            content: msg.content?.substring(0, 50) + '...',
                            rawMetadata: msg.metadata,
                            parsedMetadata: parsedMetadata,
                            sources: parsedMetadata?.sources,
                            extractedSourcesLength: extractSources(parsedMetadata).length
                        });
                        renderLoadedMessage(msg.role, msg.content, parsedMetadata);
                    }
                });
                
            } catch (error) {
                console.error('Error loading conversation:', error);
            }
        }
        
        async function deleteConversation(conversationId) {
            console.log('deleteConversation called with ID:', conversationId);
            try {
                const token = window.supabase?.getAccessToken();
                if (!token) {
                    console.log('No access token available');
                    return;
                }
                
                console.log('Sending DELETE request to:', `/api/v1/chat/conversations/${conversationId}`);
                const response = await fetch(`/api/v1/chat/conversations/${conversationId}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                console.log('Delete response status:', response.status);
                if (!response.ok) {
                    console.error('Failed to delete conversation:', response.status);
                    alert('Failed to delete conversation. Please try again.');
                    return;
                }
                
                // If the deleted conversation is currently active, clear the chat
                if (currentConversationId === conversationId) {
                    currentConversationId = null;
                    const chatList = document.getElementById('chat-list');
                    if (chatList) chatList.innerHTML = '';
                }
                
                console.log('Conversation deleted successfully, refreshing history...');
                // Force refresh conversation history immediately after successful deletion
                await forceRefreshConversationHistory();
                
            } catch (error) {
                console.error('Error deleting conversation:', error);
                alert('Failed to delete conversation. Please try again.');
            }
        }
        
        async function forceRefreshConversationHistory() {
            console.log('forceRefreshConversationHistory called - bypassing throttle');
            if (!histList) return;
            
            try {
                const token = window.supabase.getAccessToken();
                if (!token) {
                    histList.innerHTML = '<li class="empty">Authentication required</li>';
                    return;
                }
                
                const response = await fetch('/api/v1/chat/conversations', {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    console.error('❌ Failed to load conversation history:', response.status);
                    histList.innerHTML = '<li class="error">Failed to load history</li>';
                    return;
                }
                
                const data = await response.json();
                renderHistory(data.conversations || []);
                console.log('History force refreshed successfully');
            } catch (error) {
                console.error('Error force refreshing conversation history:', error);
                histList.innerHTML = '<li class="error">Failed to load history</li>';
            }
        }
        
        // Re-enable one-shot conversation history load on page init
        function initializeConversationHistory() {
            setTimeout(() => { loadConversationHistory(); }, 800);
        }
        
        // Refresh history after sending messages
        function refreshHistoryAfterMessage() {
            setTimeout(() => { loadConversationHistory(); }, 1000);
        }
        
        // Export functions so they can be called from other scripts
        window.refreshConversationHistory = refreshHistoryAfterMessage;
        window.loadConversationHistory = loadConversationHistory;
        
        // Initialize conversation history on page load
        initializeConversationHistory();
    })();
})();
