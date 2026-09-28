import pandas as pd
from logger import log_step, logger

class CompareService:
    @staticmethod
    def compare(values1, values2):
        """
        Exact implementation matching reference:
        Intersects two sets of column values and calculates counts and matching metrics.
        """
        log_step("COMPARE_SERVICE_START", f"Starting comparison between Source 1 ({len(values1)} items) and Source 2 ({len(values2)} items)")

        v1_set = set(values1) if not isinstance(values1, set) else values1
        v2_set = set(values2) if not isinstance(values2, set) else values2

        matching_values = v1_set.intersection(v2_set)
        only_source1 = v1_set - v2_set
        only_source2 = v2_set - v1_set

        s1_count = len(v1_set)
        s2_count = len(v2_set)
        matching_count = len(matching_values)

        max_count = max(s1_count, s2_count) if max(s1_count, s2_count) > 0 else 1
        matching_percentage = round((matching_count / max_count) * 100.0, 2)

        log_step("COMPARE_SERVICE_COMPLETE", f"Result: S1={s1_count}, S2={s2_count}, Matched={matching_count} ({matching_percentage}%), Only_S1={len(only_source1)}, Only_S2={len(only_source2)}")

        return {
            "source1_count": s1_count,
            "source2_count": s2_count,
            "matching_count": matching_count,
            "matching_percentage": matching_percentage,
            "only_source1": len(only_source1),
            "only_source2": len(only_source2),
            "matching_sample": list(matching_values)[:20],
            "only_source1_sample": list(only_source1)[:20],
            "only_source2_sample": list(only_source2)[:20]
        }
