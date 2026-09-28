try:
    from databricks import sql
except ImportError:
    sql = None

from config import DATABRICKS
from logger import log_step, logger

class DatabricksConnector:
    @staticmethod
    def get_connection():
        if sql is None:
            log_step("DATABRICKS_CONN", "databricks-sql-connector not installed. Operating in mock mode.", level="warning")
            return None
        try:
            conn = sql.connect(
                server_hostname=DATABRICKS.get("server_hostname", ""),
                http_path=DATABRICKS.get("http_path", ""),
                access_token=DATABRICKS.get("access_token", "")
            )
            log_step("DATABRICKS_CONN", "Successfully Connected to Databricks.")
            return conn
        except Exception as ex:
            log_step("DATABRICKS_CONN_ERROR", f"Databricks Connection failed: {str(ex)}", level="error")
            return None

    @staticmethod
    def get_schemas():
        log_step("DATABRICKS_SCHEMAS", "Fetching Databricks catalogs and schemas...")
        conn = DatabricksConnector.get_connection()
        if not conn:
            return ["silver_catalog.default", "silver_catalog.crm", "silver_catalog.finance", "silver_catalog.sales"]

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
            log_step("DATABRICKS_SCHEMAS", f"Fetched {len(results)} schemas.")
        finally:
            cursor.close()
            conn.close()
        return sorted(results)

    @staticmethod
    def get_tables(schema_name):
        log_step("DATABRICKS_TABLES", f"Fetching Databricks tables for schema: '{schema_name}'")
        conn = DatabricksConnector.get_connection()
        if not conn:
            return ["customers_delta", "orders_delta", "financial_ledger", "transactions_silver"]

        catalog, schema = schema_name.split(".", 1) if "." in schema_name else ("main", schema_name)
        cursor = conn.cursor()
        query = f"SHOW TABLES IN `{catalog}`.`{schema}`"
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        log_step("DATABRICKS_TABLES", f"Fetched {len(rows)} tables.")
        return [row[1] for row in rows]

    @staticmethod
    def get_columns(schema_name, table):
        log_step("DATABRICKS_COLUMNS", f"Fetching Databricks columns for table: '{schema_name}.{table}'")
        conn = DatabricksConnector.get_connection()
        if not conn:
            return ["customer_id", "first_name", "last_name", "email", "loyalty_tier", "total_spend", "credit_score", "account_status"]

        catalog, schema = schema_name.split(".", 1) if "." in schema_name else ("main", schema_name)
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
        log_step("DATABRICKS_COLUMNS", f"Fetched {len(columns)} columns.")
        return columns

    @staticmethod
    def get_values(schema_name, table, column, batch_size=100000):
        log_step("DATABRICKS_VALUES", f"Fetching distinct values for Schema: '{schema_name}', Table: '{table}', Column: '{column}'")

        if "." in schema_name:
            catalog, schema = schema_name.split(".", 1)
        else:
            catalog, schema = "main", schema_name

        query = f"SELECT DISTINCT CAST({column} AS STRING) FROM `{catalog}`.`{schema}`.`{table}` WHERE {column} IS NOT NULL"
        log_step("DATABRICKS_QUERY", f"Generated SQL Query:\n{query.strip()}")

        conn = DatabricksConnector.get_connection()
        if not conn:
            log_step("DATABRICKS_MOCK", "Operating in Mock Data mode for Databricks.")
            if column == "customer_id":
                return {f"CUST-{1000 + i}" for i in range(500)}
            elif column == "email":
                return {f"user{i}@example.com" for i in range(480)}
            elif column == "loyalty_tier":
                return {"Bronze", "Silver", "Gold", "Platinum"}
            elif column == "account_status":
                return {"Active", "Inactive", "Pending"}
            else:
                return {f"Val_{i}" for i in range(100)}

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
            log_step("DATABRICKS_SUCCESS", f"Successfully retrieved {len(values)} distinct values from Databricks.")
            return values
        except Exception as ex:
            log_step("DATABRICKS_ERROR", f"Database Execution Failed on Databricks: {str(ex)}", level="error")
            raise
