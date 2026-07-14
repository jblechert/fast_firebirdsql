use pyo3::exceptions::{PyRuntimeError, PyTypeError};
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::{PyBool, PyBytes, PyDict, PyTuple, PyType};
use pyo3::IntoPyObjectExt;
use rsfbclient::prelude::*;
use rsfbclient::{FbError, Row, SimpleConnection, SqlType};
use chrono::{NaiveDate, NaiveDateTime};
use std::collections::HashMap;
use std::sync::{Arc, LazyLock, Mutex};
use std::time::{Duration, Instant};

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
    fn to_python_dict(&self, py: Python) -> PyResult<Py<PyAny>> {
        let dict = PyDict::new(py);

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

        dict.into_py_any(py)
    }
}

/// Global performance metrics collector
static PERFORMANCE_METRICS: LazyLock<Mutex<HashMap<String, Vec<QueryMetrics>>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

/// Type conversion cache for common values to reduce allocations
static TYPE_CONVERSION_CACHE: LazyLock<Mutex<HashMap<String, Py<PyAny>>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

/// Query cache entry (statistics only; rsfbclient maintains the real statement cache)
#[derive(Debug, Clone)]
struct QueryCacheEntry {
    last_used: Instant,
    use_count: usize,
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

fn runtime_error(msg: impl Into<String>) -> PyErr {
    PyErr::new::<PyRuntimeError, _>(msg.into())
}

/// Does this error leave the connection unusable, so that it must be
/// discarded and rebuilt rather than reused?
///
/// - `Io`: the socket to the server is gone.
/// - SQLCODE -902: general fatal error, typically "Error writing/reading
///   data to the connection" (a dropped or half-open connection).
/// - SQLCODE -901: "unrecoverable conflict with limbo transaction" and
///   similar unrecoverable states.
/// - SQLCODE -502: "attempt to reopen an open cursor" -- the cached
///   prepared statement is in a bad state; dropping the connection clears
///   rsfbclient's statement cache so the next call starts clean.
///
/// Ordinary SQL errors (syntax -104, constraint violations, etc.) are NOT
/// fatal: the connection stays perfectly usable, so they must not trigger
/// a reconnect.
fn is_fatal_conn_error(e: &FbError) -> bool {
    match e {
        FbError::Io(_) => true,
        FbError::Sql { code, .. } => matches!(*code, -902 | -901 | -502),
        FbError::Other(_) => false,
    }
}

/// Firebird wire types as they appear in Column::raw_type (nullable bit
/// stripped). raw_type preserves the column's declared type from before
/// rsfbclient's buffer coercion, which lets us undo coercion artefacts.
mod wire_type {
    pub const TEXT: u32 = 452; // CHAR(n)
    pub const DOUBLE: u32 = 480;
    pub const FLOAT: u32 = 482;
    pub const LONG: u32 = 496;
    pub const SHORT: u32 = 500;
    pub const TIMESTAMP: u32 = 510;
    pub const TYPE_TIME: u32 = 560;
    pub const TYPE_DATE: u32 = 570;
    pub const INT64: u32 = 580;
    pub const BOOLEAN: u32 = 32764;
}

/// DB-API description internal_size for fixed-width wire types
fn wire_internal_size(raw_type: u32) -> Option<i32> {
    match raw_type {
        wire_type::SHORT => Some(2),
        wire_type::LONG | wire_type::FLOAT | wire_type::TYPE_DATE | wire_type::TYPE_TIME => Some(4),
        wire_type::INT64 | wire_type::DOUBLE | wire_type::TIMESTAMP => Some(8),
        wire_type::BOOLEAN => Some(1),
        _ => None, // CHAR/VARCHAR/BLOB: declared length not exposed by rsfbclient
    }
}

/// Does the statement contain a top-level RETURNING clause? Skips string
/// literals, quoted identifiers and comments so that e.g.
/// `... SET note = 'returning soon'` does not count.
fn contains_returning(sql: &str) -> bool {
    let bytes = sql.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        match bytes[i] {
            b'\'' | b'"' => {
                let quote = bytes[i];
                i += 1;
                while i < bytes.len() {
                    if bytes[i] == quote {
                        if bytes.get(i + 1) == Some(&quote) {
                            i += 2; // escaped quote ('' or "")
                            continue;
                        }
                        break;
                    }
                    i += 1;
                }
                i += 1;
            }
            b'-' if bytes.get(i + 1) == Some(&b'-') => {
                while i < bytes.len() && bytes[i] != b'\n' {
                    i += 1;
                }
            }
            b'/' if bytes.get(i + 1) == Some(&b'*') => {
                i += 2;
                while i + 1 < bytes.len() && !(bytes[i] == b'*' && bytes[i + 1] == b'/') {
                    i += 1;
                }
                i += 2;
            }
            c if c.is_ascii_alphabetic() || c == b'_' => {
                let start = i;
                while i < bytes.len()
                    && (bytes[i].is_ascii_alphanumeric() || bytes[i] == b'_' || bytes[i] == b'$')
                {
                    i += 1;
                }
                if sql[start..i].eq_ignore_ascii_case("returning") {
                    return true;
                }
            }
            _ => i += 1,
        }
    }
    false
}

