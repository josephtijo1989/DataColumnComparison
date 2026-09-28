try:
    import pyodbc
except ImportError:
    pyodbc = None

from config import SQLSERVER

class SqlServerConnector:
    SERVER = SQLSERVER.get('server', 'localhost')
    DATABASE = SQLSERVER.get('database', 'master')

    @staticmethod
    def get_connection():
        if pyodbc is None:
            print("pyodbc library not installed. Returning None for mock mode.")
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
        # print("Attempting SQL connection...")
        # print(conn_str)
        try:
            conn = pyodbc.connect(
                conn_str,
                timeout=30
            )
            print("Successfully Connected to SQL Server")
            return conn
        except Exception as ex:
            print("Connection failed:")
            print(str(ex))
            raise

    @staticmethod
    def get_schemas():
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
        finally:
            cur.close()
            conn.close()
        return results

    @staticmethod
    def get_tables(schema):
        conn = SqlServerConnector.get_connection()
        if not conn:
            return ["Customers", "Orders", "Transactions", "Inventory"]

        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = ?
                ORDER BY table_name
            """, schema)
            data = [r[0] for r in cur.fetchall()]
        finally:
            cur.close()
            conn.close()
        return data

    @staticmethod
    def get_columns(schema, table):
        conn = SqlServerConnector.get_connection()
        if not conn:
            return ["customer_id", "first_name", "last_name", "email", "loyalty_tier", "total_spend", "credit_score", "account_status"]

        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = ?
                AND table_name = ?
                ORDER BY ordinal_position
            """, schema, table)
            data = [r[0] for r in cur.fetchall()]
        finally:
            cur.close()
            conn.close()
        return data

    @staticmethod
    def get_values(schema, table, column):
        conn = SqlServerConnector.get_connection()
        if not conn:
            return set()

        cursor = conn.cursor()
        query = f"""
        SELECT DISTINCT
            CAST([{column}] AS VARCHAR(4000))
        FROM [{schema}].[{table}]
        WHERE [{column}] IS NOT NULL
        """
        cursor.execute(query)
        values = {
            str(row[0]).strip()
            for row in cursor.fetchall()
        }
        cursor.close()
        conn.close()
        return values
