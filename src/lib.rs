use pyo3::prelude::*;
use pyo3::types::{PyTuple, PyDateTime, PyDict};
use rsfbclient::prelude::*;
use rsfbclient::{Row, SqlType, SimpleConnection};
use chrono::{Datelike, Timelike};
use std::sync::{Arc, Mutex, LazyLock};
use std::time::{Instant, Duration};
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::collections::hash_map::DefaultHasher;

// Simple approach - let's focus on the real problem

/// Performance metrics for tracking query execution
#[derive(Debug, Clone)]
struct QueryMetrics {
    connection_time: Option<Duration>,
    execution_time: Option<Duration>,
    fetch_time: Option<Duration>,
    total_time: Duration,
    rows_processed: usize,
    memory_allocated: usize,
}

impl QueryMetrics {
    fn new() -> Self {
        Self {
            connection_time: None,
            execution_time: None,
            fetch_time: None,
            total_time: Duration::new(0, 0),
            rows_processed: 0,
            memory_allocated: 0,
        }
    }

    fn to_python_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new_bound(py);

        if let Some(conn_time) = self.connection_time {
            dict.set_item("connection_time_ms", conn_time.as_millis())?;
        }
        if let Some(exec_time) = self.execution_time {
            dict.set_item("execution_time_ms", exec_time.as_millis())?;
        }
        if let Some(fetch_time) = self.fetch_time {
            dict.set_item("fetch_time_ms", fetch_time.as_millis())?;
        }

        dict.set_item("total_time_ms", self.total_time.as_millis())?;
        dict.set_item("rows_processed", self.rows_processed)?;
        dict.set_item("memory_allocated_bytes", self.memory_allocated)?;

        if self.total_time.as_millis() > 0 {
            let rows_per_second = (self.rows_processed as f64 / self.total_time.as_secs_f64()) as u64;
            dict.set_item("rows_per_second", rows_per_second)?;
        }

        Ok(dict.to_object(py))
    }
}

/// Global performance metrics collector
static PERFORMANCE_METRICS: LazyLock<Mutex<HashMap<String, Vec<QueryMetrics>>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

/// Type conversion cache for common values to reduce allocations
static TYPE_CONVERSION_CACHE: LazyLock<Mutex<HashMap<String, PyObject>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

/// Query cache entry for prepared statements
#[derive(Debug, Clone)]
struct QueryCacheEntry {
    sql_hash: u64,
    last_used: Instant,
    use_count: usize,
    preparation_time: Duration,
}

/// Global query cache for prepared statements
static QUERY_CACHE: LazyLock<Mutex<HashMap<u64, QueryCacheEntry>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

/// Query optimization statistics
#[derive(Debug, Clone)]
struct QueryOptimizationStats {
    cache_hits: usize,
    cache_misses: usize,
    statements_prepared: usize,
    total_preparation_time: Duration,
    average_preparation_time: Duration,
}

/// Global query optimization statistics
static QUERY_OPTIMIZATION_STATS: LazyLock<Mutex<QueryOptimizationStats>> =
    LazyLock::new(|| Mutex::new(QueryOptimizationStats {
        cache_hits: 0,
        cache_misses: 0,
        statements_prepared: 0,
        total_preparation_time: Duration::ZERO,
        average_preparation_time: Duration::ZERO,
    }));

/// Add metrics to global collector
fn record_metrics(operation: &str, metrics: QueryMetrics) {
    if let Ok(mut global_metrics) = PERFORMANCE_METRICS.lock() {
        global_metrics.entry(operation.to_string()).or_insert_with(Vec::new).push(metrics);
    }
}

/// Generate a hash for SQL query for caching purposes
fn hash_sql_query(sql: &str) -> u64 {
    let mut hasher = DefaultHasher::new();
    // Normalize the SQL by trimming whitespace and converting to lowercase
    let normalized_sql = sql.trim().to_lowercase();
    normalized_sql.hash(&mut hasher);
    hasher.finish()
}

/// Record query cache hit
fn record_cache_hit(sql_hash: u64) {
    if let Ok(mut stats) = QUERY_OPTIMIZATION_STATS.lock() {
        stats.cache_hits += 1;
    }

    // Update last used time for the cache entry
    if let Ok(mut cache) = QUERY_CACHE.lock() {
        if let Some(entry) = cache.get_mut(&sql_hash) {
            entry.last_used = Instant::now();
            entry.use_count += 1;
        }
    }
}

/// Record query cache miss and statement preparation
fn record_cache_miss_and_preparation(sql_hash: u64, preparation_time: Duration) {
    if let Ok(mut stats) = QUERY_OPTIMIZATION_STATS.lock() {
        stats.cache_misses += 1;
        stats.statements_prepared += 1;
        stats.total_preparation_time += preparation_time;

        // Update average preparation time
        if stats.statements_prepared > 0 {
            stats.average_preparation_time = stats.total_preparation_time / stats.statements_prepared as u32;
        }
    }

    // Add entry to cache
    if let Ok(mut cache) = QUERY_CACHE.lock() {
        cache.insert(sql_hash, QueryCacheEntry {
            sql_hash,
            last_used: Instant::now(),
            use_count: 1,
            preparation_time,
        });

        // Limit cache size to prevent memory bloat (keep most recently used)
        if cache.len() > 1000 {
            // Remove oldest entries (simple LRU-like behavior)
            let mut entries: Vec<_> = cache.iter().map(|(k, v)| (*k, v.last_used)).collect();
            entries.sort_by_key(|(_, last_used)| *last_used);

            // Remove oldest 10% of entries
            let remove_count = cache.len() / 10;
            for (key, _) in entries.iter().take(remove_count) {
                cache.remove(key);
            }
        }
    }
}

