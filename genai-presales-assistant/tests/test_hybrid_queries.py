"""
Test cases for hybrid queries (analytics + strategy) with proper stage and date field mapping
"""

import pytest
import sys
import os

# Add project root to path for imports
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from src.sql_agent.sql_agent import SQLAgent
from src.database.database_manager import DatabaseManager
from src.orchestration.orchestrator import SalesAssistantOrchestrator
from src.rag.rag_pipeline import RAGPipeline
from src.config import settings


class TestHybridQueries:
    """Test hybrid query functionality with analytics + strategy"""
    
    @pytest.fixture
    def components(self):
        """Setup all components for testing"""
        db_manager = DatabaseManager(settings.database_path)
        sql_agent = SQLAgent(db_manager)
        rag_pipeline = RAGPipeline(defer_index_build=False)
        orchestrator = SalesAssistantOrchestrator(sql_agent, rag_pipeline)
        return {
            'db_manager': db_manager,
            'sql_agent': sql_agent,
            'rag_pipeline': rag_pipeline,
            'orchestrator': orchestrator
        }
    
    def test_closed_deal_value_with_strategy(self, components):
        """Test the original problematic query"""
        question = "Show total closed deal value in last 6 months and suggest negotiation strategy if revenue dropped compared to previous 6 months."
        
        # Test SQL generation
        sql_query, explanation = components['sql_agent'].natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "stage = 'Closed Won'" in sql_query  # Should use Closed Won, not Negotiation
        assert "actual_close_date" in sql_query  # Should use actual_close_date, not expected_close_date
        assert "SUM(value)" in sql_query  # Should aggregate value
        assert "-6 month" in sql_query  # Should filter last 6 months
        
        print(f"✅ Closed deal value test passed: {sql_query}")
    
    def test_closed_revenue_comparison_with_advice(self, components):
        """Test closed revenue comparison with advice request"""
        question = "Compare closed revenue this quarter vs last quarter and recommend strategy if decreased"
        
        sql_query, explanation = components['sql_agent'].natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "stage = 'Closed Won'" in sql_query
        assert "actual_close_date" in sql_query
        assert "SUM(value)" in sql_query
        
        print(f"✅ Revenue comparison test passed: {sql_query}")
    
    def test_negotiation_stage_with_expected_close(self, components):
        """Test that negotiation queries correctly use expected_close_date"""
        question = "Show total pipeline value for deals in negotiation stage closing in next 3 months"
        
        sql_query, explanation = components['sql_agent'].natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "stage = 'Negotiation'" in sql_query  # Should correctly detect Negotiation
        assert "expected_close_date" in sql_query  # Should use expected_close_date for pipeline
        assert "SUM(value)" in sql_query
        assert "+3 month" in sql_query  # Should filter next 3 months
        
        print(f"✅ Negotiation pipeline test passed: {sql_query}")
    
    def test_proposal_stage_with_created_date(self, components):
        """Test that proposal queries use created_date when appropriate"""
        question = "Count deals created in proposal stage last month"
        
        sql_query, explanation = components['sql_agent'].natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "stage = 'Proposal'" in sql_query
        assert "created_date" in sql_query  # Should use created_date for creation queries
        assert "COUNT(*)" in sql_query
        assert "-1 month" in sql_query
        
        print(f"✅ Proposal creation test passed: {sql_query}")
    
    def test_hybrid_query_classification(self, components):
        """Test that hybrid queries are classified correctly"""
        orchestrator = components['orchestrator']
        
        hybrid_queries = [
            "Show total closed deal value and suggest strategy",
            "Calculate revenue and recommend approach if decreased",
            "Analyze performance and provide advice",
            "Compare metrics and suggest improvements"
        ]
        
        for query in hybrid_queries:
            query_type = orchestrator._classify_query_type(query)
            assert query_type == "hybrid", f"Query '{query}' should be classified as 'hybrid', got '{query_type}'"
        
        print("✅ Hybrid query classification test passed")
    
    def test_analytics_query_classification(self, components):
        """Test that pure analytics queries are classified correctly"""
        orchestrator = components['orchestrator']
        
        analytics_queries = [
            "Show top 5 sales reps by revenue",
            "Calculate total deal value last quarter",
            "Rank industries by performance"
        ]
        
        for query in analytics_queries:
            query_type = orchestrator._classify_query_type(query)
            assert query_type == "analytics", f"Query '{query}' should be classified as 'analytics', got '{query_type}'"
        
        print("✅ Analytics query classification test passed")
    
    def test_stage_detection_priority(self, components):
        """Test that stage detection prioritizes correctly"""
        sql_agent = components['sql_agent']
        
        # Test that "closed deal value" defaults to Closed Won
        question1 = "Show closed deal value last month"
        conditions1 = sql_agent._identify_conditions(question1, "deals")
        assert any("Closed Won" in cond for cond in conditions1)
        
        # Test that explicit "negotiation" is detected correctly
        question2 = "Show deals in negotiation stage"
        conditions2 = sql_agent._identify_conditions(question2, "deals")
        assert any("Negotiation" in cond for cond in conditions2)
        
        print("✅ Stage detection priority test passed")
    
    def test_date_column_selection_logic(self, components):
        """Test date column selection logic"""
        sql_agent = components['sql_agent']
        
        # Test closed deals use actual_close_date
        date_conditions1 = sql_agent._parse_date_conditions("closed deals last 6 months", "Closed Won")
        assert any("actual_close_date" in cond for cond in date_conditions1)
        
        # Test pipeline deals use expected_close_date
        date_conditions2 = sql_agent._parse_date_conditions("deals closing next month", "Negotiation")
        assert any("expected_close_date" in cond for cond in date_conditions2)
        
        # Test general queries use created_date
        date_conditions3 = sql_agent._parse_date_conditions("deals created last week", None)
        assert any("created_date" in cond for cond in date_conditions3)
        
        print("✅ Date column selection test passed")
    
    def test_hybrid_query_end_to_end(self, components):
        """Test complete hybrid query processing"""
        orchestrator = components['orchestrator']
        
        question = "Show total closed deal value in last 6 months and suggest negotiation strategy if revenue dropped compared to previous 6 months."
        result = orchestrator.process_query(question)
        
        # Verify hybrid processing
        assert result['success'] == True
        assert result['query_type'] == 'hybrid'
        assert result['sql_result']['success'] == True
        assert len(result['rag_results']) > 0  # Should have RAG results for strategy
        assert 'Closed Won' in result['sql_result']['sql_query']
        assert 'actual_close_date' in result['sql_result']['sql_query']
        
        print(f"✅ End-to-end hybrid test passed")
        print(f"   Query type: {result['query_type']}")
        print(f"   SQL success: {result['sql_result']['success']}")
        print(f"   RAG results: {len(result['rag_results'])} documents")


