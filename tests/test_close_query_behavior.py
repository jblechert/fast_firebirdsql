#!/usr/bin/env python3
"""
Spezifischer Test für das Verhalten von Abfragen nach conn.close().

Dieser Test überprüft genau das, was der Benutzer wollte:
- Verbindung herstellen
- Abfrage ausführen (funktioniert)
- conn.close() aufrufen
- Versuchen, eine weitere Abfrage auszuführen (sollte fehlschlagen)
"""

import fast_firebirdsql
import sys
import traceback

def test_query_after_close():
    """Test query execution after connection close"""
    print("=" * 70)
    print("TEST: ABFRAGE NACH VERBINDUNGSSCHLIESSUNG")
    print("=" * 70)
    
    # Verbindungsparameter - mehrere Optionen probieren
    connection_params_list = [
        {
            'host': '192.0.2.10',
            'database': 'd:\\data\\example.fdb',
            'port': 3050,
            'user': 'EXAMPLE_USER',
            'password': 'REDACTED'
        },
        {
            'host': '192.0.2.10',
            'database': 'bstools.fdb',
            'port': 3050,
            'user': 'SYSDBA',
            'password': 'masterkey'
        }
    ]
    
    working_params = None
    
    # Zuerst eine funktionierende Verbindung finden
    print("Suche nach funktionierender Datenbankverbindung...")
    for i, params in enumerate(connection_params_list, 1):
        try:
            print(f"\nVersuch {i}: {params['host']}:{params['port']}/{params['database']}")
            test_conn = fast_firebirdsql.connect(**params)
            test_cur = test_conn.cursor()
            test_cur.execute("SELECT 1 FROM RDB$DATABASE")
            result = test_cur.fetchone()
            print(f"✅ Verbindung erfolgreich: {result}")
            test_conn.close()
            working_params = params
            break
        except Exception as e:
            print(f"❌ Verbindung fehlgeschlagen: {e}")
            continue
    
    if not working_params:
        print("\n❌ Keine funktionierende Datenbankverbindung gefunden.")
        print("Test kann nicht durchgeführt werden.")
        return False
    
    print(f"\n✅ Verwende Verbindung: {working_params}")
    
    try:
        # Haupttest beginnen
        print(f"\n" + "="*50)
        print("HAUPTTEST: Abfrage nach close()")
        print("="*50)
        
        # Schritt 1: Verbindung herstellen
        print("\n1. Verbindung herstellen...")
        conn = fast_firebirdsql.connect(**working_params)
        cur = conn.cursor()
        print("✅ Verbindung und Cursor erstellt")
        
        # Schritt 2: Erste Abfrage (sollte funktionieren)
        print("\n2. Erste Abfrage ausführen...")
        cur.execute("SELECT 'Erste Abfrage funktioniert' AS message FROM RDB$DATABASE")
        result1 = cur.fetchone()
        print(f"✅ Erste Abfrage erfolgreich: {result1}")
        
        # Schritt 3: Verbindung schließen
        print("\n3. Verbindung schließen...")
        conn.close()
        print("✅ conn.close() ausgeführt")
        
        # Schritt 4: Versuchen, eine weitere Abfrage auszuführen (sollte fehlschlagen)
        print("\n4. Zweite Abfrage nach close() versuchen...")
        try:
            cur.execute("SELECT 'Diese Abfrage sollte fehlschlagen' AS message FROM RDB$DATABASE")
            result2 = cur.fetchone()
            print(f"❌ FEHLER: Abfrage nach close() sollte fehlschlagen, aber gab zurück: {result2}")
            return False
        except Exception as e:
            print(f"✅ KORREKT: Abfrage nach close() ist fehlgeschlagen: {e}")
        
        # Schritt 5: Auch fetchall() sollte nicht mehr funktionieren
        print("\n5. fetchall() nach close() versuchen...")
        try:
            result3 = cur.fetchall()
            if result3:
                print(f"⚠️  fetchall() gab noch Daten zurück: {result3}")
                print("   (Das kann OK sein, wenn Daten bereits im Cursor zwischengespeichert waren)")
            else:
                print("✅ fetchall() gab leere Ergebnisse zurück")
        except Exception as e:
            print(f"✅ fetchall() ist korrekt fehlgeschlagen: {e}")
        
        # Schritt 6: Neue Verbindung sollte noch funktionieren
        print("\n6. Neue Verbindung nach close() testen...")
        new_conn = fast_firebirdsql.connect(**working_params)
        new_cur = new_conn.cursor()
        new_cur.execute("SELECT 'Neue Verbindung funktioniert' AS message FROM RDB$DATABASE")
        result4 = new_cur.fetchone()
        print(f"✅ Neue Verbindung funktioniert: {result4}")
        new_conn.close()
        
        print(f"\n" + "="*50)
        print("TEST ERFOLGREICH ABGESCHLOSSEN!")
        print("="*50)
        print("✅ Verbindung kann ordnungsgemäß geschlossen werden")
        print("✅ Abfragen nach close() schlagen korrekt fehl")
        print("✅ Neue Verbindungen funktionieren weiterhin")
        print("✅ Das Verbindungsmanagement arbeitet korrekt!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test fehlgeschlagen mit Fehler: {e}")
        traceback.print_exc()
        return False

def main():
    """Hauptfunktion"""
    print("FAST_FIREBIRDSQL - TEST FÜR VERBINDUNGSSCHLIESSUNG")
    print("=" * 70)
    print("Dieser Test überprüft, ob Abfragen nach conn.close() korrekt fehlschlagen.")
    
    success = test_query_after_close()
    
    if success:
        print(f"\n🎉 ALLE TESTS BESTANDEN!")
        print("Die Verbindungsschließung funktioniert korrekt.")
        sys.exit(0)
    else:
        print(f"\n❌ TESTS FEHLGESCHLAGEN!")
        print("Die Verbindungsschließung benötigt Aufmerksamkeit.")
        sys.exit(1)

if __name__ == "__main__":
    main()