/// Convert a Firebird column value to the corresponding Python object.
///
/// raw_type is the column's declared wire type; it lets us undo the
/// coercions rsfbclient applies to the fetch buffers:
/// - CHAR(n) is space-padded by the server -> trim trailing spaces
/// - NUMERIC/DECIMAL is coerced to DOUBLE -> reconstruct decimal.Decimal
/// - DATE and TIME are coerced to TIMESTAMP -> datetime.date / time
fn sqltype_to_python(py: Python, raw_type: u32, sql_type: SqlType) -> PyResult<Py<PyAny>> {
    match sql_type {
        SqlType::Text(s) => {
            if raw_type == wire_type::TEXT {
                // CHAR(n): the server pads with spaces; firebirdsql trims
                s.trim_end_matches(' ').into_py_any(py)
            } else {
                s.into_py_any(py)
            }
        },
        SqlType::Integer(i) => i.into_py_any(py),
        SqlType::Floating(f) => {
            if matches!(raw_type, wire_type::SHORT | wire_type::LONG | wire_type::INT64) {
                // Declared as an integer type but arrived as a float: this
                // is a NUMERIC/DECIMAL column that rsfbclient coerced to
                // DOUBLE. Reconstruct a decimal.Decimal from the shortest
                // round-trip representation. Exact up to the ~15-16
                // significant digits a double can carry.
                let s = format!("{f}");
                let d = decimal_type(py)?.bind(py).call1((s,))?;
                Ok(d.unbind())
            } else {
                f.into_py_any(py)
            }
        },
        SqlType::Boolean(b) => b.into_py_any(py),
        // pyo3's chrono conversions work under the limited API (abi3)
        SqlType::Timestamp(dt) => match raw_type {
            wire_type::TYPE_DATE => dt.date().into_py_any(py),
            wire_type::TYPE_TIME => dt.time().into_py_any(py),
            _ => dt.into_py_any(py),
        },
        // Vec<u8>.to_object() would produce a Python list of ints; binary
        // data (e.g. BLOB SUB_TYPE 0) must come back as bytes
        SqlType::Binary(bytes) => PyBytes::new(py, &bytes).into_py_any(py),
        SqlType::Null => Ok(py.None()),
    }
}

/// decimal.Decimal, resolved once
static DECIMAL_TYPE: PyOnceLock<Py<PyType>> = PyOnceLock::new();

fn decimal_type<'py>(py: Python<'py>) -> PyResult<&'py Py<PyType>> {
    DECIMAL_TYPE.get_or_try_init(py, || {
        let ty = py.import("decimal")?.getattr("Decimal")?;
        Ok(ty.cast_into::<PyType>().map_err(PyErr::from)?.unbind())
    })
}

