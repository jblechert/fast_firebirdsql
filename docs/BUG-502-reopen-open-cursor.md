# Bug: `-502 Attempt to reopen an open cursor` → Folge­fehler `-902 Error writing data to the connection`

- **Treiber:** fast_firebirdsql 0.11.1
- **Gemeldet:** 2026-07-14
- **Schweregrad:** hoch — korrumpiert die Verbindung; nachfolgende Queries scheitern, in bstools verschwinden dadurch neu angelegte Packlisten (INSERT läuft ins Leere).
- **Regression:** trat auf, nachdem fast_firebirdsql per Default aktiv wurde (bstools-Commit `ca832cc`, 2026-07-13). Unter dem reinen `firebirdsql`-Treiber tritt der Fehler nicht auf.

## Symptom

Im laufenden Betrieb (Firebird 2.5, remote) erscheinen wiederholt zwei zusammenhängende Fehler:

```
ERROR ... Fehler beim Lesen aller Artikel-Erinnerungen: sql error -502: SQL error code = -502
Attempt to reopen an open cursor
...
CRITICAL ... UNCAUGHT EXCEPTION: RuntimeError: sql error -902: Error writing data to the connection.
  File ".../bstoolsDB.py", line 3633, in get_packdaten_from_versandid
    self.versandcur.execute(
        f"SELECT ZEILE, ANZAHL, ... FROM VERSANDLISTE_PACKSTUECKE WHERE VERSANDID = {versandid}"
    )
RuntimeError: sql error -902: Error writing data to the connection.
```

Ablauf: Zuerst kippt eine (oft wiederholt ausgeführte, identische) Query mit **-502**. Danach ist die Verbindung in einem inkonsistenten Zustand, und die nächste `execute()` scheitert mit **-902 (Error writing data to the connection)**. Ein Neustart der App „heilt" es nur vorübergehend.

## Auslösendes Muster (Aufrufer-Seite)

Der Aufrufer (bstools) teilt sich **einen** Cursor über **eine** Verbindung für viele, teils verschachtelte Queries (`self.versandcur = self.stammcur`, ~180 Verwendungen). Dabei kommt es vor, dass auf demselben Cursor/derselben Verbindung eine neue `execute()` abgesetzt wird, während das Resultset einer vorherigen Query (bzw. deren serverseitiger Cursor) noch nicht geschlossen ist.

Das ist auf Aufrufer-Seite unsauber und wird dort separat behoben. **Aber:** der reine `firebirdsql`-Treiber toleriert dasselbe Muster klaglos, fast_firebirdsql nicht. Ein Treiber sollte pro `execute()` einen sauberen Statement-/Cursor-Zustand garantieren, statt einen fremden offenen Cursor zu erben.

## Analyse (Treiber-Ebene)

Relevante Stellen in `src/lib.rs`:

- **Geteilte Verbindung:** `FirebirdConnection::cursor()` (Z. 733) klont nur `Arc::clone(&self.shared)`. Alle Cursor teilen sich dieselbe `SharedConnection` (eine rsfbclient-`SimpleConnection` + Transaktionsstatus) hinter einem `Mutex`. Es gibt keinen cursor-eigenen Statement-Zustand.
- **Statement-Cache:** `create_connection()` (Z. 319) setzt `.stmt_cache_size(info.stmt_cache_size)`; Kommentar Z. 59: „rsfbclient maintains the real statement cache". Identische SQL-Strings werden also auf ein **wiederverwendetes prepared statement** gemappt.
- **Lazy Cursor bei SELECT:** `execute_inner()` (Z. 431) nutzt `conn.query_iter(sql, params)?.collect()`. `query_iter` hält einen offenen Firebird-Cursor auf dem (gecachten) Statement, bis der Iterator vollständig konsumiert **und gedroppt** ist.

**Hypothese:** Wird dasselbe gecachte prepared statement erneut ausgeführt, bevor der zuvor darauf geöffnete Cursor serverseitig freigegeben ist (`isc_dsql_free_statement` / `DSQL_close`), antwortet Firebird mit **-502 „Attempt to reopen an open cursor"**. Der nicht sauber geschlossene Cursor lässt die Verbindung im Half-open-Zustand zurück → nächste Operation **-902**.

Das passt dazu, dass gerade **wiederholte, identische** Queries betroffen sind (die Erinnerungs-Query; die pro-Versandid-Query im Selektions-Handler, die bei jeder Zeilenauswahl feuert).

## Reproduktion (Vorschlag)

Ein Cursor, dieselbe SELECT-SQL zweimal, ohne das erste Resultset vollständig zu lesen/zu schließen:

```python
import fast_firebirdsql as fb
conn = fb.connect(host=..., database=..., port=3050, user="SYSDBA", password="masterkey")
cur = conn.cursor()
cur.execute("SELECT * FROM RDB$RELATIONS")   # großes Resultset
# absichtlich NICHT fetchall(): vorherigen (server-)Cursor offen lassen
cur.execute("SELECT * FROM RDB$RELATIONS")   # erwartet: -502 reopen an open cursor
```

Zusätzlich mit `stmt_cache_size > 0` und identischem SQL testen, sowie den Fall „zweiter Cursor aus `conn.cursor()`, gleiches SQL, erster noch offen".

