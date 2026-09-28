import pandas as pd
import numpy as np

def run_data_comparison(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    key_column: str,
    compare_columns: list,
    case_sensitive: bool = True,
    ignore_whitespace: bool = True,
    numeric_tolerance: float = 0.0,
    source_a_name: str = "Source A (Databricks)",
    source_b_name: str = "Source B (SQL Server)"
):
    """
    Compares two DataFrames (Databricks / SQL Server / CSV) on a specified key column
    and one or more comparison target columns.
    Returns structured stats, total unique records per source, match percentage, and row diffs.
    """
    
    # Standardize column strings
    df_a = df_a.copy()
    df_b = df_b.copy()
    
    # Handle missing column checks
    if key_column not in df_a.columns or key_column not in df_b.columns:
        raise ValueError(f"Key column '{key_column}' must exist in both sources.")
        
    for col in compare_columns:
        if col not in df_a.columns or col not in df_b.columns:
            raise ValueError(f"Comparison column '{col}' must exist in both sources.")
            
    # Calculate Total Raw Records
    total_records_a = len(df_a)
    total_records_b = len(df_b)
    
    # Calculate Total Unique Records by Key Column
    unique_keys_a_set = set(df_a[key_column].dropna().astype(str).unique())
    unique_keys_b_set = set(df_b[key_column].dropna().astype(str).unique())
    
    total_unique_a = len(unique_keys_a_set)
    total_unique_b = len(unique_keys_b_set)
    
    # Key Overlap
    matched_keys_set = unique_keys_a_set.intersection(unique_keys_b_set)
    only_in_a_set = unique_keys_a_set - unique_keys_b_set
    only_in_b_set = unique_keys_b_set - unique_keys_a_set
    
    # Deduplicate DataFrames for primary key analysis (keep first occurrence if duplicates)
    df_a_unique = df_a.drop_duplicates(subset=[key_column]).copy()
    df_b_unique = df_b.drop_duplicates(subset=[key_column]).copy()
    
    # Convert key columns to str for safe joining
    df_a_unique["_join_key"] = df_a_unique[key_column].astype(str)
    df_b_unique["_join_key"] = df_b_unique[key_column].astype(str)
    
    merged = pd.merge(
        df_a_unique,
        df_b_unique,
        on="_join_key",
        suffixes=("_src_a", "_src_b"),
        how="inner"
    )
    
    # Comparison loop
    mismatched_rows = []
    exact_match_count = 0
    mismatch_count = 0
    
    per_column_stats = {col: {"match_count": 0, "mismatch_count": 0, "match_pct": 0.0} for col in compare_columns}
    
    for idx, row in merged.iterrows():
        key_val = row["_join_key"]
        row_has_mismatch = False
        row_diff_details = []
        
        for col in compare_columns:
            val_a = row[f"{col}_src_a"]
            val_b = row[f"{col}_src_b"]
            
            # Normalization logic based on parameters
            norm_a = val_a
            norm_b = val_b
            
            # Convert NaNs to None / string 'NaN'
            is_null_a = pd.isna(val_a) or val_a is None or str(val_a).strip() == ""
            is_null_b = pd.isna(val_b) or val_b is None or str(val_b).strip() == ""
            
            is_match = False
            
            if is_null_a and is_null_b:
                is_match = True
            elif is_null_a != is_null_b:
                is_match = False
            else:
                # Both non-null
                if isinstance(val_a, (int, float, np.number)) and isinstance(val_b, (int, float, np.number)):
                    diff = abs(float(val_a) - float(val_b))
                    if diff <= numeric_tolerance:
                        is_match = True
                else:
                    str_a = str(val_a)
                    str_b = str(val_b)
                    
                    if ignore_whitespace:
                        str_a = str_a.strip()
                        str_b = str_b.strip()
                    if not case_sensitive:
                        str_a = str_a.lower()
                        str_b = str_b.lower()
                        
                    if str_a == str_b:
                        is_match = True
                        
            if is_match:
                per_column_stats[col]["match_count"] += 1
            else:
                per_column_stats[col]["mismatch_count"] += 1
                row_has_mismatch = True
                row_diff_details.append({
                    "column": col,
                    "val_a": None if is_null_a else str(val_a),
                    "val_b": None if is_null_b else str(val_b),
                })
                
        if row_has_mismatch:
            mismatch_count += 1
            mismatched_rows.append({
                "key_value": key_val,
                "status": "MISMATCH",
                "diffs": row_diff_details,
                "full_record_a": {col: (None if pd.isna(row.get(f"{col}_src_a")) else str(row.get(f"{col}_src_a"))) for col in compare_columns},
                "full_record_b": {col: (None if pd.isna(row.get(f"{col}_src_b")) else str(row.get(f"{col}_src_b"))) for col in compare_columns}
            })
        else:
            exact_match_count += 1
            
    # Calculate column percentages
    total_joined = len(merged)
    for col in compare_columns:
        m_cnt = per_column_stats[col]["match_count"]
        per_column_stats[col]["match_pct"] = round((m_cnt / total_joined * 100.0), 2) if total_joined > 0 else 0.0

    # Calculate overall match percentage
    # Match percentage relative to max unique records across sources:
    max_unique = max(total_unique_a, total_unique_b) if max(total_unique_a, total_unique_b) > 0 else 1
    overall_match_percentage = round((exact_match_count / max_unique) * 100.0, 2)
    
    # Also key match percentage among common keys
    common_key_match_pct = round((exact_match_count / total_joined) * 100.0, 2) if total_joined > 0 else 0.0

    # Format missing records sample
    only_in_a_sample = list(only_in_a_set)[:50]
    only_in_b_sample = list(only_in_b_set)[:50]

    return {
        "summary": {
            "source_a_name": source_a_name,
            "source_b_name": source_b_name,
            "key_column": key_column,
            "compared_columns": compare_columns,
            "total_records_a": total_records_a,
            "total_records_b": total_records_b,
            "total_unique_a": total_unique_a,
            "total_unique_b": total_unique_b,
            "common_keys_count": len(matched_keys_set),
            "exact_matching_records": exact_match_count,
            "mismatched_records": mismatch_count,
            "only_in_source_a_count": len(only_in_a_set),
            "only_in_source_b_count": len(only_in_b_set),
            "match_percentage": overall_match_percentage,
            "common_key_match_percentage": common_key_match_pct
        },
        "per_column_stats": per_column_stats,
        "mismatched_rows_sample": mismatched_rows[:100],  # Return top 100 sample diffs
        "only_in_a_sample": only_in_a_sample,
        "only_in_b_sample": only_in_b_sample
    }