/// Convert a single Python parameter value to a Firebird SqlType
fn py_param_to_sqltype(obj: &Bound<'_, PyAny>) -> PyResult<SqlType> {
    if obj.is_none() {
        return Ok(SqlType::Null);
    }
    // bool must be checked before int (bool is a subclass of int in Python)
    if let Ok(b) = obj.cast::<PyBool>() {
        return Ok(SqlType::Boolean(b.is_true()));
    }
    // datetime must be checked before date (datetime is a subclass of
    // date); chrono extraction works under the limited API (abi3)
    if let Ok(dt) = obj.extract::<NaiveDateTime>() {
        return Ok(SqlType::Timestamp(dt));
    }
    if let Ok(d) = obj.extract::<NaiveDate>() {
        return Ok(SqlType::Timestamp(NaiveDateTime::new(d, chrono::NaiveTime::MIN)));
    }
    // Decimal must be checked before float: Decimal has __float__, so the
    // f64 extraction below would silently accept it lossily. Sent as a
    // plain-notation string; the server casts it to NUMERIC exactly.
    if obj.is_instance(decimal_type(obj.py())?.bind(obj.py()))? {
        let s = obj.call_method1("__format__", ("f",))?.extract::<String>()?;
        return Ok(SqlType::Text(s));
    }
    if let Ok(i) = obj.extract::<i64>() {
        return Ok(SqlType::Integer(i));
    }
    if let Ok(f) = obj.extract::<f64>() {
        return Ok(SqlType::Floating(f));
    }
    if let Ok(s) = obj.extract::<String>() {
        return Ok(SqlType::Text(s));
    }
    if let Ok(b) = obj.cast::<PyBytes>() {
        return Ok(SqlType::Binary(b.as_bytes().to_vec()));
    }
    Err(PyErr::new::<PyTypeError, _>(format!(
        "unsupported parameter type: {} (supported: None, bool, int, float, str, bytes, datetime, date, Decimal)",
        obj.get_type().name().map(|n| n.to_string()).unwrap_or_else(|_| "?".into())
    )))
}

/// Convert an optional Python parameter sequence (tuple/list) to Firebird params
fn py_params_to_sqltypes(params: Option<&Bound<'_, PyAny>>) -> PyResult<Vec<SqlType>> {
    let Some(params) = params else {
        return Ok(Vec::new());
    };
    if params.is_none() {
        return Ok(Vec::new());
    }
    // A bare string/bytes is almost certainly a mistake, not a sequence of params
    if params.extract::<String>().is_ok() || params.cast::<PyBytes>().is_ok() {
        return Err(PyErr::new::<PyTypeError, _>(
            "params must be a sequence (tuple or list), not a string",
        ));
    }
    let mut values = Vec::new();
    for item in params.try_iter()? {
        values.push(py_param_to_sqltype(&item?)?);
    }
    Ok(values)
}

#[derive(Clone)]
struct ConnectionInfo {
    host: String,
    database: String,
    port: u16,
    user: String,
    password: String,
    stmt_cache_size: usize,
}

/// Connection state shared between a FirebirdConnection and all its cursors
struct SharedConnection {
    conn: Option<SimpleConnection>,
    in_transaction: bool,
}

/// READ COMMITTED + RECORD VERSION + WAIT, like the pure-Python firebirdsql
/// driver. rsfbclient's own default is NO RECORD VERSION, which makes
/// readers block on uncommitted changes of other transactions.
fn default_transaction_config() -> TransactionConfiguration {
    TransactionConfiguration {
        data_access: TrDataAccessMode::ReadWrite,
        isolation: TrIsolationLevel::ReadCommited(TrRecordVersion::RecordVersion),
        lock_resolution: TrLockResolution::Wait(None),
    }
}

