#!/usr/bin/env python
"""
Quick start script to run the API server and show example curl commands.
"""
import subprocess
import sys
import time
import os

def install_flask():
    """Install Flask if not already installed."""
    try:
        import flask
    except ImportError:
        print("Flask not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "-q"])

def main():
    install_flask()
    
    print("\n" + "="*70)
    print("🚀 HYBRID GEOSPATIAL RETRIEVAL API SERVER")
    print("="*70)
    print("\n📝 Server will start on: http://127.0.0.1:5000")
    print("\n✅ Test Commands (use in another terminal):\n")
    
    print("1️⃣  Health Check:")
    print("   curl http://127.0.0.1:5000/api/health\n")
    
    print("2️⃣  Default Query (event_id=3651, radius_meters=500):")
    print("   curl http://127.0.0.1:5000/api/hybrid_geospatial_retrieval\n")
    
    print("3️⃣  Custom Query (with parameters):")
    print("   curl \"http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?event_id=3651&radius_meters=1000\"\n")
    
    print("="*70)
    print("Starting server...\n")
    
    # os.chdir("c:\\Users\\matta\\Desktop\\dati_eventi")
    subprocess.run([sys.executable, "api_server.py"])

if __name__ == "__main__":
    main()