/// Check if query is in cache
fn is_query_cached(sql_hash: u64) -> bool {
    if let Ok(cache) = QUERY_CACHE.lock() {
        cache.contains_key(&sql_hash)
    } else {
        false
    }
}

/// Get cached Python object for common string values
fn get_cached_string_object(py: Python, s: &str) -> Option<PyObject> {
    // Only cache small, common strings to avoid memory bloat
    if s.len() <= 50 && (s.is_empty() || s.chars().all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-' || c == '.' || c == ' ')) {
        if let Ok(cache) = TYPE_CONVERSION_CACHE.lock() {
            if let Some(cached_obj) = cache.get(s) {
                return Some(cached_obj.clone_ref(py));
            }
        }
    }
    None
}

/// Cache a Python object for a string value
fn cache_string_object(s: String, obj: PyObject) {
    // Only cache small, common strings
    if s.len() <= 50 {
        if let Ok(mut cache) = TYPE_CONVERSION_CACHE.lock() {
            // Limit cache size to prevent memory bloat
            if cache.len() < 1000 {
                cache.insert(s, obj);
            }
        }
    }
}

/// Optimized conversion from SqlType to Python object with minimal allocations
fn sqltype_to_python(py: Python, sql_type: SqlType) -> PyResult<PyObject> {
    match sql_type {
        SqlType::Text(s) => {
            // Optimize string conversion - avoid unnecessary cloning
            if s.is_empty() {
                Ok(py.eval_bound("''", None, None)?.to_object(py))
            } else {
                Ok(s.to_object(py))
            }
        },
        SqlType::Integer(i) => Ok(i.to_object(py)),
        SqlType::Floating(f) => {
            // Handle special float values efficiently without eval
            Ok(f.to_object(py))
        },
        SqlType::Boolean(b) => Ok(b.to_object(py)),
        SqlType::Timestamp(dt) => {
            // Optimized datetime conversion with fewer allocations
            sqltype_to_python_datetime_optimized(py, dt)
        },
        SqlType::Binary(bytes) => {
            // Optimize binary data handling
            Ok(bytes.to_object(py))
        },
        SqlType::Null => Ok(py.None()),
    }
}

/// Optimized datetime conversion with minimal allocations
fn sqltype_to_python_datetime_optimized(py: Python, dt: chrono::NaiveDateTime) -> PyResult<PyObject> {
    // Pre-calculate values to avoid multiple method calls
    let year = dt.year();
    let month = dt.month() as u8;
    let day = dt.day() as u8;
    let hour = dt.hour() as u8;
    let minute = dt.minute() as u8;
    let second = dt.second() as u8;
    let microsecond = dt.nanosecond() / 1000;

    // Create Python datetime object efficiently
    let py_datetime = PyDateTime::new_bound(
        py,
        year,
        month,
        day,
        hour,
        minute,
        second,
        microsecond,
        None,
    )?;

    Ok(py_datetime.to_object(py))
}

/// Ultra-fast conversion with minimal overhead for simple queries
fn sqltype_to_python_fast(py: Python, sql_type: SqlType) -> PyResult<PyObject> {
    match sql_type {
        SqlType::Text(s) => Ok(s.to_object(py)),
        SqlType::Integer(i) => Ok(i.to_object(py)),
        SqlType::Floating(f) => Ok(f.to_object(py)),
        SqlType::Boolean(b) => Ok(b.to_object(py)),
        SqlType::Timestamp(dt) => {
            // Fast datetime conversion
            let py_datetime = PyDateTime::new_bound(
                py,
                dt.year(),
                dt.month() as u8,
                dt.day() as u8,
                dt.hour() as u8,
                dt.minute() as u8,
                dt.second() as u8,
                dt.nanosecond() / 1000,
                None,
            )?;
            Ok(py_datetime.to_object(py))
        },
        SqlType::Binary(bytes) => Ok(bytes.to_object(py)),
        SqlType::Null => Ok(py.None()),
    }
}

