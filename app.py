import streamlit as st
import mysql.connector
import pandas as pd
import time
import matplotlib.pyplot as plt

st.set_page_config(page_title="Analiza zapytań SQL", layout="wide")
st.title("📊 Narzędzie do analizy wydajności zapytań SQL (MySQL)")

host = "localhost"
user = "root"
password = ""  # jeśli masz hasło, wpisz je tutaj

def get_databases():
    conn = mysql.connector.connect(host=host, user=user, password=password)
    cursor = conn.cursor()
    cursor.execute("SHOW DATABASES")
    dbs = [row[0] for row in cursor.fetchall() if row[0] not in ('information_schema', 'mysql', 'sys')]
    cursor.close()
    conn.close()
    return dbs

baza = st.selectbox("Wybierz bazę danych:", get_databases())
pokaz_debug = st.checkbox("🔧 Pokaż dane systemowe (diagnostycznie)", value=False)

sql_query = st.text_area("Wpisz zapytanie SQL:", height=200)
liczba_powtorzen = st.number_input("Ile razy wykonać zapytanie?", min_value=1, max_value=500, value=1)

if st.button("🔍 Wykonaj i przeanalizuj") and sql_query.strip():
    try:
        czasy = []
        conn = mysql.connector.connect(host=host, user=user, password=password, database=baza)
        cursor = conn.cursor()

        for i in range(liczba_powtorzen):
            start = time.perf_counter()
            cursor.execute(sql_query)
            _ = cursor.fetchall()
            czasy.append(round(time.perf_counter() - start, 6))

        cursor.execute(sql_query)
        rows = cursor.fetchall()
        columns = cursor.column_names

        st.success(f"✅ Średni czas wykonania zapytania: {round(sum(czasy)/len(czasy), 6)} sekundy")
        st.dataframe(pd.DataFrame(rows, columns=columns))

        st.subheader("📈 Wykres czasów wykonania zapytania")
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(range(1, liczba_powtorzen + 1), czasy, marker='o')
        ax.set_xlabel("Numer wykonania")
        ax.set_ylabel("Czas (s)")
        ax.set_title("Czas wykonania zapytania w kolejnych próbach")
        st.pyplot(fig)

        st.subheader("📊 Plan wykonania (EXPLAIN)")
        cursor.execute(f"EXPLAIN {sql_query}")
        explain_data = cursor.fetchall()
        explain_cols = cursor.column_names
        st.dataframe(pd.DataFrame(explain_data, columns=explain_cols))

        with st.expander("📖 Wyjaśnienie EXPLAIN"):
            st.markdown("""
            **id** – identyfikator zapytania w planie (wyższe id = późniejsze wykonanie)  
            **select_type** – typ SELECT-a (`SIMPLE`, `PRIMARY`, `SUBQUERY` itd.)  
            **table** – nazwa analizowanej tabeli  
            **type** – rodzaj połączenia (`ALL`, `ref`, `eq_ref`, `const`, `index`, `range`) – im bardziej szczegółowy, tym lepiej  
            **rows** – ile wierszy MySQL musi przejrzeć – im mniej, tym szybciej  
            **Extra** – dodatkowe informacje, np. `Using where`, `Using filesort`, `Using temporary`
            """)

        st.subheader("🧪 ANALYZE – rzeczywisty przebieg zapytania")
        try:
            cursor.execute(f"ANALYZE FORMAT=TRADITIONAL {sql_query}")
            analyze_data = cursor.fetchall()
            analyze_cols = cursor.column_names
            st.dataframe(pd.DataFrame(analyze_data, columns=analyze_cols))

            with st.expander("📖 Wyjaśnienie ANALYZE"):
                st.markdown("""
                `ANALYZE` pokazuje faktyczne wykonanie zapytania przez silnik bazy danych.  
                Zwraca informacje o czasie, liczbie wierszy, operacjach sortowania i filtrowania.
                """)
        except mysql.connector.Error:
            st.warning("Nie udało się wykonać ANALYZE – być może baza nie obsługuje tej funkcji.")

        perf_result = []
        try:
            perf_conn = mysql.connector.connect(host=host, user=user, password=password, database="performance_schema")
            perf_cursor = perf_conn.cursor()
            perf_query = """
            SELECT DIGEST_TEXT, COUNT_STAR, 
                   AVG_TIMER_WAIT / 1e12 AS avg_time_sec, 
                   SUM_TIMER_WAIT / 1e12 AS total_time_sec, 
                   MAX_TIMER_WAIT / 1e12 AS max_time_sec 
            FROM events_statements_summary_by_digest
            WHERE DIGEST_TEXT LIKE %s
            ORDER BY total_time_sec DESC
            LIMIT 1;
            """
            perf_cursor.execute(perf_query, (f"%{sql_query[:30]}%",))
            perf_result = perf_cursor.fetchall()
            perf_cursor.close()
            perf_conn.close()
        except mysql.connector.Error:
            pass

        st.subheader("📌 Wnioski i sugestie optymalizacji:")
        if "ALL" in [row[3] for row in explain_data]:
            st.warning("Zapytanie wykonuje pełne skanowanie tabeli – rozważ dodanie indeksów.")
        if any("Using filesort" in str(row[-1]) for row in explain_data):
            st.warning("Sortowanie w pamięci (Using filesort) – może pogarszać wydajność.")
        if any("Using temporary" in str(row[-1]) for row in explain_data):
            st.warning("Tworzenie tymczasowej tabeli (Using temporary) – może spowalniać zapytanie.")

        if perf_result:
            st.subheader("📌 Wnioski z performance_schema:")
            zapytanie, count_star, avg_time, total_time, max_time = perf_result[0]
            if count_star > 500:
                st.info(f"🔁 Zapytanie zostało wykonane {count_star} razy – możliwe, że jest zbyt często używane.")
            if avg_time > 0.5:
                st.info(f"🐢 Średni czas wykonania to {avg_time:.3f} s – warto rozważyć optymalizację.")
            if total_time > 5:
                st.info(f"🔥 Suma czasu wykonania przekracza 5 sekund – zapytanie należy do najcięższych w systemie.")
            if "JOIN" in zapytanie.upper():
                st.info("🔗 Zapytanie zawiera operację JOIN – sprawdź, czy pola łączenia są indeksowane.")
            if "nazwa_zwyczajowa" in zapytanie:
                st.info("🧠 W systemie dominują zapytania z `nazwa_zwyczajowa` – rozważ dodanie indeksu lub refaktoryzację.")

        cursor.close()
        conn.close()

    except mysql.connector.Error as e:
        st.error(f"❌ Błąd: {e}")

