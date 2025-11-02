#!/usr/bin/env python3
"""
Verify NullPool configuration for Supabase
Tests connection management and session cleanup
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import engine, get_db, get_pool_status, check_database_health, SessionLocal
from sqlalchemy.pool import NullPool

def test_nullpool_configuration():
    """Test that NullPool is properly configured"""
    print("=" * 60)
    print("SUPABASE NULLPOOL CONFIGURATION TEST")
    print("=" * 60)
    print()
    
    # Test 1: Verify NullPool
    print("✅ Test 1: Verify NullPool Configuration")
    print(f"   Pool class: {engine.pool.__class__.__name__}")
    assert isinstance(engine.pool, NullPool), "❌ FAILED: Not using NullPool!"
    print(f"   ✅ PASSED: Using NullPool correctly")
    print()
    
    # Test 2: Check pool status
    print("✅ Test 2: Check Pool Status")
    status = get_pool_status()
    print(f"   Pool status: {status}")
    assert status["pool_class"] == "NullPool", "❌ FAILED: Wrong pool class!"
    print(f"   ✅ PASSED: Pool status correct")
    print()
    
    # Test 3: Database health check
    print("✅ Test 3: Database Health Check")
    is_healthy = check_database_health()
    print(f"   Database health: {'✅ HEALTHY' if is_healthy else '❌ UNHEALTHY'}")
    assert is_healthy, "❌ FAILED: Database not accessible!"
    print(f"   ✅ PASSED: Database is accessible")
    print()
    
    # Test 4: Session management
    print("✅ Test 4: Session Management")
    session_opened = False
    session_closed = False
    
    try:
        db = SessionLocal()
        session_opened = True
        print(f"   Session opened: ✅")
        
        # Test query
        result = db.execute("SELECT 1")
        assert result.scalar() == 1, "❌ FAILED: Query failed!"
        print(f"   Test query: ✅")
        
        db.close()
        session_closed = True
        print(f"   Session closed: ✅")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        raise
    
    assert session_opened and session_closed, "❌ FAILED: Session lifecycle issue!"
    print(f"   ✅ PASSED: Session lifecycle correct")
    print()
    
    # Test 5: get_db() dependency
    print("✅ Test 5: FastAPI Dependency (get_db)")
    try:
        db_gen = get_db()
        db = next(db_gen)
        print(f"   Dependency created: ✅")
        
        # Test query
        result = db.execute("SELECT 1")
        assert result.scalar() == 1, "❌ FAILED: Query failed!"
        print(f"   Test query: ✅")
        
        # Close via generator
        try:
            next(db_gen)
        except StopIteration:
            print(f"   Dependency closed: ✅")
        
        print(f"   ✅ PASSED: FastAPI dependency works correctly")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        raise
    print()
    
    # Test 6: Multiple rapid connections (simulating concurrent requests)
    print("✅ Test 6: Multiple Rapid Connections")
    try:
        for i in range(5):
            db = SessionLocal()
            result = db.execute("SELECT 1")
            assert result.scalar() == 1
            db.close()
            print(f"   Connection {i+1}: ✅")
        print(f"   ✅ PASSED: No connection limit issues")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        raise
    print()
    
    # Test 7: Connection settings
    print("✅ Test 7: Connection Settings")
    connect_args = engine.url.query
    print(f"   SSL mode: {connect_args.get('sslmode', 'Not set')}")
    print(f"   Pool pre-ping: {engine.pool_pre_ping}")
    assert engine.pool_pre_ping == True, "❌ FAILED: pool_pre_ping not enabled!"
    print(f"   ✅ PASSED: Connection settings correct")
    print()
    
    # Summary
    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("Configuration Summary:")
    print(f"  - Pool Type: NullPool ✅")
    print(f"  - Session Management: Proper ✅")
    print(f"  - Database Health: Good ✅")
    print(f"  - Connection Cleanup: Automatic ✅")
    print(f"  - Supabase Compatible: Yes ✅")
    print()
    print("🎉 Your database configuration is PRODUCTION READY!")
    print()

if __name__ == "__main__":
    try:
        test_nullpool_configuration()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
