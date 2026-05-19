#!/usr/bin/env python3
"""
Quick start script for GenAI Pre-Sales Assistant
Starts both backend and frontend services
"""

import subprocess
import time
import sys
import os
from pathlib import Path

def start_backend():
    """Start the FastAPI backend"""
    print("🚀 Starting Backend...")
    backend_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "src.api.main:app", 
        "--host", "0.0.0.0", 
        "--port", "8001"
    ], cwd=Path(__file__).parent)
    return backend_process

def start_frontend():
    """Start the Streamlit frontend"""
    print("🎨 Starting Frontend...")
    frontend_process = subprocess.Popen([
        sys.executable, "-m", "streamlit", 
        "run", "frontend.py", 
        "--server.port", "8501"
    ], cwd=Path(__file__).parent)
    return frontend_process

def main():
    """Main startup function"""
    print("🎯 GenAI Pre-Sales Assistant - Service Starter")
    print("=" * 50)
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    try:
        # Start backend
        backend_process = start_backend()
        print("✅ Backend starting on http://localhost:8001")
        
        # Wait for backend to initialize
        print("⏳ Waiting for backend to initialize...")
        time.sleep(10)
        
        # Start frontend
        frontend_process = start_frontend()
        print("✅ Frontend starting on http://localhost:8501")
        
        print("\n🎉 Both services started!")
        print("📱 Frontend: http://localhost:8501")
        print("🔧 Backend API: http://localhost:8001")
        print("📚 API Docs: http://localhost:8001/docs")
        print("\nPress Ctrl+C to stop both services")
        
        # Wait for processes
        backend_process.wait()
        frontend_process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        if 'backend_process' in locals():
            backend_process.terminate()
        if 'frontend_process' in locals():
            frontend_process.terminate()
        print("✅ Services stopped")

if __name__ == "__main__":
    main()