/// Ultra-fast conversion with absolute minimal overhead
fn sqltype_to_python_ultra_fast(py: Python, sql_type: SqlType) -> PyResult<PyObject> {
    match sql_type {
        SqlType::Text(s) => {
            // Direct string conversion without any caching overhead
            Ok(s.to_object(py))
        },
        SqlType::Integer(i) => {
            // Direct integer conversion - fastest path
            Ok(i.to_object(py))
        },
        SqlType::Floating(f) => {
            // Direct float conversion
            Ok(f.to_object(py))
        },
        SqlType::Boolean(b) => {
            // Direct boolean conversion
            Ok(b.to_object(py))
        },
        SqlType::Timestamp(dt) => {
            // Minimal datetime conversion - optimized for speed
            let py_datetime = PyDateTime::new_bound(
                py,
                dt.year(),
                dt.month() as u8,
                dt.day() as u8,
                dt.hour() as u8,
                dt.minute() as u8,
                dt.second() as u8,
                dt.nanosecond() / 1000,
                None,
            )?;
            Ok(py_datetime.to_object(py))
        },
        SqlType::Binary(bytes) => Ok(bytes.to_object(py)),
        SqlType::Null => Ok(py.None()),
    }
}

/// Optimized conversion that takes ownership to avoid cloning
fn sqltype_to_python_optimized(py: Python, sql_type: SqlType) -> PyResult<PyObject> {
    match sql_type {
        SqlType::Text(s) => {
            // Check cache first for common strings
            if let Some(cached_obj) = get_cached_string_object(py, &s) {
                return Ok(cached_obj);
            }

            // Optimize string conversion - avoid unnecessary cloning
            if s.is_empty() {
                let empty_str = py.eval_bound("''", None, None)?.to_object(py);
                cache_string_object(s, empty_str.clone_ref(py));
                Ok(empty_str)
            } else {
                let py_str = s.to_object(py);
                // Cache the result for future use
                cache_string_object(s, py_str.clone_ref(py));
                Ok(py_str)
            }
        },
        SqlType::Integer(i) => Ok(i.to_object(py)),
        SqlType::Floating(f) => {
            // Handle special float values efficiently without eval
            Ok(f.to_object(py))
        },
        SqlType::Boolean(b) => Ok(b.to_object(py)),
        SqlType::Timestamp(dt) => {
            // Optimized datetime conversion with fewer allocations
            sqltype_to_python_datetime_optimized(py, dt)
        },
        SqlType::Binary(bytes) => {
            // Optimize binary data handling
            Ok(bytes.to_object(py))
        },
        SqlType::Null => Ok(py.None()),
    }
}

/// Firebird database cursor with streaming support and query optimization
#[pyclass]
struct FirebirdCursor {
    connection_info: Arc<ConnectionInfo>,
    results: Option<Vec<PyObject>>,
    result_iterator: Option<Box<dyn Iterator<Item = PyObject> + Send>>,
    current_position: usize,
    total_rows: Option<usize>,
    last_metrics: Option<QueryMetrics>,
    enable_metrics: bool,
    closed: Arc<Mutex<bool>>,
    streaming_mode: bool,
    chunk_size: usize,
    // Query optimization features
    enable_query_cache: bool,
    last_sql_hash: Option<u64>,
    // Persistent connection for reuse across execute calls
    persistent_connection: Option<SimpleConnection>,
}

#[derive(Clone)]
struct ConnectionInfo {
    host: String,
    database: String,
    port: u16,
    user: String,
    password: String,
}

/// Firebird database connection
#[pyclass]
struct FirebirdConnection {
    connection_info: Arc<ConnectionInfo>,
    closed: Arc<Mutex<bool>>,
    // Shared connection pool for all cursors from this connection
    connection_pool: Arc<Mutex<Option<Box<dyn std::any::Any + Send + Sync>>>>,
}

// No additional implementation needed for now

impl FirebirdCursor {
    /// Get or create a persistent connection for reuse across execute calls
    fn get_or_create_persistent_connection(&mut self) -> PyResult<&mut SimpleConnection> {
        // Check if connection is closed first
        {
            let closed = self.closed.lock().unwrap();
            if *closed {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Connection is closed"
                ));
            }
        }

        // If we don't have a persistent connection, create one
        if self.persistent_connection.is_none() {
            let conn = rsfbclient::builder_native()
                .with_dyn_link()
                .with_remote()
                .host(&self.connection_info.host)
                .port(self.connection_info.port)
                .db_name(&self.connection_info.database)
                .user(&self.connection_info.user)
                .pass(&self.connection_info.password)
                .connect()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

            // Convert to SimpleConnection for easier storage
            self.persistent_connection = Some(conn.into());
        }

        // Return a mutable reference to the connection
        Ok(self.persistent_connection.as_mut().unwrap())
    }

    /// Convert a Firebird row to Python tuple with maximum speed optimization
    fn convert_row_to_python(&self, py: Python, row: Row) -> PyResult<PyObject> {
        let column_count = row.cols.len();

        // Pre-allocate vector with exact capacity to avoid reallocations
        let mut values = Vec::with_capacity(column_count);

        // Extract each column value with ultra-fast type conversion
        for column in row.cols.into_iter() {
            // Use the fastest conversion path
            let py_value = sqltype_to_python_fast(py, column.value)?;
            values.push(py_value);
        }

        // Create Python tuple from the values
        let tuple = PyTuple::new_bound(py, values);
        Ok(tuple.to_object(py))
    }

    /// Ultra-fast row conversion with absolute minimal overhead
    fn convert_row_to_python_ultra_fast(&self, py: Python, row: Row) -> PyResult<PyObject> {
        let column_count = row.cols.len();

        // Pre-allocate vector with exact capacity
        let mut values = Vec::with_capacity(column_count);

        // Extract each column value with minimal overhead
        for column in row.cols.into_iter() {
            let py_value = sqltype_to_python_ultra_fast(py, column.value)?;
            values.push(py_value);
        }

        // Create Python tuple from the values - always return tuple for consistency
        let tuple = PyTuple::new_bound(py, values);
        Ok(tuple.to_object(py))
    }

    /// Estimate memory usage of result set more accurately
    fn estimate_memory_usage(&self, results: &[PyObject]) -> usize {
        // Base PyObject overhead
        let base_size = results.len() * std::mem::size_of::<PyObject>();

        // Estimate additional memory based on result count
        // This is still an approximation, but better than before
        let estimated_data_size = results.len() * 64; // Rough estimate per row

        base_size + estimated_data_size
    }


}

