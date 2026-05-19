# 🚀 GenAI Pre-Sales Assistant - Demo Usage Guide

## 🎯 Quick Demo Setup

### 1. Start the System
```bash
# Option A: Start both backend and frontend together (recommended)
python start_demo.py

# Option B: Start manually
# Terminal 1: Backend
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8001

# Terminal 2: Frontend  
streamlit run frontend.py --server.port 8501
```

### 2. Access the Interface
- **Frontend UI**: http://localhost:8501
- **Backend API**: http://localhost:8001

## 🎪 Demo Features

### 💬 Chat Interface
- Clean, professional chat-style UI
- Real-time responses with loading indicators
- Conversation history maintained

### 📊 Sample Queries (Click to use)
The sidebar includes 8 pre-configured sample queries:

1. **"Show me the top 5 deals by value"**
   - Demonstrates SQL agent capabilities
   - Shows deal ranking and analysis

2. **"How many customers are in the technology industry?"**
   - Shows customer segmentation analysis
   - Demonstrates filtering and counting

3. **"What's the total value of all deals?"**
   - Demonstrates aggregation queries
   - Shows pipeline value analysis

4. **"Draft a proposal for a software implementation project"**
   - Shows RAG document retrieval
   - Generates structured proposals

5. **"Write a follow-up email for a deal in negotiation stage"**
   - Demonstrates email template generation
   - Shows negotiation strategies

6. **"Analyze sales performance for this quarter"**
   - Complex analytical queries
   - Performance metrics

7. **"List recent activities for Sales Rep 1"**
   - Activity tracking and reporting
   - Shows sales rep performance

8. **"Compare deal values across different industries"**
   - Cross-industry analysis
   - Demonstrates complex SQL joins

### 🔍 Response Features

#### Main Response
- Clean, formatted AI responses
- Context-aware answers

#### Expandable Details
- **🗄️ SQL Query Details**: Shows the generated SQL, explanation, and results
- **📚 Retrieved Documents**: Shows RAG document sources and relevance scores
- **Query Type**: Identifies the type of request (general, proposal, analysis, etc.)
- **Sources Used**: Shows which data sources were consulted

#### Error Handling
- Graceful error messages
- Connection status indicators
- Backend health checks

## 🎯 Demo Scenarios

### Scenario 1: Sales Analysis
**Query**: "What's our average deal size by industry?"
**Shows**: SQL generation, data aggregation, industry analysis

### Scenario 2: Document Generation  
**Query**: "Draft a proposal for a $50k CRM implementation"
**Shows**: RAG retrieval, template-based generation, professional formatting

### Scenario 3: Deal Intelligence
**Query**: "Show me deals that are closing this month"
**Shows**: Date filtering, pipeline management, opportunity tracking

### Scenario 4: Customer Insights
**Query**: "Which customers have the highest deal values?"
**Shows**: Customer analysis, deal correlation, value ranking

## 🎪 Technical Demo Points

### 1. **Synthetic Data Generation**
- 850+ realistic CRM records
- Multiple data types (customers, deals, products, activities)
- Realistic relationships and distributions

### 2. **Natural Language to SQL**
- Safe query generation
- Complex SQL operations (joins, aggregations, filtering)
- Query explanations and optimization

### 3. **RAG Pipeline**
- Semantic document retrieval
- FAISS vector database
- Relevance scoring and ranking

### 4. **LLM Integration**
- Groq API integration (free tier)
- Context-aware response generation
- Professional business language

### 5. **System Architecture**
- Modular, clean code structure
- FastAPI backend with proper endpoints
- Streamlit frontend for easy demos

## 💡 Pro Tips for Demos

1. **Start with simple queries** to build confidence
2. **Use the sample queries** first, then customize
3. **Show the expandable sections** to demonstrate transparency
4. **Highlight the sources** to show RAG capabilities
5. **Demonstrate error handling** by trying invalid queries
6. **Show conversation history** to demonstrate context maintenance

## 🚀 Ready to Demo!

The system is now fully operational with:
- ✅ Backend API running on port 8001
- ✅ Frontend UI running on port 8501  
- ✅ All 850+ synthetic records loaded
- ✅ RAG documents indexed
- ✅ Groq LLM integration active

Perfect for interviews, presentations, and technical demonstrations! 🎉
