#!/usr/bin/env python3
"""
Test script for Master Agent with Gmail MCP integration
This tests the agentic conversation flow without API authentication
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.master_agent import master_agent
from app.services.mcp_client_simple import google_mcp_client

async def test_master_agent():
    """Test Master Agent with simulated Gmail scenario"""
    print("🧪 Testing Master Agent with Gmail MCP integration...")
    
    # Simulate conversation history with initial Gmail check
    formatted_history = [
        {
            "role": "user",
            "content": "check my recent emails from Gmail"
        },
        {
            "role": "assistant", 
            "content": """📧 **Gmail Email Summary:**

**Email 1: Jubilo Meeting Preparation**
   👤 **From:** john@jubilo.com
   🎯 **Subject:** Meeting Preparation Required - Q4 Planning
   📅 **Date:** 2025-01-05 10:30 AM
   📝 **Content:**
   Hi there,
   
   We need to prepare for the Q4 planning meeting scheduled for January 10th. Please review the following:
   
   1. Budget allocations for the upcoming quarter
   2. Resource planning documentation 
   3. Timeline for project deliverables
   4. Risk assessment reports
   
   The meeting will be at 2 PM in Conference Room A. Please bring printed copies of all documents.
   
   Best regards,
   John Smith
   Project Manager
   
**Email 2: Training Schedule Update**
   👤 **From:** hr@company.com
   🎯 **Subject:** Mandatory Training - Updated Schedule
   📅 **Date:** 2025-01-05 09:15 AM
   📝 **Content:**
   Dear Team,
   
   The mandatory compliance training has been rescheduled to January 8th at 3 PM. Please block your calendars accordingly.
   
   Topics covered:
   - Data protection policies
   - Workplace safety protocols
   - Ethics and compliance guidelines
   
   Attendance is required for all employees.
   
   HR Team
   
**Email 3: Client Presentation Feedback**
   👤 **From:** client@bigcorp.com
   🎯 **Subject:** Presentation Review - Action Items
   📅 **Date:** 2025-01-04 4:45 PM
   📝 **Content:**
   Hello,
   
   Thank you for the excellent presentation yesterday. We have a few follow-up items:
   
   1. Provide detailed cost breakdown by January 7th
   2. Submit technical specifications document
   3. Schedule follow-up call for contract discussion
   
   Looking forward to moving forward with this partnership.
   
   Best,
   Sarah Johnson
   Big Corp Inc."""
        }
    ]
    
    # Test follow-up question about specific email
    follow_up_message = "what is the Jubilo email about?"
    user_id = "test_user_123"
    
    try:
        print(f"🔍 Processing follow-up question: '{follow_up_message}'")
        
        result = await master_agent.process_user_request(
            user_message=follow_up_message,
            conversation_history=formatted_history,
            user_id=user_id,
            mcp_client=google_mcp_client
        )
        
        print(f"✅ Master Agent Response:")
        print(f"📝 Content: {result}")
        print("\n" + "="*50)
        
        # Test action extraction question
        action_message = "what do I need to do?"
        print(f"🔍 Processing action question: '{action_message}'")
        
        action_result = await master_agent.process_user_request(
            user_message=action_message,
            conversation_history=formatted_history,
            user_id=user_id,
            mcp_client=google_mcp_client
        )
        
        print(f"✅ Action Extraction Response:")
        print(f"📋 Content: {action_result}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_master_agent())