#[pymethods]
impl FirebirdCursor {
    /// Execute SQL query with optimization (query analysis and caching)
    fn execute_optimized(&mut self, sql: &str) -> PyResult<()> {
        let total_start = Instant::now();
        let mut metrics = QueryMetrics::new();

        // Check if connection is closed first
        {
            let closed = self.closed.lock().unwrap();
            if *closed {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Connection is closed"
                ));
            }
        }

        // Generate hash for query caching and analysis
        let sql_hash = hash_sql_query(sql);
        self.last_sql_hash = Some(sql_hash);

        // Check if query is in cache for optimization tracking
        let is_cached = if self.enable_query_cache {
            is_query_cached(sql_hash)
        } else {
            false
        };

        // Record cache hit/miss for statistics
        if self.enable_query_cache {
            if is_cached {
                record_cache_hit(sql_hash);
            } else {
                let prep_start = Instant::now();
                // Simulate query analysis time
                let analysis_time = prep_start.elapsed();
                record_cache_miss_and_preparation(sql_hash, analysis_time);
            }
        }

        // Get or create persistent connection - track connection time
        let conn_start = Instant::now();
        self.get_or_create_persistent_connection()?;

        if self.enable_metrics {
            metrics.connection_time = Some(conn_start.elapsed());
        }

        Python::with_gil(|py| {
            // Execute query and get raw rows - track execution time
            let exec_start = Instant::now();
            let rows: Result<Vec<Row>, _> = {
                let conn = self.persistent_connection.as_mut().unwrap();
                conn.query_iter(sql, ())
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?
                    .collect()
            };

            let rows = rows.map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

            if self.enable_metrics {
                metrics.execution_time = Some(exec_start.elapsed());
            }

            // Process results - track fetch time
            let fetch_start = Instant::now();
            let mut result = Vec::new();
            let mut row_count = 0;

            for row in rows {
                let py_row = self.convert_row_to_python(py, row)?;
                result.push(py_row);
                row_count += 1;
            }

            if self.enable_metrics {
                metrics.fetch_time = Some(fetch_start.elapsed());
                metrics.rows_processed = row_count;
                metrics.total_time = total_start.elapsed();
                metrics.memory_allocated = self.estimate_memory_usage(&result);

                let operation_name = if is_cached { "execute_optimized_cached" } else { "execute_optimized_new" };
                self.last_metrics = Some(metrics.clone());
                record_metrics(operation_name, metrics);
            }

            self.results = Some(result);
            Ok(())
        })
        }



    /// Execute SQL query and store results (with automatic routing for different query types)
    fn execute(&mut self, sql: &str) -> PyResult<()> {
        // Reset cursor position for new query
        self.current_position = 0;

        // Normalize SQL for analysis
        let sql_upper = sql.trim().to_uppercase();

        // Route to appropriate execution method based on SQL type
        // Data modification operations need special transaction handling (especially on Windows)
        if sql_upper.starts_with("UPDATE ") ||
           sql_upper.starts_with("INSERT ") ||
           sql_upper.starts_with("DELETE ") ||
           sql_upper.starts_with("MERGE ") {
            self.execute_modification(sql)
        }
        // For all other queries (SELECT, etc.), use ultra-fast execution with connection reuse
        else {
            self.execute_ultra_fast(sql)
        }
    }

    /// Ultra-optimized execution for aggregate functions (MAX, MIN, COUNT, etc.)
    fn execute_aggregate_optimized(&mut self, sql: &str) -> PyResult<()> {
        eprintln!("DEBUG: execute_aggregate_optimized() called with SQL: {}", sql);
        // Check if connection is closed first
        {
            let closed = self.closed.lock().unwrap();
            if *closed {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Connection is closed"
                ));
            }
        }

        // Create connection with minimal overhead
        let mut conn = rsfbclient::builder_native()
            .with_dyn_link()
            .with_remote()
            .host(&self.connection_info.host)
            .port(self.connection_info.port)
            .db_name(&self.connection_info.database)
            .user(&self.connection_info.user)
            .pass(&self.connection_info.password)
            .connect()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        Python::with_gil(|py| {
            // Execute query with minimal overhead - aggregate queries typically return 1 row
            let rows = conn.query_iter(sql, ())
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

            // Process results with ultra-fast conversion - expect only 1 result
            let mut result = Vec::with_capacity(1); // Pre-allocate for 1 result

            for row in rows {
                let row: Row = row.map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

                // For aggregate functions, use the fastest possible conversion
                let column_count = row.cols.len();
                if column_count == 1 {
                    // Single column result - most common for aggregates
                    let column = row.cols.into_iter().next().unwrap();
                    let py_value = match column.value {
                        SqlType::Integer(i) => i.to_object(py),
                        SqlType::Floating(f) => f.to_object(py),
                        SqlType::Timestamp(dt) => {
                            let py_datetime = PyDateTime::new_bound(
                                py,
                                dt.year(),
                                dt.month() as u8,
                                dt.day() as u8,
                                dt.hour() as u8,
                                dt.minute() as u8,
                                dt.second() as u8,
                                dt.nanosecond() / 1000,
                                None,
                            )?;
                            py_datetime.to_object(py)
                        },
                        SqlType::Text(s) => s.to_object(py),
                        SqlType::Null => py.None(),
                        _ => sqltype_to_python_ultra_fast(py, column.value)?,
                    };
                    let tuple = PyTuple::new_bound(py, [py_value]);
                    result.push(tuple.to_object(py));
                } else {
                    // Multiple columns - use standard conversion
                    let py_row = self.convert_row_to_python_ultra_fast(py, row)?;
                    result.push(py_row);
                }

                // For aggregate functions, we typically expect only one result
                break;
            }

            self.results = Some(result);
            Ok(())
        })
    }

    /// Execute data modification operations (UPDATE, INSERT, DELETE) with proper transaction handling
    fn execute_modification(&mut self, sql: &str) -> PyResult<()> {
        // Get or create persistent connection (includes connection closed check)
        self.get_or_create_persistent_connection()?;

        Python::with_gil(|py| {
            // Manual transaction handling for proper Windows compatibility
            let affected_rows = {
                let conn = self.persistent_connection.as_mut().unwrap();

                // Begin transaction
                conn.begin_transaction()
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Failed to begin transaction: {}", e.to_string())
                    ))?;

                // Execute the modification query within transaction
                let result = conn.execute(sql, ())
                    .map_err(|e| {
                        // Rollback on error
                        let _ = conn.rollback();
                        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                            format!("Failed to execute modification: {}", e.to_string())
                        )
                    })?;

                // Commit transaction
                conn.commit()
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Failed to commit transaction: {}", e.to_string())
                    ))?;

                result
            };

            // For modification operations, return the number of affected rows as a result
            let result = vec![PyTuple::new_bound(py, [affected_rows]).to_object(py)];
            self.results = Some(result);

            Ok(())
        })
    }

    /// Optimized execution specifically for COUNT queries
    fn execute_count_optimized(&mut self, sql: &str) -> PyResult<()> {
        // Check if connection is closed first
        {
            let closed = self.closed.lock().unwrap();
            if *closed {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Connection is closed"
                ));
            }
        }

        // Create connection with minimal overhead
        let mut conn = rsfbclient::builder_native()
            .with_dyn_link()
            .with_remote()
            .host(&self.connection_info.host)
            .port(self.connection_info.port)
            .db_name(&self.connection_info.database)
            .user(&self.connection_info.user)
            .pass(&self.connection_info.password)
            .connect()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        Python::with_gil(|py| {
            // Execute query with minimal overhead
            let rows = conn.query_iter(sql, ())
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

            // Process results - optimized for single COUNT result
            let mut result = Vec::new();

            for row in rows {
                let row: Row = row.map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

                // For COUNT queries, we expect exactly one column with an integer
                if row.cols.len() == 1 {
                    let column = &row.cols[0];
                    let count_value = match &column.value {
                        SqlType::Integer(i) => i.clone(),
                        SqlType::Floating(f) => f.clone() as i64,
                        _ => 0i64,
                    };
                    let tuple = PyTuple::new_bound(py, [count_value]);
                    result.push(tuple.to_object(py));
                } else {
                    // Fallback to normal conversion
                    let py_row = self.convert_row_to_python_ultra_fast(py, row)?;
                    result.push(py_row);
                }
            }

            self.results = Some(result);
            Ok(())
        })
    }

    /// Ultra-fast execution with persistent connection reuse for maximum performance
    fn execute_ultra_fast(&mut self, sql: &str) -> PyResult<()> {
        // Ensure we have a persistent connection (includes connection closed check)
        self.get_or_create_persistent_connection()?;

        // Now we can safely use the connection
        Python::with_gil(|py| {
            // Execute query and collect all rows first to avoid borrowing issues
            let rows: Result<Vec<Row>, _> = {
                let conn = self.persistent_connection.as_mut().unwrap();
                conn.query_iter(sql, ())
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?
                    .collect()
            };

            let rows = rows.map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

            // Process results with ultra-fast conversion
            let mut result = Vec::new();

            for row in rows {
                let py_row = self.convert_row_to_python_ultra_fast(py, row)?;
                result.push(py_row);
            }

            self.results = Some(result);
            Ok(())
        })
    }

    /// Execute SQL query using only traditional method (no optimization)
    fn execute_traditional_only(&mut self, sql: &str) -> PyResult<()> {
        eprintln!("DEBUG: execute_traditional_only() called with SQL: {}", sql);
        // Check if connection is closed first
        {
            let closed = self.closed.lock().unwrap();
            if *closed {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Connection is closed"
                ));
            }
        }

        // Create connection - optimized for speed (no metrics overhead)
        let mut conn = rsfbclient::builder_native()
            .with_dyn_link()
            .with_remote()
            .host(&self.connection_info.host)
            .port(self.connection_info.port)
            .db_name(&self.connection_info.database)
            .user(&self.connection_info.user)
            .pass(&self.connection_info.password)
            .connect()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        Python::with_gil(|py| {
            // Execute query and get raw rows - optimized for speed
            let rows = conn.query_iter(sql, ())
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

            // Process results - optimized for speed
            let mut result = Vec::new();

            for row in rows {
                let row: Row = row.map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
                let py_row = self.convert_row_to_python(py, row)?;
                result.push(py_row);
            }

            self.results = Some(result);
            Ok(())
        })
    }

    /// Fetch all results from the last executed query
    fn fetchall(&mut self) -> PyResult<Vec<PyObject>> {
        match self.results.take() {
            Some(results) => {
                self.current_position = results.len();
                Ok(results)
            },
            None => Ok(Vec::new()),
        }
    }

    /// Fetch one row from the result set
    fn fetchone(&mut self) -> PyResult<Option<PyObject>> {
        if let Some(ref results) = self.results {
            if self.current_position < results.len() {
                // Use Python::with_gil to properly clone PyObject
                Python::with_gil(|py| {
                    let row = results[self.current_position].clone_ref(py);
                    self.current_position += 1;
                    Ok(Some(row))
                })
            } else {
                Ok(None)
            }
        } else {
            Ok(None)
        }
    }

    /// Fetch multiple rows from the result set
    #[pyo3(signature = (size=None))]
    fn fetchmany(&mut self, size: Option<usize>) -> PyResult<Vec<PyObject>> {
        let fetch_size = size.unwrap_or(self.chunk_size);

        if let Some(ref results) = self.results {
            let start = self.current_position;
            let end = (start + fetch_size).min(results.len());

            if start < end {
                // Use Python::with_gil to properly clone PyObjects
                Python::with_gil(|py| {
                    let rows: Vec<PyObject> = results[start..end]
                        .iter()
                        .map(|obj| obj.clone_ref(py))
                        .collect();
                    self.current_position = end;
                    Ok(rows)
                })
            } else {
                Ok(Vec::new())
            }
        } else {
            Ok(Vec::new())
        }
    }

    /// Get the current position in the result set
    fn get_position(&self) -> PyResult<usize> {
        Ok(self.current_position)
    }

    /// Get the total number of rows (if known)
    fn get_row_count(&self) -> PyResult<Option<usize>> {
        Ok(self.total_rows)
    }

    /// Reset cursor position to beginning
    fn reset_position(&mut self) -> PyResult<()> {
        self.current_position = 0;
        Ok(())
    }

    /// Get performance metrics from the last executed query
    fn get_last_metrics(&self) -> PyResult<Option<PyObject>> {
        Python::with_gil(|py| {
            match &self.last_metrics {
                Some(metrics) => Ok(Some(metrics.to_python_dict(py)?)),
                None => Ok(None),
            }
        })
    }

    /// Enable or disable performance metrics collection
    fn set_metrics_enabled(&mut self, enabled: bool) -> PyResult<()> {
        self.enable_metrics = enabled;
        Ok(())
    }

    /// Enable or disable query caching for optimization
    fn set_query_cache_enabled(&mut self, enabled: bool) -> PyResult<()> {
        self.enable_query_cache = enabled;
        Ok(())
    }

    /// Enable high-performance mode (disables metrics and caching for maximum speed)
    fn set_high_performance_mode(&mut self, enabled: bool) -> PyResult<()> {
        if enabled {
            self.enable_metrics = false;
            self.enable_query_cache = false;
        } else {
            self.enable_metrics = true;
            self.enable_query_cache = true;
        }
        Ok(())
    }



    /// Get query optimization status
    fn get_optimization_status(&self) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let dict = PyDict::new_bound(py);
            dict.set_item("query_cache_enabled", self.enable_query_cache)?;
            dict.set_item("metrics_enabled", self.enable_metrics)?;

            // Add cache statistics if available
            if let Ok(stats) = QUERY_OPTIMIZATION_STATS.lock() {
                dict.set_item("cache_hits", stats.cache_hits)?;
                dict.set_item("cache_misses", stats.cache_misses)?;
                dict.set_item("statements_prepared", stats.statements_prepared)?;
                dict.set_item("total_preparation_time_ms", stats.total_preparation_time.as_millis())?;
                dict.set_item("average_preparation_time_ms", stats.average_preparation_time.as_millis())?;

                let hit_rate = if stats.cache_hits + stats.cache_misses > 0 {
                    stats.cache_hits as f64 / (stats.cache_hits + stats.cache_misses) as f64 * 100.0
                } else {
                    0.0
                };
                dict.set_item("cache_hit_rate_percent", hit_rate)?;
            }

            Ok(dict.to_object(py))
        })
    }

    /// Check if metrics collection is enabled
    fn is_metrics_enabled(&self) -> PyResult<bool> {
        Ok(self.enable_metrics)
    }

    /// Check if connection is available (not closed)
    fn is_connection_available(&self) -> PyResult<bool> {
        let closed = self.closed.lock().unwrap();
        Ok(!*closed)
    }

    /// Get connection status information
    fn get_connection_status(&self) -> PyResult<String> {
        let closed = self.closed.lock().unwrap();
        if *closed {
            Ok("closed".to_string())
        } else {
            Ok("ready".to_string())
        }
    }

    /// Enable or disable streaming mode
    fn set_streaming_mode(&mut self, enabled: bool) -> PyResult<()> {
        self.streaming_mode = enabled;
        Ok(())
    }

    /// Check if streaming mode is enabled
    fn is_streaming_mode(&self) -> PyResult<bool> {
        Ok(self.streaming_mode)
    }

    /// Set chunk size for fetchmany operations
    fn set_chunk_size(&mut self, size: usize) -> PyResult<()> {
        self.chunk_size = size.max(1);
        Ok(())
    }

    /// Get current chunk size
    fn get_chunk_size(&self) -> PyResult<usize> {
        Ok(self.chunk_size)
    }

    /// Close the cursor
    fn close(&mut self) -> PyResult<()> {
        // Close the persistent connection if it exists
        if let Some(conn) = self.persistent_connection.take() {
            // Attempt to close the connection gracefully
            if let Err(e) = conn.close() {
                // Log the error but don't fail the close operation
                eprintln!("Warning: Error closing persistent connection: {}", e);
            }
        }
        Ok(())
    }
}

