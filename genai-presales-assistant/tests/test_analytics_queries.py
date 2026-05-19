"""
Comprehensive test cases for analytics queries with aggregation + grouping + ranking
"""

import pytest
import sys
import os

# Add project root to path for imports
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from src.sql_agent.sql_agent import SQLAgent
from src.database.database_manager import DatabaseManager
from src.config import settings


class TestAnalyticsQueries:
    """Test analytics query functionality with aggregation + grouping + ranking"""
    
    @pytest.fixture
    def sql_agent(self):
        """Setup SQL Agent for testing"""
        db_manager = DatabaseManager(settings.database_path)
        agent = SQLAgent(db_manager)
        return agent
    
    def test_top_sales_reps_by_revenue_last_6_months(self, sql_agent):
        """Test the original problematic query"""
        question = "Show top 5 sales reps by total closed won deal value in last 6 months, along with number of deals they closed."
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "deal_owner" in sql_query  # Should group by sales rep
        assert "SUM(value)" in sql_query  # Should aggregate total value
        assert "COUNT(*)" in sql_query  # Should count deals
        assert "GROUP BY deal_owner" in sql_query  # Should have GROUP BY
        assert "ORDER BY total_value DESC" in sql_query  # Should order by total value
        assert "LIMIT 5" in sql_query  # Should limit to top 5
        assert "stage = 'Closed Won'" in sql_query  # Should filter closed won deals
        assert "actual_close_date" in sql_query  # Should use actual_close_date for closed deals
        assert "-6 month" in sql_query  # Should filter last 6 months
        print(f"✅ Top sales reps test passed: {sql_query}")
    
    def test_top_industries_by_total_deal_value(self, sql_agent):
        """Test top industries by total deal value"""
        question = "Show top 3 industries by total deal value"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "industry" in sql_query
        assert "SUM(value)" in sql_query
        assert "GROUP BY industry" in sql_query
        assert "ORDER BY total_value DESC" in sql_query
        assert "LIMIT 3" in sql_query
        print(f"✅ Top industries test passed: {sql_query}")
    
    def test_sales_reps_with_highest_avg_deal_size(self, sql_agent):
        """Test sales reps with highest average deal size"""
        question = "Show sales reps with highest average deal size"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "deal_owner" in sql_query
        assert "AVG(value)" in sql_query
        assert "GROUP BY deal_owner" in sql_query
        assert "ORDER BY avg_value DESC" in sql_query
        print(f"✅ Highest avg deal size test passed: {sql_query}")
    
    def test_rep_wise_deal_count_leaderboard(self, sql_agent):
        """Test rep-wise deal count leaderboard"""
        question = "Show rep-wise deal count leaderboard for last quarter"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "deal_owner" in sql_query
        assert "COUNT(*)" in sql_query
        assert "GROUP BY deal_owner" in sql_query
        assert "ORDER BY deal_count DESC" in sql_query
        assert "last quarter" in sql_query.lower() or "-3 month" in sql_query
        print(f"✅ Rep-wise deal count test passed: {sql_query}")
    
    def test_performance_by_stage(self, sql_agent):
        """Test performance analysis by deal stage"""
        question = "Analyze total value by deal stage"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "stage" in sql_query
        assert "SUM(value)" in sql_query
        assert "GROUP BY stage" in sql_query
        assert "ORDER BY total_value DESC" in sql_query
        print(f"✅ Performance by stage test passed: {sql_query}")
    
    def test_customer_revenue_ranking(self, sql_agent):
        """Test customer revenue ranking"""
        question = "Show top 10 customers by total revenue"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "customer_id" in sql_query
        assert "SUM(annual_revenue)" in sql_query
        assert "GROUP BY customer_id" in sql_query
        assert "ORDER BY total_value DESC" in sql_query
        assert "LIMIT 10" in sql_query
        print(f"✅ Customer revenue ranking test passed: {sql_query}")
    
    def test_complex_multi_metric_analytics(self, sql_agent):
        """Test complex multi-metric analytics query"""
        question = "Show top 5 industries by average deal value and total deal count"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "industry" in sql_query
        assert "AVG(value)" in sql_query
        assert "COUNT(*)" in sql_query
        assert "GROUP BY industry" in sql_query
        assert "ORDER BY" in sql_query
        assert "LIMIT 5" in sql_query
        print(f"✅ Complex multi-metric test passed: {sql_query}")
    
    def test_time_filtered_analytics(self, sql_agent):
        """Test analytics with time filters"""
        question = "Show top sales reps by closed deals value this year"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "deal_owner" in sql_query
        assert "SUM(value)" in sql_query
        assert "GROUP BY deal_owner" in sql_query
        assert "this year" in sql_query.lower()
        print(f"✅ Time filtered analytics test passed: {sql_query}")
    
    def test_query_classification_analytics(self, sql_agent):
        """Test that analytics queries are classified correctly"""
        from src.orchestration.orchestrator import SalesAssistantOrchestrator
        
        orchestrator = SalesAssistantOrchestrator()
        
        analytics_queries = [
            "Show top 5 sales reps by revenue",
            "Rank industries by total deal value",
            "Performance analysis per rep",
            "Sales leaderboard by deal count"
        ]
        
        for query in analytics_queries:
            query_type = orchestrator._classify_query_type(query)
            assert query_type == "analytics", f"Query '{query}' should be classified as 'analytics', got '{query_type}'"
        
        print("✅ Query classification test passed")
    
    def test_sql_validation_aggregation(self, sql_agent):
        """Test SQL validation for aggregation consistency"""
        from src.database.database_manager import DatabaseManager
        
        db_manager = DatabaseManager(settings.database_path)
        
        # Valid aggregation query
        valid_query = "SELECT deal_owner, SUM(value) as total_value FROM deals GROUP BY deal_owner ORDER BY total_value DESC LIMIT 5"
        is_safe, message = db_manager.validate_query_safety(valid_query)
        assert is_safe, f"Valid query should pass validation: {message}"
        
        # Invalid aggregation (missing GROUP BY)
        invalid_query = "SELECT deal_owner, SUM(value) FROM deals ORDER BY value DESC LIMIT 5"
        is_safe, message = db_manager.validate_query_safety(invalid_query)
        assert not is_safe, "Invalid query should fail validation"
        assert "missing GROUP BY" in message
        
        print("✅ SQL validation test passed")