fn create_connection(info: &ConnectionInfo) -> PyResult<SimpleConnection> {
    let conn = rsfbclient::builder_native()
        .with_dyn_link()
        .with_remote()
        .host(&info.host)
        .port(info.port)
        .db_name(&info.database)
        .user(&info.user)
        .pass(&info.password)
        .stmt_cache_size(info.stmt_cache_size)
        .transaction(default_transaction_config())
        .connect()
        .map_err(|e| runtime_error(e.to_string()))?;
    Ok(conn.into())
}

/// Firebird database cursor (DB-API style)
#[pyclass]
struct FirebirdCursor {
    connection_info: Arc<ConnectionInfo>,
    shared: Arc<Mutex<SharedConnection>>,
    autocommit: bool,
    results: Option<Vec<Py<PyAny>>>,
    current_position: usize,
    total_rows: Option<usize>,
    row_count: i64,
    column_info: Option<Vec<(String, u32)>>,
    last_metrics: Option<QueryMetrics>,
    enable_metrics: bool,
    closed: Arc<Mutex<bool>>,
    streaming_mode: bool,
    chunk_size: usize,
    enable_query_cache: bool,
}

/// Firebird database connection
#[pyclass]
struct FirebirdConnection {
    connection_info: Arc<ConnectionInfo>,
    closed: Arc<Mutex<bool>>,
    shared: Arc<Mutex<SharedConnection>>,
    autocommit: bool,
}

impl FirebirdCursor {
    fn check_open(&self) -> PyResult<()> {
        let closed = self.closed.lock().unwrap();
        if *closed {
            return Err(runtime_error("Connection is closed"));
        }
        Ok(())
    }

    /// Convert a Firebird row to a Python tuple
    fn convert_row_to_python(&self, py: Python, row: Row) -> PyResult<Py<PyAny>> {
        let mut values = Vec::with_capacity(row.cols.len());

        for column in row.cols.into_iter() {
            values.push(sqltype_to_python(py, column.raw_type, column.value)?);
        }

        let tuple = PyTuple::new(py, values)?;
        tuple.into_py_any(py)
    }

    /// Execute a statement on the shared connection, starting a transaction if needed
    fn execute_inner(&mut self, py: Python, sql: &str, params: Vec<SqlType>) -> PyResult<()> {
        self.check_open()?;
        self.current_position = 0;
        self.results = None;
        self.column_info = None;
        self.row_count = -1;
        self.total_rows = None;

        // Only the first keyword decides the routing; avoid uppercasing the
        // whole statement
        let first_word = sql
            .split_whitespace()
            .next()
            .unwrap_or("")
            .to_uppercase();
        let returns_rows = first_word == "SELECT" || first_word == "WITH";
        // INSERT/UPDATE/DELETE/MERGE ... RETURNING yields a single row via
        // a different protocol op (execute2)
        let has_returning = !returns_rows
            && matches!(first_word.as_str(), "INSERT" | "UPDATE" | "DELETE" | "MERGE")
            && contains_returning(sql);

        let shared_arc = Arc::clone(&self.shared);
        let info = Arc::clone(&self.connection_info);
        let autocommit = self.autocommit;

        // All network work (connect, transaction start, execute, fetch)
        // runs without the GIL so other Python threads keep running.
        //
        // The shared-connection Mutex is locked *inside* detach, i.e. after
        // the GIL is released. Locking it before detach would deadlock when
        // two Python threads share one connection: thread A holds the Mutex
        // inside detach and needs the GIL back to return, while thread B
        // holds the GIL and blocks on the Mutex before it can detach.
        let db_result: PyResult<DbResult> = py.detach(move || {
            let mut guard = shared_arc.lock().unwrap();
            let shared: &mut SharedConnection = &mut guard;
            if shared.conn.is_none() {
                shared.conn = Some(create_connection(&info)?);
            }
            // Run the DB interaction, keeping the raw FbError so that a
            // fatal connection error can be detected below.
            let outcome: Result<DbResult, FbError> = 'stmt: {
                // DB-API: statements run inside a transaction until
                // commit()/rollback(), unless autocommit=True was requested
                if !autocommit && !shared.in_transaction {
                    if let Err(e) = shared
                        .conn
                        .as_mut()
                        .unwrap()
                        .begin_transaction_config(default_transaction_config())
                    {
                        break 'stmt Err(e);
                    }
                    shared.in_transaction = true;
                }
                let conn = shared.conn.as_mut().unwrap();

                if returns_rows {
                    conn.query_iter(sql, params)
                        .and_then(|it| it.collect::<Result<Vec<Row>, _>>())
                        .map(DbResult::Rows)
                } else if has_returning {
                    conn.execute_returnable(sql, params).map(|row: Row| DbResult::Rows(vec![row]))
                } else {
                    // INSERT/UPDATE/DELETE/DDL/...
                    conn.execute(sql, params).map(DbResult::Affected)
                }
            };

            match outcome {
                Ok(result) => Ok(result),
                Err(e) => {
                    // A connection-fatal error (socket loss, -902, or a
                    // poisoned cursor/statement state) leaves the shared
                    // connection unusable. Discard it so the next execute
                    // reconnects fresh -- clearing rsfbclient's statement
                    // cache -- instead of failing on every subsequent call
                    // until the app is restarted.
                    if is_fatal_conn_error(&e) {
                        shared.conn = None;
                        shared.in_transaction = false;
                    }
                    Err(runtime_error(e.to_string()))
                }
            }
        });

