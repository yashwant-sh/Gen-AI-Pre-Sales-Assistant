"""
Demo Startup Script for GenAI Pre-Sales Assistant

Starts both the FastAPI backend and Streamlit frontend for easy demo setup.
"""

import subprocess
import time
import sys
import os
from pathlib import Path


def check_backend_ready(url: str = "http://localhost:8001/health", timeout: int = 60) -> bool:
    """Check if backend is ready"""
    import requests
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(2)
    
    return False


def main():
    """Main function to start both backend and frontend"""
    print("🚀 Starting GenAI Pre-Sales Assistant Demo...")
    print("=" * 50)
    
    # Check if backend is already running
    try:
        import requests
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is already running!")
            backend_process = None
        else:
            print("❌ Backend responded with error, restarting...")
            backend_process = None
    except:
        print("🔧 Starting backend server...")
        backend_process = None
    
    # Start backend if not running
    if not backend_process:
        try:
            backend_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "src.api.main:app", 
                "--host", "0.0.0.0", 
                "--port", "8001"
            ], cwd=Path(__file__).parent)
            
            print("⏳ Waiting for backend to start...")
            if check_backend_ready():
                print("✅ Backend is ready!")
            else:
                print("❌ Backend failed to start within timeout")
                return
                
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return
    
    # Start frontend
    print("🎨 Starting Streamlit frontend...")
    try:
        frontend_process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", 
            "frontend.py", 
            "--server.port", "8501"
        ], cwd=Path(__file__).parent)
        
        print("✅ Frontend started!")
        print("=" * 50)
        print("🌐 Demo is ready!")
        print("📊 Backend API: http://localhost:8001")
        print("🎨 Frontend UI: http://localhost:8501")
        print("💡 Use Ctrl+C to stop both servers")
        print("=" * 50)
        
        # Wait for processes
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down demo...")
            
    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
    
    # Cleanup
    if backend_process:
        backend_process.terminate()
    if frontend_process:
        frontend_process.terminate()
    
    print("✅ Demo stopped!")


if __name__ == "__main__":
    main()
