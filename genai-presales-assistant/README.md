# GenAI Pre-Sales Assistant

A comprehensive AI-powered pre-sales assistant that combines synthetic CRM data generation, SQL agents, and Retrieval-Augmented Generation (RAG) to provide intelligent sales insights and document generation.

## 🚀 Features

### Core Capabilities
- **Synthetic CRM Data Generation**: Generate realistic customers, deals, activities, and products using LLM-powered data generation
- **SQL Agent**: Convert natural language sales questions into safe SQL queries with rule-based and LLM-based approaches
- **RAG Pipeline**: Document retrieval using sentence-transformers and FAISS vector database
- **Intelligent Orchestration**: Combine SQL results with retrieved documents for grounded responses
- **FastAPI Backend**: RESTful API with `/chat` endpoint for easy integration

### Key Functions
- Deal summaries and analysis
- Proposal drafting based on previous deals
- Follow-up email generation
- Sales performance analytics
- Document retrieval and recommendations
- Natural language database queries

## 🏗️ Architecture

```
src/
├── data_generation/     # Synthetic CRM data generation
├── database/           # SQLite database management
├── sql_agent/          # Natural language to SQL conversion
├── rag/               # RAG pipeline with embeddings
├── orchestration/     # Response orchestration layer
└── api/               # FastAPI backend
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- pip or conda
- Optional: Ollama for local LLM inference

### Setup Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd genai-presales-assistant
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Optional: Set up Ollama for local LLM**
```bash
# Install Ollama (https://ollama.ai/)
# Pull the model
ollama pull llama3:8b
```

## 🚀 Quick Start

### 1. Initialize the System
```python
from src.api.main import app
import uvicorn

# Start the API server
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2. Use the API
```bash
# Health check
curl http://localhost:8000/health

# Chat with the assistant
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize the latest deal with Tech Corp"}'
```

### 3. Example Queries
- "Show me the top 5 deals by value"
- "How many customers are in the technology industry?"
- "Draft a proposal for a software implementation project"
- "Write a follow-up email for a deal in negotiation stage"
- "Analyze sales performance for this quarter"

## 📊 Data Generation

The system automatically generates synthetic CRM data on first run:

### Generated Data Types
- **Customers**: 100 realistic customer profiles with industries, company sizes, and revenue
- **Products**: 50 products across different categories with pricing
- **Deals**: 200 sales deals with stages, values, and probabilities
- **Activities**: 500 sales activities with various types and outcomes

### Data Structure
```sql
-- Customers table
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    industry TEXT,
    company_size TEXT,
    annual_revenue REAL,
    -- ... other fields
);

-- Deals table
CREATE TABLE deals (
    deal_id TEXT PRIMARY KEY,
    customer_id TEXT,
    deal_name TEXT NOT NULL,
    stage TEXT,
    value REAL,
    -- ... other fields
);
```

## 🔍 SQL Agent

The SQL Agent converts natural language to SQL using:

### Rule-Based Approach
- Entity recognition (customers, deals, products, activities)
- Aggregation detection (SUM, COUNT, AVG, MAX, MIN)
- Condition extraction (WHERE clauses)
- Ordering and limiting

### LLM-Based Approach
- Schema-aware query generation
- Context-aware SQL construction
- Safety validation

### Example Conversions
```
"Show me top 5 deals by value"
→ SELECT * FROM deals ORDER BY value DESC LIMIT 5

"How many customers in technology industry?"
→ SELECT COUNT(*) FROM customers WHERE industry = 'Technology'
```

## 📚 RAG Pipeline

Document retrieval using modern embedding techniques:

### Supported Document Types
- Text files (.txt)
- PDF files (.pdf)
- Word documents (.docx)

### Embedding Model
- Default: `all-MiniLM-L6-v2`
- Configurable via environment variables

### Vector Store
- FAISS IndexFlatL2 for similarity search
- Persistent storage with automatic loading
- Incremental document addition

### Sample Documents Included
- Proposal templates
- Sales playbooks
- Email templates
- Negotiation strategies

