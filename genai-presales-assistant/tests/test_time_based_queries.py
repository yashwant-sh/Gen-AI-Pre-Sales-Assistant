"""
Test cases for time-based SQL query generation with smart date column selection
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


class TestTimeBasedQueries:
    """Test time-based query functionality"""
    
    @pytest.fixture
    def sql_agent(self):
        """Setup SQL Agent for testing"""
        db_manager = DatabaseManager(settings.database_path)
        agent = SQLAgent(db_manager)
        return agent
    
    def test_closed_won_deals_last_3_months(self, sql_agent):
        """Test the specific case mentioned in the bug report"""
        question = "Show closed won deals in last 3 months"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "stage = 'Closed Won'" in sql_query
        assert "actual_close_date" in sql_query  # Should use actual_close_date for closed deals
        assert "-3 month" in sql_query
        print(f"✅ Closed won last 3 months test passed: {sql_query}")
    
    def test_closed_lost_deals_last_quarter(self, sql_agent):
        """Test closed lost deals with last quarter"""
        question = "Find closed lost deals in last quarter"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "stage = 'Closed Lost'" in sql_query
        assert "actual_close_date" in sql_query
        assert "last quarter" in explanation.lower() or "-3 month" in sql_query
        print(f"✅ Closed lost last quarter test passed: {sql_query}")
    
    def test_pipeline_deals_next_month(self, sql_agent):
        """Test pipeline deals with expected close date"""
        question = "Show deals expected to close next month"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "expected_close_date" in sql_query  # Should use expected_close_date for pipeline
        assert "next month" in sql_query.lower()
        print(f"✅ Pipeline deals next month test passed: {sql_query}")
    
    def test_negotiation_deals_last_2_weeks(self, sql_agent):
        """Test deals in negotiation stage with time filter"""
        question = "Find deals in negotiation stage from last 2 weeks"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "stage = 'Negotiation'" in sql_query
        assert "created_date" in sql_query  # Should use created_date for non-closed deals
        assert "-2 week" in sql_query
        print(f"✅ Negotiation deals last 2 weeks test passed: {sql_query}")
    
    def test_proposals_last_month(self, sql_agent):
        """Test proposals created last month"""
        question = "Show proposals created last month"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "stage = 'Proposal'" in sql_query
        assert "created_date" in sql_query
        assert "last month" in sql_query.lower()
        print(f"✅ Proposals last month test passed: {sql_query}")
    
    def test_all_deals_this_year(self, sql_agent):
        """Test all deals from this year"""
        question = "List all deals created this year"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "created_date" in sql_query
        assert "this year" in sql_query.lower()
        print(f"✅ All deals this year test passed: {sql_query}")
    
    def test_won_deals_last_30_days(self, sql_agent):
        """Test won deals in last 30 days"""
        question = "Show won deals in last 30 days"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "stage = 'Closed Won'" in sql_query
        assert "actual_close_date" in sql_query
        assert "-30 day" in sql_query
        print(f"✅ Won deals last 30 days test passed: {sql_query}")
    
    def test_complex_time_and_probability_filters(self, sql_agent):
        """Test complex query with time and probability filters"""
        question = "Find closed won deals in last 6 months with probability 100%"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "stage = 'Closed Won'" in sql_query
        assert "actual_close_date" in sql_query
        assert "-6 month" in sql_query
        assert "probability = 100" in sql_query
        print(f"✅ Complex time and probability test passed: {sql_query}")


def run_time_based_tests():
    """Run all time-based query tests manually"""
    print("🧪 Running Time-Based Query Tests...")
    print("=" * 60)
    
    # Setup
    db_manager = DatabaseManager(settings.database_path)
    agent = SQLAgent(db_manager)
    
    test_cases = [
        ("Show closed won deals in last 3 months", "Closed Won + Last 3 Months"),
        ("Find closed lost deals in last quarter", "Closed Lost + Last Quarter"),
        ("Show deals expected to close next month", "Pipeline + Next Month"),
        ("Find deals in negotiation stage from last 2 weeks", "Negotiation + Last 2 Weeks"),
        ("Show proposals created last month", "Proposals + Last Month"),
        ("List all deals created this year", "All Deals + This Year"),
        ("Show won deals in last 30 days", "Won Deals + Last 30 Days"),
        ("Find closed won deals in last 6 months with probability 100%", "Complex Time + Probability"),
    ]
    
    for i, (question, test_name) in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_name}")
        print(f"Query: {question}")
        
        try:
            sql_query, explanation = agent.natural_language_to_sql(question)
            if sql_query:
                print(f"✅ Generated SQL: {sql_query}")
                print(f"📝 Explanation: {explanation}")
                
                # Verify smart column selection
                if "closed" in question.lower():
                    if "actual_close_date" in sql_query:
                        print(f"🎯 Smart column selection: actual_close_date ✓")
                    else:
                        print(f"❌ Smart column selection failed - should use actual_close_date")
                elif "expected" in question.lower() or "close" in question.lower():
                    if "expected_close_date" in sql_query:
                        print(f"🎯 Smart column selection: expected_close_date ✓")
                    else:
                        print(f"❌ Smart column selection failed - should use expected_close_date")
                        
            else:
                print(f"❌ Failed to generate SQL")
                print(f"📝 Explanation: {explanation}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Time-based query test suite completed!")


if __name__ == "__main__":
    run_time_based_tests()
