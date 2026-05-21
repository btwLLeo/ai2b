#!/usr/bin/env python
"""
Test client for the Hybrid Geospatial Retrieval API using curl.
"""
import subprocess
import time
import sys
import json

BASE_URL = "http://127.0.0.1:5000"

def curl_request(endpoint, params=""):
    """Execute a curl request and return the response."""
    full_url = f"{BASE_URL}{endpoint}"
    if params:
        full_url += f"?{params}"
    
    try:
        result = subprocess.run(
            ["curl", "-s", full_url],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout
    except Exception as e:
        return f"Error: {str(e)}"

def print_result(title, response):
    """Pretty print the curl result."""
    print(f"\n{'='*70}")
    print(f"🧪 {title}")
    print('='*70)
    try:
        # Try to parse as JSON for pretty printing
        data = json.loads(response)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        # If not JSON, print as-is
        print(response)

def main():
    print("\n" + "="*70)
    print("🚀 TESTING HYBRID GEOSPATIAL RETRIEVAL API")
    print("="*70)
    
    # Wait for server to be ready
    print("\n⏳ Waiting for server to be ready...")
    for i in range(30):
        try:
            response = curl_request("/api/health")
            if "ok" in response:
                print("✅ Server is ready!\n")
                break
        except:
            pass
        time.sleep(1)
        sys.stdout.write(f"\rAttempt {i+1}/30...")
    else:
        print("❌ Server did not start in time!")
        return

    # Test 1: Health Check
    response = curl_request("/api/health")
    print_result("TEST 1: Health Check", response)

    # Test 2: Default query
    response = curl_request("/api/hybrid_geospatial_retrieval")
    print_result("TEST 2: Default Query (event_id=3651, radius=500m)", response)

    # Test 3: Custom radius
    response = curl_request("/api/hybrid_geospatial_retrieval", "event_id=3651&radius_meters=1000")
    print_result("TEST 3: Extended Radius (radius=1000m)", response)

    # Test 4: Non-existent event
    response = curl_request("/api/hybrid_geospatial_retrieval", "event_id=99999")
    print_result("TEST 4: Non-existent Event (error handling)", response)

    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETED")
    print("="*70)
    print("\n💡 Manual Testing Commands:")
    print("   curl http://127.0.0.1:5000/api/health")
    print("   curl http://127.0.0.1:5000/api/hybrid_geospatial_retrieval")
    print("   curl \"http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?event_id=3651&radius_meters=1000\"\n")

if __name__ == "__main__":
    main()