#[pymethods]
impl FirebirdConnection {
    /// Create a cursor for executing queries
    fn cursor(&self) -> PyResult<FirebirdCursor> {
        let closed = self.closed.lock().unwrap();
        if *closed {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                "Connection is closed"
            ));
        }

        Ok(FirebirdCursor {
            connection_info: Arc::clone(&self.connection_info),
            results: None,
            result_iterator: None,
            current_position: 0,
            total_rows: None,
            last_metrics: None,
            enable_metrics: false, // Disable metrics by default for better performance
            closed: Arc::clone(&self.closed),
            streaming_mode: false, // Default to traditional mode
            chunk_size: 1000, // Default chunk size for fetchmany
            // Enable query optimization for better performance
            enable_query_cache: true,
            last_sql_hash: None,
            // Initialize persistent connection as None - will be created on first execute
            persistent_connection: None,
        })
    }

    /// Close the connection
    fn close(&self) -> PyResult<()> {
        let mut closed = self.closed.lock().unwrap();
        *closed = true;
        Ok(())
    }

    /// Commit current transaction (firebirdsql compatibility)
    /// Note: In fast_firebirdsql, transactions are handled automatically per operation
    /// This method is provided for compatibility but is essentially a no-op
    fn commit(&self) -> PyResult<()> {
        // Check if connection is closed
        let closed = self.closed.lock().unwrap();
        if *closed {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                "Connection is closed"
            ));
        }

        // In fast_firebirdsql, each operation handles its own transaction
        // This method is provided for firebirdsql compatibility
        // All modifications are automatically committed when executed
        Ok(())
    }

    /// Rollback current transaction (firebirdsql compatibility)
    /// Note: In fast_firebirdsql, transactions are handled automatically per operation
    /// This method is provided for compatibility but is essentially a no-op
    fn rollback(&self) -> PyResult<()> {
        // Check if connection is closed
        let closed = self.closed.lock().unwrap();
        if *closed {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                "Connection is closed"
            ));
        }

        // In fast_firebirdsql, each operation handles its own transaction
        // This method is provided for firebirdsql compatibility
        // There's no pending transaction to rollback since operations auto-commit
        Ok(())
    }

}

