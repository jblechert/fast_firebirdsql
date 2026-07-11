#!/usr/bin/env python3
"""
Test script to compare pymssql vs pyodbc migration for SeeburgerDB.py

This script tests both versions to ensure they produce identical results.
"""

import sys
import os
import datetime
import traceback

# Add the bstools directory to the path
sys.path.append('/home/mjb/src/bstools-dev')

def test_connection():
    """Test database connections for both versions"""
    print("=" * 60)
    print("TESTING DATABASE CONNECTIONS")
    print("=" * 60)
    
    # Test original pymssql version
    print("\n1. Testing original pymssql version...")
    try:
        from bstools.SeeburgerDB import SeeburgerDB as SeeburgerDB_pymssql
        db_pymssql = SeeburgerDB_pymssql()
        print(f"   ✓ pymssql connection successful: {db_pymssql.login_ok}")
    except Exception as e:
        print(f"   ✗ pymssql connection failed: {e}")
        traceback.print_exc()
        db_pymssql = None
    
    # Test new pyodbc version
    print("\n2. Testing new pyodbc version...")
    try:
        # Import the new version
        sys.path.insert(0, '/home/mjb/src/fast_firebird')
        from SeeburgerDB_pyodbc import SeeburgerDB as SeeburgerDB_pyodbc
        db_pyodbc = SeeburgerDB_pyodbc()
        print(f"   ✓ pyodbc connection successful: {db_pyodbc.login_ok}")
    except Exception as e:
        print(f"   ✗ pyodbc connection failed: {e}")
        traceback.print_exc()
        db_pyodbc = None
    
    return db_pymssql, db_pyodbc

def test_dfue_abrufe_structure(db_pymssql, db_pyodbc):
    """Test if both versions have the same dfue_abrufe structure"""
    print("\n" + "=" * 60)
    print("TESTING DFUE_ABRUFE DATA STRUCTURE")
    print("=" * 60)
    
    if not db_pymssql or not db_pyodbc:
        print("   ⚠ Skipping test - one or both connections failed")
        return False
    
    if not db_pymssql.login_ok or not db_pyodbc.login_ok:
        print("   ⚠ Skipping test - one or both logins failed")
        return False
    
    try:
        # Compare the keys at the top level
        pymssql_keys = set(db_pymssql.dfue_abrufe.keys())
        pyodbc_keys = set(db_pyodbc.dfue_abrufe.keys())
        
        print(f"   pymssql dfue_abrufe keys count: {len(pymssql_keys)}")
        print(f"   pyodbc dfue_abrufe keys count: {len(pyodbc_keys)}")
        
        if pymssql_keys == pyodbc_keys:
            print("   ✓ Top-level keys match")
            
            # Test a few sample entries for deeper comparison
            sample_keys = list(pymssql_keys)[:3]  # Test first 3 keys
            for key in sample_keys:
                pymssql_data = db_pymssql.dfue_abrufe[key]
                pyodbc_data = db_pyodbc.dfue_abrufe[key]
                
                if str(pymssql_data) == str(pyodbc_data):
                    print(f"   ✓ Data for key '{key}' matches")
                else:
                    print(f"   ✗ Data for key '{key}' differs")
                    print(f"     pymssql: {str(pymssql_data)[:100]}...")
                    print(f"     pyodbc:  {str(pyodbc_data)[:100]}...")
            
            return True
        else:
            print("   ✗ Top-level keys differ")
            missing_in_pyodbc = pymssql_keys - pyodbc_keys
            missing_in_pymssql = pyodbc_keys - pymssql_keys
            
            if missing_in_pyodbc:
                print(f"   Missing in pyodbc: {list(missing_in_pyodbc)[:5]}")
            if missing_in_pymssql:
                print(f"   Missing in pymssql: {list(missing_in_pymssql)[:5]}")
            
            return False
            
    except Exception as e:
        print(f"   ✗ Error comparing dfue_abrufe: {e}")
        traceback.print_exc()
        return False

def test_get_dfue_attachments(db_pymssql, db_pyodbc):
    """Test get_dfue_attachments method with sample date range"""
    print("\n" + "=" * 60)
    print("TESTING GET_DFUE_ATTACHMENTS METHOD")
    print("=" * 60)
    
    if not db_pymssql or not db_pyodbc:
        print("   ⚠ Skipping test - one or both connections failed")
        return False
    
    if not db_pymssql.login_ok or not db_pyodbc.login_ok:
        print("   ⚠ Skipping test - one or both logins failed")
        return False
    
    try:
        # Test with a recent date range
        von = datetime.datetime.now() - datetime.timedelta(days=7)
        bis = datetime.datetime.now()
        
        print(f"   Testing date range: {von.strftime('%Y-%m-%d')} to {bis.strftime('%Y-%m-%d')}")
        
        # Get results from both versions
        pymssql_result = db_pymssql.get_dfue_attachments(von, bis)
        pyodbc_result = db_pyodbc.get_dfue_attachments(von, bis)
        
        print(f"   pymssql result count: {len(pymssql_result)}")
        print(f"   pyodbc result count: {len(pyodbc_result)}")
        
        if len(pymssql_result) == len(pyodbc_result):
            print("   ✓ Result counts match")
            
            # Compare a few sample results
            sample_keys = list(pymssql_result.keys())[:3]
            for key in sample_keys:
                if key in pyodbc_result:
                    if pymssql_result[key] == pyodbc_result[key]:
                        print(f"   ✓ Data for key '{key}' matches")
                    else:
                        print(f"   ✗ Data for key '{key}' differs")
                else:
                    print(f"   ✗ Key '{key}' missing in pyodbc result")
            
            return True
        else:
            print("   ✗ Result counts differ")
            return False
            
    except Exception as e:
        print(f"   ✗ Error testing get_dfue_attachments: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("PYMSSQL TO PYODBC MIGRATION TEST")
    print("=" * 60)
    print("This script compares the original pymssql version with the new pyodbc version")
    print("to ensure they produce identical results.")
    
    # Test connections
    db_pymssql, db_pyodbc = test_connection()
    
    # Test dfue_abrufe structure
    test_dfue_abrufe_structure(db_pymssql, db_pyodbc)
    
    # Test get_dfue_attachments method
    test_get_dfue_attachments(db_pymssql, db_pyodbc)
    
    print("\n" + "=" * 60)
    print("MIGRATION TEST COMPLETED")
    print("=" * 60)
    print("Review the results above to ensure the migration is successful.")
    print("If all tests pass, the pyodbc version can replace the pymssql version.")

if __name__ == "__main__":
    main()
