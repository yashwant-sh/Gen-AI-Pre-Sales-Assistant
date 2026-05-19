"""
Main entry point for the GenAI Pre-Sales Assistant

This script provides a simple way to run the entire system without
requiring manual setup of individual components.
"""

import sys
import os
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import settings
from src.data_generation.crm_generator import CRMDataGenerator
from src.database.database_manager import DatabaseManager
from src.sql_agent.sql_agent import SQLAgent
from src.rag.rag_pipeline import RAGPipeline
from src.orchestration.orchestrator import SalesAssistantOrchestrator
from src.llm.llm_client import LLMClient
from loguru import logger


def setup_logging():
    """Setup logging configuration"""
    logger.add(
        "logs/app.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )


def initialize_system():
    """Initialize all system components"""
    logger.info("Initializing GenAI Pre-Sales Assistant...")
    
    # Create necessary directories
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Initialize database
    logger.info("Setting up database...")
    db_manager = DatabaseManager(settings.database_path)
    db_manager.create_schema()
    
    # Check if data exists
    schema_info = db_manager.get_schema_info()
    has_data = any(table["row_count"] > 0 for table in schema_info.values())
    
    if not has_data:
        logger.info("Generating synthetic CRM data...")
        generator = CRMDataGenerator()
        files = generator.generate_all_data(
            num_customers=100,
            num_products=50,
            num_deals=200,
            num_activities=500,
            output_dir="data/raw"
        )
        
        # Load data into database
        for table, csv_file in files.items():
            db_manager.load_data_from_csv(csv_file, table)
        
        logger.info("CRM data generation completed")
    else:
        logger.info("Database already contains data")
    
    # Initialize LLM client
    logger.info("Initializing LLM client...")
    llm_client = None
    try:
        llm_client = LLMClient(
            provider=settings.default_llm_provider,
            groq_api_key=settings.groq_api_key,
            ollama_base_url=settings.ollama_base_url,
        )
    except Exception as e:
        logger.warning(f"LLM client init failed ({e}); continuing without LLM")
    
    # Initialize SQL agent
    logger.info("Initializing SQL agent...")
    sql_agent = SQLAgent(db_manager, llm_client)
    
    # Initialize RAG pipeline
    logger.info("Initializing RAG pipeline...")
    rag_pipeline = RAGPipeline(
        embedding_model=settings.embedding_model,
        vector_store_path=settings.vector_store_path,
        documents_path=settings.documents_path,
        llm_client=llm_client,
        defer_index_build=False,
    )
    
    # Initialize orchestrator
    logger.info("Initializing orchestrator...")
    orchestrator = SalesAssistantOrchestrator(sql_agent, rag_pipeline)
    
    logger.info("System initialization completed successfully")
    return orchestrator, db_manager


def interactive_mode(orchestrator):
    """Run the system in interactive mode"""
    print("\n" + "="*60)
    print("🚀 GenAI Pre-Sales Assistant - Interactive Mode")
    print("="*60)
    print("\nType your questions or 'quit' to exit")
    print("\nExample queries:")
    print("- Show me the top 5 deals by value")
    print("- How many customers are in the technology industry?")
    print("- Draft a proposal for a software implementation project")
    print("- Write a follow-up email for a deal in negotiation stage")
    print("-" * 60)
    
    while True:
        try:
            query = input("\n🤖 Your question: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not query:
                continue
            
            print("\n🔄 Processing...")
            result = orchestrator.process_query(query)
            
            if result.get("success"):
                print(f"\n📊 Query Type: {result.get('query_type', 'general')}")
                print(f"📚 Sources Used: {', '.join(result.get('sources_used', []))}")
                print(f"\n💬 Response:")
                print("-" * 40)
                print(result.get('response', 'No response generated'))
                print("-" * 40)
            else:
                print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")


def api_mode():
    """Run the system in API mode"""
    logger.info("Starting API server...")
    import uvicorn
    from src.api.main import app
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )


def demo_mode(orchestrator):
    """Run a demonstration of the system"""
    print("\n" + "="*60)
    print("🎯 GenAI Pre-Sales Assistant - Demo Mode")
    print("="*60)
    
    demo_queries = [
        "Show me the top 3 deals by value",
        "How many customers are in the technology industry?",
        "What's the total value of all deals in proposal stage?",
        "Draft a proposal for a software implementation project",
        "Write a follow-up email for a deal in negotiation stage"
    ]
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n🔍 Demo {i}: {query}")
        print("-" * 50)
        
        try:
            result = orchestrator.process_query(query)
            
            if result.get("success"):
                print(f"📊 Type: {result.get('query_type')}")
                print(f"📚 Sources: {', '.join(result.get('sources_used', []))}")
                print(f"\n💬 Response:")
                print(result.get('response', 'No response'))
            else:
                print(f"❌ Error: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "="*50)
        
        if i < len(demo_queries):
            input("Press Enter to continue...")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="GenAI Pre-Sales Assistant")
    parser.add_argument(
        "--mode", 
        choices=["interactive", "api", "demo"], 
        default="interactive",
        help="Run mode: interactive, api, or demo"
    )
    parser.add_argument(
        "--no-init",
        action="store_true",
        help="Skip system initialization"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    try:
        # Initialize system
        if not args.no_init:
            orchestrator, db_manager = initialize_system()
        else:
            # Load existing components
            db_manager = DatabaseManager(settings.database_path)
            sql_agent = SQLAgent(db_manager)
            rag_pipeline = RAGPipeline(defer_index_build=False)
            orchestrator = SalesAssistantOrchestrator(sql_agent, rag_pipeline)
        
        # Run in specified mode
        if args.mode == "interactive":
            interactive_mode(orchestrator)
        elif args.mode == "api":
            api_mode()
        elif args.mode == "demo":
            demo_mode(orchestrator)
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
