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
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/schemas")
def get_schemas(source_type: str):
    try:
        if source_type.lower() == "databricks":
            schemas = DatabricksConnector.get_schemas()
        else:
            schemas = SqlServerConnector.get_schemas()
        return {"schemas": schemas}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tables")
def get_tables(source_type: str, schema: str):
    try:
        if source_type.lower() == "databricks":
            tables = DatabricksConnector.get_tables(schema)
        else:
            tables = SqlServerConnector.get_tables(schema)
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/columns")
def get_columns(source_type: str, schema: str, table: str):
    try:
        if source_type.lower() == "databricks":
            columns = DatabricksConnector.get_columns(schema, table)
        else:
            columns = SqlServerConnector.get_columns(schema, table)
        return {"columns": columns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def fetch_source_values(src_config: SourceConfig):
    """Helper function to fetch distinct values for a given source."""
    if src_config.type.lower() == "databricks":
        return DatabricksConnector.get_values(src_config.db_schema, src_config.table, src_config.column)
    else:
        return SqlServerConnector.get_values(src_config.db_schema, src_config.table, src_config.column)


@app.post("/api/compare")
def compare_data(payload: ComparePayload):
    try:
        # High-Performance Parallel Execution:
        # Queries Source 1 (Databricks) and Source 2 (SQL Server) concurrently in parallel threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(fetch_source_values, payload.source1)
            future2 = executor.submit(fetch_source_values, payload.source2)

            values1 = future1.result()
            values2 = future2.result()

        # Run CompareService.compare(values1, values2)
        results = CompareService.compare(values1, values2)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)
