"""
SQL Agent for Natural Language to SQL Conversion

Converts natural language sales questions into safe SQL queries,
executes them on the CRM database, and returns structured results.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
from src.database.database_manager import DatabaseManager


class SQLAgent:
    """Agent for converting natural language to SQL and executing queries"""
    
    def __init__(self, database_manager: DatabaseManager, llm_client=None):
        """Initialize SQL Agent"""
        self.db_manager = database_manager
        self.llm_client = llm_client
        self.schema_info = None
        self._load_schema()
        
        # Business threshold definitions for vague queries
        self.business_thresholds = {
            "high_value": {
                "value_threshold": 800000,
                "percentile_threshold": 0.75,
                "description": "High value deals (>$800K or top 25%)"
            },
            "low_probability": {
                "probability_threshold": 40,
                "description": "Low probability deals (<40%)"
            },
            "at_risk": {
                "probability_threshold": 50,
                "days_threshold": 30,
                "description": "At-risk deals (low probability + old)"
            },
            "needs_attention": {
                "probability_threshold": 60,
                "days_threshold": 14,
                "description": "Deals needing attention (moderate probability + recent)"
            },
            "stalled": {
                "days_threshold": 60,
                "description": "Stalled deals (no recent activity)"
            }
        }
        
        # Vague query patterns
        self.vague_patterns = {
            r'\b(high value|high-value)\b': "high_value",
            r'\b(low probability|low-probability|low prob)\b': "low_probability",
            r'\b(at risk|at-risk)\b': "at_risk",
            r'\b(needs attention|need attention)\b': "needs_attention",
            r'\b(stalled|stuck|inactive)\b': "stalled"
        }
        self.entity_mappings = {
            "customers": "customers",
            "customer": "customers", 
            "clients": "customers",
            "client": "customers",
            "deals": "deals",
            "deal": "deals",
            "opportunities": "deals",
            "opportunity": "deals",
            "sales": "deals",
            "revenue": "deals",
            "earnings": "deals",
            "money": "deals",
            "income": "deals",
            "profit": "deals",
            "turnover": "deals",
            "deal value": "deals",
            "total deal value": "deals",
            "products": "products",
            "product": "products",
            "activities": "activities",
            "activity": "activities",
            "tasks": "activities",
            "task": "activities"
        }
        
        self.column_mappings = {
            "revenue": "annual_revenue",
            "income": "annual_revenue",
            "sales": "value",
            "value": "value",
            "amount": "value",
            "price": "unit_price",
            "cost": "cost",
            "margin": "margin_percent",
            "probability": "probability",
            "stage": "stage",
            "status": "stage",
            "industry": "industry",
            "size": "company_size",
            "owner": "account_owner",
            "rep": "account_owner",
            "date": "created_date",
            "created": "created_date",
            "modified": "last_modified_date",
            "close": "expected_close_date"
        }
        
        self.aggregation_patterns = {
            "total": "SUM",
            "sum": "SUM", 
            "average": "AVG",
            "avg": "AVG",
            "mean": "AVG",
            "count": "COUNT",
            "number": "COUNT",
            "how many": "COUNT",
            "maximum": "MAX",
            "max": "MAX",
            "minimum": "MIN",
            "min": "MIN"
        }
    
    def _detect_vague_query(self, query: str) -> Optional[str]:
        """Detect if query contains vague business terms and return the business concept"""
        query_lower = query.lower()
        
        for pattern, concept in self.vague_patterns.items():
            if re.search(pattern, query_lower):
                return concept
        
        return None
    
    def _get_business_threshold_sql(self, concept: str) -> Dict[str, Any]:
        """Generate SQL conditions for business concept"""
        threshold_info = self.business_thresholds[concept]
        sql_conditions = []
        explanation_parts = []
        
        if concept == "high_value":
            # Get actual percentile threshold from database
            percentile_query = """
                SELECT value as threshold_value 
                FROM deals 
                WHERE value IS NOT NULL 
                ORDER BY value DESC 
                LIMIT 1 OFFSET (SELECT COUNT(*) * 3/4 FROM deals WHERE value IS NOT NULL)
            """
            
            try:
                result = self.db_manager.execute_query(percentile_query)
                if result and len(result) > 0:
                    percentile_threshold = result[0]['threshold_value']
                    sql_conditions.append(f"value >= {percentile_threshold}")
                    explanation_parts.append(f"value >= ${percentile_threshold:,.0f} (top 25% percentile)")
                else:
                    # Fallback to fixed threshold
                    sql_conditions.append(f"value >= {threshold_info['value_threshold']}")
                    explanation_parts.append(f"value >= ${threshold_info['value_threshold']:,.0f}")
            except:
                sql_conditions.append(f"value >= {threshold_info['value_threshold']}")
                explanation_parts.append(f"value >= ${threshold_info['value_threshold']:,.0f}")
        
        elif concept == "low_probability":
            sql_conditions.append(f"probability < {threshold_info['probability_threshold']}")
            explanation_parts.append(f"probability < {threshold_info['probability_threshold']}%")
        
        elif concept == "at_risk":
            sql_conditions.append(f"probability < {threshold_info['probability_threshold']}")
            explanation_parts.append(f"probability < {threshold_info['probability_threshold']}%")
            
            # Add age condition (days since last modified)
            sql_conditions.append(f"julianday('now') - julianday(last_modified_date) > {threshold_info['days_threshold']}")
            explanation_parts.append(f"no activity for >{threshold_info['days_threshold']} days")
        
        elif concept == "needs_attention":
            sql_conditions.append(f"probability < {threshold_info['probability_threshold']}")
            explanation_parts.append(f"probability < {threshold_info['probability_threshold']}%")
            
            # Recent activity condition
            sql_conditions.append(f"julianday('now') - julianday(last_modified_date) <= {threshold_info['days_threshold']}")
            explanation_parts.append(f"recent activity (<= {threshold_info['days_threshold']} days)")
        
        elif concept == "stalled":
            sql_conditions.append(f"julianday('now') - julianday(last_modified_date) > {threshold_info['days_threshold']}")
            explanation_parts.append(f"no activity for >{threshold_info['days_threshold']} days")
        
        return {
            "sql_conditions": sql_conditions,
            "explanation": f"{threshold_info['description']}: {' AND '.join(explanation_parts)}",
            "concept": concept,
            "description": threshold_info["description"]
        }
    
    def _load_schema(self):
        """Load database schema information"""
        try:
            self.schema_info = self.db_manager.get_schema_info()
            logger.info("Database schema loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            self.schema_info = {}
    
    def natural_language_to_sql(self, question: str) -> Tuple[str, str]:
        """Convert natural language question to SQL query"""
        logger.info(f"=== DEBUG: Converting question to SQL: {question} ===")
        
        question_lower = question.lower()
        
        # Check for time-based analytics queries FIRST
        # Identify entity for time analytics
        entity = self._identify_entity(question)
        if entity:
            time_analytics_query = self._build_time_analytics_query(question, entity)
            if time_analytics_query:
                logger.info(f"=== DEBUG: Using time analytics SQL builder for entity: {entity} ===")
                return time_analytics_query, "Time-based analytics query generated"
        
        logger.info(f"=== DEBUG: Time analytics check failed, trying rule-based conversion ===")
        
        # Try rule-based approach
        sql_query = self._rule_based_conversion(question_lower)
        
        if sql_query:
            logger.info(f"=== DEBUG: Rule-based conversion succeeded ===")
            explanation = self._generate_explanation(question, sql_query)
            return sql_query, explanation
        
        logger.info(f"=== DEBUG: Rule-based failed, trying LLM-based ===")
        
        # If rule-based fails, try LLM-based approach
        if self.llm_client:
            try:
                sql_query, explanation = self._llm_based_conversion(question)
                logger.info(f"=== DEBUG: LLM-based conversion succeeded ===")
                return sql_query, explanation
            except Exception as e:
                logger.error(f"LLM-based conversion failed: {e}")
        
        logger.info(f"=== DEBUG: All conversion methods failed ===")
        # Fallback response
        return None, "Unable to convert question to SQL. Please rephrase your question."
    
    def _rule_based_conversion(self, question: str) -> Optional[str]:
        """Rule-based natural language to SQL conversion with confidence scoring and analytics support"""
        logger.info(f"Attempting rule-based conversion for: {question}")
        
        # Identify the main entity
        entity = self._identify_entity(question)
        if not entity:
            logger.info("No entity identified, returning None")
            return None
        
        # Check for comparison patterns first
        comparison_pattern = self._identify_comparison_pattern(question)
        
        # If it's a comparison query, use special handling
        if comparison_pattern:
            sql_query = self._build_comparison_query(question, entity, comparison_pattern)
            if sql_query:
                logger.info(f"Generated comparison SQL: {sql_query}")
                return sql_query
        
        # Check for aggregation
        aggregation = self._identify_aggregation(question)
        
        # Identify grouping column for analytics (but not for simple "how many" queries)
        if "how many" not in question.lower():
            grouping_column = self._identify_grouping_column(question, entity)
        else:
            grouping_column = None
        
        # Identify multiple metrics for analytics
        analytics_metrics = self._identify_analytics_metrics(question)
        
        # If we have analytics metrics but no grouping, try to infer grouping
        if analytics_metrics and not grouping_column:
            # Default grouping for common analytics patterns (but only for aggregation queries)
            if aggregation and ('rep' in question.lower() or 'owner' in question.lower()):
                grouping_column = 'deal_owner'
            elif aggregation and 'industry' in question.lower():
                grouping_column = 'industry'
            elif aggregation and 'stage' in question.lower():
                grouping_column = 'stage'
        
        # Identify conditions/filters
        conditions = self._identify_conditions(question, entity)
        
        # Identify ordering
        order_by = self._identify_ordering(question)
        
        # Identify limit
        limit = self._identify_limit(question)
        
        # Calculate confidence score (enhanced for analytics)
        confidence = self._calculate_confidence(question, entity, conditions, aggregation, order_by, limit, grouping_column, analytics_metrics)
        logger.info(f"Rule-based confidence score: {confidence}")
        
        # If confidence is low, try LLM fallback with better error handling
        if confidence < 0.6:
            logger.info(f"Low confidence ({confidence}), attempting LLM fallback")
            try:
                llm_sql = self._llm_fallback(question)
                if llm_sql:
                    logger.info(f"LLM fallback successful: {llm_sql}")
                    return llm_sql
                else:
                    logger.warning("LLM fallback returned None")
                    # For simple data queries, try basic SELECT as last resort
                    if entity and not aggregation and not conditions:
                        basic_sql = f"SELECT * FROM {entity} LIMIT 10"
                        logger.info(f"Using basic fallback SQL: {basic_sql}")
                        return basic_sql
                    return None
            except Exception as e:
                logger.error(f"LLM fallback failed: {e}")
                return None
        
        # Build SQL query with enhanced analytics support (main execution path)
        logger.info(f"=== DEBUG: Building SQL with entity='{entity}', aggregation='{aggregation}', conditions={conditions}, order_by='{order_by}', limit={limit}, grouping_column='{grouping_column}' ===")
        sql_query = self._build_sql_query(
            entity=entity,
            aggregation=aggregation,
            conditions=conditions,
            order_by=order_by,
            limit=limit,
            grouping_column=grouping_column,
            analytics_metrics=analytics_metrics
        )
        
        logger.info(f"Generated SQL: {sql_query}")
        return sql_query
    
    def _llm_fallback(self, question: str) -> Optional[str]:
        """Fallback LLM-based SQL generation when rule-based conversion fails"""
        try:
            # Simple heuristic-based fallback for common patterns
            question_lower = question.lower()
            
            # Handle "show me all X" patterns
            if "show me all" in question_lower:
                if "deals" in question_lower:
                    return "SELECT * FROM deals LIMIT 10"
                elif "customers" in question_lower:
                    return "SELECT * FROM customers LIMIT 10"
                elif "activities" in question_lower:
                    return "SELECT * FROM activities LIMIT 10"
                elif "products" in question_lower:
                    return "SELECT * FROM products LIMIT 10"
            
            # Handle "analyze X" patterns
            if "analyze" in question_lower:
                if "sales" in question_lower or "deals" in question_lower:
                    if "rep" in question_lower or "owner" in question_lower:
                        return "SELECT deal_owner, COUNT(*) as deal_count, SUM(value) as total_value, AVG(value) as avg_value FROM deals GROUP BY deal_owner ORDER BY total_value DESC"
                    else:
                        return "SELECT stage, COUNT(*) as count, SUM(value) as total_value FROM deals GROUP BY stage ORDER BY total_value DESC"
                elif "customers" in question_lower:
                    return "SELECT * FROM customers LIMIT 10"
                elif "activities" in question_lower:
                    return "SELECT * FROM activities LIMIT 10"
                elif "products" in question_lower:
                    return "SELECT * FROM products LIMIT 10"
            
            # Handle "recent X" patterns
            if "recent" in question_lower:
                if "activities" in question_lower:
                    return "SELECT * FROM activities ORDER BY activity_date DESC LIMIT 10"
                elif "deals" in question_lower:
                    return "SELECT * FROM deals ORDER BY created_date DESC LIMIT 10"
                elif "customers" in question_lower:
                    return "SELECT * FROM customers ORDER BY created_date DESC LIMIT 10"
                elif "products" in question_lower:
                    return "SELECT * FROM products ORDER BY created_date DESC LIMIT 10"
            
            # Handle "compare across industries" pattern
            if "compare" in question_lower and ("industry" in question_lower or "industries" in question_lower):
                return """
                    SELECT c.industry, 
                           COUNT(d.deal_id) as deal_count,
                           SUM(d.value) as total_value,
                           AVG(d.value) as avg_value,
                           MAX(d.value) as max_value,
                           MIN(d.value) as min_value
                    FROM deals d
                    JOIN customers c ON d.customer_id = c.customer_id
                    GROUP BY c.industry
                    ORDER BY total_value DESC
                """
            
            # Handle "list X" patterns
            if "list" in question_lower:
                if "deals" in question_lower:
                    return "SELECT * FROM deals LIMIT 10"
                elif "customers" in question_lower:
                    return "SELECT * FROM customers LIMIT 10"
                elif "activities" in question_lower:
                    return "SELECT * FROM activities LIMIT 10"
                elif "products" in question_lower:
                    return "SELECT * FROM products LIMIT 10"
            
            # Debug: Show distinct owner values in activities
            if "show owners" in question_lower or "debug owners" in question_lower:
                return "SELECT DISTINCT owner FROM activities ORDER BY owner"
            
            # Debug: Show sample activity data with owners
            if "sample activities" in question_lower:
                return "SELECT activity_id, owner, activity_date, subject FROM activities ORDER BY activity_date DESC LIMIT 5"
            
            # Handle simple count queries
            if "how many" in question_lower:
                if "deals" in question_lower:
                    return "SELECT COUNT(*) as deal_count FROM deals"
                elif "customers" in question_lower:
                    return "SELECT COUNT(*) as customer_count FROM customers"
                elif "activities" in question_lower:
                    return "SELECT COUNT(*) as activity_count FROM activities"
                elif "products" in question_lower:
                    return "SELECT COUNT(*) as product_count FROM products"
            
            # Default fallback
            logger.warning(f"No pattern matched for LLM fallback: {question}")
            return None
            
        except Exception as e:
            logger.error(f"Error in _llm_fallback: {e}")
            return None
    
    def _calculate_confidence(self, question: str, entity: str, conditions: List[str], 
                             aggregation: Optional[str], order_by: Optional[str], limit: Optional[str],
                             grouping_column: Optional[str] = None, analytics_metrics: Optional[List[str]] = None) -> float:
        """Calculate confidence score for rule-based SQL generation with analytics support"""
        confidence = 0.0
        
        # Base confidence for entity identification
        if entity:
            confidence += 0.3
        
        # Add confidence for recognized patterns
        if aggregation:
            confidence += 0.2
        
        # Add confidence for analytics patterns (higher confidence)
        if analytics_metrics and len(analytics_metrics) > 1:
            confidence += 0.3  # Multi-metric analytics
        elif analytics_metrics:
            confidence += 0.2  # Single metric analytics
        
        # Add confidence for grouping (analytics queries)
        if grouping_column:
            confidence += 0.2
        
        # Add confidence for conditions (but penalize if too complex)
        if conditions:
            if len(conditions) <= 2:
                confidence += 0.3
            elif len(conditions) <= 4:
                confidence += 0.2
            else:
                confidence += 0.1  # Too many conditions might indicate complexity
        
        # Add confidence for ordering
        if order_by:
            confidence += 0.1
        
        # Add confidence for limit
        if limit:
            confidence += 0.1
        
        # Boost confidence for clear analytics patterns
        analytics_indicators = ['top', 'best', 'highest', 'ranking', 'leaderboard', 'performance']
        if any(indicator in question.lower() for indicator in analytics_indicators):
            confidence += 0.2
        
        # Boost confidence for simple aggregation queries
        aggregation_indicators = ['how many', 'count', 'total', 'sum', 'average', 'avg', 'maximum', 'max', 'minimum', 'min']
        if any(indicator in question.lower() for indicator in aggregation_indicators):
            confidence += 0.3
        
        # Boost confidence for temporal queries (recent, latest, etc.)
        temporal_indicators = ['recent', 'latest', 'latest', 'newest', 'today', 'yesterday', 'last week', 'last month']
        if any(indicator in question.lower() for indicator in temporal_indicators):
            confidence += 0.3
        
        # Boost confidence for listing queries
        listing_indicators = ['list', 'show', 'display', 'get', 'find', 'search']
        if any(indicator in question.lower() for indicator in listing_indicators):
            confidence += 0.2
        
        # Penalize for complex language patterns
        complex_indicators = ['between', 'except', 'not', 'null', 'case', 'when', 'subquery', 'join']
        if any(indicator in question.lower() for indicator in complex_indicators):
            confidence -= 0.3
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))
    
    def _identify_entity(self, question: str) -> Optional[str]:
        """Identify the main table/entity from the question"""
        question_lower = question.lower()
        
        # Check for activities first (highest priority)
        activity_terms = ["activities", "activity", "tasks", "task"]
        if any(term in question_lower for term in activity_terms):
            logger.info(f"=== DEBUG: Activity term detected, defaulting to 'activities' entity ===")
            return "activities"
        
        # Check for financial terms next (revenue, earnings, money, etc.)
        financial_terms = ["revenue", "earnings", "money", "income", "profit", "turnover", "deal value"]
        if any(term in question_lower for term in financial_terms):
            logger.info(f"=== DEBUG: Financial term detected, defaulting to 'deals' entity ===")
            return "deals"
        
        # Check for sales last (most ambiguous)
        if "sales" in question_lower and "rep" in question_lower:
            logger.info(f"=== DEBUG: Sales rep detected, checking context ===")
            # If it's about sales reps but also mentions activities, prioritize activities
            if any(term in question_lower for term in activity_terms):
                return "activities"
            else:
                return "deals"
        
        # Prioritize longer, more specific matches first
        # Order matters: check for activities before sales, deals before sales, etc.
        priority_entities = [
            ("activities", "activities"),
            ("activity", "activities"),
            ("tasks", "activities"), 
            ("task", "activities"),
            ("deals", "deals"),
            ("deal", "deals"),
            ("opportunities", "deals"),
            ("opportunity", "deals"),
            ("customers", "customers"),
            ("customer", "customers"),
            ("clients", "customers"),
            ("client", "customers"),
            ("products", "products"),
            ("product", "products"),
            # Put sales last as it's ambiguous
            ("sales", "deals")
        ]
        
        for keyword, table in priority_entities:
            if keyword in question_lower:
                logger.info(f"=== DEBUG: Identified entity '{table}' from keyword '{keyword}' ===")
                return table
        
        logger.info(f"=== DEBUG: No entity identified for question: {question} ===")
        return None
    
    def _identify_comparison_pattern(self, question: str) -> Optional[str]:
        """Identify comparison patterns in the question"""
        question_lower = question.lower()
        
        # Revenue comparison patterns
        comparison_patterns = [
            (r'compared to (?:previous|last)', 'period_comparison'),
            (r'versus (?:previous|last)', 'period_comparison'),
            (r'vs (?:previous|last)', 'period_comparison'),
            (r'if (?:revenue|sales|value) (?:dropped|decreased|fell)', 'drop_detection'),
            (r'compared to (?:\d+\s+months? ago|last \d+\s+months?)', 'period_comparison'),
            (r'previous (?:\d+\s+months?)', 'period_comparison'),
            (r'last (?:\d+\s+months?) (?:and|vs|versus) previous', 'period_comparison')
        ]
        
        for pattern, comparison_type in comparison_patterns:
            if re.search(pattern, question_lower):
                return comparison_type
        
        return None
    
    def _build_comparison_query(self, question: str, entity: str, comparison_type: str) -> Optional[str]:
        """Build comparison query for revenue/period comparisons"""
        question_lower = question.lower()
        
        # Extract conditions (stage, etc.)
        conditions = self._identify_conditions(question, entity)
        
        # Determine date column based on context
        date_column = 'created_date'  # default
        if any('closed' in cond.lower() for cond in conditions):
            date_column = 'actual_close_date'
        elif 'expected' in question_lower:
            date_column = 'expected_close_date'
        
        # Build WHERE clause
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # Build comparison query based on type
        if comparison_type == 'period_comparison':
            # Check for specific period mentions
            last_6_match = re.search(r'last (\d+)\s+months?', question_lower)
            previous_match = re.search(r'previous (\d+)\s+months?', question_lower)
            
            # Default to 6 months if not specified
            recent_months = 6
            if last_6_match:
                recent_months = int(last_6_match.group(1))
            
            # Build filtered aggregation query
            sql_query = f"""SELECT
    SUM(CASE 
        WHEN {date_column} >= DATE('now', '-{recent_months} month') 
        THEN value ELSE 0 END) as last_{recent_months}_months,
    
    SUM(CASE 
        WHEN {date_column} BETWEEN DATE('now', '-{recent_months * 2} month') AND DATE('now', '-{recent_months} month') 
        THEN value ELSE 0 END) as previous_{recent_months}_months
