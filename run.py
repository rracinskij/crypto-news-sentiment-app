"""
Simple launcher script for the Crypto News Sentiment App.
Run this with: python run.py
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

if __name__ == "__main__":
    from main import APP
    import uvicorn
    
    print("🚀 Starting Crypto News Sentiment App...")
    print("📍 Access the app at: http://localhost:8000")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 50)
    
    # Check if API key is available
    if not os.getenv("OPENROUTER_API_KEY"):
        print("⚠️  WARNING: OPENROUTER_API_KEY not found in environment or .env file")
        print("   Create a .env file in the project root with your API key:")
        print("   OPENROUTER_API_KEY=sk-or-your-actual-key-here")
        print("-" * 50)
    
    uvicorn.run(APP, host="0.0.0.0", port=8000)
