#!/usr/bin/env python3
"""
Test that all classes can be imported correctly.
"""

def test_imports():
    """Test importing all classes"""
    print("Testing imports...")
    
    # Test importing the main function
    from fast_firebirdsql import connect
    print("✅ connect function imported successfully")

    # Test importing the connection class
    from fast_firebirdsql import FirebirdConnection
    print("✅ FirebirdConnection class imported successfully")

    # Test importing the cursor class
    from fast_firebirdsql import FirebirdCursor
    print("✅ FirebirdCursor class imported successfully")
    
    # Test that we can create instances
    conn = connect(
        host="192.0.2.10",
        database="d:\\data\\example.fdb",
        port=3050,
        user="EXAMPLE_USER",
        password="REDACTED"
    )
    print("✅ Connection created successfully")
    
    cursor = conn.cursor()
    print("✅ Cursor created successfully")
    
    # Test types
    print(f"Connection type: {type(conn)}")
    print(f"Cursor type: {type(cursor)}")
    
    conn.close()
    print("✅ All imports and basic functionality working!")

if __name__ == "__main__":
    test_imports()