FROM {entity}
{where_clause}"""
            
        elif comparison_type == 'drop_detection':
            # Similar to period comparison but focused on drop detection
            sql_query = f"""SELECT
    SUM(CASE 
        WHEN {date_column} >= DATE('now', '-6 month') 
        THEN value ELSE 0 END) as last_6_months,
    
    SUM(CASE 
        WHEN {date_column} BETWEEN DATE('now', '-12 month') AND DATE('now', '-6 month') 
        THEN value ELSE 0 END) as previous_6_months
FROM {entity}
{where_clause}"""
        
        else:
            return None
        
        logger.info(f"Built comparison query for {comparison_type}")
        return sql_query.strip()
    
    def _identify_aggregation(self, question: str) -> Optional[str]:
        """Identify aggregation function from the question"""
        question_lower = question.lower()
        
        # Check for industry comparison patterns
        if 'compare' in question_lower and ('industry' in question_lower or 'industries' in question_lower):
            return 'INDUSTRY_COMPARISON'
        
        for keyword, func in self.aggregation_patterns.items():
            if keyword in question:
                return func
        return None
    
    def _identify_conditions(self, question: str, entity: str) -> List[str]:
        """Identify WHERE conditions from the question"""
        conditions = []
        logger.info(f"Identifying conditions for question: {question}")
        
        # Get table columns
        if entity not in self.schema_info:
            return conditions
        
        columns = [col['name'] for col in self.schema_info[entity]['columns']]
        logger.info(f"Available columns for {entity}: {columns}")
        
        # Extract stage first for smart date column selection - PRIORITY ORDER MATTERS!
        detected_stage = None
        stage_keywords = [
            'closed won', 'closed lost',  # Highest priority - closed deals
            'prospect', 'qualification', 'proposal', 'negotiation'  # Lower priority
        ]
        
        # Special handling for "closed" context - prioritize closed stages
        question_lower = question.lower()
        if 'closed' in question_lower:
            # Look for closed stages first when "closed" is mentioned
            closed_stages = ['closed won', 'closed lost']
            for stage in closed_stages:
                if stage in question_lower and 'stage' in columns:
                    detected_stage = stage.title()
                    conditions.append(f"stage = '{detected_stage}'")
                    logger.info(f"Added stage condition: stage = '{detected_stage}' (closed priority)")
                    break
            
            # If no specific closed stage found, default to 'Closed Won' for revenue/value queries
            if not detected_stage and ('value' in question_lower or 'revenue' in question_lower or 'deal value' in question_lower):
                detected_stage = 'Closed Won'
                conditions.append(f"stage = '{detected_stage}'")
                logger.info(f"Added stage condition: stage = '{detected_stage}' (closed deal value default)")
        
        # If no closed stage detected, check for other stages
        if not detected_stage:
            for stage in stage_keywords:
                if stage in question_lower and 'stage' in columns:
                    detected_stage = stage.title()
                    conditions.append(f"stage = '{detected_stage}'")
                    logger.info(f"Added stage condition: stage = '{detected_stage}'")
                    break
        
        # Probability filters
        prob_patterns = [
            (r'probability\s*(?:above|over|greater than|>)\s*(\d+)', '>'),
            (r'probability\s*(?:below|under|less than|<)\s*(\d+)', '<'),
            (r'probability\s*(\d+)%', '='),
            (r'(\d+)\s*%\s*probability', '='),
            (r'probability\s*(\d+)', '='),
            (r'(\d+)\s*percent\s*probability', '=')
        ]
        
        for pattern, operator in prob_patterns:
            match = re.search(pattern, question)
            if match and 'probability' in columns:
                value = match.group(1)
                conditions.append(f"probability {operator} {value}")
                logger.info(f"Added probability condition: probability {operator} {value}")
                break
        
        # Date range filters with smart column selection
        date_conditions = self._parse_date_conditions(question, detected_stage)
        conditions.extend(date_conditions)
        
        # Industry filter — handle "in the X industry", "industry: X", and "X industry"
        industry_patterns = [
            r'(?:in|from|of)\s+(?:the\s+)?(\w+)\s+industry',   # "in the technology industry"
            r'industry\s*[:\s]\s*([a-zA-Z]+)',                   # "industry: technology"
            r'(\w+)\s+(?:industry|sector)\s+(?:customers?|deals?|clients?)',  # "technology industry customers"
        ]
        for ip in industry_patterns:
            industry_match = re.search(ip, question, re.IGNORECASE)
            if industry_match and 'industry' in columns:
                industry = industry_match.group(1).strip().title()
                conditions.append(f"industry = '{industry}'")
                logger.info(f"Added industry condition: industry = '{industry}'")
                break
        
        # Value filters
        if 'greater than' in question or 'over' in question or '>' in question:
            value_match = re.search(r'(\d+(?:,\d+)*)', question)
            if value_match and 'value' in columns:
                value = value_match.group(1).replace(',', '')
                conditions.append(f"value > {value}")
                logger.info(f"Added value condition: value > {value}")
        
        if 'less than' in question or 'under' in question or '<' in question:
            value_match = re.search(r'(\d+(?:,\d+)*)', question)
            if value_match and 'value' in columns:
                value = value_match.group(1).replace(',', '')
                conditions.append(f"value < {value}")
                logger.info(f"Added value condition: value < {value}")
        
        # Check for owner/rep filters
        owner_patterns = [
            r'(sales\s*rep\s*\d+)',
            r'(rep\s*\d+)',
            r'for\s+(sales\s*rep\s*\d+)',
            r'for\s+(rep\s*\d+)',
            r'(sales\s*rep|rep|owner|account\s*owner)\s*([A-Za-z]+\s*\d+)',
            r'for\s+(sales\s*rep|rep|owner)\s*([A-Za-z]+\s*\d+)'
        ]
        
        for pattern in owner_patterns:
            match = re.search(pattern, question_lower)
            if match:
                # Get the full match for "Sales Rep 1" patterns
                if 'sales rep' in pattern:
                    owner_value = match.group(1).title()  # Full "Sales Rep 1" pattern
                else:
                    owner_value = match.group(1) if len(match.groups()) > 0 else match.group()
                
                if not owner_value:
                    continue
                
                # For activities, ensure we use right column name with case-insensitive matching
                if entity == 'activities':
                    conditions.append(f"LOWER(owner) LIKE LOWER('%{owner_value}%')")
                elif entity == 'deals':
                    conditions.append(f"LOWER(deal_owner) LIKE LOWER('%{owner_value}%')")
                elif entity == 'customers':
                    conditions.append(f"LOWER(account_owner) LIKE LOWER('%{owner_value}%')")
                logger.info(f"Found owner condition: {conditions[-1]}")
                break
        
        logger.info(f"Final conditions: {conditions}")
        return conditions
    
    def _parse_date_conditions(self, question: str, stage: Optional[str] = None) -> List[str]:
        """Parse date-related conditions with smart column selection"""
        conditions = []
        question_lower = question.lower()
        
        # Determine which date column to use based on deal stage and context
        if stage and 'closed' in stage.lower():
            date_column = 'actual_close_date'
        elif 'closed' in question_lower and ('deal' in question_lower or 'revenue' in question_lower):
            # When asking about closed deals/revenue, use actual_close_date even if stage not explicitly mentioned
            date_column = 'actual_close_date'
        elif 'expected' in question_lower:
            date_column = 'expected_close_date'
        else:
            # Default to created_date for general queries
            date_column = 'created_date'
        
        logger.info(f"Using date column: {date_column} for stage: {stage}")
        
        # Next X days
        next_days_match = re.search(r'next (\d+) days?', question_lower)
        if next_days_match:
            days = next_days_match.group(1)
            conditions.append(f"{date_column} <= DATE('now', '+{days} day')")
            logger.info(f"Added date condition: {date_column} <= DATE('now', '+{days} day')")
        
        # Last X days
        last_days_match = re.search(r'(?:last|past) (\d+) days?', question_lower)
        if last_days_match:
            days = last_days_match.group(1)
            conditions.append(f"{date_column} >= DATE('now', '-{days} day')")
            logger.info(f"Added date condition: {date_column} >= DATE('now', '-{days} day')")
        
        # Last X months
        last_months_match = re.search(r'(?:last|past) (\d+) months?', question_lower)
        if last_months_match:
            months = last_months_match.group(1)
            conditions.append(f"{date_column} >= DATE('now', '-{months} month')")
            logger.info(f"Added date condition: {date_column} >= DATE('now', '-{months} month')")
        
        # Last X weeks
        last_weeks_match = re.search(r'(?:last|past) (\d+) weeks?', question_lower)
        if last_weeks_match:
            weeks = last_weeks_match.group(1)
            conditions.append(f"{date_column} >= DATE('now', '-{weeks} week')")
            logger.info(f"Added date condition: {date_column} >= DATE('now', '-{weeks} week')")
        
        # Last quarter
        if 'last quarter' in question_lower:
            conditions.append(f"{date_column} >= DATE('now', 'start of month', '-3 month')")
            conditions.append(f"{date_column} < DATE('now', 'start of month')")
            logger.info(f"Added date condition: {date_column} in last quarter")
        
        # Last X quarters - NEW
        last_quarters_match = re.search(r'(?:last|past) (\d+) quarters?', question_lower)
        if last_quarters_match:
            num_quarters = int(last_quarters_match.group(1))
            conditions.append(f"{date_column} >= DATE('now', 'start of month', '-{num_quarters * 3} month')")
            logger.info(f"Added date condition: {date_column} in last {num_quarters} quarters")
        
        # Last year
        if 'last year' in question_lower:
            conditions.append(f"{date_column} >= DATE('now', 'start of year', '-1 year')")
            conditions.append(f"{date_column} < DATE('now', 'start of year')")
            logger.info(f"Added date condition: {date_column} in last year")
        
        # Next month
        if 'next month' in question_lower:
            conditions.append(f"{date_column} <= DATE('now', 'start of month', '+1 month', '-1 day')")
            logger.info(f"Added date condition: {date_column} <= next month end")
        
        # Last month
        if 'last month' in question_lower:
            conditions.append(f"{date_column} >= DATE('now', 'start of month', '-1 month')")
            conditions.append(f"{date_column} < DATE('now', 'start of month')")
            logger.info(f"Added date condition: {date_column} in last month")
        
        # This month
        if 'this month' in question_lower:
            conditions.append(f"{date_column} >= DATE('now', 'start of month')")
            conditions.append(f"{date_column} <= DATE('now', 'start of month', '+1 month', '-1 day')")
            logger.info(f"Added date condition: {date_column} this month")
        
        # Next quarter
        if 'next quarter' in question_lower:
            conditions.append(f"{date_column} <= DATE('now', 'start of month', '+3 month', '-1 day')")
            logger.info(f"Added date condition: {date_column} <= next quarter end")
        
        # This quarter
        if 'this quarter' in question_lower:
            conditions.append(f"{date_column} >= DATE('now', 'start of month', '-3 months')")
            conditions.append(f"{date_column} <= DATE('now', 'start of month', '+1 month', '-1 day')")
            logger.info(f"Added date condition: {date_column} this quarter")
        
        # This year
        if 'this year' in question_lower:
            conditions.append(f"{date_column} >= DATE('now', 'start of year')")
            conditions.append(f"{date_column} <= DATE('now', 'start of year', '+1 year', '-1 day')")
            logger.info(f"Added date condition: {date_column} this year")
        
        return conditions
    
    def _identify_grouping_column(self, question: str, entity: str) -> Optional[str]:
        """Identify grouping column for analytics queries"""
        question_lower = question.lower()
        
        # Get available columns
        if entity not in self.schema_info:
            return None
        
        columns = [col['name'] for col in self.schema_info[entity]['columns']]
        
        # Grouping patterns
        grouping_patterns = [
            (r'\b(per|by|for each)\s+(sales\s+rep|rep|owner)', 'deal_owner'),
            (r'\b(per|by|for each)\s+(customer|client)', 'customer_id'),
            (r'\b(per|by|for each)\s+(industry)', 'industry'),
            (r'\b(per|by|for each)\s+(stage)', 'stage'),
            (r'\b(per|by|for each)\s+(region)', 'region'),
            (r'\b(per|by|for each)\s+(team)', 'team'),
            (r'\bsales\s+(rep|representative)', 'deal_owner'),
            (r'\bowner', 'deal_owner'),
            (r'\bcustomer', 'customer_id'),
            (r'\bindustry', 'industry'),
            (r'\bstage', 'stage')
        ]
        
        for pattern, column in grouping_patterns:
            if re.search(pattern, question_lower) and column in columns:
                return column
        
        return None
    
    def _identify_analytics_metrics(self, question: str) -> List[str]:
        """Identify multiple metrics for analytics queries"""
        question_lower = question.lower()
        metrics = []
        
        # Check for multiple metrics
        if 'along with' in question_lower or 'with number of' in question_lower or 'and count' in question_lower:
            if 'count' in question_lower or 'number' in question_lower:
                metrics.append('COUNT')
            if 'sum' in question_lower or 'total' in question_lower or 'value' in question_lower:
                metrics.append('SUM')
            if 'average' in question_lower or 'avg' in question_lower:
                metrics.append('AVG')
        
        return metrics
    
    def _identify_ordering(self, question: str) -> Optional[str]:
        """Identify ORDER BY clause from question"""
        question_lower = question.lower()
        
        # Check for temporal ordering (recent, latest, etc.) - PRIORITY for activities
        if any(word in question_lower for word in ['recent', 'latest', 'newest']):
            # Use appropriate date column based on entity context
            if 'activities' in question_lower or 'activity' in question_lower:
                return 'activity_date DESC'  # FIXED: Use activity_date for activities
            elif 'deals' in question_lower or 'deal' in question_lower:
                return 'created_date DESC'
            elif 'customers' in question_lower or 'customer' in question_lower:
                return 'created_date DESC'
            else:
                return 'created_date DESC'
        
        # Check for ascending order
        if any(word in question_lower for word in ['oldest', 'earliest', 'first']):
            if 'activities' in question_lower or 'activity' in question_lower:
                return 'activity_date ASC'
            elif 'deal' in question_lower or 'deals' in question_lower:
                return 'created_date ASC'
            elif 'customer' in question_lower or 'customers' in question_lower:
                return 'created_date ASC'
            else:
                return 'created_date ASC'
        
        # Check for value-based ordering
        if any(word in question_lower for word in ['highest', 'largest', 'most', 'top']):
            return 'value DESC'
        
        if any(word in question_lower for word in ['lowest', 'smallest', 'least']):
            return 'value ASC'
        
        return None
    
    def _identify_limit(self, question: str) -> Optional[int]:
        """Identify LIMIT clause from question"""
        question_lower = question.lower()
        
        # Explicit number patterns
        number_patterns = [
            r'top\s+(\d+)',
            r'first\s+(\d+)',
            r'latest\s+(\d+)',
            r'recent\s+(\d+)',
            r'show\s+\w+\s+(\d+)',
            r'list\s+\w+\s+(\d+)'
        ]
        
        for pattern in number_patterns:
            match = re.search(pattern, question_lower)
            if match:
                return int(match.group(1))
        
        # Default limits for certain question types
        if 'top' in question or 'best' in question:
            return 10
        elif 'recent' in question or 'latest' in question:
            return 10  # FIXED: Increased from 5 to 10 for better activity visibility
        elif any(keyword in question_lower for keyword in ['highest', 'lowest', 'maximum', 'minimum', 'most', 'least']):
            return 1  # For ranking questions, return only top/bottom result
        
        return None
    
    def _build_sql_query(self, entity: str, aggregation: Optional[str], 
                        conditions: List[str], order_by: Optional[str], 
                        limit: Optional[int], grouping_column: Optional[str] = None,
                        analytics_metrics: Optional[List[str]] = None) -> str:
        """Build SQL query from components with support for GROUP BY and analytics"""
        
        # SELECT clause - Enhanced for analytics
        if aggregation == 'INDUSTRY_COMPARISON':
            # Industry comparison query - join deals with customers to get industry data
            select_clause = """
                SELECT c.industry, 
                       COUNT(d.deal_id) as deal_count,
                       SUM(d.value) as total_value,
                       AVG(d.value) as avg_value,
                       MAX(d.value) as max_value,
                       MIN(d.value) as min_value
                FROM deals d
                JOIN customers c ON d.customer_id = c.customer_id
                """
            grouping_column = "c.industry"
            order_clause = "ORDER BY total_value DESC"
        elif analytics_metrics and grouping_column:
            # Multi-metric analytics query
            select_parts = [f"{grouping_column}"]
            
            for metric in analytics_metrics:
                if metric == 'COUNT':
                    select_parts.append("COUNT(*) as deal_count")
                elif metric == 'SUM':
                    target_column = "value" if entity == "deals" else "annual_revenue"
                    select_parts.append(f"SUM({target_column}) as total_value")
                elif metric == 'AVG':
                    target_column = "value" if entity == "deals" else "annual_revenue"
                    select_parts.append(f"AVG({target_column}) as avg_value")
            
            select_clause = "SELECT " + ", ".join(select_parts)
            
        elif grouping_column and aggregation:
            # Single aggregation with grouping
            if aggregation == "COUNT":
                select_clause = f"SELECT {grouping_column}, COUNT(*) as deal_count"
            elif aggregation == "SUM":
                target_column = "value" if entity == "deals" else "annual_revenue"
                select_clause = f"SELECT {grouping_column}, SUM({target_column}) as total_value"
            elif aggregation == "AVG":
                target_column = "value" if entity == "deals" else "annual_revenue"
                select_clause = f"SELECT {grouping_column}, AVG({target_column}) as avg_value"
            else:
                target_column = "value" if entity == "deals" else "annual_revenue"
                select_clause = f"SELECT {grouping_column}, {aggregation}({target_column}) as {aggregation.lower()}_value"
        elif aggregation:
            # Simple aggregation without grouping
            if aggregation == "COUNT":
                select_clause = "SELECT COUNT(*) as total_count"
            else:
                target_column = "value" if entity == "deals" else "annual_revenue"
                select_clause = f"SELECT {aggregation}({target_column}) as {aggregation.lower()}_value"
        else:
            select_clause = "SELECT *"
        
        # FROM clause
        if aggregation == 'INDUSTRY_COMPARISON':
            from_clause = "FROM deals d JOIN customers c ON d.customer_id = c.customer_id"
        else:
            from_clause = f"FROM {entity}"
        
        # WHERE clause
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # GROUP BY clause
        group_by_clause = ""
        if grouping_column:
            group_by_clause = f"GROUP BY {grouping_column}"
        
        # ORDER BY clause - Enhanced for analytics
        order_clause = ""
        if order_by:
            if analytics_metrics and grouping_column:
                # For multi-metric queries, order by the first metric (usually SUM)
                if 'SUM' in analytics_metrics:
                    order_clause = "ORDER BY total_value DESC"
                elif 'COUNT' in analytics_metrics:
                    order_clause = "ORDER BY deal_count DESC"
                elif 'AVG' in analytics_metrics:
                    order_clause = "ORDER BY avg_value DESC"
            elif grouping_column and aggregation:
                # For single aggregation with grouping
                if aggregation == 'SUM':
                    order_clause = "ORDER BY total_value DESC"
                elif aggregation == 'COUNT':
                    order_clause = "ORDER BY deal_count DESC"
                elif aggregation == 'AVG':
                    order_clause = "ORDER BY avg_value DESC"
                else:
                    # order_by already contains the full ordering string
                    order_clause = f"ORDER BY {order_by}"
            else:
                # Standard ordering - order_by already contains the full ordering string
                order_clause = f"ORDER BY {order_by}"
        
        # LIMIT clause
        limit_clause = ""
        if limit:
            limit_clause = f"LIMIT {limit}"
        
        # Combine all clauses
        query_parts = [select_clause, from_clause]
        if where_clause:
            query_parts.append(where_clause)
        if group_by_clause:
            query_parts.append(group_by_clause)
        if order_clause:
            query_parts.append(order_clause)
        if limit_clause:
            query_parts.append(limit_clause)
        
        return " ".join(query_parts)
    
    def _llm_based_conversion(self, question: str) -> Tuple[str, str]:
        """LLM-based natural language to SQL conversion"""
        schema_text = self._format_schema_for_llm()
        
        prompt = (
            f"Database Schema:\n{schema_text}\n\n"
            f"Question: {question}\n\n"
            "Generate ONLY the SQL query, nothing else. No markdown, no explanation."
        )
        system_prompt = (
            "You are a SQL expert. Convert natural language to safe SELECT-only SQL. "
            "Rules: only SELECT queries, use exact column/table names from the schema, "
            "add LIMIT when appropriate, never use DROP/DELETE/UPDATE/INSERT."
        )
        
        try:
            sql_query = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=500,
            )
            
            sql_query = re.sub(r'```sql\n?', '', sql_query)
            sql_query = re.sub(r'\n?```', '', sql_query)
            sql_query = sql_query.strip()
            
            explanation = f"Generated SQL query using LLM: {sql_query}"
            return sql_query, explanation
            
        except Exception as e:
            logger.error(f"LLM conversion error: {e}")
            return None, "LLM-based conversion failed"
    
    def _format_schema_for_llm(self) -> str:
        """Format database schema for LLM prompt"""
        schema_text = ""
        for table_name, table_info in self.schema_info.items():
            schema_text += f"\nTable: {table_name}\n"
            schema_text += "Columns:\n"
            for col in table_info['columns']:
                schema_text += f"  - {col['name']} ({col['type']})\n"
        
        return schema_text
    
    def _generate_explanation(self, question: str, sql_query: str) -> str:
        """Generate explanation for the SQL query"""
        explanation = f"Converted '{question}' to SQL: {sql_query}"
        
        # Add more detailed explanation based on query components
        if "WHERE" in sql_query:
            explanation += "\n- Applied filters to narrow results"
        if "ORDER BY" in sql_query:
            explanation += "\n- Sorted results for better relevance"
        if "LIMIT" in sql_query:
            explanation += "\n- Limited results to most relevant entries"
        if any(func in sql_query for func in ["SUM", "COUNT", "AVG", "MAX", "MIN"]):
            explanation += "\n- Applied aggregation to summarize data"
        
        return explanation
    
    def _is_scalar_aggregation(self, sql_query: str) -> bool:
        """Detect if SQL query should return a single scalar value"""
        sql_upper = sql_query.upper()
        
        # Simple COUNT(*) without GROUP BY is scalar
        if 'COUNT(*)' in sql_upper and 'GROUP BY' not in sql_upper:
            return True
        
        # Single aggregation function without GROUP BY is scalar
        aggregation_functions = ['SUM(', 'AVG(', 'MIN(', 'MAX(']
        has_aggregation = any(func in sql_upper for func in aggregation_functions)
        has_group_by = 'GROUP BY' in sql_upper
        
        # More flexible: Check for any aggregation function in query
        has_any_aggregation = any(func in sql_upper for func in aggregation_functions)
        
        # Allow GROUP BY if it has aggregation functions OR if it's a simple data retrieval query
        if has_any_aggregation or ('GROUP BY' in sql_upper and 
            ('ORDER BY' in sql_upper or 'LIMIT' in sql_upper or 
             any(keyword in sql_upper for keyword in ['SELECT', 'FROM', 'WHERE']))):
            return True
        
        return has_aggregation and not has_group_by
    
    def _generate_aggregation_answer(self, sql_query: str, results: List[Dict[str, Any]]) -> str:
        """Generate direct natural language answer for aggregation queries"""
        if not results or len(results) == 0:
            return "No results found."
        
        # Get the first (and only) result
        result = results[0]
        
        # Detect aggregation type and generate appropriate answer
        sql_upper = sql_query.upper()
        
        if 'COUNT(' in sql_upper:
            if 'COUNT(*)' in sql_upper:
                count_value = list(result.values())[0] if result else 0
                return f"There are {count_value} total records."
            else:
                # Count with specific column
                count_value = list(result.values())[0] if result else 0
                return f"There are {count_value} records matching your criteria."
        
        elif 'SUM(' in sql_upper:
            sum_value = list(result.values())[0] if result else 0
            if 'value' in sql_upper or 'revenue' in sql_upper:
                return f"The total value is ${sum_value:,.0f}."
            else:
                return f"The total sum is {sum_value:,.0f}."
        
        elif 'AVG(' in sql_upper:
            avg_value = list(result.values())[0] if result else 0
            if 'value' in sql_upper or 'revenue' in sql_upper:
                return f"The average value is ${avg_value:,.0f}."
            else:
                return f"The average is {avg_value:,.0f}."
        
        elif 'MAX(' in sql_upper:
            max_value = list(result.values())[0] if result else 0
            if 'value' in sql_upper or 'revenue' in sql_upper:
                return f"The maximum value is ${max_value:,.0f}."
            else:
                return f"The maximum is {max_value:,.0f}."
        
        elif 'MIN(' in sql_upper:
            min_value = list(result.values())[0] if result else 0
            if 'value' in sql_upper or 'revenue' in sql_upper:
                return f"The minimum value is ${min_value:,.0f}."
            else:
                return f"The minimum is {min_value:,.0f}."
        
        # Fallback for other aggregations
        value = list(result.values())[0] if result else 0
        return f"The result is {value}."
    
    def execute_direct_query(self, question: str) -> Dict[str, Any]:
        """Execute query without validation for simple data queries"""
        try:
            # Convert to SQL using existing logic but bypass validation
            sql_query, explanation = self.natural_language_to_sql(question)
            logger.info(f"=== DEBUG: Direct query execution: {sql_query} ===")
            
            # Execute query
            results = self.db_manager.execute_query(sql_query)
            logger.info(f"=== DEBUG: Query executed, returned {len(results) if results else 0} rows ===")
            
            return {
                "success": True,
                "results": results,
                "sql_query": sql_query,
                "explanation": explanation
            }
        except Exception as e:
            logger.error(f"Direct query execution failed: {str(e)}")
            return {
                "success": False,
                "error": "Could not convert question to SQL",
                "explanation": str(e)
            }
    
    def execute_query(self, question: str) -> Dict[str, Any]:
        """Execute natural language query and return results"""
        try:
            logger.info(f"=== DEBUG: Executing query: {question} ===")
            
            # Check for vague business queries first
            vague_concept = self._detect_vague_query(question)
            
            if vague_concept:
                logger.info(f"Detected vague query concept: {vague_concept}")
                return self._execute_vague_query(question, vague_concept)
            
            # Convert to SQL for normal queries
            sql_query, explanation = self.natural_language_to_sql(question)
            logger.info(f"=== DEBUG: Generated SQL: {sql_query} ===")
            
            if not sql_query:
                logger.error("=== DEBUG: SQL generation failed ===")
                return {
                    "success": False,
                    "error": "Could not convert question to SQL",
                    "explanation": explanation
                }
            
            # Validate query safety
            is_safe, safety_message = self.db_manager.validate_query_safety(sql_query)
            if not is_safe:
                logger.error(f"=== DEBUG: Query validation failed: {safety_message} ===")
                return {
                    "success": False,
                    "error": "Query validation failed",
                    "explanation": safety_message
                }
            
            # Execute query
            results = self.db_manager.execute_query(sql_query)
            logger.info(f"=== DEBUG: Query executed, returned {len(results) if results else 0} rows ===")
            
            # Check if this is an aggregation query with scalar result
            if self._is_scalar_aggregation(sql_query) and results and len(results) == 1:
                # Generate direct natural language answer for aggregation
                direct_answer = self._generate_aggregation_answer(sql_query, results)
                return {
                    "success": True,
                    "question": question,
                    "sql_query": sql_query,
                    "explanation": explanation,
                    "results": results,
                    "result_count": len(results),
                    "direct_answer": direct_answer,
                    "is_aggregation": True
                }
            
            return {
                "success": True,
                "question": question,
                "sql_query": sql_query,
                "explanation": explanation,
                "results": results,
                "result_count": len(results),
                "is_aggregation": False
            }
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "explanation": "Query execution failed"
            }
    
    def _execute_vague_query(self, question: str, concept: str) -> Dict[str, Any]:
        """Execute vague business query with intelligent threshold inference"""
        try:
            # Get business threshold SQL conditions
            threshold_info = self._get_business_threshold_sql(concept)
            
            # Build SQL query for vague concept
            if concept == "high_value":
                sql_query = f"""
                    SELECT deal_name, deal_owner, value, probability, stage, 
                           expected_close_date, created_date
                    FROM deals 
                    WHERE {' AND '.join(threshold_info['sql_conditions'])}
                    ORDER BY value DESC
                    LIMIT 10
                """
            
            elif concept in ["low_probability", "at_risk", "needs_attention"]:
                sql_query = f"""
                    SELECT deal_name, deal_owner, value, probability, stage, 
                           expected_close_date, last_modified_date,
                           julianday('now') - julianday(last_modified_date) as days_inactive
                    FROM deals 
                    WHERE {' AND '.join(threshold_info['sql_conditions'])}
                    ORDER BY probability ASC, value DESC
                    LIMIT 10
                """
            
            elif concept == "stalled":
                sql_query = f"""
                    SELECT deal_name, deal_owner, value, probability, stage, 
                           last_modified_date,
                           julianday('now') - julianday(last_modified_date) as days_inactive
                    FROM deals 
                    WHERE {' AND '.join(threshold_info['sql_conditions'])}
                    ORDER BY days_inactive DESC, value DESC
                    LIMIT 10
                """
            
            # Execute the query
            results = self.db_manager.execute_query(sql_query)
            
            # Generate business insight explanation
            explanation = f"""
