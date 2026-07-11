# Windows UPDATE Crash Fix - Version 0.3.1

## Problem Description

**Issue**: Windows builds of fast_firebirdsql crashed when executing UPDATE, INSERT, or DELETE operations, while SELECT operations worked correctly. This issue was specific to Windows and did not occur on Linux.

**Root Cause**: The library was using `query_iter()` for all SQL operations, including data modification operations (UPDATE/INSERT/DELETE). While this worked on Linux due to more lenient auto-commit behavior, Windows requires explicit transaction management for data modification operations.

## Technical Analysis

### Original Code Problem
```rust
// All operations used query_iter() - problematic for modifications
let rows = conn.query_iter(sql, ())
    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
```

### Why It Failed on Windows
1. **Transaction Handling**: Windows Firebird client requires explicit transaction commits for data modifications
2. **Auto-commit Behavior**: Linux was more forgiving with implicit commits
3. **Memory Management**: Uncommitted transactions could cause memory access violations on Windows

## Solution Implemented

### 1. SQL Operation Detection
Added logic to detect data modification operations:
```rust
// Check if this is a data modification operation
if sql_upper.starts_with("UPDATE ") || sql_upper.starts_with("INSERT ") || 
   sql_upper.starts_with("DELETE ") || sql_upper.starts_with("MERGE ") {
    self.execute_modification(sql)
}
```

### 2. Dedicated Modification Handler
Created `execute_modification()` method with proper transaction handling:
```rust
fn execute_modification(&mut self, sql: &str) -> PyResult<()> {
    // ... connection setup ...
    
    Python::with_gil(|py| {
        // Use with_transaction for proper transaction handling
        let affected_rows = conn.with_transaction(|tr| {
            // Execute the modification query within transaction
            tr.execute(sql, ())
        }).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Failed to execute modification with transaction: {}", e.to_string())
        ))?;

        // Return the number of affected rows
        let result = vec![PyTuple::new_bound(py, [affected_rows]).to_object(py)];
        self.results = Some(result);
        
        Ok(())
    })
}
```

### 3. Key Improvements
- **Explicit Transactions**: Uses `conn.with_transaction()` for automatic commit/rollback
- **Error Handling**: Better error messages for transaction failures
- **Return Values**: Returns affected row count for modification operations
- **Platform Compatibility**: Works consistently across Windows and Linux

## Testing

### Test Script
Created `test_windows_updates.py` to verify the fix:
- Tests connection establishment
- Tests SELECT operations (baseline)
- Tests INSERT operations
- Tests UPDATE operations (critical test)
- Tests DELETE operations
- Verifies no crashes occur

### Expected Results
- ✅ All operations complete without crashes
- ✅ UPDATE operations properly modify data
- ✅ Transactions are properly committed
- ✅ Error handling works correctly

## Version Changes

### Version 0.3.1 Changes
- **Fixed**: Windows crash on UPDATE/INSERT/DELETE operations
- **Added**: Proper transaction handling for data modifications
- **Added**: Better error messages for transaction failures
- **Added**: Test script for Windows UPDATE operations

### Version 0.3.2 Changes (Critical Compatibility Fix)
- **Fixed**: Missing `commit()` and `rollback()` methods on FirebirdConnection
- **Added**: `conn.commit()` method for firebirdsql compatibility
- **Added**: `conn.rollback()` method for firebirdsql compatibility
- **Resolved**: AttributeError: 'builtins.FirebirdConnection' object has no attribute 'commit'

### Files Modified
- `src/lib.rs`: Added `execute_modification()`, `commit()`, and `rollback()` methods
- `pyproject.toml`: Version bump to 0.3.2
- `Cargo.toml`: Version bump to 0.3.2
- Added: `test_windows_updates.py`
- Added: `test_commit_rollback.py`
- Added: `WINDOWS_UPDATE_FIX.md` (this file)

## Installation

### Windows Wheel (Latest)
```bash
pip install fast_firebirdsql-0.3.2-cp313-cp313-win_amd64.whl
```

### Verification
Run the test script to verify the fix:
```bash
python test_windows_updates.py
```

## Compatibility

- **Windows**: ✅ Fixed - no more crashes on UPDATE operations
- **Linux**: ✅ Maintained - continues to work as before
- **Python**: 3.13+ (as specified in wheel)
- **Firebird**: All supported versions

## Performance Impact

- **SELECT Operations**: No performance impact (same code path)
- **UPDATE/INSERT/DELETE**: Minimal overhead from explicit transaction handling
- **Memory Usage**: Improved due to proper transaction cleanup
- **Error Recovery**: Better due to automatic rollback on failures

## Future Considerations

1. **Batch Operations**: Could optimize multiple modifications in single transaction
2. **Transaction Control**: Could expose manual transaction control to users
3. **Connection Pooling**: Could reuse connections with proper transaction state
4. **Async Support**: Could add async transaction support in future versions

## Conclusion

This fix resolves the critical Windows crash issue while maintaining full compatibility with existing code. The solution follows Firebird best practices for transaction management and provides better error handling across all platforms.
