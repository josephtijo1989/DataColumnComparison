from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import io

from mock_data import generate_preset_datasets
from services.compare_service import CompareService
from connectors.databricks_connector import DatabricksConnector
from connectors.sqlserver_connector import SqlServerConnector

app = FastAPI(
    title="Databricks & SQL Server Data Comparison Engine",
    description="Backend API for high-performance cross-source data validation and column match analysis.",
    version="1.0.0"
)

# Enable CORS for Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORED_DATASETS: Dict[str, pd.DataFrame] = {}
PRESETS = generate_preset_datasets()

for p_key, p_val in PRESETS.items():
    STORED_DATASETS[f"{p_key}_src_a"] = p_val["df_a"]
    STORED_DATASETS[f"{p_key}_src_b"] = p_val["df_b"]


class CompareRequest(BaseModel):
    source_a_type: str
    source_a_id: str
    source_b_type: str
    source_b_id: str
    key_column: str
    compare_columns: List[str]
    case_sensitive: Optional[bool] = True
    ignore_whitespace: Optional[bool] = True
    numeric_tolerance: Optional[float] = 0.0
    source_a_name: Optional[str] = "Databricks Delta"
    source_b_name: Optional[str] = "SQL Server"


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Databricks & SQL Server Data Comparator API",
        "endpoints": ["/api/presets", "/api/schema/{dataset_id}", "/api/compare", "/api/upload"]
    }


@app.get("/api/presets")
def get_presets():
    result = []
    for k, v in PRESETS.items():
        result.append({
            "id": k,
            "title": v["title"],
            "description": v["description"],
            "source_a_name": v["source_a_name"],
            "source_b_name": v["source_b_name"],
            "source_a_id": f"{k}_src_a",
            "source_b_id": f"{k}_src_b",
            "default_key": v["default_key"],
            "default_compare": v["default_compare"],
            "available_columns_a": list(v["df_a"].columns),
            "available_columns_b": list(v["df_b"].columns)
        })
    return result


@app.get("/api/schema/{dataset_id}")
def get_dataset_schema(dataset_id: str):
    if dataset_id not in STORED_DATASETS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    
    df = STORED_DATASETS[dataset_id]
    return {
        "dataset_id": dataset_id,
        "row_count": len(df),
        "columns": list(df.columns),
        "dtypes": {col: str(df[col].dtype) for col in df.columns},
        "sample_preview": df.head(5).to_dict(orient="records")
    }


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...), source_tag: str = Form(...)):
    try:
        contents = await file.read()
        filename = file.filename.lower()
        
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif filename.endswith(".json"):
            df = pd.read_json(io.BytesIO(contents))
        elif filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format.")
            
        dataset_id = f"upload_{source_tag}_{file.filename}"
        STORED_DATASETS[dataset_id] = df
        
        return {
            "status": "success",
            "dataset_id": dataset_id,
            "filename": file.filename,
            "row_count": len(df),
            "columns": list(df.columns)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload error: {str(e)}")


@app.post("/api/connect-test")
def test_connection(config: Dict[str, Any]):
    db_type = config.get("db_type", "databricks")
    try:
        if db_type == "databricks":
            schemas = DatabricksConnector.get_schemas()
            return {
                "status": "connected",
                "message": f"Successfully authenticated and queried Databricks Catalogs & Schemas.",
                "schemas": schemas
            }
        else:
            schemas = SqlServerConnector.get_schemas()
            return {
                "status": "connected",
                "message": f"Successfully connected to SQL Server instance.",
                "schemas": schemas
            }
    except Exception as ex:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(ex)}")


@app.post("/api/compare")
def compare_datasets(req: CompareRequest):
    if req.source_a_id not in STORED_DATASETS:
        raise HTTPException(status_code=400, detail=f"Source A dataset '{req.source_a_id}' not found.")
    if req.source_b_id not in STORED_DATASETS:
        raise HTTPException(status_code=400, detail=f"Source B dataset '{req.source_b_id}' not found.")
        
    df_a = STORED_DATASETS[req.source_a_id]
    df_b = STORED_DATASETS[req.source_b_id]
    
    try:
        results = CompareService.compare_dataframes(
            df_a=df_a,
            df_b=df_b,
            key_column=req.key_column,
            compare_columns=req.compare_columns,
            case_sensitive=req.case_sensitive if req.case_sensitive is not None else True,
            ignore_whitespace=req.ignore_whitespace if req.ignore_whitespace is not None else True,
            numeric_tolerance=req.numeric_tolerance if req.numeric_tolerance is not None else 0.0,
            source_a_name=req.source_a_name or "Databricks Delta",
            source_b_name=req.source_b_name or "SQL Server"
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Comparison engine failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
