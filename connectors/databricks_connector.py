try:
    from databricks import sql
except ImportError:
    sql = None

from config import DATABRICKS

class DatabricksConnector:
    @staticmethod
    def get_connection():
        if sql is None:
            return None
        try:
            conn = sql.connect(
                server_hostname=DATABRICKS.get("server_hostname", ""),
                http_path=DATABRICKS.get("http_path", ""),
                access_token=DATABRICKS.get("access_token", "")
            )
            print("Successfully Connected to Databricks")
            return conn
        except Exception as ex:
            print("Databricks Connection failed:")
            print(str(ex))
            return None

    @staticmethod
    def get_schemas():
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
        finally:
            cursor.close()
            conn.close()
        return sorted(results)

    @staticmethod
    def get_tables(schema_name):
        conn = DatabricksConnector.get_connection()
        if not conn:
            return ["customers_delta", "orders_delta", "financial_ledger", "transactions_silver"]

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
    def get_values(schema_name, table, column, batch_size=100000):
        """
        Optimized Chunked Fetching:
        Streams distinct records in 100k row batches to minimize memory overhead on huge datasets.
        """
        conn = DatabricksConnector.get_connection()
        if not conn:
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

        catalog, schema = schema_name.split(".", 1)
        cursor = conn.cursor()
        query = f"SELECT DISTINCT CAST({column} AS STRING) FROM `{catalog}`.`{schema}`.`{table}` WHERE {column} IS NOT NULL"
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
        return values