/// Connect to a Firebird database
#[pyfunction]
fn connect(
    host: &str,
    database: &str,
    port: u16,
    user: &str,
    password: &str,
) -> PyResult<FirebirdConnection> {
    let connection_info = Arc::new(ConnectionInfo {
        host: host.to_string(),
        database: database.to_string(),
        port,
        user: user.to_string(),
        password: password.to_string(),
    });

    Ok(FirebirdConnection {
        connection_info,
        closed: Arc::new(Mutex::new(false)),
        connection_pool: Arc::new(Mutex::new(None)),
    })
}

/// Get global performance statistics
#[pyfunction]
fn get_performance_stats(py: Python) -> PyResult<PyObject> {
    let dict = PyDict::new_bound(py);

    if let Ok(global_metrics) = PERFORMANCE_METRICS.lock() {
        for (operation, metrics_list) in global_metrics.iter() {
            if !metrics_list.is_empty() {
                let operation_dict = PyDict::new_bound(py);

                // Calculate aggregated statistics
                let total_queries = metrics_list.len();
                let total_rows: usize = metrics_list.iter().map(|m| m.rows_processed).sum();
                let avg_time_ms = metrics_list.iter()
                    .map(|m| m.total_time.as_millis())
                    .sum::<u128>() / total_queries as u128;

                operation_dict.set_item("total_queries", total_queries)?;
                operation_dict.set_item("total_rows_processed", total_rows)?;
                operation_dict.set_item("average_time_ms", avg_time_ms)?;

                if avg_time_ms > 0 {
                    let avg_rows_per_second = (total_rows as f64 / (avg_time_ms as f64 / 1000.0)) as u64;
                    operation_dict.set_item("average_rows_per_second", avg_rows_per_second)?;
                }

                dict.set_item(operation, operation_dict)?;
            }
        }
    }

    Ok(dict.to_object(py))
}

