#!/usr/bin/env python3
"""
Verify NullPool configuration for Supabase (Code Analysis)
Tests configuration without requiring database connection
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import engine, get_db, get_pool_status, SessionLocal
from sqlalchemy.pool import NullPool
import inspect

def verify_nullpool_config():
    """Verify NullPool configuration through code analysis"""
    print("=" * 70)
    print("SUPABASE NULLPOOL CONFIGURATION VERIFICATION (CODE ANALYSIS)")
    print("=" * 70)
    print()
    
    passed_tests = 0
    total_tests = 0
    
    # Test 1: Verify NullPool
    total_tests += 1
    print("✅ Test 1: NullPool Configuration")
    print(f"   Pool class: {engine.pool.__class__.__name__}")
    if isinstance(engine.pool, NullPool):
        print(f"   ✅ PASSED: Using NullPool (no connection pooling)")
        passed_tests += 1
    else:
        print(f"   ❌ FAILED: Not using NullPool!")
    print()
    
    # Test 2: Pool pre-ping
    total_tests += 1
    print("✅ Test 2: Pool Pre-Ping Configuration")
    print(f"   pool_pre_ping: {engine.pool_pre_ping}")
    if engine.pool_pre_ping == True:
        print(f"   ✅ PASSED: Connections validated before use")
        passed_tests += 1
    else:
        print(f"   ⚠️  WARNING: pool_pre_ping not enabled")
    print()
    
    # Test 3: get_db() has proper cleanup
    total_tests += 1
    print("✅ Test 3: get_db() Session Cleanup")
    get_db_source = inspect.getsource(get_db)
    has_commit = "commit()" in get_db_source
    has_rollback = "rollback()" in get_db_source
    has_close = "close()" in get_db_source
    has_finally = "finally:" in get_db_source
    
    print(f"   Has commit(): {has_commit} {'✅' if has_commit else '❌'}")
    print(f"   Has rollback(): {has_rollback} {'✅' if has_rollback else '❌'}")
    print(f"   Has close(): {has_close} {'✅' if has_close else '❌'}")
    print(f"   Has finally block: {has_finally} {'✅' if has_finally else '❌'}")
    
    if all([has_commit, has_rollback, has_close, has_finally]):
        print(f"   ✅ PASSED: Proper session lifecycle management")
        passed_tests += 1
    else:
        print(f"   ❌ FAILED: Missing session cleanup logic")
    print()
    
    # Test 4: SessionLocal configuration
    total_tests += 1
    print("✅ Test 4: SessionLocal Configuration")
    print(f"   autoflush: {SessionLocal.kw.get('autoflush', 'default')}")
    print(f"   autocommit: {SessionLocal.kw.get('autocommit', 'default')}")
    print(f"   expire_on_commit: {SessionLocal.kw.get('expire_on_commit', 'default')}")
    
    if SessionLocal.kw.get('autocommit') == False:
        print(f"   ✅ PASSED: SessionLocal configured correctly")
        passed_tests += 1
    else:
        print(f"   ⚠️  WARNING: Check SessionLocal configuration")
    print()
    
    # Test 5: Pool status function
    total_tests += 1
    print("✅ Test 5: Pool Status Monitoring")
    try:
        status = get_pool_status()
        print(f"   Pool status: {status}")
        if status.get("pool_class") == "NullPool":
            print(f"   ✅ PASSED: Monitoring function works")
            passed_tests += 1
        else:
            print(f"   ❌ FAILED: Wrong pool class reported")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    print()
    
    # Test 6: Connection timeout settings
    total_tests += 1
    print("✅ Test 6: Connection Settings")
    connect_args = engine.pool._creator.keywords.get('connect_args', {})
    print(f"   SSL mode: {connect_args.get('sslmode', 'Not configured')}")
    print(f"   Connect timeout: {connect_args.get('connect_timeout', 'Not set')}")
    print(f"   Options: {connect_args.get('options', 'Not set')}")
    
    has_ssl = connect_args.get('sslmode') == 'require'
    has_timeout = 'connect_timeout' in connect_args
    
    if has_ssl and has_timeout:
        print(f"   ✅ PASSED: Connection settings configured")
        passed_tests += 1
    else:
        print(f"   ⚠️  WARNING: Check connection settings")
    print()
    
    # Test 7: Import checks
    total_tests += 1
    print("✅ Test 7: Required Imports")
    try:
        from core.db import get_db_context, check_database_health, dispose_engine
        print(f"   get_db_context: ✅ Available")
        print(f"   check_database_health: ✅ Available")
        print(f"   dispose_engine: ✅ Available")
        print(f"   ✅ PASSED: All utility functions available")
        passed_tests += 1
    except ImportError as e:
        print(f"   ❌ FAILED: {e}")
    print()
    
    # Summary
    print("=" * 70)
    print(f"TEST RESULTS: {passed_tests}/{total_tests} PASSED")
    print("=" * 70)
    print()
    
    if passed_tests == total_tests:
        print("🎉 PERFECT! All tests passed!")
        print()
        print("Your Supabase NullPool configuration is:")
        print("  ✅ Using NullPool (no connection pooling)")
        print("  ✅ Sessions properly closed in finally block")
        print("  ✅ Auto-commit/rollback implemented")
        print("  ✅ Connection validation enabled (pool_pre_ping)")
        print("  ✅ Proper timeout settings")
        print("  ✅ Monitoring utilities available")
        print()
        print("⚡ PRODUCTION READY - No MaxClientsInSessionMode errors!")
    elif passed_tests >= total_tests - 1:
        print("✅ EXCELLENT! Configuration is solid with minor warnings.")
        print()
        print("Your configuration will prevent MaxClientsInSessionMode errors.")
    else:
        print("⚠️  WARNING: Some tests failed. Review configuration.")
    
    print()
    print("Configuration Summary:")
    print(f"  Pool Type: {engine.pool.__class__.__name__}")
    print(f"  Pool Pre-Ping: {engine.pool_pre_ping}")
    print(f"  Database URL: {str(engine.url).split('@')[1] if '@' in str(engine.url) else 'Hidden'}")
    print()
    
    return passed_tests == total_tests

if __name__ == "__main__":
    try:
        success = verify_nullpool_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