Business Intelligence Analysis: {threshold_info['description']}

Inferred Thresholds:
- {threshold_info['explanation']}

Query Strategy:
- Automatically detected business concept: '{concept}'
- Applied intelligent filtering based on data patterns
- Ranked results by business relevance
- {len(results)} deals identified matching criteria
            """
            
            return {
                "success": True,
                "question": question,
                "sql_query": sql_query,
                "explanation": explanation.strip(),
                "results": results,
                "result_count": len(results),
                "business_concept": concept,
                "threshold_info": threshold_info
            }
            
        except Exception as e:
            logger.error(f"Vague query execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "explanation": f"Failed to analyze vague query concept: {concept}"
            }
    
    def get_schema_summary(self) -> Dict[str, Any]:
        """Get summary of database schema for context"""
        if not self.schema_info:
            self._load_schema()
        
        summary = {}
        for table_name, table_info in self.schema_info.items():
            summary[table_name] = {
                "columns": [col['name'] for col in table_info['columns']],
                "row_count": table_info['row_count']
            }
        
        return summary

    def _build_time_analytics_query(self, question: str, entity: str) -> Optional[str]:
        """Build time-based analytics queries with proper quarter grouping and dimensional analysis"""
        question_lower = question.lower()
        logger.info(f"=== DEBUG: Time analytics builder checking: {question} ===")
        
        # Detect grouping dimensions (industry, rep, stage, etc.)
        grouping_dimension = self._detect_grouping_dimension(question_lower, entity)
        logger.info(f"=== DEBUG: Grouping dimension detected: {grouping_dimension} ===")
        
        # Detect time-based patterns - ENHANCED
        time_patterns = [
            r'last (\d+) quarters?',
            r'past (\d+) quarters?',
            r'last quarter',
            r'past quarter',
            r'this quarter',
            r'recent quarter',
            r'last (\d+) months?',
            r'past (\d+) months?'
        ]
        
        # Also check for trend keywords that imply time analysis
        trend_keywords = ['trend', 'trends', 'compare', 'comparison', 'analysis', 'performance', 'quarterly', 'monthly', 'growth']
        has_trend_keyword = any(keyword in question_lower for keyword in trend_keywords)
        
        time_period = None
        for pattern in time_patterns:
            match = re.search(pattern, question_lower)
            if match:
                logger.info(f"=== DEBUG: Pattern matched: {pattern} ===")
                if match.groups():
                    if 'quarter' in pattern:
                        time_period = f"last_{match.group(1)}_quarters"
                    else:
                        time_period = f"last_{match.group(1)}_months"
                else:
                    time_period = "last_quarter"
                break
        
        logger.info(f"=== DEBUG: Time period detected: {time_period} ===")
        logger.info(f"=== DEBUG: Has trend keyword: {has_trend_keyword} ===")
        
        # Use time analytics if we have time period OR trend keywords with time references
        if time_period or (has_trend_keyword and any(word in question_lower for word in ['quarter', 'month', 'year'])):
            logger.info(f"=== DEBUG: Time analytics conditions met ===")
            # If no specific time period but trend analysis requested, default to last 2 quarters for comparison
            if not time_period:
                time_period = "last_2_quarters"
                logger.info(f"=== DEBUG: Defaulting to last_2_quarters for trend analysis ===")
        else:
            logger.info(f"=== DEBUG: Time analytics conditions NOT met, returning None ===")
            return None
        
        # Check if it's a trend analysis query
        trend_keywords = ['trend', 'declining', 'improving', 'growth', 'decline', 'compare', 'analysis']
        is_trend_analysis = any(keyword in question_lower for keyword in trend_keywords)
        
        # Get appropriate date column
        date_column = self._get_date_column_for_entity(entity)
        if not date_column:
            date_column = 'created_date'  # fallback
        
        # Generate SQL based on whether we have a grouping dimension
        if grouping_dimension:
            logger.info(f"=== DEBUG: Generating grouped time analytics SQL for dimension: {grouping_dimension} ===")
            return self._build_grouped_time_analytics_query(question_lower, entity, time_period, grouping_dimension, date_column, is_trend_analysis)
        else:
            logger.info(f"=== DEBUG: Generating simple time analytics SQL ===")
            return self._build_simple_time_analytics_query(entity, time_period, date_column, is_trend_analysis)
    
    def _detect_grouping_dimension(self, question_lower: str, entity: str) -> Optional[str]:
        """Detect grouping dimensions like industry, rep, stage, etc."""
        
        # Define dimension mappings for different entities
        dimension_mappings = {
            'deals': {
                'industry': ['industry', 'industries', 'sector', 'sectors'],
                'rep': ['rep', 'sales rep', 'owner', 'account owner', 'representative'],
                'stage': ['stage', 'stages', 'status', 'statuses'],
                'customer': ['customer', 'customers', 'client', 'clients']
            },
            'customers': {
                'industry': ['industry', 'industries', 'sector', 'sectors'],
                'size': ['size', 'company size', 'employees', 'headcount'],
                'owner': ['owner', 'account owner', 'rep']
            }
        }
        
        if entity not in dimension_mappings:
            return None
        
        # Check for dimension keywords in the query
        for dimension, keywords in dimension_mappings[entity].items():
            if any(keyword in question_lower for keyword in keywords):
                logger.info(f"=== DEBUG: Found dimension '{dimension}' with keywords: {keywords} ===")
                return dimension
        
        return None
    
    def _build_grouped_time_analytics_query(self, question_lower: str, entity: str, time_period: str, 
                                         grouping_dimension: str, date_column: str, is_trend_analysis: bool) -> str:
        """Build time analytics query with dimensional grouping"""
        
        # Map dimension to actual column names
        column_mappings = {
            'deals': {
                'industry': 'c.industry',
                'rep': 'd.account_owner',
                'stage': 'd.stage',
                'customer': 'd.customer_id'
            },
            'customers': {
                'industry': 'industry',
                'size': 'company_size',
                'owner': 'account_owner'
            }
        }
        
        # Get the appropriate column name
        if entity in column_mappings and grouping_dimension in column_mappings[entity]:
            dimension_column = column_mappings[entity][grouping_dimension]
        else:
            dimension_column = grouping_dimension
        
        # Determine join requirements
        join_clause = ""
        if entity == 'deals' and grouping_dimension in ['industry', 'customer']:
            join_clause = f"LEFT JOIN customers c ON d.customer_id = c.customer_id"
        
        # Build the grouped query
        if time_period == "last_2_quarters" or (time_period.startswith("last_") and "quarters" in time_period):
            # Multi-quarter grouped analysis
            num_quarters = 2 if time_period == "last_2_quarters" else int(time_period.split("_")[1])
            
            sql_query = f"""