## Mögliche Fixe (Treiber)

1. **Vor jeder `execute()` den vorher offenen Cursor/Statement-Zustand der geteilten Verbindung schließen** (defensiv `close`/`free` auf dem gecachten Statement), damit ein neuer `execute()` nie einen offenen Cursor erbt.
2. **-502 gezielt behandeln:** bei „reopen an open cursor" den Cursor schließen und die Query einmal retryen, statt die Verbindung im Half-open-Zustand zu lassen.
3. **-902/-502 als Verbindungsabbruch klassifizieren** und in `FB_CONNECTION_ERRORS` bzw. über einen dedizierten Exception-Typ nach oben reichen, damit Aufrufer gezielt reconnecten können (aktuell exponiert fast_firebirdsql keine Exception-Klassen → Aufrufer sehen nur generisches `RuntimeError`).
4. Prüfen, ob der rsfbclient-Statement-Cache bei geteilter Verbindung + lazy `query_iter` überhaupt gefahrlos ist; ggf. `stmt_cache_size(0)` als sichere Default-Option evaluieren.

## Gegenprobe

- Isoliertes `INSERT INTO PACKLISTEN (PACKLISTE_ID, JSON_DATA) VALUES (...)` über fast_firebirdsql funktioniert einwandfrei (Trigger füllt `ID`, `ERLEDIGT` DEFAULT 0). Der Fehler entsteht ausschließlich im Zusammenspiel mit einem noch offenen Cursor auf derselben Verbindung.
- Unter dem reinen `firebirdsql`-Treiber tritt weder -502 noch -902 auf.

---

## AUFLÖSUNG (v0.11.2, 2026-07-14)

Die ursprüngliche Hypothese (nicht geschlossener Cursor auf einem gecachten
Statement) trifft für diesen Treiber **nicht** zu: `execute()` materialisiert
jedes Resultset vollständig und lässt den `StmtIter` sofort fallen, wodurch
rsfbclient den Server-Cursor schließt. Alle einzelthread-Reproversuche
(identische Query zweimal ohne `fetchall`, zwei Cursor, 50× Wiederholung,
verschachtelte Queries) liefen **fehlerfrei** — kein -502.

**Tatsächliche Ursache: ein GIL/Mutex-Deadlock bei geteilter Verbindung über
mehrere Threads.** bstools teilt eine Verbindung zwischen dem Haupt-Thread und
einem Hintergrund-Thread (z. B. dem Erinnerungs-Timer). `execute_inner`
sperrte den internen Verbindungs-`Mutex` **bevor** der GIL freigegeben wurde:

- Thread A: hält den `Mutex`, ist in `py.detach` (GIL freigegeben), macht DB-I/O
  und braucht den GIL zurück, um zurückzukehren.
- Thread B: hält den GIL, betritt `execute` und blockiert in `self.shared.lock()`,
  **bevor** er `py.detach` erreicht (also bevor er den GIL freigibt).

A braucht den GIL (bei B), B braucht den `Mutex` (bei A) → klassischer Deadlock.
Der reine `firebirdsql`-Treiber gibt den GIL nicht frei und kann diesen Deadlock
prinzipiell nicht haben — daher „firebirdsql toleriert dasselbe Muster". Das
in Produktion sichtbare -502/-902 entsteht, wenn eine so eingefrorene
Verbindung von außen abgebrochen/reused wird und danach im Half-open-Zustand ist.

**Reproduktion (read-only, System­tabellen):** zwei Threads, dieselbe Verbindung,
je eine Endlos-`SELECT`-Schleife → hängt innerhalb weniger Iterationen. Nach dem
Fix: 5 Threads (identische Query, Cache-Churn mit distinktem SQL, commit/rollback
gemischt), 12 s Last, **0 Fehler, sauberes Ende**.

**Umgesetzte Fixe (`src/lib.rs`):**

1. **Deadlock behoben (Kern):** Der `shared`-`Mutex` wird jetzt **innerhalb**
   `py.detach` gesperrt (nach GIL-Freigabe) — in `execute_inner`, `commit`,
   `rollback` und `close`. Damit gibt jeder Thread den GIL frei, bevor er auf den
   `Mutex` wartet; kein Deadlock mehr, Zugriffe werden sauber serialisiert.
2. **Self-Healing (Fix 2/3 oben):** `is_fatal_conn_error()` erkennt
   `FbError::Io`, SQLCODE -902/-901 und -502. Bei einem solchen Fehler wird die
   Verbindung verworfen (`shared.conn = None`, `in_transaction = false`) und beim
   nächsten `execute()` frisch aufgebaut (leert damit auch den Statement-Cache) —
   statt bis zum App-Neustart bei jedem Aufruf zu scheitern.
3. **Regressionstest:** `test_shared_connection_across_threads_no_deadlock`
   (drei Threads, `join(timeout=15)`) — schlägt auf dem Bug-Build durch Timeout fehl.

Nicht umgesetzt (bewusst): dedizierte DB-API-Exception-Klassen (Fix 3, zweiter
Teil) — größere API-Fläche, von bstools nicht benötigt; separat nachrüstbar.
Kein Auto-Retry für schreibende Statements (unklar, ob committet → kein stilles
Doppel-Insert); nur die Verbindung wird verworfen, der Fehler propagiert.
