"""
Enhanced test cases for SQL Agent with probability and date filters
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


class TestEnhancedSQLAgent:
    """Test enhanced SQL Agent functionality"""
    
    @pytest.fixture
    def sql_agent(self):
        """Setup SQL Agent for testing"""
        db_manager = DatabaseManager(settings.database_path)
        agent = SQLAgent(db_manager)
        return agent
    
    def test_probability_filter_above(self, sql_agent):
        """Test probability filter with 'above'"""
        question = "Show deals that are likely to close with probability above 60%"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "probability > 60" in sql_query
        assert "deals" in sql_query.lower()
        print(f"✅ Probability above test passed: {sql_query}")
    
    def test_probability_filter_over(self, sql_agent):
        """Test probability filter with 'over'"""
        question = "Find deals with probability over 75"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "probability > 75" in sql_query
        print(f"✅ Probability over test passed: {sql_query}")
    
    def test_probability_filter_percentage(self, sql_agent):
        """Test probability filter with percentage format"""
        question = "List deals with 80% probability"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "probability = 80" in sql_query
        print(f"✅ Probability percentage test passed: {sql_query}")
    
    def test_date_filter_next_days(self, sql_agent):
        """Test date filter with 'next X days'"""
        question = "Show deals that are likely to close in next 30 days"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "expected_close_date" in sql_query
        assert "+30 day" in sql_query
        print(f"✅ Next days date filter test passed: {sql_query}")
    
    def test_date_filter_last_days(self, sql_agent):
        """Test date filter with 'last X days'"""
        question = "Find deals created in last 7 days"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "created_date" in sql_query
        assert "-7 day" in sql_query
        print(f"✅ Last days date filter test passed: {sql_query}")
    
    def test_combined_probability_and_date_filters(self, sql_agent):
        """Test combined probability and date filters"""
        question = "Show deals that are likely to close in next 30 days with probability above 60%"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "probability > 60" in sql_query
        assert "expected_close_date" in sql_query
        assert "+30 day" in sql_query
        assert "AND" in sql_query
        print(f"✅ Combined filters test passed: {sql_query}")
    
    def test_value_filter_greater_than(self, sql_agent):
        """Test value filter with greater than"""
        question = "Show deals with value greater than 100000"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "value > 100000" in sql_query
        print(f"✅ Value greater than test passed: {sql_query}")
    
    def test_multiple_conditions(self, sql_agent):
        """Test multiple conditions"""
        question = "Show top 5 deals with probability above 70% and value over 50000"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "probability > 70" in sql_query
        assert "value > 50000" in sql_query
        assert "LIMIT 5" in sql_query
        print(f"✅ Multiple conditions test passed: {sql_query}")
    
    def test_date_filter_this_month(self, sql_agent):
        """Test date filter with 'this month'"""
        question = "Find deals created this month"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "created_date" in sql_query
        assert "start of month" in sql_query
        print(f"✅ This month date filter test passed: {sql_query}")
    
    def test_date_filter_next_month(self, sql_agent):
        """Test date filter with 'next month'"""
        question = "Show deals expected to close next month"
        sql_query, explanation = sql_agent.natural_language_to_sql(question)
        
        assert sql_query is not None
        assert "expected_close_date" in sql_query
        assert "+1 month" in sql_query
        print(f"✅ Next month date filter test passed: {sql_query}")
    
    def test_confidence_scoring_simple_query(self, sql_agent):
        """Test confidence scoring for simple query"""
        question = "Show top 5 deals"
        confidence = sql_agent._calculate_confidence(
            question, "deals", [], None, "value DESC", "5"
        )
        
        assert confidence >= 0.8  # Should have high confidence
        print(f"✅ Simple query confidence: {confidence}")
    
    def test_confidence_scoring_complex_query(self, sql_agent):
        """Test confidence scoring for complex query"""
        question = "Find deals between specific ranges with complex conditions"
        confidence = sql_agent._calculate_confidence(
            question, "deals", ["condition1", "condition2", "condition3"], None, None, None
        )
        
        assert confidence < 0.6  # Should have low confidence, trigger LLM fallback
        print(f"✅ Complex query confidence: {confidence}")


def run_tests():
    """Run all tests manually"""
    print("🧪 Running Enhanced SQL Agent Tests...")
    print("=" * 50)
    
    # Setup
    db_manager = DatabaseManager(settings.database_path)
    agent = SQLAgent(db_manager)
    
    test_cases = [
        ("Show deals that are likely to close with probability above 60%", "Probability + Date"),
        ("Find deals with probability over 75", "Probability Over"),
        ("List deals with 80% probability", "Probability Percentage"),
        ("Show deals that are likely to close in next 30 days", "Next Days Date"),
        ("Find deals created in last 7 days", "Last Days Date"),
        ("Show deals with value greater than 100000", "Value Filter"),
        ("Show top 5 deals with probability above 70% and value over 50000", "Multiple Conditions"),
        ("Find deals created this month", "This Month Date"),
        ("Show deals expected to close next month", "Next Month Date"),
    ]
    
    for i, (question, test_name) in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_name}")
        print(f"Query: {question}")
        
        try:
            sql_query, explanation = agent.natural_language_to_sql(question)
            if sql_query:
                print(f"✅ Generated SQL: {sql_query}")
                print(f"📝 Explanation: {explanation}")
            else:
                print(f"❌ Failed to generate SQL")
                print(f"📝 Explanation: {explanation}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Test suite completed!")


if __name__ == "__main__":
    run_tests()