SELECT 
    {dimension_column} as {grouping_dimension},
    CASE 
        WHEN d.{date_column} >= DATE('now', 'start of month', '-3 month') 
        THEN 'Current Quarter'
        WHEN d.{date_column} >= DATE('now', 'start of month', '-6 month') 
        THEN 'Previous Quarter'
    END as quarter_period,
    SUM(d.value) as total_value,
    COUNT(*) as deal_count,
    AVG(d.value) as avg_deal_value
FROM {entity} d
{join_clause}
WHERE d.{date_column} >= DATE('now', 'start of month', '-{num_quarters * 3} month')
GROUP BY {grouping_dimension}, quarter_period
ORDER BY {grouping_dimension}, quarter_period DESC
"""
        else:
            # Single quarter grouped analysis
            sql_query = f"""
SELECT 
    {dimension_column} as {grouping_dimension},
    SUM(d.value) as total_value,
    COUNT(*) as deal_count,
    AVG(d.value) as avg_deal_value
FROM {entity} d
{join_clause}
WHERE d.{date_column} >= DATE('now', 'start of month', '-3 month')
AND d.{date_column} < DATE('now', 'start of month')
GROUP BY {grouping_dimension}
ORDER BY total_value DESC
"""
        
        return sql_query.strip()
    
    def _build_simple_time_analytics_query(self, entity: str, time_period: str, date_column: str, is_trend_analysis: bool) -> str:
        
        if time_period == "last_2_quarters" and is_trend_analysis:
            # Special case: compare last 2 quarters with proper grouping
            sql_query = f"""