if pokaz_debug:
    st.subheader("🔧 Diagnostyka performance_schema – wybrane źródła")
    try:
        conn = mysql.connector.connect(host=host, user=user, password=password, database="performance_schema")
        cursor = conn.cursor()

        queries = {
            "Top zapytania wg SUM_TIMER_WAIT": """
                SELECT DIGEST_TEXT, COUNT_STAR, 
                       SUM_TIMER_WAIT / 1e12 AS total_sec,
                       AVG_TIMER_WAIT / 1e12 AS avg_sec,
                       MAX_TIMER_WAIT / 1e12 AS max_sec,
                       FIRST_SEEN, LAST_SEEN
                FROM events_statements_summary_by_digest
                ORDER BY total_sec DESC
                LIMIT 10;
            """,
            "⏱ Aktywne obecnie zapytania": "SELECT * FROM events_statements_current LIMIT 10;",
            "💽 Opóźnienia I/O (waits)": "SELECT * FROM events_waits_summary_by_instance ORDER BY SUM_TIMER_WAIT DESC LIMIT 10;",
            "📋 Operacje na tabelach": "SELECT * FROM table_io_waits_summary_by_table ORDER BY SUM_TIMER_WAIT DESC LIMIT 10;",
            "📂 Operacje na indeksach": "SELECT * FROM table_io_waits_summary_by_index_usage ORDER BY SUM_TIMER_WAIT DESC LIMIT 10;",
            "🧵 Aktywność wątków (threads)": "SELECT * FROM threads LIMIT 10;",
        }

        for title, q in queries.items():
            st.subheader(title)
            try:
                cursor.execute(q)
                results = cursor.fetchall()
                cols = cursor.column_names
                st.dataframe(pd.DataFrame(results, columns=cols))
            except Exception as err:
                st.warning(f"Błąd zapytania: {err}")

        with st.expander("📖 Wyjaśnienie źródeł danych w performance_schema"):
            st.markdown("""
            - **events_statements_summary_by_digest** – zagregowane statystyki zapytań
            - **events_statements_current** – zapytania wykonywane w tej chwili
            - **events_waits_summary_by_instance** – operacje czekające na zasoby I/O
            - **table_io_waits_summary_by_table** – czasy oczekiwania dla poszczególnych tabel
            - **table_io_waits_summary_by_index_usage** – jak wykorzystywane są indeksy w praktyce
            - **threads** – aktywność wątków obsługujących połączenia
            """)

        st.subheader("📌 Wnioski diagnostyczne z performance_schema:")
        st.markdown("""
        🔍 **Analiza TOP zapytań:** Jeżeli suma czasu (`SUM_TIMER_WAIT`) przekracza 5s lub zapytanie było wykonywane >500 razy, należy sprawdzić jego użycie oraz zoptymalizować (np. indeksy, cache).

        🧠 **Opóźnienia I/O:** Wysokie wartości w `events_waits_summary_by_instance` sugerują, że storage (np. InnoDB lub MyISAM) może być przeciążony – zalecane sprawdzenie IOPS oraz logów dysku.

        📊 **Wskaźniki użycia indeksów:** Jeśli `table_io_waits_summary_by_index_usage` pokazuje niskie `COUNT_STAR`, a `SUM_TIMER_WAIT` jest wysokie – indeks może być nieużywany i do usunięcia lub źle dobrany.

        ⚙️ **Wątki (`threads`) z wysokim `PROCESSLIST_TIME`** mogą oznaczać zawieszone zapytania lub wolne odpowiedzi – przeanalizuj zapytania długotrwałe lub zablokowane.
        """)

        cursor.close()
        conn.close()
    except mysql.connector.Error:
        st.warning("❗ Nie udało się pobrać danych diagnostycznych z performance_schema.")