def run_analytics_tests():
    """Run all analytics query tests manually"""
    print("🧪 Running Analytics Query Tests...")
    print("=" * 70)
    
    # Setup
    db_manager = DatabaseManager(settings.database_path)
    agent = SQLAgent(db_manager)
    
    test_cases = [
        ("Show top 5 sales reps by total closed won deal value in last 6 months, along with number of deals they closed.", "Top Sales Reps + Multi-Metric"),
        ("Show top 3 industries by total deal value", "Top Industries"),
        ("Show sales reps with highest average deal size", "Highest Avg Deal Size"),
        ("Show rep-wise deal count leaderboard for last quarter", "Rep-wise Leaderboard"),
        ("Analyze total value by deal stage", "Performance by Stage"),
        ("Show top 10 customers by total revenue", "Customer Revenue Ranking"),
        ("Show top 5 industries by average deal value and total deal count", "Complex Multi-Metric"),
        ("Show top sales reps by closed deals value this year", "Time Filtered Analytics"),
    ]
    
    for i, (question, test_name) in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_name}")
        print(f"Query: {question}")
        
        try:
            sql_query, explanation = agent.natural_language_to_sql(question)
            if sql_query:
                print(f"✅ Generated SQL: {sql_query}")
                print(f"📝 Explanation: {explanation}")
                
                # Validate analytics features
                analytics_features = {
                    "GROUP BY": "GROUP BY" in sql_query.upper(),
                    "Aggregation": any(agg in sql_query.upper() for agg in ["SUM(", "COUNT(", "AVG(", "MIN(", "MAX("]),
                    "ORDER BY": "ORDER BY" in sql_query.upper(),
                    "Proper Column": any(col in sql_query for col in ["deal_owner", "industry", "stage", "customer_id"])
                }
                
                print(f"🎯 Analytics Features: {analytics_features}")
                        
            else:
                print(f"❌ Failed to generate SQL")
                print(f"📝 Explanation: {explanation}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("🎉 Analytics query test suite completed!")


if __name__ == "__main__":
    run_analytics_tests()