SELECT 
    CASE 
        WHEN {date_column} >= DATE('now', 'start of month', '-3 month') 
        THEN 'Current Quarter'
        WHEN {date_column} >= DATE('now', 'start of month', '-6 month') 
        THEN 'Previous Quarter'
    END as quarter_period,
    SUM(value) as total_value,
    COUNT(*) as deal_count,
    AVG(value) as avg_deal_value
FROM {entity}
WHERE {date_column} >= DATE('now', 'start of month', '-6 month')
GROUP BY quarter_period
ORDER BY quarter_period DESC
"""
            return sql_query.strip()
        
        elif time_period.startswith("last_") and ("quarters" in time_period or "quarter" in time_period):
            # General case: group by quarter for multiple quarters OR single quarter
            if "quarters" in time_period:
                # Multiple quarters
                num_quarters = int(time_period.split("_")[1])
                sql_query = f"""
SELECT 
    CASE 
        WHEN {date_column} >= DATE('now', 'start of month', '-3 month') THEN 'Q0 (Current)'
        WHEN {date_column} >= DATE('now', 'start of month', '-6 month') THEN 'Q1 (Previous)'
        WHEN {date_column} >= DATE('now', 'start of month', '-9 month') THEN 'Q2'
        WHEN {date_column} >= DATE('now', 'start of month', '-12 month') THEN 'Q3'
    END as quarter_period,
    SUM(value) as total_value,
    COUNT(*) as deal_count,
    AVG(value) as avg_deal_value
