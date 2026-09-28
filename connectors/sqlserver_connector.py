try:
    import pyodbc
except ImportError:
    pyodbc = None

from config import SQLSERVER
from logger import log_step, logger

class SqlServerConnector:
    SERVER = SQLSERVER.get('server', 'localhost')
    DATABASE = SQLSERVER.get('database', 'master')

    @staticmethod
    def get_connection():
        if pyodbc is None:
            log_step("SQL_SERVER_CONN", "pyodbc library not installed. Operating in mock mode.", level="warning")
            return None

        conn_str = (
            "Driver={ODBC Driver 18 for SQL Server};"
            f"Server={SqlServerConnector.SERVER};"
            f"Database={SqlServerConnector.DATABASE};"
            "Authentication=ActiveDirectoryInteractive;"
            "Encrypt=no;"
            "TrustServerCertificate=yes;"
            "Pooling=no;"
            "MultipleActiveResultSets=no;"
        )
        try:
            conn = pyodbc.connect(
                conn_str,
                timeout=30
            )
            log_step("SQL_SERVER_CONN", "Successfully Connected to SQL Server.")
            return conn
        except Exception as ex:
            log_step("SQL_SERVER_CONN_ERROR", f"SQL Server Connection failed: {str(ex)}", level="error")
            return None

    @staticmethod
    def get_schemas():
        log_step("SQL_SERVER_SCHEMAS", "Fetching SQL Server schemas...")
        conn = SqlServerConnector.get_connection()
        if not conn:
            return ["dbo", "Production", "Sales", "Finance"]

        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT schema_name
                FROM information_schema.schemata
                ORDER BY schema_name
            """)
            results = [r[0] for r in cur.fetchall()]
            log_step("SQL_SERVER_SCHEMAS", f"Fetched {len(results)} schemas.")
            return results
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def get_tables(schema):
        log_step("SQL_SERVER_TABLES", f"Fetching SQL Server tables for schema: '{schema}'")
        conn = SqlServerConnector.get_connection()
        if not conn:
            return ["Customers", "Orders", "Transactions", "Inventory"]

        raw_schema = str(schema).strip() if schema else ""
        schema_parts = [p.strip("[] ") for p in raw_schema.split(".") if p.strip("[] ")]
        target_schema = schema_parts[-1] if schema_parts else "dbo"

        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = ?
                ORDER BY table_name
            """, target_schema)
            data = [r[0] for r in cur.fetchall()]
            log_step("SQL_SERVER_TABLES", f"Fetched {len(data)} tables.")
            return data
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def get_columns(schema, table):
        log_step("SQL_SERVER_COLUMNS", f"Fetching columns for table: '{schema}.{table}'")
        conn = SqlServerConnector.get_connection()
        if not conn:
            return ["customer_id", "first_name", "last_name", "email", "loyalty_tier", "total_spend", "credit_score", "account_status"]

        raw_schema = str(schema).strip() if schema else ""
        schema_parts = [p.strip("[] ") for p in raw_schema.split(".") if p.strip("[] ")]
        target_schema = schema_parts[-1] if schema_parts else "dbo"

        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = ?
                AND table_name = ?
                ORDER BY ordinal_position
            """, target_schema, table)
            data = [r[0] for r in cur.fetchall()]
            log_step("SQL_SERVER_COLUMNS", f"Fetched {len(data)} columns.")
            return data
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def get_values(schema, table, column, batch_size=100000):
        log_step("SQL_SERVER_VALUES", f"Fetching distinct values for Schema: '{schema}', Table: '{table}', Column: '{column}'")

        raw_schema = str(schema).strip() if schema else ""
        if not raw_schema or raw_schema.startswith("Select"):
            formatted_schema = "[dbo]"
        else:
            schema_parts = [p.strip("[] ") for p in raw_schema.split(".") if p.strip("[] ")]
            formatted_schema = ".".join(f"[{p}]" for p in schema_parts) or "[dbo]"

        clean_table = str(table).strip("[] ")
        clean_column = str(column).strip("[] ")

        if not clean_table or clean_table.startswith("Select"):
            err_msg = f"Invalid Table name selected: '{table}'"
            log_step("SQL_SERVER_VALIDATION", err_msg, level="error")
            raise ValueError(err_msg)

        if not clean_column or clean_column.startswith("Select"):
            err_msg = f"Invalid Column name selected: '{column}'"
            log_step("SQL_SERVER_VALIDATION", err_msg, level="error")
            raise ValueError(err_msg)

        query = f"""
        SELECT DISTINCT
            CAST([{clean_column}] AS VARCHAR(4000)) AS val
        FROM {formatted_schema}.[{clean_table}]
        WHERE [{clean_column}] IS NOT NULL
        """
        log_step("SQL_SERVER_QUERY", f"Generated SQL Query:\n{query.strip()}")

        conn = SqlServerConnector.get_connection()
        if not conn:
            log_step("SQL_SERVER_MOCK", "Operating in Mock Data mode for SQL Server.")
            if column == "customer_id":
                ids = {f"CUST-{1000 + i}" for i in range(470)}
                ids.update({f"CUST-SQL-{9000 + j}" for j in range(25)})
                return ids
            elif column == "email":
                return {f"user{i}@example.com" for i in range(450)}
            elif column == "loyalty_tier":
                return {"Bronze", "Silver", "Gold", "Platinum"}
            elif column == "account_status":
                return {"Active", "Inactive"}
            else:
                return {f"Val_{i}" for i in range(95)}

        try:
            cursor = conn.cursor()
            cursor.execute(query)

            values = set()
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                for row in rows:
                    if row[0] is not None:
                        values.add(str(row[0]).strip())

            cursor.close()
            conn.close()
            log_step("SQL_SERVER_SUCCESS", f"Successfully retrieved {len(values)} distinct values from SQL Server.")
            return values
        except Exception as ex:
            log_step("SQL_SERVER_ERROR", f"Database Execution Failed on SQL Server: {str(ex)}", level="error")
            raise