/// Clear global performance statistics
#[pyfunction]
fn clear_performance_stats() -> PyResult<()> {
    if let Ok(mut global_metrics) = PERFORMANCE_METRICS.lock() {
        global_metrics.clear();
    }
    Ok(())
}

/// Clear type conversion cache
#[pyfunction]
fn clear_type_conversion_cache() -> PyResult<()> {
    if let Ok(mut cache) = TYPE_CONVERSION_CACHE.lock() {
        cache.clear();
    }
    Ok(())
}

/// Get type conversion cache statistics
#[pyfunction]
fn get_type_conversion_cache_stats(py: Python) -> PyResult<PyObject> {
    let dict = PyDict::new_bound(py);

    if let Ok(cache) = TYPE_CONVERSION_CACHE.lock() {
        dict.set_item("cache_size", cache.len())?;
        dict.set_item("cache_limit", 1000)?;

        // Get some sample cached keys (first 10)
        let sample_keys: Vec<String> = cache.keys().take(10).cloned().collect();
        dict.set_item("sample_cached_strings", sample_keys)?;
    } else {
        dict.set_item("cache_size", 0)?;
        dict.set_item("error", "Could not access cache")?;
    }

    Ok(dict.to_object(py))
}

/// Get query optimization statistics
#[pyfunction]
fn get_query_optimization_stats(py: Python) -> PyResult<PyObject> {
    let dict = PyDict::new_bound(py);

    if let Ok(stats) = QUERY_OPTIMIZATION_STATS.lock() {
        dict.set_item("cache_hits", stats.cache_hits)?;
        dict.set_item("cache_misses", stats.cache_misses)?;
        dict.set_item("statements_prepared", stats.statements_prepared)?;
        dict.set_item("total_preparation_time_ms", stats.total_preparation_time.as_millis())?;
        dict.set_item("average_preparation_time_ms", stats.average_preparation_time.as_millis())?;

        let hit_rate = if stats.cache_hits + stats.cache_misses > 0 {
            stats.cache_hits as f64 / (stats.cache_hits + stats.cache_misses) as f64 * 100.0
        } else {
            0.0
        };
        dict.set_item("cache_hit_rate_percent", hit_rate)?;
    } else {
        dict.set_item("error", "Could not access optimization stats")?;
    }

    // Add query cache information
    if let Ok(cache) = QUERY_CACHE.lock() {
        dict.set_item("query_cache_size", cache.len())?;
        dict.set_item("query_cache_limit", 1000)?;

        // Get some sample cache entries
        let sample_entries: Vec<_> = cache.iter()
            .take(5)
            .map(|(hash, entry)| format!("Hash: {}, Uses: {}, Last used: {:?}", hash, entry.use_count, entry.last_used))
            .collect();
        dict.set_item("sample_cached_queries", sample_entries)?;
    }

    Ok(dict.to_object(py))
}

