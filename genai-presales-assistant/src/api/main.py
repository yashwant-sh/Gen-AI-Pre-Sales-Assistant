"""
FastAPI Backend for GenAI Pre-Sales Assistant

Exposes the system via a FastAPI backend with a /chat endpoint that accepts user queries
like "Summarize the latest deal with Client X" or "Draft a proposal based on our previous deals."
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import uvicorn
from loguru import logger
import sys
import os

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.database.database_manager import DatabaseManager
from src.sql_agent.sql_agent import SQLAgent
from src.rag.rag_pipeline import RAGPipeline
from src.orchestration.improved_orchestrator import create_improved_orchestrator
from src.llm.llm_client import LLMClient
from src.memory.session_manager import SessionManager


# Pydantic models for request/response
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    summary: Optional[str] = None
    insight: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    sql_query: Optional[str] = None
    query_type: str
    sources_used: List[str]
    sql_result: Optional[Dict[str, Any]] = None
    rag_results: Optional[List[Dict[str, Any]]] = None
    success: bool
    error: Optional[str] = None
    session_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    components: Dict[str, str]
    database_stats: Optional[Dict[str, Any]] = None


class InitializeRequest(BaseModel):
    generate_data: bool = True
    num_customers: int = 100
    num_products: int = 50
    num_deals: int = 200
    num_activities: int = 500


# Initialize FastAPI app
app = FastAPI(
    title="GenAI Pre-Sales Assistant",
    description="An AI-powered pre-sales assistant that combines synthetic CRM data, SQL queries, and RAG",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for components
db_manager: Optional[DatabaseManager] = None
sql_agent: Optional[SQLAgent] = None
rag_pipeline: Optional[RAGPipeline] = None
orchestrator = None
llm_client = None
session_mgr: Optional[SessionManager] = None


def ensure_app_directories():
    """Create dirs SQLite, CSV dumps, FAISS, and logs need (Docker/Railway often has no empty data/)."""
    db_dir = os.path.dirname(os.path.abspath(settings.database_path))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    vdir = os.path.dirname(os.path.abspath(settings.vector_store_path))
    if vdir:
        os.makedirs(vdir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)


def initialize_components():
    """Initialize all components"""
    global db_manager, sql_agent, rag_pipeline, orchestrator, llm_client, session_mgr
    
    try:
        logger.info("Initializing components...")
        
        # Initialize LLM client
        try:
            llm_client = LLMClient(
                provider=settings.default_llm_provider,
                groq_api_key=settings.groq_api_key,
                ollama_base_url=settings.ollama_base_url,
            )
            logger.info("LLM client initialized successfully")
        except Exception as e:
            logger.warning(f"LLM client init failed ({e}); continuing without LLM")
            llm_client = None
        
        # Initialize database manager
        db_manager = DatabaseManager(settings.database_path)
        
        # Initialize SQL agent
        sql_agent = SQLAgent(db_manager, llm_client)
        
        # Initialize RAG pipeline with LLM for actual generation
        rag_pipeline = RAGPipeline(
            embedding_model=settings.embedding_model,
            vector_store_path=settings.vector_store_path,
            documents_path=settings.documents_path,
            llm_client=llm_client,
            defer_index_build=True,
        )
        
        # Initialize orchestrator with enhanced intent routing
        orchestrator = create_improved_orchestrator(sql_agent, rag_pipeline, llm_client)
        
        # Initialize session manager (conversation memory + query cache)
        session_mgr = SessionManager(session_ttl=3600, cache_ttl=300)
        
        logger.info("Components initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        return False


def setup_database_and_data(
    num_customers: int = 100,
    num_products: int = 50,
    num_deals: int = 200,
    num_activities: int = 500,
):
    """Setup database and generate synthetic data"""
    try:
        logger.info("Setting up database...")
        ensure_app_directories()

        # Create schema
        db_manager.create_schema()
        
        # Check if data already exists
        schema_info = db_manager.get_schema_info()
        has_data = any(table["row_count"] > 0 for table in schema_info.values())
        
        if not has_data:
            logger.info("Generating synthetic data...")
            from src.data_generation.crm_generator import CRMDataGenerator
            
            generator = CRMDataGenerator()
            files = generator.generate_all_data(
                num_customers=num_customers,
                num_products=num_products,
                num_deals=num_deals,
                num_activities=num_activities,
                output_dir="data/raw",
            )
            
            # Load data into database
            for table, csv_file in files.items():
                db_manager.load_data_from_csv(csv_file, table)
            
            logger.info("Database setup completed")
        else:
            logger.info("Database already contains data")
        
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    logger.info("Starting GenAI Pre-Sales Assistant API...")
    ensure_app_directories()

    # Initialize components
    if not initialize_components():
        logger.error("Failed to initialize components")
        return
    
    # Setup database and data
    if not setup_database_and_data():
        logger.error("Failed to setup database")
        return
    
    logger.info("API startup completed successfully")


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "GenAI Pre-Sales Assistant API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    components = {}
    
    # Check database
    try:
        if db_manager:
            db_stats = db_manager.get_database_stats()
            components["database"] = "healthy"
            database_stats = db_stats
        else:
            components["database"] = "not_initialized"
            database_stats = None
    except Exception as e:
        components["database"] = f"error: {str(e)}"
        database_stats = None
    
    # Check SQL agent
    try:
        if sql_agent:
            components["sql_agent"] = "healthy"
        else:
            components["sql_agent"] = "not_initialized"
    except Exception as e:
        components["sql_agent"] = f"error: {str(e)}"
    
    # Check RAG pipeline
    try:
        if rag_pipeline:
            rag_summary = rag_pipeline.get_document_summary()
            components["rag_pipeline"] = "healthy"
        else:
            components["rag_pipeline"] = "not_initialized"
    except Exception as e:
        components["rag_pipeline"] = f"error: {str(e)}"
    
    # Check orchestrator
    try:
        if orchestrator:
            components["orchestrator"] = "healthy"
        else:
            components["orchestrator"] = "not_initialized"
    except Exception as e:
        components["orchestrator"] = f"error: {str(e)}"
    
    overall_status = "healthy" if all("healthy" in status for status in components.values()) else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        components=components,
        database_stats=database_stats
    )


@app.post("/initialize", response_model=Dict[str, str])
async def initialize_system(request: InitializeRequest, background_tasks: BackgroundTasks):
    """Initialize the system with optional data generation"""
    try:
        if request.generate_data:
            background_tasks.add_task(
                setup_database_and_data,
                request.num_customers,
                request.num_products,
                request.num_deals,
                request.num_activities,
            )
            return {"message": "System initialization started in background"}
        else:
            # Just initialize components
            if initialize_components():
                return {"message": "System initialized successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to initialize system")
    
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint with conversation memory and query caching"""
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="System not initialized")
        
        # Get or create session
        session = session_mgr.get_or_create_session(request.session_id)
        
        # Check query cache first
        cached = session_mgr.get_cached_result(request.query)
        if cached is not None:
            logger.info(f"Returning cached result for session {session.session_id}")
            payload = dict(cached)
            payload["session_id"] = session.session_id
            if not payload.get("response") and payload.get("summary"):
                payload["response"] = payload["summary"]
            session.add_user_message(request.query)
            session.add_assistant_message(
                payload.get("summary") or payload.get("response", ""),
                payload.get("query_type", ""),
            )
            return ChatResponse(**payload)
        
        # Record user message in memory
        session.add_user_message(request.query)
        
        # Build conversation context for LLM (last 6 turns)
        conversation_history = session.get_context_for_llm(last_n=6)
        # Remove the current message (it will be the prompt itself)
        if conversation_history and conversation_history[-1]["role"] == "user":
            conversation_history = conversation_history[:-1]
        
        # Process the query with conversation context
        result = orchestrator.process_query(
            request.query,
            conversation_history=conversation_history if conversation_history else None,
        )
        
        # Record assistant response in memory
        answer_text = result.get("summary") or result.get("response", "")
        session.add_assistant_message(answer_text, result.get("query_type", ""))
        
        if result.get("success"):
            main_text = (result.get("response") or result.get("summary") or "").strip()
            response_data = {
                "response": main_text,
                "summary": result.get("summary"),
                "insight": result.get("insight"),
                "data": result.get("data"),
                "sql_query": result.get("sql_query"),
                "query_type": result.get("query_type", ""),
                "sources_used": result.get("sources_used", []),
                "sql_result": result.get("sql_result"),
                "rag_results": result.get("rag_results"),
                "success": True,
                "session_id": session.session_id,
            }
            # Cache the result
            session_mgr.set_cached_result(request.query, response_data)
            return ChatResponse(**response_data)
        else:
            return ChatResponse(
                response="",
                query_type="",
                sources_used=[],
                success=False,
                error=result.get("error", "Unknown error"),
                session_id=session.session_id,
            )
    
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=Dict[str, Any])
async def get_system_stats():
    """Get system statistics"""
    try:
        stats = {}
        
        # Database stats
        if db_manager:
            stats["database"] = db_manager.get_database_stats()
        
        # RAG stats
        if rag_pipeline:
            stats["rag"] = rag_pipeline.get_document_summary()
        
        # SQL agent schema
        if sql_agent:
            stats["sql_schema"] = sql_agent.get_schema_summary()
        
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/stats", response_model=Dict[str, Any])
async def session_stats():
    """Get session and cache statistics"""
    if session_mgr:
        return session_mgr.get_stats()
    return {"error": "Session manager not initialized"}


@app.get("/query-suggestions", response_model=List[str])
async def get_query_suggestions():
    """Get sample query suggestions"""
    suggestions = [
        "Summarize the latest deal with Tech Corp",
        "Show me the top 5 deals by value",
        "How many customers are in the technology industry?",
        "Draft a proposal for a software implementation project",
        "Write a follow-up email for a deal in negotiation stage",
        "Analyze sales performance for this quarter",
        "What's the total value of all deals in proposal stage?",
        "List recent activities for Sales Rep 1",
        "Compare deal values across different industries",
        "Recommend next steps for deals in qualification stage"
    ]
    
    return suggestions


@app.post("/rag/add-documents", response_model=Dict[str, str])
async def add_documents(document_paths: List[str]):
    """Add new documents to the RAG pipeline"""
    try:
        if not rag_pipeline:
            raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
        
        rag_pipeline.add_documents(document_paths)
        
        return {"message": f"Added {len(document_paths)} documents to RAG pipeline"}
    
    except Exception as e:
        logger.error(f"Failed to add documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Configure logging
    logger.add(
        "logs/api.log",
        rotation="1 day",
        retention="30 days",
        level="INFO"
    )
    
    # Run the API
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )
