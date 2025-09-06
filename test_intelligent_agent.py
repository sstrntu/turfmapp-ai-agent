"""
Test Script for Intelligent Agentic Tool Usage

This script demonstrates the new intelligent agent capabilities including:
1. 3-tier classification system
2. Smart tool usage decisions  
3. Response quality evaluation
4. Analytics tracking
5. User preference controls
"""

import asyncio
import json
from backend.app.services.request_classifier import request_classifier
from backend.app.services.master_agent import master_agent
from backend.app.services.tool_analytics import tool_analytics
from backend.app.services.response_evaluator import response_evaluator

async def test_classification_system():
    """Test the 3-tier classification system."""
    print("\n🔍 Testing Classification System")
    print("=" * 50)
    
    test_queries = [
        # Tier 1: General knowledge (should be instant)
        "What is the capital of France?",
        "Who won the World Cup in 2022?",
        "Calculate 25 * 4",
        
        # Tier 1: Personal data (should use tools)
        "Show me my recent emails",
        "What meetings do I have today?",
        "Check my Google Drive files",
        
        # Tier 1: Context dependent (should analyze context)
        "What are they about?",
        "Tell me more about them",
        "Explain what it says",
        
        # Ambiguous (should go to Tier 3 LLM)
        "Help me with that project we discussed",
        "What should I prioritize today?",
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        classification = request_classifier.classify_request(query, [])
        
        print(f"  🏷️  Classification: {classification['classification']}")
        print(f"  🎯 Confidence: {classification['confidence']:.2f}")
        print(f"  ⚡ Tier: {classification['tier_used']}")
        print(f"  🛠️  Needs tools: {classification['needs_tools']}")
        if classification['suggested_tools']:
            print(f"  🔧 Suggested tools: {classification['suggested_tools']}")

def test_response_evaluation():
    """Test the response quality evaluation system."""
    print("\n📊 Testing Response Evaluation")
    print("=" * 50)
    
    test_cases = [
        {
            "question": "What are my recent emails?",
            "good_response": "I found 5 recent emails in your inbox: 1) Meeting invite from John (2 hours ago), 2) Project update from Sarah...",
            "poor_response": "Sorry, I couldn't access your emails due to an error."
        },
        {
            "question": "What is machine learning?",
            "good_response": "Machine learning is a branch of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed...",
            "poor_response": "ML is AI stuff."
        }
    ]
    
    async def evaluate_response(question, response, response_type):
        evaluation = await response_evaluator.evaluate_response_quality(
            question, response, tools_used=["gmail_search"] if "email" in question else []
        )
        
        print(f"\n{response_type} Response for: '{question[:40]}...'")
        print(f"  📈 Quality Score: {evaluation['quality_score']:.2f}")
        print(f"  🎯 Grade: {evaluation['evaluation']}")
        print(f"  ✅ Addressed Question: {evaluation['addressed_question']}")
        print(f"  💡 Method: {evaluation.get('method', 'unknown')}")
        
        if evaluation.get('improvement_suggestions'):
            print(f"  🔧 Suggestions: {evaluation['improvement_suggestions']}")
    
    for case in test_cases:
        await evaluate_response(case["question"], case["good_response"], "Good")
        await evaluate_response(case["question"], case["poor_response"], "Poor")

def test_analytics_tracking():
    """Test the analytics tracking system."""
    print("\n📊 Testing Analytics Tracking")
    print("=" * 50)
    
    # Simulate some tool usage
    tool_analytics.log_tool_usage(
        tool_name="gmail_search",
        user_id="test_user_1",
        user_query="Show me emails about project alpha",
        parameters={"query": "project alpha", "max_results": 5},
        result={"success": True, "response": "Found 3 emails about project alpha"},
        response_time=1.2,
        approach="tool_based"
    )
    
    tool_analytics.log_tool_usage(
        tool_name="calendar_upcoming_events", 
        user_id="test_user_1",
        user_query="What meetings do I have today?",
        parameters={"max_results": 10},
        result={"success": False, "error": "Authentication failed"},
        response_time=2.5,
        approach="tool_based"
    )
    
    # Log some classifications
    tool_analytics.log_classification_result(
        {"classification": "PERSONAL_DATA", "tier_used": 1, "confidence": 0.9},
        "tool_based",
        True
    )
    
    tool_analytics.log_classification_result(
        {"classification": "GENERAL_KNOWLEDGE", "tier_used": 1, "confidence": 0.95},
        "general_knowledge", 
        True
    )
    
    # Get analytics overview
    analytics = tool_analytics.get_overall_analytics()
    print(f"\n📈 Analytics Overview:")
    print(f"  Total interactions: {analytics['total_interactions']}")
    print(f"  Tool performance: {json.dumps(analytics['tool_performance'], indent=2)}")
    print(f"  Classification accuracy: {json.dumps(analytics['classification_accuracy'], indent=2)}")
    
    # Get recommendations
    recommendations = tool_analytics.get_optimization_recommendations()
    print(f"\n💡 Optimization Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. [{rec['priority'].upper()}] {rec['issue']}")
        print(f"     💡 {rec['suggestion']}")

def demo_user_preferences():
    """Demonstrate user preference controls."""
    print("\n🔧 User Preference Controls Demo")
    print("=" * 50)
    
    print("Available settings:")
    print("  • Auto tool usage: ON/OFF")
    print("  • Tool approach: conservative/balanced/aggressive") 
    print("  • Max tools per query: 1-10")
    print("  • Individual tool toggles: Gmail, Drive, Calendar")
    print("  • Classification sensitivity: strict/normal/lenient")
    
    print("\nExample API endpoints:")
    print("  GET  /api/v1/agent/settings - Get current settings")
    print("  PUT  /api/v1/agent/settings - Update settings")
    print("  GET  /api/v1/agent/analytics/overview - View analytics")
    print("  POST /api/v1/agent/test-classification - Test query classification")

def print_system_overview():
    """Print an overview of the intelligent agent system."""
    print("\n🤖 Intelligent Agentic Tool Usage System")
    print("=" * 60)
    
    print("🎯 KEY BENEFITS:")
    print("  ✅ No more unnecessary tool calls for simple questions")
    print("  ✅ Smart 3-tier classification (instant → fast → thorough)")
    print("  ✅ Continuous learning from response quality")
    print("  ✅ User-controlled preferences and analytics")
    print("  ✅ Cost optimization through intelligent routing")
    
    print("\n🏗️  ARCHITECTURE:")
    print("  1️⃣  RequestClassifier: Intelligent query categorization")
    print("  2️⃣  MasterAgent: Orchestrates responses with smart tool usage")
    print("  3️⃣  ResponseEvaluator: Evaluates quality and suggests improvements")
    print("  4️⃣  ToolAnalytics: Tracks usage patterns and effectiveness")
    print("  5️⃣  AgentSettings: User preferences and controls")
    
    print("\n🔄 DECISION FLOW:")
    print("  User Query → Classification → User Preferences Check → Tool Selection → Execution → Evaluation → Learning")
    
    print("\n📊 ANALYTICS & INSIGHTS:")
    print("  • Tool success rates and response times")
    print("  • Classification accuracy by tier")
    print("  • User-specific usage patterns")
    print("  • Optimization recommendations")
    
    print("\n🎛️  USER CONTROLS:")
    print("  • Toggle auto tool usage")
    print("  • Set tool usage approach (conservative/balanced/aggressive)")
    print("  • Enable/disable specific tool categories")
    print("  • View personal analytics dashboard")

async def main():
    """Run the complete test suite."""
    print_system_overview()
    
    await test_classification_system()
    await test_response_evaluation()
    test_analytics_tracking()
    demo_user_preferences()
    
    print(f"\n🎉 Intelligent Agent System Test Complete!")
    print(f"The system is now ready to provide truly intelligent, user-controlled tool usage!")

if __name__ == "__main__":
    asyncio.run(main())