def run_hybrid_query_tests():
    """Run all hybrid query tests manually"""
    print("🧪 Running Hybrid Query Tests...")
    print("=" * 70)
    
    # Setup components
    db_manager = DatabaseManager(settings.database_path)
    sql_agent = SQLAgent(db_manager)
    rag_pipeline = RAGPipeline(defer_index_build=False)
    orchestrator = SalesAssistantOrchestrator(sql_agent, rag_pipeline)
    
    components = {
        'db_manager': db_manager,
        'sql_agent': sql_agent,
        'rag_pipeline': rag_pipeline,
        'orchestrator': orchestrator
    }
    
    test_cases = [
        ("Show total closed deal value in last 6 months and suggest negotiation strategy if revenue dropped compared to previous 6 months.", "Original Problematic Query"),
        ("Compare closed revenue this quarter vs last quarter and recommend strategy if decreased", "Revenue Comparison"),
        ("Show total pipeline value for deals in negotiation stage closing in next 3 months", "Negotiation Pipeline"),
        ("Count deals created in proposal stage last month", "Proposal Creation"),
        ("Show top 5 sales reps by revenue and provide improvement suggestions", "Analytics + Advice"),
        ("Calculate total deal value last quarter", "Pure Analytics"),
        ("Draft negotiation strategy for enterprise deals", "Pure Strategy")
    ]
    
    for i, (question, test_name) in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_name}")
        print(f"Query: {question}")
        
        try:
            # Test SQL generation
            sql_query, explanation = sql_agent.natural_language_to_sql(question)
            
            # Test classification
            query_type = orchestrator._classify_query_type(question)
            
            # Test full processing
            result = orchestrator.process_query(question)
            
            print(f"✅ Query type: {query_type}")
            print(f"✅ SQL: {sql_query}")
            print(f"✅ Processing success: {result['success']}")
            print(f"✅ SQL success: {result['sql_result']['success']}")
            print(f"✅ RAG results: {len(result['rag_results'])} documents")
            
            # Validate specific requirements
            if "closed" in question.lower() and "deal value" in question.lower():
                if "Closed Won" in sql_query and "actual_close_date" in sql_query:
                    print("🎯 Correctly uses Closed Won + actual_close_date")
                else:
                    print("❌ Incorrect stage/date field mapping")
            
            if "negotiation" in question.lower() and "closing" in question.lower():
                if "Negotiation" in sql_query and "expected_close_date" in sql_query:
                    print("🎯 Correctly uses Negotiation + expected_close_date")
                else:
                    print("❌ Incorrect stage/date field mapping")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("🎉 Hybrid query test suite completed!")


if __name__ == "__main__":
    run_hybrid_query_tests()
