from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import os
import concurrent.futures

from connectors.databricks_connector import DatabricksConnector
from connectors.sqlserver_connector import SqlServerConnector
from services.compare_service import CompareService
from logger import log_step, logger

app = FastAPI(title="Data Comparison Tool")

# Setup templates & static files directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


class SourceConfig(BaseModel):
    type: str
    db_schema: str = Field(alias="schema")
    table: str
    column: str

    class Config:
        populate_by_name = True


class ComparePayload(BaseModel):
    source1: SourceConfig
    source2: SourceConfig


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Renders the main Data Comparison Tool page."""
    log_step("HTTP_INDEX", "Renders index page.")
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/schemas")
def get_schemas(source_type: str):
    log_step("API_SCHEMAS", f"Fetching schemas for source_type: '{source_type}'")
    try:
        if source_type.lower() == "databricks":
            schemas = DatabricksConnector.get_schemas()
        else:
            schemas = SqlServerConnector.get_schemas()
        return {"schemas": schemas}
    except Exception as e:
        log_step("API_SCHEMAS_ERROR", f"Error fetching schemas: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tables")
def get_tables(source_type: str, schema: str):
    log_step("API_TABLES", f"Fetching tables for source_type: '{source_type}', schema: '{schema}'")
    try:
        if source_type.lower() == "databricks":
            tables = DatabricksConnector.get_tables(schema)
        else:
            tables = SqlServerConnector.get_tables(schema)
        return {"tables": tables}
    except Exception as e:
        log_step("API_TABLES_ERROR", f"Error fetching tables: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/columns")
def get_columns(source_type: str, schema: str, table: str):
    log_step("API_COLUMNS", f"Fetching columns for source_type: '{source_type}', schema: '{schema}', table: '{table}'")
    try:
        if source_type.lower() == "databricks":
            columns = DatabricksConnector.get_columns(schema, table)
        else:
            columns = SqlServerConnector.get_columns(schema, table)
        return {"columns": columns}
    except Exception as e:
        log_step("API_COLUMNS_ERROR", f"Error fetching columns: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


def fetch_source_values(src_config: SourceConfig, source_name: str):
    """Helper function to fetch distinct values for a given source."""
    log_step("THREAD_START", f"[{source_name}] Type={src_config.type}, Schema={src_config.db_schema}, Table={src_config.table}, Column={src_config.column}")
    if src_config.type.lower() == "databricks":
        return DatabricksConnector.get_values(src_config.db_schema, src_config.table, src_config.column)
    else:
        return SqlServerConnector.get_values(src_config.db_schema, src_config.table, src_config.column)


@app.post("/api/compare")
def compare_data(payload: ComparePayload):
    s1 = payload.source1
    s2 = payload.source2
    log_step("API_COMPARE_REQUEST", f"Received compare request: S1={s1.type}:{s1.db_schema}.{s1.table}.{s1.column} VS S2={s2.type}:{s2.db_schema}.{s2.table}.{s2.column}")

    try:
        # High-Performance Parallel Execution:
        # Queries Source 1 and Source 2 concurrently in parallel threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(fetch_source_values, s1, "SOURCE_1")
            future2 = executor.submit(fetch_source_values, s2, "SOURCE_2")

            values1 = future1.result()
            values2 = future2.result()

        # Run CompareService.compare(values1, values2)
        results = CompareService.compare(values1, values2)
        return results
    except Exception as e:
        log_step("API_COMPARE_FAILED", f"Comparison failed with error: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)
