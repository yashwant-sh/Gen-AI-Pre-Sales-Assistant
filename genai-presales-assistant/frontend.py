"""
Streamlit Frontend for GenAI Pre-Sales Assistant

A simple chat-style interface to interact with the FastAPI backend.
Designed for demos and interviews - minimal and focused on usability.
"""

import os

import streamlit as st
import requests
import json
import uuid
from typing import Dict, Any, Optional
import time


class GenAIFrontend:
    """Frontend class for GenAI Pre-Sales Assistant"""
    
    def __init__(self, api_url: str = "http://localhost:8001"):
        """Initialize the frontend"""
        self.api_url = api_url
        self.chat_endpoint = f"{api_url}/chat"
        self.health_endpoint = f"{api_url}/health"
    
    @staticmethod
    def _escape_dollars(text: str) -> str:
        """Escape $ signs so Streamlit markdown doesn't treat them as LaTeX."""
        if not text:
            return text
        return text.replace("$", "\\$")
        
    def check_backend_health(self) -> bool:
        """Check if the backend is running"""
        try:
            response = requests.get(self.health_endpoint, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def send_query(self, query: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Send query to backend and return response"""
        try:
            payload = {"query": query}
            if session_id:
                payload["session_id"] = session_id
            response = requests.post(
                self.chat_endpoint,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code} - {response.text}"
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timed out. Please try again."
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"Cannot connect to backend at {self.api_url}. Is the API running?",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def display_response(self, response: Dict[str, Any]):
        """Display the API response in a formatted way"""
        if not response.get("success", False):
            st.error(f"❌ Error: {response.get('error', 'Unknown error')}")
            return
        
        # Main response
        if response.get("response"):
            st.markdown("### 💬 AI Response")
            st.markdown(self._escape_dollars(response["response"]))
        
        # Query information
        col1, col2 = st.columns(2)
        with col1:
            if response.get("query_type"):
                st.info(f"🔍 Query Type: `{response['query_type']}`")
        
        with col2:
            if response.get("sources_used"):
                sources = ", ".join(response["sources_used"])
                st.info(f"📚 Sources: {sources}")
        
        if response.get("success"):
            st.success("✅ Query processed successfully!")
            
            # Check if we have structured response (new format)
            if "summary" in response and "data" in response:
                # Display structured enterprise-style output
                
                # Check for single-value aggregation results (sum/total/count/avg)
                if (response.get("data") and 
                    len(response["data"]) == 1 and 
                    len(response["data"][0]) == 1):
                    
                    # Extract the single aggregated value
                    row = response["data"][0]
                    value = list(row.values())[0]
                    column_name = list(row.keys())[0]
                    
                    # Build a clean label from the column name
                    label = column_name.replace('_', ' ').title()
                    
                    # Determine display format — check count BEFORE total (total_count has both)
                    if 'count' in column_name.lower():
                        st.markdown(f"### 🔢 {label}: {int(value):,}")
                    elif 'avg' in column_name.lower() or 'average' in column_name.lower():
                        st.markdown(f"### 📊 {label}: ${value:,.2f}")
                    elif any(keyword in column_name.lower() for keyword in ['sum', 'total', 'value', 'revenue']):
                        st.markdown(f"### 💰 {label}: ${value:,.2f}")
                    else:
                        st.markdown(f"### 📈 {label}: {value:,.2f}")
                    
                    # Also show the summary if it's different
                    if response.get("summary") and "total sum" not in response["summary"].lower():
                        st.markdown(f"### ✅ {self._escape_dollars(response['summary'])}")
                
                # Handle multi-row results or time analytics
                elif response.get("data") and len(response["data"]) > 0:
                    # Show summary first
                    if response.get("summary"):
                        st.markdown(f"### ✅ {self._escape_dollars(response['summary'])}")
                    
                    # Show data in a nice format
                    st.markdown("### 📊 Results")
                    import pandas as pd
                    df = pd.DataFrame(response["data"])
                    
                    # Special formatting for time analytics
                    if 'quarter_period' in df.columns:
                        st.markdown("**Quarterly Performance:**")
                        for _, row in df.iterrows():
                            quarter = row.get('quarter_period', 'Unknown')
                            total = row.get('total_value', 0)
                            count = row.get('deal_count', 0)
                            st.markdown(f"- **{quarter}**: ${total:,.2f} ({count} deals)")
                    else:
                        # General data table
                        st.dataframe(df, use_container_width=True)
                
                # Show summary if no data was returned but summary exists
                elif response.get("summary"):
                    st.markdown(f"### ✅ {self._escape_dollars(response['summary'])}")
                
                # Insight (if available)
                if response.get("insight"):
                    st.markdown(f"### 💡 Business Insight\n{self._escape_dollars(response['insight'])}")
                
                # SQL Query (expandable)
                if response.get("sql_query"):
                    with st.expander("🔎 SQL Query Details", expanded=False):
                        st.code(response["sql_query"], language="sql")
            
            else:
                # Fallback to original display for legacy responses
                response_content = response.get("response", "")
                st.markdown(self._escape_dollars(response_content))
        
        # Legacy SQL Result display (if available)
        if response.get("sql_result") and response["sql_result"].get("success"):
            sql_result = response["sql_result"]
            
            # Only show if not already displayed in structured format
            if not ("summary" in response and "data" in response):
                with st.expander("🗄️ SQL Query Details", expanded=False):
                    st.code(sql_result.get("sql_query", ""), language="sql")
        
        # RAG Results (if available)
        if response.get("rag_results") and len(response["rag_results"]) > 0:
            with st.expander("📚 Retrieved Documents", expanded=False):
                rag_results = response["rag_results"]
                
                for i, doc in enumerate(rag_results[:3]):  # Limit to 3 documents
                    st.markdown(f"**Document {i+1}** (Score: {doc.get('score', 'N/A'):.4f})")
                    st.write(f"**Source:** `{doc.get('source', 'Unknown')}`")
                    st.write(f"**Content:** {doc.get('content', '')[:300]}...")
                    st.write("")
                
                if len(rag_results) > 3:
                    st.info(f"📄 Showing 3 of {len(rag_results)} retrieved documents")
    
    def run(self):
        """Run the Streamlit app"""
        st.set_page_config(
            page_title="GenAI Pre-Sales Assistant",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
        # Header
        st.title("🤖 GenAI Pre-Sales Assistant")
        st.markdown("Ask questions about deals, customers, proposals, and sales strategies.")
        
        # Check backend health
        if not self.check_backend_health():
            st.error("❌ Backend server is not reachable. Check that the API is running and `BACKEND_URL` is set correctly.")
            st.code(f"Configured API: {self.api_url}\n\nLocal dev:\npython -m uvicorn src.api.main:app --host 0.0.0.0 --port 8001")
            st.stop()
        
        # Success message
        st.success("✅ Backend connected successfully!")
        
        # Sidebar with sample queries
        with st.sidebar:
            st.header("💡 Sample Queries")
            sample_queries = [
                "Show me the top 5 deals by value",
                "How many customers are in the technology industry?",
                "What's the total value of all deals?",
                "Draft a proposal for a software implementation project",
                "Write a follow-up email for a deal in negotiation stage",
                "Analyze sales performance for this quarter",
                "List recent activities for Sales Rep 1",
                "Compare deal values across different industries"
            ]
            
            for i, query in enumerate(sample_queries):
                if st.button(query, key=f"sample_{i}"):
                    st.session_state.user_input = query
                    st.rerun()
        
        # Initialize session state
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "user_input" not in st.session_state:
            st.session_state.user_input = ""
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    self.display_response(message["content"])
        
        # Chat input
        user_input = st.chat_input("Ask about deals, customers, proposals, or sales strategies...")
        
        # Check if user input came from button click or chat input
        input_to_process = user_input or st.session_state.get("user_input", "")
        
        if input_to_process:
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": input_to_process})
            
            with st.chat_message("user"):
                st.write(input_to_process)
            
            # Get AI response
            with st.chat_message("assistant"):
                with st.spinner("🤔 Thinking..."):
                    response = self.send_query(input_to_process, st.session_state.session_id)
                    self.display_response(response)
                    if response and response.get("session_id"):
                        st.session_state.session_id = response["session_id"]
            
            # Add assistant response to chat
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Clear input
            st.session_state.user_input = ""
            st.rerun()
        
        # Footer
        st.markdown("---")
        st.markdown(
            f"""
            <div style='text-align: center; color: #666;'>
                <p>🚀 GenAI Pre-Sales Assistant | Backend: <code>{self.api_url}</code></p>
                <p>Built with ❤️ using Streamlit + FastAPI + RAG + SQL Agents</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main():
    """Main function to run the Streamlit app"""
    api_url = os.environ.get("BACKEND_URL", os.environ.get("API_URL", "http://localhost:8001")).rstrip("/")
    frontend = GenAIFrontend(api_url=api_url)
    frontend.run()


if __name__ == "__main__":
    main()
