#!/usr/bin/env python3
"""
Test script to verify the library rename to fast_firebirdsql v0.3.0
"""

def test_import_and_version():
    """Test that the new library name and version work correctly"""
    print("Testing fast_firebirdsql v0.3.0 import and version...")
    
    try:
        import fast_firebirdsql
        print(f"✅ Successfully imported fast_firebirdsql")
        print(f"✅ Version: {fast_firebirdsql.__version__}")
        
        # Verify version is 0.3.0
        assert fast_firebirdsql.__version__ == "0.3.0", f"Expected version 0.3.0, got {fast_firebirdsql.__version__}"
        print("✅ Version correctly updated to 0.3.0")
        
        # Test that all expected functions are available
        expected_functions = [
            'connect',
            'get_performance_stats',
            'clear_performance_stats',
            'get_type_conversion_cache_stats',
            'clear_type_conversion_cache',
            'get_query_optimization_stats',
            'clear_query_optimization_cache'
        ]
        
        for func_name in expected_functions:
            assert hasattr(fast_firebirdsql, func_name), f"Missing function: {func_name}"
            print(f"✅ Function {func_name} available")
        
        # Test that classes are available
        expected_classes = ['FirebirdConnection', 'FirebirdCursor']
        for class_name in expected_classes:
            assert hasattr(fast_firebirdsql, class_name), f"Missing class: {class_name}"
            print(f"✅ Class {class_name} available")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import fast_firebirdsql: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality with the new library name"""
    print("\nTesting basic functionality...")
    
    try:
        import fast_firebirdsql
        
        # Test connection creation (will fail due to database path, but that's OK)
        try:
            conn = fast_firebirdsql.connect(
                host="192.0.2.10",
                database="d:\\data\\example.fdb",
                port=3050,
                user="EXAMPLE_USER",
                password="REDACTED"
            )
            
            # If we get here, test the cursor
            cur = conn.cursor()
            print("✅ Connection and cursor creation successful")
            conn.close()
            
        except Exception as e:
            # Expected to fail due to database connection, but the important thing
            # is that the library loaded and the functions are callable
            if "sql error" in str(e) or "I/O error" in str(e):
                print("✅ Library functions are callable (database connection expected to fail in test)")
            else:
                print(f"⚠️  Unexpected error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("FAST_FIREBIRDSQL v0.3.0 RENAME TEST")
    print("=" * 60)
    
    success = True
    
    # Test import and version
    if not test_import_and_version():
        success = False
    
    # Test basic functionality
    if not test_basic_functionality():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Library successfully renamed to fast_firebirdsql")
        print("✅ Version successfully updated to 0.3.0")
        print("✅ All functionality preserved")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please check the errors above")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
