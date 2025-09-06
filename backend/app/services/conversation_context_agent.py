"""
Conversation Context Agent - Intelligent conversation analysis and action planning

This agent analyzes conversation history and current user input to:
1. Understand context and intent
2. Decide which tools/actions are needed
3. Execute appropriate MCP calls
4. Format responses intelligently
"""

from __future__ import annotations

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

class ConversationContextAgent:
    """Intelligent agent that analyzes conversation context and handles MCP requests."""
    
    def __init__(self):
        # Pattern definitions for different types of queries
        self.email_patterns = {
            'direct': [
                r'(show|get|fetch|find|check)\s+.*?my.*?email',
                r'what.*?email.*?do.*?i.*?have',
                r'my.*?inbox',
                r'my.*?latest.*?message',
                r'my.*?recent.*?mail',
                r'gmail.*?(inbox|messages)',
                r'mail.*?(latest|recent|new)',
                r'check.*?my.*?mail',
                r'list.*?my.*?emails',
                r'unread.*?emails',
                r'important.*?emails'
            ],
            'followup': [
                r'what.*?about.*?that.*?email',
                r'tell me more.*?about.*?email',
                r'what.*?does.*?that.*?email.*?say',
                r'details.*?about.*?email',
                r'content.*?of.*?email',
                r'read.*?that.*?email',
                r'what.*?it.*?(say|about).*?email',
                r'summary.*?of.*?email',
                r'what.*?happened.*?in.*?email',
                r'who.*?from.*?email',
                r'when.*?sent.*?email'
            ],
            'analysis': [
                r'what.*?do.*?i.*?need.*?do.*?email',
                r'what.*?should.*?i.*?do.*?email',
                r'what.*?next.*?step.*?email',
                r'what.*?action.*?required.*?email',
                r'what.*?my.*?todo.*?email',
                r'what.*?need.*?response.*?email',
                r'what.*?need.*?reply.*?email',
                r'summarize.*?email',
                r'analyze.*?email',
                r'key.*?point.*?email',
                r'main.*?takeaway.*?email',
                r'action.*?item.*?email',
                r'what.*?important.*?email'
            ]
        }
        
        self.drive_patterns = {
            'direct': [
                r'(show|get|list).*?files?',
                r'google drive',
                r'documents?',
                r'folders?',
                r'spreadsheets?',
                r'upload',
            ],
            'followup': [
                r'what.*?files',
                r'show.*?content',
            ]
        }
        
        self.calendar_patterns = {
            'direct': [
                r'(show|get|check).*?calendar',
                r'meetings?',
                r'events?',
                r'schedule',
                r'appointments?',
            ],
            'followup': [
                r'when.*?meeting',
                r'what.*?scheduled',
            ]
        }
    
    async def analyze_conversation_context(
        self, 
        current_message: str, 
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze conversation context and determine required actions using LLM."""
        
        # Use LLM for intelligent context analysis
        try:
            llm_analysis = await self._analyze_context_with_llm(current_message, conversation_history)
            if llm_analysis:
                return llm_analysis
        except Exception as e:
            print(f"❌ LLM context analysis failed: {e}")
        
        # Fallback to pattern-based analysis
        analysis = {
            'intent': 'general',
            'service': None,
            'action_type': 'direct',  # direct or followup
            'required_tools': [],
            'context_data': {},
            'instructions': None,
            'confidence': 0.0
        }
        
        current_lower = current_message.lower()
        
        # Check for direct service requests
        direct_intent = self._check_direct_patterns(current_lower)
        if direct_intent:
            analysis.update(direct_intent)
            analysis['confidence'] = 0.9
            return analysis
        
        # Check for follow-up patterns
        followup_intent = self._check_followup_patterns(current_lower, conversation_history)
        if followup_intent:
            analysis.update(followup_intent)
            analysis['confidence'] = 0.8
            return analysis
        
        return analysis
    
    def _check_direct_patterns(self, message: str) -> Optional[Dict[str, Any]]:
        """Check if message matches direct service request patterns."""
        
        # Check email patterns
        for pattern in self.email_patterns['direct']:
            if re.search(pattern, message):
                return {
                    'intent': 'email_query',
                    'service': 'gmail',
                    'action_type': 'direct',
                    'required_tools': ['gmail_recent', 'gmail_search', 'gmail_get_message', 'gmail_important'],
                    'instructions': 'Use Gmail tools to fetch and display email information.'
                }
        
        # Check drive patterns  
        for pattern in self.drive_patterns['direct']:
            if re.search(pattern, message):
                return {
                    'intent': 'drive_query',
                    'service': 'drive',
                    'action_type': 'direct',
                    'required_tools': ['drive_list_files', 'drive_create_folder', 'drive_list_folder_files'],
                    'instructions': 'Use Drive tools to manage files and folders.'
                }
        
        # Check calendar patterns
        for pattern in self.calendar_patterns['direct']:
            if re.search(pattern, message):
                return {
                    'intent': 'calendar_query', 
                    'service': 'calendar',
                    'action_type': 'direct',
                    'required_tools': ['calendar_list_events', 'calendar_upcoming_events'],
                    'instructions': 'Use Calendar tools to show events and schedules.'
                }
        
        return None
    
    def _check_followup_patterns(
        self, 
        message: str, 
        conversation_history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Check if message is a follow-up to previous service interactions."""
        
        # Enhanced follow-up detection patterns
        general_followup_patterns = [
            r'what.*?about.*?it',
            r'tell me more.*?about.*?it',
            r'what.*?does.*?it.*?say',
            r'details.*?about.*?it',
            r'what.*?is.*?it.*?about',
            r'can you.*?read.*?it',
            r'what.*?in.*?it',
            r'summary.*?of.*?it',
            r'what.*?happened.*?in.*?it',
            r'who.*?from.*?it',
            r'when.*?sent.*?it',
            r'what.*?they.*?about',
            r'tell me.*?about.*?them',
            r'what.*?do.*?they.*?say',
            r'details.*?about.*?them',
            r'what.*?are.*?they.*?about',
            r'what.*?that.*?about',
            r'tell me.*?about.*?that',
            r'what.*?does.*?that.*?say',
            r'details.*?about.*?that'
        ]
        
        # Check if current message matches follow-up patterns
        email_followup = any(re.search(pattern, message) for pattern in self.email_patterns['followup'])
        drive_followup = any(re.search(pattern, message) for pattern in self.drive_patterns['followup'])
        calendar_followup = any(re.search(pattern, message) for pattern in self.calendar_patterns['followup'])
        general_followup = any(re.search(pattern, message) for pattern in general_followup_patterns)
        
        if not (email_followup or drive_followup or calendar_followup or general_followup):
            return None
        
        # Analyze recent conversation history (last 5 messages)
        recent_history = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
        history_text = " ".join([msg.get('content', '') for msg in recent_history]).lower()
        
        # Check what service was discussed recently using intelligent context analysis
        if email_followup or general_followup:
            # Look for email-related patterns in conversation history
            email_context_patterns = [
                r'\b(email|gmail|message|inbox|mail|sender|subject)\b',
                r'\b(sent|received|reply|forward)\b.*\b(email|message)\b',
                r'\b(attachment|cc|bcc|subject line)\b',
                r'\b(unread|read|important|starred)\b.*\b(email|message)\b'
            ]
            
            has_email_context = any(re.search(pattern, history_text) for pattern in email_context_patterns)
            if has_email_context:
                return {
                    'intent': 'email_followup',
                    'service': 'gmail',
                    'action_type': 'followup',
                    'required_tools': ['gmail_recent', 'gmail_search', 'gmail_get_message'],
                    'context_data': self._extract_email_context(recent_history),
                    'instructions': f'''The user is asking a follow-up question about emails discussed earlier. 
                    Recent context shows email-related conversation. Use gmail_recent to get current email information and provide details about the content.
                    Current follow-up question: "{message}"'''
                }
        
        if drive_followup or general_followup:
            # Look for file/document-related patterns in conversation history
            drive_context_patterns = [
                r'\b(drive|file|folder|document|spreadsheet|presentation)\b',
                r'\b(upload|download|share|edit)\b.*\b(file|document)\b',
                r'\b(google drive|onedrive|dropbox)\b',
                r'\b(pdf|doc|docx|xlsx|pptx)\b'
            ]
            
            has_drive_context = any(re.search(pattern, history_text) for pattern in drive_context_patterns)
            if has_drive_context:
                return {
                    'intent': 'drive_followup',
                    'service': 'drive', 
                    'action_type': 'followup',
                    'required_tools': ['drive_list_files', 'drive_list_folder_files'],
                    'instructions': f'''The user is asking a follow-up question about Drive files discussed earlier.
                    Current follow-up question: "{message}"'''
                }
        
        if calendar_followup or general_followup:
            # Look for calendar/event-related patterns in conversation history
            calendar_context_patterns = [
                r'\b(calendar|event|meeting|schedule|appointment|conference|call)\b',
                r'\b(upcoming|today|tomorrow|this week|next week)\b.*\b(meeting|event)\b',
                r'\b(zoom|teams|google meet|webex)\b',
                r'\b(reminder|notification|alert)\b.*\b(meeting|event)\b'
            ]
            
            has_calendar_context = any(re.search(pattern, history_text) for pattern in calendar_context_patterns)
            if has_calendar_context:
                return {
                    'intent': 'calendar_followup',
                    'service': 'calendar',
                    'action_type': 'followup', 
                    'required_tools': ['calendar_list_events', 'calendar_upcoming_events'],
                    'instructions': f'''The user is asking a follow-up question about calendar events discussed earlier.
                    Current follow-up question: "{message}"'''
                }
        
        # If general follow-up but no specific service context, check for general knowledge context
        if general_followup:
            # Look for general knowledge patterns in conversation history
            general_knowledge_context_patterns = [
                r'\b(sports|news|weather|history|science|definition|explanation)\b',
                r'\b(who is|what is|when was|where is|how does|why is)\b',
                r'\b(famous|well-known|popular|important)\b.*\b(person|place|thing)\b',
                r'\b(invented|discovered|created|founded)\b',
                r'\b(capital|currency|language|population)\b.*\b(of|in)\b'
            ]
            
            has_general_knowledge_context = any(re.search(pattern, history_text) for pattern in general_knowledge_context_patterns)
            if has_general_knowledge_context:
                return {
                    'intent': 'general_followup',
                    'service': None,
                    'action_type': 'followup',
                    'required_tools': [],
                    'instructions': f'''The user is asking a follow-up question about general knowledge discussed earlier.
                    Answer from existing conversation context without using tools.
                    Current follow-up question: "{message}"'''
                }
        
        return None
    
    async def _analyze_context_with_llm(
        self, 
        current_message: str, 
        conversation_history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to intelligently analyze conversation context and determine required actions."""
        
        # Build conversation context for LLM
        recent_context = ""
        if conversation_history:
            recent_messages = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
            for msg in recent_messages:
                role = msg.get('role', 'user').title()
                content = msg.get('content', '')
                recent_context += f"{role}: {content}\n"
        
        system_prompt = f"""You are an intelligent assistant that analyzes conversation context to determine what the user needs.

Current User Message: "{current_message}"

Recent Conversation Context:
{recent_context}

Analyze the user's message and conversation context to determine:

1. INTENT ANALYSIS:
   - Is this a direct request for personal data (emails, files, calendar)?
   - Is this a follow-up question referring to something discussed earlier?
   - Is this a general knowledge question?
   - Is this asking about existing conversation content?

2. CONTEXT ANALYSIS:
   - What is the user referring to with pronouns like "it", "they", "them", "that"?
   - What type of content was discussed in recent conversation?
   - Is this a follow-up to personal data or general knowledge?

3. SERVICE DETECTION:
   - If personal data related: gmail, drive, or calendar?
   - If general knowledge: no service needed
   - If follow-up: determine what service the follow-up refers to

4. ACTION TYPE:
   - "direct": User explicitly asking for something
   - "followup": User asking about something mentioned earlier
   - "general": General knowledge question

Return your analysis as VALID JSON:
{{
    "intent": "email_query|drive_query|calendar_query|general_followup|general",
    "service": "gmail|drive|calendar|null",
    "action_type": "direct|followup|general",
    "required_tools": ["tool1", "tool2"],
    "context_data": {{}},
    "instructions": "Specific instructions for handling this query",
    "confidence": 0.0-1.0,
    "reasoning": "Explanation of your analysis"
}}

IMPORTANT:
- Return only valid JSON
- Be intelligent about context - don't rely on keywords
- Understand what pronouns refer to
- Distinguish between personal data and general knowledge
- Use high confidence (0.8+) for clear cases, lower for ambiguous ones
"""

        try:
            import httpx
            import json
            import os
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("❌ No OpenAI API key found for LLM analysis")
                return None
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 500
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    try:
                        # Remove markdown code block formatting if present
                        if content.startswith("```json"):
                            content = content.replace("```json", "").replace("```", "").strip()
                        elif content.startswith("```"):
                            content = content.replace("```", "").strip()
                        
                        analysis = json.loads(content)
                        print(f"🧠 LLM Context Analysis: {analysis.get('intent', 'unknown')} ({analysis.get('confidence', 0):.1f} confidence)")
                        return analysis
                    except json.JSONDecodeError:
                        print(f"❌ Failed to parse LLM context analysis: {content}")
                        return None
                else:
                    print(f"❌ LLM context analysis API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error in LLM context analysis: {e}")
            return None
    
    def _extract_email_context(self, recent_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract relevant email context from conversation history."""
        context = {
            'mentioned_emails': [],
            'email_subjects': [],
            'email_senders': [],
            'last_email_action': None,
            'entities_mentioned': []
        }
        
        for msg in recent_history:
            content = msg.get('content', '')
            
            # Look for email subjects mentioned  
            subject_matches = re.findall(r'["\']([^"\']+)["\']', content)
            context['email_subjects'].extend(subject_matches)
            
            # Look for sender names
            sender_matches = re.findall(r'from:\s*([^\n]+)', content, re.IGNORECASE)
            context['email_senders'].extend(sender_matches)
            
            # Extract entities from email content (company names, project names, etc.)
            entities = self._extract_entities_from_text(content)
            context['entities_mentioned'].extend(entities)
            
            # Identify last email-related action
            if 'recent email' in content.lower():
                context['last_email_action'] = 'recent'
            elif 'search' in content.lower() and 'email' in content.lower():
                context['last_email_action'] = 'search'
        
        return context
    
    def _extract_entities_from_text(self, text: str) -> List[str]:
        """Extract potential search entities from email content."""
        entities = []
        
        # Look for specific patterns in email responses
        # Pattern 1: Subject lines with "Re: [Project/Company Name]"
        subject_pattern = r'Re:\s*([^_\n\-]+?)(?:\s*[-_]|\s*\d{4})'
        subject_matches = re.findall(subject_pattern, text)
        for match in subject_matches:
            clean_match = re.sub(r'\s+', ' ', match.strip())
            if len(clean_match) > 3 and not clean_match.lower() in ['your', 'the', 'and']:
                entities.append(clean_match)
        
        # Pattern 2: Company/Project names that appear before "proposal", "project", "International"
        project_pattern = r'\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\s+(?:proposal|project|SNS|International)\b'
        project_matches = re.findall(project_pattern, text)
        entities.extend(project_matches)
        
        # Pattern 3: Proper nouns (capitalized words) that might be company/project names
        # But exclude common email words
        proper_nouns = re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', text)
        email_stopwords = {
            'Your', 'The', 'And', 'For', 'You', 'Are', 'This', 'That', 'With', 'From', 
            'Email', 'Gmail', 'Message', 'Subject', 'Sender', 'Recent', 'Latest', 'Most',
            'Understanding', 'Infrastructure', 'Services', 'Web', 'Amazon', 'Fri', 'Thu', 'Sep'
        }
        
        for noun in proper_nouns:
            if noun not in email_stopwords and len(noun) > 3:
                entities.append(noun)
        
        # Clean and filter entities
        filtered_entities = []
        for entity in entities:
            entity = entity.strip('*_-:"' )
            if (len(entity) > 3 and 
                entity not in filtered_entities and
                not entity.startswith('Re:') and
                not entity.endswith('"')):
                filtered_entities.append(entity)
        
        # Limit to most relevant entities
        return filtered_entities[:3]
    
    def _extract_search_terms(self, message: str) -> List[str]:
        """Extract search terms from user message."""
        # Look for proper nouns and specific entities
        terms = []
        
        # Extract capitalized words that might be entities
        capitalized_words = re.findall(r'\b[A-Z][a-zA-Z]+\b', message)
        terms.extend(capitalized_words)
        
        # Remove common words
        common_words = {'What', 'The', 'Is', 'Are', 'About', 'Email', 'Gmail', 'Message'}
        terms = [term for term in terms if term not in common_words]
        
        return terms
    
    async def should_use_agent_for_query(self, message: str, history: List[Dict[str, Any]]) -> bool:
        """Let the LLM decide - don't use complex agent logic."""
        # Simplified approach: let the LLM decide what tools to use
        # No need for complex pattern matching or context analysis
        return False
    
    async def handle_contextual_query(
        self, 
        message: str, 
        conversation_history: List[Dict[str, Any]],
        user_id: str,
        mcp_client
    ) -> Dict[str, Any]:
        """Handle a contextual query using appropriate MCP tools."""
        
        # Store conversation history for use in sub-methods
        self._last_conversation_history = conversation_history
        
        analysis = await self.analyze_conversation_context(message, conversation_history)
        
        if analysis['intent'] == 'general':
            return {
                'success': False,
                'error': 'No contextual service identified',
                'use_default_llm': True
            }
        
        print(f"🤖 Context Agent Analysis: {analysis['intent']} ({analysis['confidence']:.1f} confidence)")
        print(f"🤖 Service: {analysis['service']}, Action: {analysis['action_type']}")
        
        try:
            # Execute appropriate MCP tool based on analysis
            if analysis['service'] == 'gmail':
                return await self._handle_gmail_context(analysis, user_id, mcp_client, message)
            elif analysis['service'] == 'drive':
                return await self._handle_drive_context(analysis, user_id, mcp_client, message)
            elif analysis['service'] == 'calendar':
                return await self._handle_calendar_context(analysis, user_id, mcp_client, message)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported service: {analysis["service"]}',
                    'use_default_llm': True
                }
                
        except Exception as e:
            print(f"❌ Context agent error: {e}")
            return {
                'success': False,
                'error': str(e),
                'use_default_llm': True
            }
    
    async def _handle_gmail_context(
        self, 
        analysis: Dict[str, Any], 
        user_id: str, 
        mcp_client, 
        original_message: str
    ) -> Dict[str, Any]:
        """Handle Gmail-related contextual queries."""
        
        # Extract search terms from the message for entity-specific queries
        search_terms = self._extract_search_terms(original_message)
        print(f"🔍 Extracted search terms from message: {search_terms}")
        
        # If no explicit search terms but this is a follow-up question, check conversation history
        if not search_terms and analysis['action_type'] == 'followup':
            # Extract context and entities from recent conversation
            recent_history = []
            if hasattr(self, '_last_conversation_history'):
                recent_history = self._last_conversation_history
            
            context = self._extract_email_context(recent_history)
            if context['entities_mentioned']:
                # Use the most relevant entity from conversation history
                search_terms = context['entities_mentioned'][:2]  # Take top 2 entities
                print(f"🔍 Using entities from conversation history: {search_terms}")
        
        # Determine if this is a search query or recent query
        should_search = bool(search_terms) or any(word in original_message.lower() for word in ['about', 'regarding', 'from', 'subject'])
        
        if should_search and search_terms:
            # Use gmail_search for specific entity queries
            search_query = ' '.join(search_terms)
            print(f"🔍 Using gmail_search with query: '{search_query}'")
            
            result = await mcp_client.call_tool('gmail_search', {
                'query': search_query,
                'max_results': 3,
                'user_id': user_id
            })
            
            if result.get('success'):
                email_info = result.get('response', '')
                
                # Create contextual response based on search results
                if 'about' in original_message.lower():
                    response = f"Here's what I found about '{search_query}' emails:\n\n{email_info}"
                else:
                    response = email_info
                
                return {
                    'success': True,
                    'response': response,
                    'service': 'gmail', 
                    'tool_used': 'gmail_search',
                    'search_query': search_query
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to search for emails about "{search_query}"',
                    'use_default_llm': True
                }
        
        elif analysis['action_type'] == 'followup':
            # For follow-ups without specific search terms, get recent emails
            result = await mcp_client.call_tool('gmail_recent', {
                'max_results': 1,
                'user_id': user_id
            })
            
            if result.get('success'):
                email_info = result.get('response', '')
                
                # Create a contextual response based on the follow-up question
                if 'about' in original_message.lower():
                    response = f"The most recent email is about:\n\n{email_info}\n\nThis appears to be regarding the subject line shown above."
                elif 'tell me more' in original_message.lower():
                    response = f"Here are more details about your recent email:\n\n{email_info}\n\nWould you like me to search for more emails on this topic?"
                elif 'content' in original_message.lower() or 'say' in original_message.lower():
                    response = f"Here's what your recent email contains:\n\n{email_info}\n\nNote: This shows the email preview. Would you like me to get the full content?"
                else:
                    response = f"Here's information about your recent email:\n\n{email_info}"
                
                return {
                    'success': True,
                    'response': response,
                    'service': 'gmail',
                    'tool_used': 'gmail_recent'
                }
            else:
                return {
                    'success': False, 
                    'error': 'Failed to retrieve email information',
                    'use_default_llm': True
                }
        
        else:
            # For direct queries, use gmail_recent as default
            result = await mcp_client.call_tool('gmail_recent', {
                'max_results': 5,
                'user_id': user_id  
            })
            
            if result.get('success'):
                return {
                    'success': True,
                    'response': result.get('response', ''),
                    'service': 'gmail',
                    'tool_used': 'gmail_recent'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Gmail query failed'),
                    'use_default_llm': True
                }
    
    async def _handle_drive_context(
        self, 
        analysis: Dict[str, Any], 
        user_id: str, 
        mcp_client, 
        original_message: str
    ) -> Dict[str, Any]:
        """Handle Drive-related contextual queries."""
        
        result = await mcp_client.call_tool('drive_list_files', {
            'max_results': 10,
            'user_id': user_id
        })
        
        if result.get('success'):
            return {
                'success': True,
                'response': result.get('response', ''),
                'service': 'drive',
                'tool_used': 'drive_list_files'
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Drive query failed'),
                'use_default_llm': True
            }
    
    async def _handle_calendar_context(
        self, 
        analysis: Dict[str, Any], 
        user_id: str, 
        mcp_client, 
        original_message: str
    ) -> Dict[str, Any]:
        """Handle Calendar-related contextual queries."""
        
        result = await mcp_client.call_tool('calendar_upcoming_events', {
            'days': 7,
            'user_id': user_id
        })
        
        if result.get('success'):
            return {
                'success': True,
                'response': result.get('response', ''),
                'service': 'calendar', 
                'tool_used': 'calendar_upcoming_events'
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Calendar query failed'),
                'use_default_llm': True
            }


# Global instance
conversation_context_agent = ConversationContextAgent()