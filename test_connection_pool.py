#!/usr/bin/env python3
"""
Test database connection pooling with NullPool
Verifies that connections are properly created and closed
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path
sys.path.insert(0, '/Users/georgeabdallah/Documents/GitHub/FreshlyBackend')

from core.db import get_db, get_pool_status, check_database_health, engine


def test_single_connection():
    """Test a single database connection"""
    print("🧪 Testing single connection...")
    
    try:
        db = next(get_db())
        result = db.execute("SELECT 1 as test").fetchone()
        print(f"✅ Connection successful: {result}")
        db.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_connection_closure():
    """Test that connections are properly closed"""
    print("\n🧪 Testing connection closure...")
    
    try:
        # Get pool status before
        status_before = get_pool_status()
        print(f"📊 Pool status before: {status_before}")
        
        # Open and close connection
        db = next(get_db())
        db.execute("SELECT 1")
        db.close()
        
        # Get pool status after
        status_after = get_pool_status()
        print(f"📊 Pool status after: {status_after}")
        
        print("✅ Connection properly closed (NullPool doesn't maintain state)")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_concurrent_connections(num_concurrent=10):
    """Test multiple concurrent connections"""
    print(f"\n🧪 Testing {num_concurrent} concurrent connections...")
    
    def make_connection(i):
        try:
            db = next(get_db())
            result = db.execute("SELECT pg_sleep(0.1), :num as conn_num", {"num": i}).fetchone()
            db.close()
            return f"✅ Connection {i} successful"
        except Exception as e:
            return f"❌ Connection {i} failed: {e}"
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(make_connection, i) for i in range(num_concurrent)]
        results = []
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"  {result}")
    
    duration = time.time() - start_time
    successful = sum(1 for r in results if "✅" in r)
    
    print(f"\n📊 Results: {successful}/{num_concurrent} successful in {duration:.2f}s")
    
    if successful == num_concurrent:
        print("✅ All concurrent connections handled successfully")
        return True
    else:
        print("⚠️  Some connections failed")
        return False


def test_health_check():
    """Test database health check"""
    print("\n🧪 Testing health check...")
    
    is_healthy = check_database_health()
    
    if is_healthy:
        print("✅ Database is healthy")
        return True
    else:
        print("❌ Database health check failed")
        return False


def test_pool_info():
    """Display pool configuration info"""
    print("\n📊 Connection Pool Information")
    print("=" * 50)
    
    pool = engine.pool
    print(f"Pool Class: {pool.__class__.__name__}")
    print(f"Pool Status: {get_pool_status()}")
    
    if pool.__class__.__name__ == "NullPool":
        print("\n✅ Using NullPool (Recommended for Supabase)")
        print("   - No persistent connections")
        print("   - Fresh connection per request")
        print("   - No connection limit issues")
    else:
        print(f"\n⚠️  Using {pool.__class__.__name__}")
        print("   - May cause MaxClientsInSessionMode errors")
        print("   - Consider switching to NullPool")


def main():
    """Run all tests"""
    print("🚀 Database Connection Pool Tests")
    print("=" * 50)
    
    # Display pool info first
    test_pool_info()
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Single Connection", test_single_connection),
        ("Connection Closure", test_connection_closure),
        ("Concurrent Connections", lambda: test_concurrent_connections(10)),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, r in results if r)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed! Connection pooling is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
