"""
Enhanced Intent Classifier for GenAI Pre-Sales Assistant
Hybrid approach: Rule-based + LLM fallback for clean, production-ready routing
"""

import re
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class IntentResult:
    """Structured result for intent classification"""
    intent: str
    confidence: float
    keywords_matched: list
    reasoning: str

class IntentClassifier:
    """
    Hybrid Intent Classifier for GenAI Pre-Sales Assistant
    
    Priority Order:
    1. Time Analytics (highest specificity)
    2. Data Query (SQL-based aggregations)
    3. Document Query (RAG-based knowledge)
    4. General (fallback)
    """
    
    def __init__(self):
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Initialize keyword patterns for each intent type"""
        
        # TIME ANALYTICS PATTERNS (Highest Priority)
        self.time_analytics_patterns = {
            'time_periods': [
                r'last (\d+) quarters?', r'past (\d+) quarters?', r'last quarter',
                r'past quarter', r'this quarter', r'recent quarter',
                r'last (\d+) months?', r'past (\d+) months?', r'quarterly',
                r'monthly trend', r'year over year', r'yoy', r'period over period'
            ],
            'trend_keywords': [
                'trend', 'trends', 'declining', 'improving', 'growth', 'decline',
                'compare', 'comparison', 'analysis', 'performance', 'quarterly', 'monthly'
            ],
            'aggregation_keywords': [
                'analyze', 'compare', 'show trends', 'identify', 'track', 'measure'
            ]
        }
        
        # DATA QUERY PATTERNS (SQL-based)
        self.data_query_patterns = {
            'aggregation_keywords': [
                'total', 'sum', 'count', 'average', 'max', 'min', 'revenue',
                'sales', 'income', 'earnings', 'money', 'value', 'deal value'
            ],
            'metric_keywords': [
                'how many', 'how much', 'what is', 'show me', 'list', 'get',
                'find', 'calculate', 'total revenue', 'total sales'
            ],
            'entity_keywords': [
                'deals', 'customers', 'activities', 'stages', 'reps', 'owners'
            ],
            'filter_keywords': [
                'closed won', 'closed lost', 'stage', 'status', 'where', 'by'
            ]
        }
        
        # DOCUMENT QUERY PATTERNS (RAG-based)
        self.document_query_patterns = {
            'knowledge_keywords': [
                'how to', 'what is', 'best practices', 'tips', 'guide', 'help',
                'advice', 'recommendation', 'strategy', 'approach'
            ],
            'content_keywords': [
                'proposal', 'email', 'template', 'draft', 'objections',
                'negotiation', 'pitch', 'presentation', 'follow-up'
            ],
            'process_keywords': [
                'write', 'create', 'draft', 'generate', 'help me', 'suggest'
            ]
        }
    
    def classify_intent(self, query: str) -> IntentResult:
        """
        Main classification method with hybrid approach
        
        Args:
            query: User query string
            
        Returns:
            IntentResult with classification details
        """
        
        query_lower = query.lower().strip()
        logger.info(f"=== CLASSIFYING INTENT FOR: '{query}' ===")
        
        # Step 1: Try rule-based classification first
        rule_result = self._rule_based_classification(query_lower)
        
        # Step 2: If high confidence, return immediately
        if rule_result.confidence >= 0.8:
            logger.info(f"✅ HIGH CONFIDENCE RULE-BASED: {rule_result.intent} ({rule_result.confidence:.2f})")
            return rule_result
        
        # Step 3: For medium confidence, try LLM verification (if available)
        elif rule_result.confidence >= 0.5:
            logger.info(f"⚠️ MEDIUM CONFIDENCE: {rule_result.intent} ({rule_result.confidence:.2f})")
            # TODO: Add LLM verification here if needed
            return rule_result
        
        # Step 4: Low confidence - use fallback logic
        else:
            logger.info(f"❌ LOW CONFIDENCE: Using fallback logic")
            return self._fallback_classification(query_lower)
    
    def _rule_based_classification(self, query: str) -> IntentResult:
        """
        Rule-based classification with keyword matching and scoring
        Priority order for business logic:
        1. Document Query (email/proposal writing - highest business priority)
        2. Time Analytics (specific time-based analysis)
        3. Data Query (SQL aggregations)
        4. General (fallback)
        """
        
        # Check Document Query FIRST (email/proposal generation has priority)
        doc_result = self._check_document_query(query)
        if doc_result.confidence > 0:
            return doc_result
        
        # Check Time Analytics second
        time_result = self._check_time_analytics(query)
        if time_result.confidence > 0:
            return time_result
        
        # Check Data Query third
        data_result = self._check_data_query(query)
        if data_result.confidence > 0:
            return data_result
        
        # Fallback to general
        return IntentResult(
            intent="general",
            confidence=0.3,
            keywords_matched=[],
            reasoning="No specific patterns matched, defaulting to general"
        )
    
    def _check_time_analytics(self, query: str) -> IntentResult:
        """Check for time analytics intent"""
        
        score = 0
        keywords_matched = []
        reasoning_parts = []
        
        # Check for time periods
        for pattern in self.time_analytics_patterns['time_periods']:
            if re.search(pattern, query):
                score += 0.4
                keywords_matched.append(pattern)
                reasoning_parts.append(f"Time period detected: {pattern}")
        
        # Check for trend keywords
        trend_matches = [kw for kw in self.time_analytics_patterns['trend_keywords'] if kw in query]
        if trend_matches:
            score += 0.3 * len(trend_matches)
            keywords_matched.extend(trend_matches)
            reasoning_parts.append(f"Trend keywords: {trend_matches}")
        
        # Check for aggregation keywords
        agg_matches = [kw for kw in self.time_analytics_patterns['aggregation_keywords'] if kw in query]
        if agg_matches:
            score += 0.2 * len(agg_matches)
            keywords_matched.extend(agg_matches)
            reasoning_parts.append(f"Aggregation keywords: {agg_matches}")
        
        # Cap score at 1.0
        score = min(score, 1.0)
        
        return IntentResult(
            intent="time_analytics" if score >= 0.3 else "",
            confidence=score,
            keywords_matched=keywords_matched,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No time analytics patterns"
        )
    
    def _check_data_query(self, query: str) -> IntentResult:
        """Check for data query intent"""
        
        score = 0
        keywords_matched = []
        reasoning_parts = []
        
        # Check for aggregation keywords (highest weight)
        agg_matches = [kw for kw in self.data_query_patterns['aggregation_keywords'] if kw in query]
        if agg_matches:
            score += 0.4 * len(agg_matches)
            keywords_matched.extend(agg_matches)
            reasoning_parts.append(f"Aggregation keywords: {agg_matches}")
        
        # Check for metric keywords
        metric_matches = [kw for kw in self.data_query_patterns['metric_keywords'] if kw in query]
        if metric_matches:
            score += 0.3 * len(metric_matches)
            keywords_matched.extend(metric_matches)
            reasoning_parts.append(f"Metric keywords: {metric_matches}")
        
        # Check for entity keywords
        entity_matches = [kw for kw in self.data_query_patterns['entity_keywords'] if kw in query]
        if entity_matches:
            score += 0.2 * len(entity_matches)
            keywords_matched.extend(entity_matches)
            reasoning_parts.append(f"Entity keywords: {entity_matches}")
        
        # Check for filter keywords
        filter_matches = [kw for kw in self.data_query_patterns['filter_keywords'] if kw in query]
        if filter_matches:
            score += 0.1 * len(filter_matches)
            keywords_matched.extend(filter_matches)
            reasoning_parts.append(f"Filter keywords: {filter_matches}")
        
        # Cap score at 1.0
        score = min(score, 1.0)
        
        return IntentResult(
            intent="data_query" if score >= 0.3 else "",
            confidence=score,
            keywords_matched=keywords_matched,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No data query patterns"
        )
    
    def _check_document_query(self, query: str) -> IntentResult:
        """Check for document query intent with enhanced email/proposal detection"""
        
        score = 0
        keywords_matched = []
        reasoning_parts = []
        
        # HIGH PRIORITY: Check for email/proposal writing keywords (highest weight)
        writing_keywords = ['write', 'draft', 'create', 'generate', 'help me', 'suggest']
        writing_matches = [kw for kw in writing_keywords if kw in query]
        if writing_matches:
            score += 0.6 * len(writing_matches)  # Increased weight
            keywords_matched.extend(writing_matches)
            reasoning_parts.append(f"Writing keywords: {writing_matches}")
        
        # Check for content keywords (email, proposal, etc.)
        content_matches = [kw for kw in self.document_query_patterns['content_keywords'] if kw in query]
        if content_matches:
            score += 0.5 * len(content_matches)  # Increased weight
            keywords_matched.extend(content_matches)
            reasoning_parts.append(f"Content keywords: {content_matches}")
        
        # Check for knowledge keywords
        knowledge_matches = [kw for kw in self.document_query_patterns['knowledge_keywords'] if kw in query]
        if knowledge_matches:
            score += 0.3 * len(knowledge_matches)
            keywords_matched.extend(knowledge_matches)
            reasoning_parts.append(f"Knowledge keywords: {knowledge_matches}")
        
        # Special bonus for email + follow-up combination
        if 'email' in query and 'follow' in query:
            score += 0.3
            keywords_matched.append('email_follow_up')
            reasoning_parts.append("Email follow-up pattern detected")
        
        # Special bonus for proposal + draft combination
        if 'proposal' in query and any(word in query for word in ['draft', 'write', 'create']):
            score += 0.3
            keywords_matched.append('proposal_draft')
            reasoning_parts.append("Proposal draft pattern detected")
        
        # Cap score at 1.0
        score = min(score, 1.0)
        
        return IntentResult(
            intent="document_query" if score >= 0.4 else "",  # Lower threshold
            confidence=score,
            keywords_matched=keywords_matched,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No document query patterns"
        )
    
    def _fallback_classification(self, query: str) -> IntentResult:
        """Fallback classification logic"""
        
        # Simple keyword-based fallback
        if any(word in query for word in ['revenue', 'total', 'count', 'sales', 'deals']):
            return IntentResult(
                intent="data_query",
                confidence=0.6,
                keywords_matched=['fallback_data_keyword'],
                reasoning="Fallback: Contains data-related keywords"
            )
        
        elif any(word in query for word in ['how to', 'what is', 'help', 'guide']):
            return IntentResult(
                intent="document_query",
                confidence=0.6,
                keywords_matched=['fallback_document_keyword'],
                reasoning="Fallback: Contains knowledge-seeking keywords"
            )
        
        else:
            return IntentResult(
                intent="general",
                confidence=0.4,
                keywords_matched=[],
                reasoning="Fallback: No clear intent detected"
            )

# Example usage and testing
if __name__ == "__main__":
    classifier = IntentClassifier()
    
    test_queries = [
        "What is total revenue from closed won deals?",
        "Compare quarterly revenue growth across industries",
        "How to write a sales proposal?",
        "Show me all deals in negotiation stage",
        "Analyze sales performance for last 2 quarters",
        "What are best practices for handling objections?"
    ]
    
    print("🎯 INTENT CLASSIFICATION TEST RESULTS")
    print("=" * 60)
    
    for query in test_queries:
        result = classifier.classify_intent(query)
        print(f"\n📝 Query: {query}")
        print(f"🎯 Intent: {result.intent}")
        print(f"📊 Confidence: {result.confidence:.2f}")
        print(f"🔑 Keywords: {result.keywords_matched}")
        print(f"💭 Reasoning: {result.reasoning}")
        print("-" * 40)
