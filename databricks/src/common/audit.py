"""
Execution Audit and Runtime Tracking Module.
Modernizes customCode.getFormattedTime and provides structured pipeline metrics.
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional


def format_duration(milliseconds: float) -> str:
    """
    Equivalence implementation of customCode.getFormattedTime(long milliseconds).
    Converts milliseconds into formatted duration string:
    - < 60s -> Xs
    - < 60m -> Xm Ys (or 0Xm Ys)
    - >= 60m -> Xh Ym Zs
    """
    secs = int(round(milliseconds / 1000.0))
    if secs < 60:
        return f"{secs}s"
    
    mins = secs // 60
    remainder_secs = secs - (mins * 60)
    sec_str = f"0{remainder_secs}" if remainder_secs < 10 else f"{remainder_secs}"
    
    if mins < 60:
        min_str = f"0{mins}" if mins < 10 else f"{mins}"
        return f"{min_str}m {sec_str}s"
    else:
        hours = mins // 60
        remainder_mins = mins - (hours * 60)
        min_str = f"0{remainder_mins}" if remainder_mins < 10 else f"{remainder_mins}"
        return f"{hours}h {min_str}m {sec_str}s"


class PipelineAuditTracker:
    """
    Collects runtime statistics, execution milestones, row counts, and durations.
    """

    def __init__(self, job_name: str):
        self.job_name = job_name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.metrics: Dict[str, Any] = {}

    def start(self) -> None:
        self.start_time = time.time()
        start_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("-----------------------------------------------------------------------------")
        print(f"Début d'exécution du job {self.job_name}        : {start_dt}")
        print("-----------------------------------------------------------------------------")

    def record_metric(self, key: str, value: Any) -> None:
        self.metrics[key] = value

    def finish(self) -> Dict[str, Any]:
        self.end_time = time.time()
        duration_ms = (self.end_time - (self.start_time or self.end_time)) * 1000.0
        formatted_duration = format_duration(duration_ms)
        end_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print("-----------------------------------------------------------------------------")
        for k, v in self.metrics.items():
            print(f"{k.ljust(45)}: {v}")
        print("-----------------------------------------------------------------------------")
        print(f"Fin d'exécution du job {self.job_name}          : {end_dt}")
        print(f"Durée totale d'exécution du job {self.job_name} : {formatted_duration}")
        print("-----------------------------------------------------------------------------")

        return {
            "job_name": self.job_name,
            "duration_ms": duration_ms,
            "formatted_duration": formatted_duration,
            "metrics": self.metrics,
            "end_time": end_dt
        }