        match db_result? {
            DbResult::Rows(rows) => {
                if let Some(first) = rows.first() {
                    self.column_info = Some(
                        first
                            .cols
                            .iter()
                            .map(|c| (c.name.clone(), c.raw_type))
                            .collect(),
                    );
                }

                let mut result = Vec::with_capacity(rows.len());
                for row in rows {
                    result.push(self.convert_row_to_python(py, row)?);
                }

                self.row_count = result.len() as i64;
                self.total_rows = Some(result.len());
                self.results = Some(result);
            }
            DbResult::Affected(affected) => {
                self.row_count = affected as i64;
                self.results = Some(Vec::new());
            }
        }

        Ok(())
    }
}

/// Result of the GIL-free database phase of execute_inner
enum DbResult {
    Rows(Vec<Row>),
    Affected(usize),
}

#[pymethods]
impl FirebirdCursor {
    /// Execute an SQL statement, optionally with qmark-style (?) parameters
    #[pyo3(signature = (sql, params=None))]
    fn execute(&mut self, py: Python<'_>, sql: &str, params: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let params = py_params_to_sqltypes(params)?;
        self.execute_inner(py, sql, params)
    }

    /// Execute an SQL statement once per parameter set
    fn executemany(&mut self, py: Python<'_>, sql: &str, param_sets: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut total: i64 = 0;
        let mut executed = false;
        for params in param_sets.try_iter()? {
            let params = py_params_to_sqltypes(Some(&params?))?;
            self.execute_inner(py, sql, params)?;
            executed = true;
            if self.row_count > 0 {
                total += self.row_count;
            }
        }
        self.results = Some(Vec::new());
        self.row_count = if executed { total } else { -1 };
        Ok(())
    }

    /// Legacy alias for execute() (kept for backwards compatibility)
    fn execute_ultra_fast(&mut self, py: Python<'_>, sql: &str) -> PyResult<()> {
        self.execute_inner(py, sql, Vec::new())
    }

    /// DB-API: sequence of 7-tuples describing the result columns of the
    /// last SELECT (derived from the first result row; None if no rows).
    /// type_code is the numeric Firebird wire type (e.g. 496 for INTEGER),
    /// matching the firebirdsql driver. precision/scale/null_ok are not
    /// available through rsfbclient and stay None.
    #[getter]
    #[allow(clippy::type_complexity)]
    fn description(
        &self,
    ) -> Option<Vec<(String, u32, Option<i32>, Option<i32>, Option<i32>, Option<i32>, Option<bool>)>> {
        self.column_info.as_ref().map(|cols| {
            cols.iter()
                .map(|(name, raw_type)| {
                    (name.clone(), *raw_type, None, wire_internal_size(*raw_type), None, None, None)
                })
                .collect()
        })
    }

