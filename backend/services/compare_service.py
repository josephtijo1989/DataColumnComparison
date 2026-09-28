import pandas as pd
import numpy as np

class CompareService:
    @staticmethod
    def compare(values1, values2):
        matching_values = values1.intersection(values2)
        only_source1 = values1 - values2
        only_source2 = values2 - values1
        return {
            "source1_count": len(values1),
            "source2_count": len(values2),
            "matching_count": len(matching_values),
            "only_source1": len(only_source1),
            "only_source2": len(only_source2)
        }

    @staticmethod
    def compare_sets(values1: set, values2: set):
        """
        Reference method as requested:
        Compares two sets of column values/keys and returns exact set intersection and differences.
        """
        matching_values = values1.intersection(values2)
        only_source1 = values1 - values2
        only_source2 = values2 - values1
        return {
            "source1_count": len(values1),
            "source2_count": len(values2),
            "matching_count": len(matching_values),
            "only_source1": len(only_source1),
            "only_source2": len(only_source2)
        }

    @staticmethod
    def compare_dataframes(
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        key_column: str,
        compare_columns: list,
        case_sensitive: bool = True,
        ignore_whitespace: bool = True,
        numeric_tolerance: float = 0.0,
        source_a_name: str = "Databricks Delta",
        source_b_name: str = "SQL Server"
    ):
        """
        Full cross-source reconciliation engine building upon set operations.
        Computes total unique records, exact matches, mismatch details, and match percentage.
        """
        df_a = df_a.copy()
        df_b = df_b.copy()

        # Extract set of keys
        keys_a = set(df_a[key_column].dropna().astype(str).unique())
        keys_b = set(df_b[key_column].dropna().astype(str).unique())

        # Perform core set comparison algorithm
        set_stats = CompareService.compare_sets(keys_a, keys_b)

        # Merge on key column for column-by-column value validation
        df_a["_join_key"] = df_a[key_column].astype(str)
        df_b["_join_key"] = df_b[key_column].astype(str)

        df_a_dedup = df_a.drop_duplicates(subset=["_join_key"])
        df_b_dedup = df_b.drop_duplicates(subset=["_join_key"])

        merged = pd.merge(
            df_a_dedup,
            df_b_dedup,
            on="_join_key",
            suffixes=("_src_a", "_src_b"),
            how="inner"
        )

        mismatched_rows = []
        exact_match_count = 0
        mismatch_count = 0

        per_column_stats = {col: {"match_count": 0, "mismatch_count": 0, "match_pct": 0.0} for col in compare_columns}

        for idx, row in merged.iterrows():
            key_val = row["_join_key"]
            row_has_mismatch = False
            diff_details = []

            for col in compare_columns:
                val_a = row.get(f"{col}_src_a")
                val_b = row.get(f"{col}_src_b")

                is_null_a = pd.isna(val_a) or val_a is None or str(val_a).strip() == ""
                is_null_b = pd.isna(val_b) or val_b is None or str(val_b).strip() == ""

                is_match = False
                if is_null_a and is_null_b:
                    is_match = True
                elif is_null_a != is_null_b:
                    is_match = False
                else:
                    if isinstance(val_a, (int, float, np.number)) and isinstance(val_b, (int, float, np.number)):
                        if abs(float(val_a) - float(val_b)) <= numeric_tolerance:
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
                    diff_details.append({
                        "column": col,
                        "val_a": None if is_null_a else str(val_a),
                        "val_b": None if is_null_b else str(val_b)
                    })

            if row_has_mismatch:
                mismatch_count += 1
                mismatched_rows.append({
                    "key_value": key_val,
                    "status": "MISMATCH",
                    "diffs": diff_details,
                    "full_record_a": {},
                    "full_record_b": {}
                })
            else:
                exact_match_count += 1

        total_joined = len(merged)
        for col in compare_columns:
            m_cnt = per_column_stats[col]["match_count"]
            per_column_stats[col]["match_pct"] = round((m_cnt / total_joined * 100.0), 2) if total_joined > 0 else 0.0

        max_unique = max(set_stats["source1_count"], set_stats["source2_count"]) if max(set_stats["source1_count"], set_stats["source2_count"]) > 0 else 1
        overall_match_percentage = round((exact_match_count / max_unique) * 100.0, 2)

        return {
            "summary": {
                "source_a_name": source_a_name,
                "source_b_name": source_b_name,
                "key_column": key_column,
                "compared_columns": compare_columns,
                "total_records_a": len(df_a),
                "total_records_b": len(df_b),
                "total_unique_a": set_stats["source1_count"],
                "total_unique_b": set_stats["source2_count"],
                "common_keys_count": set_stats["matching_count"],
                "exact_matching_records": exact_match_count,
                "mismatched_records": mismatch_count,
                "only_in_source_a_count": set_stats["only_source1"],
                "only_in_source_b_count": set_stats["only_source2"],
                "match_percentage": overall_match_percentage,
                "common_key_match_percentage": round((exact_match_count / total_joined * 100.0), 2) if total_joined > 0 else 0.0
            },
            "per_column_stats": per_column_stats,
            "mismatched_rows_sample": mismatched_rows[:100],
            "only_in_a_sample": list(keys_a - keys_b)[:50],
            "only_in_b_sample": list(keys_b - keys_a)[:50]
        }
