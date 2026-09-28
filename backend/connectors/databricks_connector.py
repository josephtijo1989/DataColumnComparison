try:
    from databricks import sql
except ImportError:
    sql = None

from config import DATABRICKS

class DatabricksConnector:
    @staticmethod
    def get_connection():
        if sql is None:
            print("databricks-sql-connector not installed. Returning None for mock mode.")
            return None
        try:
            conn = sql.connect(
                server_hostname=DATABRICKS["server_hostname"],
                http_path=DATABRICKS["http_path"],
                access_token=DATABRICKS["access_token"]
            )
            print("Successfully Connected to Databricks")
            return conn
        except Exception as ex:
            print("Connection failed:")
            print(str(ex))
            raise

    @staticmethod
    def get_schemas():
        conn = DatabricksConnector.get_connection()
        if not conn:
            return ["silver_catalog.default", "silver_catalog.crm", "silver_catalog.finance"]

        cursor = conn.cursor()
        results = []
        try:
            cursor.execute("SHOW CATALOGS")
            catalogs = cursor.fetchall()
            for catalog in catalogs:
                catalog_name = catalog[0]
                cursor.execute(f"SHOW SCHEMAS IN `{catalog_name}`")
                schemas = cursor.fetchall()
                for schema in schemas:
                    results.append(f"{catalog_name}.{schema[0]}")
        finally:
            cursor.close()
            conn.close()
        return sorted(results)

    @staticmethod
    def get_tables(schema_name):
        conn = DatabricksConnector.get_connection()
        if not conn:
            return ["customers_delta", "orders_delta", "financial_ledger"]

        catalog, schema = schema_name.split(".", 1)
        cursor = conn.cursor()
        query = f"SHOW TABLES IN `{catalog}`.`{schema}`"
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [row[1] for row in rows]

    @staticmethod
    def get_columns(schema_name, table):
        conn = DatabricksConnector.get_connection()
        if not conn:
            return ["customer_id", "first_name", "last_name", "email", "loyalty_tier", "total_spend", "credit_score", "account_status"]

        catalog, schema = schema_name.split(".", 1)
        cursor = conn.cursor()
        query = f"DESCRIBE `{catalog}`.`{schema}`.`{table}`"
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = []
        for row in rows:
            col = str(row[0])
            if col and not col.startswith("#"):
                columns.append(col)
        cursor.close()
        conn.close()
        return columns

    @staticmethod
    def get_values(schema_name, table, column):
        conn = DatabricksConnector.get_connection()
        if not conn:
            return set()

        catalog, schema = schema_name.split(".", 1)
        cursor = conn.cursor()
        query = f"SELECT DISTINCT CAST({column} AS STRING) FROM `{catalog}`.`{schema}`.`{table}` WHERE {column} IS NOT NULL"
        cursor.execute(query)
        values = {str(row[0]).strip() for row in cursor.fetchall()}
        cursor.close()
        conn.close()
        return values