    /// DB-API: number of rows returned by the last SELECT or affected by the
    /// last modification (-1 if no statement was executed yet)
    #[getter]
    fn rowcount(&self) -> i64 {
        self.row_count
    }

    /// Fetch all results from the last executed query
    fn fetchall(&mut self) -> PyResult<Vec<Py<PyAny>>> {
        match self.results.take() {
            Some(results) => {
                self.current_position = results.len();
                Ok(results)
            },
            None => Ok(Vec::new()),
        }
    }

    /// Fetch one row from the result set
    fn fetchone(&mut self) -> PyResult<Option<Py<PyAny>>> {
        if let Some(ref results) = self.results {
            if self.current_position < results.len() {
                Python::attach(|py| {
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
    fn fetchmany(&mut self, size: Option<usize>) -> PyResult<Vec<Py<PyAny>>> {
        let fetch_size = size.unwrap_or(self.chunk_size);

        if let Some(ref results) = self.results {
            let start = self.current_position;
            let end = (start + fetch_size).min(results.len());

            if start < end {
                Python::attach(|py| {
                    let rows: Vec<Py<PyAny>> = results[start..end]
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
    fn get_last_metrics(&self) -> PyResult<Option<Py<PyAny>>> {
        Python::attach(|py| {
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
    fn get_optimization_status(&self) -> PyResult<Py<PyAny>> {
        Python::attach(|py| {
            let dict = PyDict::new(py);
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

            dict.into_py_any(py)
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

    /// Close the cursor (the underlying connection stays open; it belongs
    /// to the FirebirdConnection object)
    fn close(&mut self) -> PyResult<()> {
        self.results = None;
        self.column_info = None;
        self.current_position = 0;
        Ok(())
    }
}

#[pymethods]
impl FirebirdConnection {
    /// Create a cursor for executing queries
    fn cursor(&self) -> PyResult<FirebirdCursor> {
        let closed = self.closed.lock().unwrap();
        if *closed {
            return Err(runtime_error("Connection is closed"));
        }

        Ok(FirebirdCursor {
            connection_info: Arc::clone(&self.connection_info),
            shared: Arc::clone(&self.shared),
            autocommit: self.autocommit,
            results: None,
            current_position: 0,
            total_rows: None,
            row_count: -1,
            column_info: None,
            last_metrics: None,
            enable_metrics: false,
            closed: Arc::clone(&self.closed),
            streaming_mode: false,
            chunk_size: 1000,
            enable_query_cache: true,
        })
    }

    /// Commit the current transaction
    fn commit(&self, py: Python<'_>) -> PyResult<()> {
        {
            let closed = self.closed.lock().unwrap();
            if *closed {
                return Err(runtime_error("Connection is closed"));
            }
        }

        // Lock the shared Mutex inside detach (after releasing the GIL) to
        // avoid the GIL/Mutex deadlock described in execute_inner.
        let shared_arc = Arc::clone(&self.shared);
        py.detach(move || {
            let mut guard = shared_arc.lock().unwrap();
            let shared: &mut SharedConnection = &mut guard;
            if shared.in_transaction {
                shared
                    .conn
                    .as_mut()
                    .unwrap()
                    .commit()
                    .map_err(|e| runtime_error(format!("Failed to commit transaction: {e}")))?;
                shared.in_transaction = false;
            }
            Ok(())
        })
    }

    /// Roll back the current transaction
    fn rollback(&self, py: Python<'_>) -> PyResult<()> {
        {
            let closed = self.closed.lock().unwrap();
            if *closed {
                return Err(runtime_error("Connection is closed"));
            }
        }

        // Lock the shared Mutex inside detach (after releasing the GIL) to
        // avoid the GIL/Mutex deadlock described in execute_inner.
        let shared_arc = Arc::clone(&self.shared);
        py.detach(move || {
            let mut guard = shared_arc.lock().unwrap();
            let shared: &mut SharedConnection = &mut guard;
            if shared.in_transaction {
                shared
                    .conn
                    .as_mut()
                    .unwrap()
                    .rollback()
                    .map_err(|e| runtime_error(format!("Failed to roll back transaction: {e}")))?;
                shared.in_transaction = false;
            }
            Ok(())
        })
    }

    /// Close the connection. An open transaction is rolled back (DB-API).
    fn close(&self, py: Python<'_>) -> PyResult<()> {
        {
            let mut closed = self.closed.lock().unwrap();
            *closed = true;
        }

        // Lock the shared Mutex inside detach (after releasing the GIL) to
        // avoid the GIL/Mutex deadlock described in execute_inner.
        let shared_arc = Arc::clone(&self.shared);
        py.detach(move || {
            let mut guard = shared_arc.lock().unwrap();
            let shared: &mut SharedConnection = &mut guard;
            if let Some(mut conn) = shared.conn.take() {
                if shared.in_transaction {
                    let _ = conn.rollback();
                    shared.in_transaction = false;
                }
                if let Err(e) = conn.close() {
                    eprintln!("Warning: Error closing connection: {e}");
                }
            }
        });
        Ok(())
    }
}

/// Connect to a Firebird database.
///
/// With autocommit=False (default, DB-API behaviour) statements run inside a
/// transaction that must be ended with conn.commit() or conn.rollback().
/// With autocommit=True every statement is committed immediately.
///
/// stmt_cache_size (default 20) is the number of prepared statements kept
/// per connection (LRU); raise it for workloads with many distinct queries.
#[pyfunction]
#[pyo3(signature = (host, database, port=3050, user="SYSDBA", password="masterkey", autocommit=false, stmt_cache_size=20))]
#[allow(clippy::too_many_arguments)] // mirrors the Python keyword API
fn connect(
    py: Python<'_>,
    host: &str,
    database: &str,
    port: u16,
    user: &str,
    password: &str,
    autocommit: bool,
    stmt_cache_size: usize,
) -> PyResult<FirebirdConnection> {
    let connection_info = Arc::new(ConnectionInfo {
        host: host.to_string(),
        database: database.to_string(),
        port,
        user: user.to_string(),
        password: password.to_string(),
        stmt_cache_size: stmt_cache_size.max(1),
    });

    // Connect eagerly so that connection errors surface here, not on the
    // first execute; the handshake runs without the GIL
    let conn = {
        let info = Arc::clone(&connection_info);
        py.detach(move || create_connection(&info))?
    };

    Ok(FirebirdConnection {
        connection_info,
        closed: Arc::new(Mutex::new(false)),
        shared: Arc::new(Mutex::new(SharedConnection {
            conn: Some(conn),
            in_transaction: false,
        })),
        autocommit,
    })
}

/// Get global performance statistics
#[pyfunction]
fn get_performance_stats(py: Python) -> PyResult<Py<PyAny>> {
    let dict = PyDict::new(py);

    if let Ok(global_metrics) = PERFORMANCE_METRICS.lock() {
        for (operation, metrics_list) in global_metrics.iter() {
            if !metrics_list.is_empty() {
                let operation_dict = PyDict::new(py);

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

    dict.into_py_any(py)
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
fn get_type_conversion_cache_stats(py: Python) -> PyResult<Py<PyAny>> {
    let dict = PyDict::new(py);

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

    dict.into_py_any(py)
}

/// Get query optimization statistics
#[pyfunction]
fn get_query_optimization_stats(py: Python) -> PyResult<Py<PyAny>> {
    let dict = PyDict::new(py);

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

    dict.into_py_any(py)
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

    // Add version information (single source of truth: Cargo.toml)
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // DB-API 2.0 module attributes
    m.add("apilevel", "2.0")?;
    m.add("threadsafety", 1)?; // threads may share the module, not connections
    m.add("paramstyle", "qmark")?;

    Ok(())
}
