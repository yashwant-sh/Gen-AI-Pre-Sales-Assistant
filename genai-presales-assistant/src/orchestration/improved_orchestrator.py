"""
Improved Orchestrator with Enhanced Intent Routing
Clean, production-ready implementation for GenAI Pre-Sales Assistant
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from .intent_classifier import IntentClassifier, IntentResult

logger = logging.getLogger(__name__)

class ImprovedSalesAssistantOrchestrator:
    """
    Enhanced Orchestrator with Clean Intent Routing + Conversation Memory
    
    Architecture:
    1. Intent Classification (Rule-based + LLM fallback)
    2. Route to appropriate handler:
       - time_analytics → Time analytics SQL builder
       - data_query → SQL agent for aggregations
       - document_query → RAG pipeline for knowledge
       - general → General response
    3. Conversation history is injected into LLM calls for context
    """
    
    def __init__(self, sql_agent, rag_pipeline, llm_client):
        self.sql_agent = sql_agent
        self.rag_pipeline = rag_pipeline
        self.llm_client = llm_client
        self.intent_classifier = IntentClassifier()
        
        logger.info("Improved Sales Assistant Orchestrator initialized")
    
    def process_query(self, user_query: str,
                      conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Main query processing with enhanced intent routing
        
        Args:
            user_query: User's natural language query
            conversation_history: Prior turns for multi-turn context
            
        Returns:
            Structured response with results
        """
        
        try:
            logger.info(f"🎯 PROCESSING QUERY: '{user_query}' (history={len(conversation_history or [])} turns)")
            
            # Step 1: Enhanced Intent Classification
            intent_result = self.intent_classifier.classify_intent(user_query)
            logger.info(f"📊 INTENT: {intent_result.intent} (confidence: {intent_result.confidence:.2f})")
            
            # Step 2: Route based on intent
            if intent_result.intent == "time_analytics":
                return self._handle_time_analytics(user_query, intent_result)
            elif intent_result.intent == "data_query":
                return self._handle_data_query(user_query, intent_result)
            elif intent_result.intent == "document_query":
                return self._handle_document_query(user_query, intent_result, conversation_history)
            else:
                return self._handle_general_query(user_query, intent_result, conversation_history)
                
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return self._error_response(str(e))
    
    def _handle_time_analytics(self, query: str, intent_result: IntentResult) -> Dict[str, Any]:
        """Handle time-based analytics queries"""
        
        logger.info("📈 ROUTING TO TIME ANALYTICS")
        
        try:
            # Generate time-based SQL
            sql_result = self.sql_agent.execute_query(query)
            
            if sql_result.get('success'):
                # Extract data from SQL result
                results = sql_result.get('results', [])
                direct_answer = sql_result.get('direct_answer', '')
                
                # Generate summary if not provided
                summary = sql_result.get('summary', '')
                if not summary and direct_answer:
                    summary = direct_answer
                elif not summary and results:
                    # Create a summary from results
                    if len(results) == 1 and 'sum_value' in results[0]:
                        total_revenue = results[0]['sum_value']
                        summary = f"The total revenue from closed won deals is ${total_revenue:,.2f}."
                    else:
                        summary = f"Query executed successfully. Found {len(results)} results."
                
                # Generate business insights from data
                business_insight = self._generate_business_insight(results, query)
                
                return {
                    "success": True,
                    "query": query,
                    "query_type": "time_analytics",
                    "intent_confidence": intent_result.confidence,
                    "intent_reasoning": intent_result.reasoning,
                    "summary": summary,
                    "insight": business_insight,
                    "data": results,
                    "sql_query": sql_result.get('sql_query', ''),
                    "sql_result": sql_result,
                    "rag_results": [],
                    "sources_used": ["sql_database"],
                    "routing_path": "time_analytics_sql"
                }
            else:
                return self._sql_error_response(sql_result, query, "time_analytics", intent_result)
                
        except Exception as e:
            logger.error(f"Time analytics error: {str(e)}")
            return self._error_response(str(e))
    
    def _handle_data_query(self, query: str, intent_result: IntentResult) -> Dict[str, Any]:
        """Handle data aggregation queries"""
        
        logger.info("💰 ROUTING TO DATA QUERY (SQL)")
        
        try:
            # Generate SQL for data aggregation
            sql_result = self.sql_agent.execute_query(query)
            
            if sql_result.get('success'):
                # Extract data from SQL result
                results = sql_result.get('results', [])
                direct_answer = sql_result.get('direct_answer', '')
                
                # Generate summary if not provided
                summary = sql_result.get('summary', '')
                if not summary and direct_answer:
                    summary = direct_answer
                elif not summary and results:
                    # Create a summary from results
                    if len(results) == 1 and 'sum_value' in results[0]:
                        total_revenue = results[0]['sum_value']
                        summary = f"The total revenue from closed won deals is ${total_revenue:,.2f}."
                    else:
                        summary = f"Query executed successfully. Found {len(results)} results."
                
                # Generate business insights from data
                business_insight = self._generate_business_insight(results, query)
                
                return {
                    "success": True,
                    "query": query,
                    "query_type": "data_query",
                    "intent_confidence": intent_result.confidence,
                    "intent_reasoning": intent_result.reasoning,
                    "summary": summary,
                    "insight": business_insight,
                    "data": results,
                    "sql_query": sql_result.get('sql_query', ''),
                    "sql_result": sql_result,
                    "rag_results": [],
                    "sources_used": ["sql_database"],
                    "routing_path": "data_query_sql"
                }
            else:
                return self._sql_error_response(sql_result, query, "data_query", intent_result)
                
        except Exception as e:
            logger.error(f"Data query error: {str(e)}")
            return self._error_response(str(e))
    
    def _handle_document_query(self, query: str, intent_result: IntentResult,
                              conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Handle document/knowledge queries"""
        
        logger.info("📚 ROUTING TO DOCUMENT QUERY (RAG)")
        
        try:
            # Generate response using RAG
            if self.rag_pipeline:
                query_lower = query.lower()
                is_long_form = any(w in query_lower for w in [
                    "proposal", "draft", "email", "write", "generate", "create",
                ])
                top_k = 8 if is_long_form else 5
                retrieved_docs = self.rag_pipeline.retrieve(query, top_k=top_k)
                
                # Generate answer with conversation context
                answer = self.rag_pipeline.generate_answer(
                    query, retrieved_docs,
                    conversation_history=conversation_history,
                )
                
                sources = list({
                    Path(doc.get("source", "unknown")).stem
                    for doc in retrieved_docs
                })
                
                if any(w in query_lower for w in ["proposal", "draft proposal"]):
                    insight = "Proposal generated using product catalog, case studies, and proposal content library"
                elif any(w in query_lower for w in ["email", "follow-up", "followup"]):
                    insight = "Email generated using sales playbook and customer reference material"
                elif any(w in query_lower for w in ["competitor", "battle", "vs", "versus", "compare"]):
                    insight = "Competitive analysis sourced from battle cards and product catalog"
                else:
                    insight = f"Response generated from {len(retrieved_docs)} relevant knowledge base documents"

                return {
                    "success": True,
                    "query": query,
                    "query_type": "document_query",
                    "intent_confidence": intent_result.confidence,
                    "intent_reasoning": intent_result.reasoning,
                    "summary": answer,
                    "insight": insight,
                    "data": [],
                    "sql_query": "",
                    "sql_result": {},
                    "rag_results": [{"source": d.get("source", ""), "score": d.get("score", 0)} for d in retrieved_docs],
                    "sources_used": sources,
                    "routing_path": "document_query_rag"
                }
            else:
                return self._rag_unavailable_response(query, intent_result)
                
        except Exception as e:
            logger.error(f"Document query error: {str(e)}")
            return self._error_response(str(e))
    
    def _handle_general_query(self, query: str, intent_result: IntentResult,
                             conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Handle general queries"""
        
        logger.info("💬 ROUTING TO GENERAL RESPONSE")
        
        try:
            # Try LLM first, then fallback
            if self.llm_client:
                response = self.llm_client.generate(
                    prompt=query,
                    system_prompt=(
                        "You are a helpful pre-sales assistant for a B2B software company. "
                        "Answer concisely and professionally. Use the conversation history "
                        "for context when the user refers to previous messages."
                    ),
                    conversation_history=conversation_history,
                )
                return {
                    "success": True,
                    "query": query,
                    "query_type": "general",
                    "intent_confidence": intent_result.confidence,
                    "intent_reasoning": intent_result.reasoning,
                    "summary": response,
                    "insight": "",
                    "data": [],
                    "sql_query": "",
                    "sql_result": None,
                    "rag_results": [],
                    "sources_used": ["llm"],
                    "routing_path": "general_llm"
                }
            else:
                return {
                    "success": True,
                    "query": query,
                    "query_type": "general",
                    "intent_confidence": intent_result.confidence,
                    "intent_reasoning": intent_result.reasoning,
                    "summary": "I'm here to help with sales data analysis, document generation, and strategic advice. Please ask about revenue, deals, proposals, or performance trends.",
                    "insight": "",
                    "data": [],
                    "sql_query": "",
                    "sql_result": None,
                    "rag_results": [],
                    "sources_used": ["fallback"],
                    "routing_path": "general_fallback"
                }
                
        except Exception as e:
            logger.error(f"General query error: {str(e)}")
            return self._error_response(str(e))
    
    def _generate_business_insight(self, results: List[Dict], query: str) -> str:
        """Generate business insights from query results"""
        
        if not results:
            return "No data available for analysis."
        
        # Analyze query type and results
        query_lower = query.lower()
        
        # Industry comparison analysis
        if 'industry' in query_lower or 'industries' in query_lower:
            if len(results) > 1 and 'total_value' in results[0]:
                # Sort by total value
                sorted_results = sorted(results, key=lambda x: x.get('total_value', 0), reverse=True)
                top_industry = sorted_results[0]
                bottom_industry = sorted_results[-1]
                
                insight_parts = [
                    f"🏆 {top_industry.get('industry', 'Unknown')} has the highest total revenue: ${top_industry.get('total_value', 0):,.0f}"
                ]
                
                if 'avg_value' in top_industry and 'avg_value' in bottom_industry:
                    top_avg = top_industry.get('avg_value', 0)
                    bottom_avg = bottom_industry.get('avg_value', 0)
                    if top_avg > bottom_avg:
                        insight_parts.append(f"📊 {top_industry.get('industry', 'Unknown')} shows higher average deal value: ${top_avg:,.0f}")
                
                if 'deal_count' in bottom_industry:
                    low_count = bottom_industry.get('deal_count', 0)
                    if low_count < 10:
                        insight_parts.append(f"📉 {bottom_industry.get('industry', 'Unknown')} has lower deal volume: {low_count} deals")
                
                insight_parts.append("💡 Recommendation: Focus on high-performing industries with scalable potential.")
                
                return " | ".join(insight_parts)
        
        # Revenue analysis
        if 'revenue' in query_lower and len(results) == 1 and 'sum_value' in results[0]:
            total = results[0]['sum_value']
            if total > 1000000:
                return f"💰 Strong revenue performance: ${total:,.0f} indicates healthy sales pipeline."
            elif total > 500000:
                return f"💰 Moderate revenue of ${total:,.0f} suggests room for growth."
            else:
                return f"💰 Current revenue is ${total:,.0f}. Focus on scaling sales activities."
        
        # Deal count analysis
        if 'count' in query_lower and len(results) == 1:
            count = results[0].get('count_value', 0)
            return f"📊 Found {count:,} deals. Consider analyzing by stage or rep for deeper insights."
        
        # Comparison analysis (multiple results)
        if len(results) > 1:
            if 'value' in results[0]:
                # Sort by value
                sorted_results = sorted(results, key=lambda x: x.get('value', 0), reverse=True)
                top_performer = sorted_results[0]
                bottom_performer = sorted_results[-1]
                
                insight_parts = [
                    f"🏆 Top performer: ${top_performer.get('value', 0):,.0f}",
                    f"📉 Bottom performer: ${bottom_performer.get('value', 0):,.0f}"
                ]
                
                if len(sorted_results) >= 3:
                    median_idx = len(sorted_results) // 2
                    median_value = sorted_results[median_idx].get('value', 0)
                    insight_parts.append(f"📊 Median value: ${median_value:,.0f}")
                
                return " | ".join(insight_parts)
        
        # General data insight
        return f"📈 Data analysis complete: Found {len(results)} records. Consider drilling down for more specific insights."
    
    def _sql_error_response(self, sql_result: Dict, query: str, query_type: str, intent_result: IntentResult) -> Dict[str, Any]:
        """Handle SQL execution errors"""
        return {
            "success": False,
            "query": query,
            "query_type": query_type,
            "intent_confidence": intent_result.confidence,
            "intent_reasoning": intent_result.reasoning,
            "error": sql_result.get('error', 'Unknown SQL error'),
            "summary": "I couldn't process your data query. Please check your question format.",
            "insight": "Try rephrasing with specific metrics like 'total revenue' or 'deal count'.",
            "data": [],
            "sql_query": sql_result.get('sql_query', ''),
            "sql_result": sql_result,
            "rag_results": [],
            "sources_used": [],
            "routing_path": f"{query_type}_error"
        }
    
    def _rag_unavailable_response(self, query: str, intent_result: IntentResult) -> Dict[str, Any]:
        """Handle RAG pipeline unavailability"""
        return {
            "success": False,
            "query": query,
            "query_type": "document_query",
            "intent_confidence": intent_result.confidence,
            "intent_reasoning": intent_result.reasoning,
            "error": "RAG pipeline not available",
            "summary": "Document search is currently unavailable. Please try asking about specific data metrics.",
            "insight": "You can ask about revenue, deals, customers, and sales performance instead.",
            "data": [],
            "sql_query": "",
            "sql_result": None,
            "rag_results": [],
            "sources_used": [],
            "routing_path": "document_query_unavailable"
        }
    
    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """Generic error response"""
        return {
            "success": False,
            "error": error_message,
            "summary": "An error occurred while processing your query.",
            "insight": "Please try again or contact support if the issue persists.",
            "data": [],
            "sql_query": "",
            "sql_result": None,
            "rag_results": [],
            "sources_used": [],
            "routing_path": "error"
        }

# Factory function for easy initialization
def create_improved_orchestrator(sql_agent, rag_pipeline=None, llm_client=None):
    """Factory function to create improved orchestrator"""
    return ImprovedSalesAssistantOrchestrator(sql_agent, rag_pipeline, llm_client)
