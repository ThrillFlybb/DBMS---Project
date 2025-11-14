"""
Quick test script to verify the demo backend is working
"""
import requests
import json

BASE_URL = "http://localhost:5001"

def test_endpoint(name, endpoint):
    """Test an API endpoint"""
    try:
        url = f"{BASE_URL}{endpoint}"
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print(f"   ✅ Status: {response.status_code} OK")
            data = response.json()
            print(f"   📦 Response keys: {list(data.keys()) if isinstance(data, dict) else 'Array'}")
            if isinstance(data, dict) and 'items' in data:
                print(f"   📊 Items returned: {len(data.get('items', []))}")
            return True
        else:
            print(f"   ❌ Status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection Error: Backend not running on {BASE_URL}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("Testing Demo Backend Server")
    print("=" * 60)
    
    results = []
    
    # Test all endpoints
    results.append(("Health Check", test_endpoint("Health Check", "/health")))
    results.append(("Metrics", test_endpoint("Metrics", "/metrics")))
    results.append(("Queries", test_endpoint("Queries", "/queries")))
    results.append(("Statistics", test_endpoint("Statistics", "/statistics")))
    results.append(("Benchmarks", test_endpoint("Benchmarks", "/benchmarks")))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Backend is working correctly.")
        print("\nNext steps:")
        print("1. Go to Settings in your main app (http://localhost:5000)")
        print("2. Set Data Source to 'REST'")
        print("3. Set Backend URL to: http://localhost:5001")
        print("4. Save and verify data loads from backend")
    else:
        print("\n⚠️  Some tests failed. Check if backend is running.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()