FROM {entity}
WHERE {date_column} >= DATE('now', 'start of month', '-{num_quarters * 3} month')
GROUP BY quarter_period
ORDER BY quarter_period
"""
            else:
                # Single quarter - generate quarterly summary
                sql_query = f"""
SELECT 
    '{time_period.replace('_', ' ').title()}' as quarter_period,
    SUM(value) as total_value,
    COUNT(*) as deal_count,
    AVG(value) as avg_deal_value
FROM {entity}
WHERE {date_column} >= DATE('now', 'start of month', '-3 month')
AND {date_column} < DATE('now', 'start of month')
GROUP BY quarter_period
"""
            return sql_query.strip()
        
        return None
    
    def _get_date_column_for_entity(self, entity: str) -> Optional[str]:
        """Get the most appropriate date column for an entity"""
        date_columns = {
            'deals': ['created_date', 'expected_close_date', 'last_modified_date'],
            'activities': ['date', 'created_date'],
            'customers': ['created_date', 'last_contact_date']
        }
        
        if entity in date_columns:
            return date_columns[entity][0]  # Return primary date column
        
        return 'created_date'  # Default fallback


if __name__ == "__main__":
    # Example usage
    from ..database.database_manager import DatabaseManager
    
    db_manager = DatabaseManager()
    sql_agent = SQLAgent(db_manager)
    
    # Test queries
    test_questions = [
        "Show me the top 5 deals by value",
        "How many customers are in the technology industry?",
        "What's the total value of all deals?",
        "List recent activities for Sales Rep 1"
    ]
    
    for question in test_questions:
        result = sql_agent.execute_query(question)
        print(f"Question: {question}")
        print(f"Result: {result}")
        print("-" * 50)
