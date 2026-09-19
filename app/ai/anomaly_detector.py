import numpy as np
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("coal_governance.anomaly")


def detect_operational_anomalies(data_points: List[Dict[str, Any]], metric_key: str = "value", contamination: float = 0.1) -> List[Dict[str, Any]]:
    """
    Detects statistical operational deviations (production drop, sudden absenteeism, violation spikes)
    using IsolationForest and Z-Score.
    Never claims wrongdoing; always uses non-defamatory investigation guidance.
    """
    if not data_points or len(data_points) < 5:
        # Not enough historical baseline
        return []

    values = np.array([float(d.get(metric_key, 0)) for d in data_points]).reshape(-1, 1)
    mean_val = float(np.mean(values))
    std_val = float(np.std(values)) or 1.0

    anomalies = []

    try:
        from sklearn.ensemble import IsolationForest
        iso = IsolationForest(contamination=contamination, random_state=42)
        preds = iso.fit_predict(values)

        for i, (pred, item) in enumerate(zip(preds, data_points)):
            val = float(item.get(metric_key, 0))
            z_score = round((val - mean_val) / std_val, 2)

            # Both IsolationForest flags anomaly (-1) and |z_score| > 1.8
            if pred == -1 and abs(z_score) >= 1.8:
                deviation_direction = "sharp drop" if z_score < 0 else "unusual surge"
                anomalies.append({
                    "index": i,
                    "date": item.get("date", f"Day {i+1}"),
                    "metric": metric_key,
                    "observed_value": val,
                    "baseline_mean": round(mean_val, 2),
                    "z_score": z_score,
                    "deviation": deviation_direction,
                    "status_tag": "Anomaly detected — investigation recommended.",
                    "notes": f"Observed {val} deviates significantly ({z_score} standard deviations) from baseline {round(mean_val, 2)}."
                })

    except Exception as e:
        logger.warning(f"Isolation forest failed ({e}). Falling back to statistical Z-score.")
        for i, item in enumerate(data_points):
            val = float(item.get(metric_key, 0))
            z_score = round((val - mean_val) / std_val, 2)
            if abs(z_score) >= 2.0:
                deviation_direction = "sharp drop" if z_score < 0 else "unusual surge"
                anomalies.append({
                    "index": i,
                    "date": item.get("date", f"Day {i+1}"),
                    "metric": metric_key,
                    "observed_value": val,
                    "baseline_mean": round(mean_val, 2),
                    "z_score": z_score,
                    "deviation": deviation_direction,
                    "status_tag": "Anomaly detected — investigation recommended.",
                    "notes": f"Value {val} outside 2-sigma baseline threshold."
                })

    return anomalies