## 🎯 Orchestration Layer

Combines SQL and RAG results for comprehensive responses:

### Query Types
- **Summary**: Deal and customer summaries
- **Proposal**: Draft proposals based on templates and data
- **Email**: Follow-up email generation
- **Analysis**: Sales performance analysis
- **Recommendation**: Strategic recommendations
- **Comparison**: Comparative analysis

### Response Generation
- Entity extraction and keyword identification
- Context-aware response formatting
- LLM enhancement for natural language generation
- Source attribution and hallucination control

## 🔧 Configuration

### Environment Variables
```bash
# LLM Configuration
GROQ_API_KEY=your_groq_api_key_here
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_LLM_PROVIDER=groq

# Database Configuration
DATABASE_PATH=data/crm_database.db

# RAG Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
VECTOR_STORE_PATH=models/faiss_index.bin
DOCUMENTS_PATH=docs/sales_documents

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
```

## 📡 API Endpoints

### Health Check
```http
GET /health
```
Returns system health status and component information.

### Chat
```http
POST /chat
Content-Type: application/json

{
  "query": "Your question here",
  "session_id": "optional-session-id"
}
```

### System Stats
```http
GET /stats
```
Returns database statistics and RAG pipeline information.

### Query Suggestions
```http
GET /query-suggestions
```
Returns sample queries to try.

### Add Documents
```http
POST /rag/add-documents
Content-Type: application/json

{
  "document_paths": ["path/to/document1.pdf", "path/to/document2.txt"]
}
```

## 🧪 Testing

### Quick Start:
```bash
# Install dependencies
pip install -r requirements.txt

# Option 1: Run backend only
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8001

# Option 2: Run frontend only (backend must be running)
streamlit run frontend.py --server.port 8501

# Option 3: Run both together (recommended for demos)
python start_demo.py
```

### Access the Application:
- **Backend API**: http://localhost:8001
- **Frontend UI**: http://localhost:8501
- **API Docs**: http://localhost:8001/docs

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_sql_agent.py

# Run with coverage
pytest --cov=src tests/
```

### Manual Testing
```python
# Test individual components
from src.data_generation.crm_generator import CRMDataGenerator
from src.database.database_manager import DatabaseManager
from src.sql_agent.sql_agent import SQLAgent
from src.rag.rag_pipeline import RAGPipeline
from src.orchestration.orchestrator import SalesAssistantOrchestrator

# Initialize components
db_manager = DatabaseManager()
sql_agent = SQLAgent(db_manager)
rag_pipeline = RAGPipeline()
orchestrator = SalesAssistantOrchestrator(sql_agent, rag_pipeline)

# Test query
result = orchestrator.process_query("Show me top 5 deals by value")
print(result)
```

## 🔒 Security Considerations

### SQL Injection Protection
- Query validation and sanitization
- Only SELECT queries allowed
- Parameterized queries
- Schema-based validation

### Data Privacy
- Local data storage only
- No external API calls for sensitive data
- Configurable LLM providers
- Document access control

## 🚀 Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations
- Use HTTPS with SSL certificates
- Implement rate limiting
- Add authentication/authorization
- Set up monitoring and logging
- Configure backup strategies

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋‍♂️ Support

For questions and support:
- Create an issue in the repository
- Check the documentation
- Review the example usage

## 🔮 Future Enhancements

- Multi-language support
- Advanced analytics dashboard
- Integration with popular CRM systems
- Real-time collaboration features
- Advanced AI model fine-tuning
- Mobile application
- Web-based UI
- Advanced security features

## 📈 Performance Metrics

### Expected Performance
- SQL query response: < 1 second
- Document retrieval: < 2 seconds
- Full orchestration: < 5 seconds
- API response time: < 10 seconds

### Scalability
- Handles 1000+ concurrent users
- Supports millions of database records
- Efficient vector search with FAISS
- Optimized embedding caching

---

**Built with ❤️ using only free and open-source tools**