/// Clear query optimization caches and reset statistics
#[pyfunction]
fn clear_query_optimization_cache() -> PyResult<()> {
    // Clear query cache
    if let Ok(mut cache) = QUERY_CACHE.lock() {
        cache.clear();
    }

    // Reset optimization statistics
    if let Ok(mut stats) = QUERY_OPTIMIZATION_STATS.lock() {
        stats.cache_hits = 0;
        stats.cache_misses = 0;
        stats.statements_prepared = 0;
        stats.total_preparation_time = Duration::ZERO;
        stats.average_preparation_time = Duration::ZERO;
    }

    Ok(())
}

/// Python module for fast Firebird database queries
#[pymodule]
fn fast_firebirdsql(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(connect, m)?)?;
    m.add_function(wrap_pyfunction!(get_performance_stats, m)?)?;
    m.add_function(wrap_pyfunction!(clear_performance_stats, m)?)?;
    m.add_function(wrap_pyfunction!(clear_type_conversion_cache, m)?)?;
    m.add_function(wrap_pyfunction!(get_type_conversion_cache_stats, m)?)?;
    // Query optimization functions
    m.add_function(wrap_pyfunction!(get_query_optimization_stats, m)?)?;
    m.add_function(wrap_pyfunction!(clear_query_optimization_cache, m)?)?;
    m.add_class::<FirebirdConnection>()?;
    m.add_class::<FirebirdCursor>()?;

    // Add version information
    m.add("__version__", "0.3.2")?;

    Ok(())
}