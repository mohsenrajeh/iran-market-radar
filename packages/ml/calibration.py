"""Probability calibration, Brier score, ECE, Wilson CI, and ML model governance."""
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

# ── 1. Formal Label Contract ──
LABEL_CONTRACT = {
    "target_name": "is_profitable_5d_net",
    "definition_fa": "بازدهی خالص مثبت (> ۰.۰٪) پس از کسر کارمزد کامل ۱.۲۵۶۲٪ و ۲۰ پیپ اسلیپیج در افق ۵ روز معاملاتی یا دستیابی به حد سود قبل از حد ضرر",
    "horizon_sessions": 5,
    "round_trip_friction_pct": 1.2562,
    "slippage_bps": 20.0,
    "status": "FROZEN_SPECIFICATION",
}

# ── 2. Locked Champion Model Metadata ──
CHAMPION_MODEL_METADATA = {
    "model_id": None,
    "model_type": "Isotonic Regression + Prior Shrinkage",
    "version": None,
    "training_universe": None,
    "calibration_method": "isotonic_regression",
    "brier_score": None,
    "expected_calibration_error": None,
    "log_loss": None,
    "min_sample_threshold": 1000,
    "governance_status": "NOT_FITTED",
    "governance_status_fa": "مدل کالیبراسیون معتبر هنوز با داده خارج از نمونه برازش نشده است",
    "effective_date": None,
}


def calculate_wilson_confidence_interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """
    Computes Wilson Score 95% Confidence Interval for small binomial sample sizes.
    Essential for institutional audit when sample size n < 30.
    """
    if n <= 0:
        return (0.0, 1.0)
    
    z = 1.96  # 95% confidence z-score
    p_hat = k / n
    denom = 1 + (z**2) / n
    center = (p_hat + (z**2) / (2 * n)) / denom
    margin = (z * np.sqrt((p_hat * (1 - p_hat) / n) + (z**2) / (4 * n**2))) / denom
    
    low = max(0.0, float(center - margin))
    high = min(1.0, float(center + margin))
    return (round(low, 3), round(high, 3))


class SignalProbabilityCalibrator:
    """
    Fits and applies empirical calibration models (Isotonic Regression / Platt Scaling)
    exclusively on out-of-sample prediction folds with sample size guards.
    """

    def __init__(self, method: str = "isotonic"):
        self.method = method
        self.calibrator = None
        self.is_fitted = False
        self.model_version = CHAMPION_MODEL_METADATA["version"]

    def fit(self, y_score: np.ndarray, y_true: np.ndarray):
        """Fits calibrator on held-out validation predictions (requires n >= 50)."""
        if len(y_score) < 50:
            self.is_fitted = False
            return self

        y_score = np.clip(y_score, 0.001, 0.999)
        if self.method == "isotonic":
            self.calibrator = IsotonicRegression(out_of_bounds="clip")
            self.calibrator.fit(y_score, y_true)
        else:
            self.calibrator = LogisticRegression()
            self.calibrator.fit(y_score.reshape(-1, 1), y_true)

        self.is_fitted = True
        return self

    @classmethod
    def from_isotonic_curve(
        cls,
        x_thresholds: list[float],
        y_thresholds: list[float],
        *,
        model_version: str,
    ) -> "SignalProbabilityCalibrator":
        """Restore a validated JSON curve without executing a pickle/joblib artifact."""
        if len(x_thresholds) < 2 or len(x_thresholds) != len(y_thresholds):
            raise ValueError("Stored calibration curve is malformed.")
        if any(b <= a for a, b in zip(x_thresholds, x_thresholds[1:])):
            raise ValueError("Calibration x thresholds must be strictly increasing.")
        if any(value < 0.0 or value > 1.0 for value in y_thresholds):
            raise ValueError("Calibration probabilities must be within [0, 1].")
        instance = cls(method="isotonic")
        curve = IsotonicRegression(out_of_bounds="clip")
        curve.fit(np.asarray(x_thresholds, dtype=float), np.asarray(y_thresholds, dtype=float))
        instance.calibrator = curve
        instance.is_fitted = True
        instance.model_version = model_version
        return instance

    def export_isotonic_curve(self) -> tuple[list[float], list[float]]:
        if not self.is_fitted or self.method != "isotonic" or self.calibrator is None:
            raise RuntimeError("Only a fitted isotonic calibrator can be exported.")
        return (
            [float(value) for value in self.calibrator.X_thresholds_],
            [float(value) for value in self.calibrator.y_thresholds_],
        )

    def predict_p_profit(self, raw_score: float) -> float:
        """Transforms a raw score into a calibrated probability of profit (0.0 to 1.0)."""
        if not self.is_fitted or self.calibrator is None:
            raise RuntimeError(
                "Probability calibration is unavailable until an out-of-sample calibrator is fitted."
            )

        score_arr = np.array([raw_score])
        if self.method == "isotonic":
            p = self.calibrator.predict(score_arr)[0]
        else:
            p = self.calibrator.predict_proba(score_arr.reshape(-1, 1))[0, 1]

        # Prior shrinkage to prevent extreme 0 or 1 overconfidence
        shrunk_p = (p * 0.90) + (0.50 * 0.10)
        return float(np.clip(shrunk_p, 0.10, 0.90))


def calculate_brier_score(y_prob: np.ndarray, y_true: np.ndarray) -> float | None:
    """Computes Brier Score: Mean squared error of calibrated probability vs outcome."""
    if len(y_prob) == 0:
        return None
    return float(np.mean((y_prob - y_true) ** 2))


def calculate_ece(y_prob: np.ndarray, y_true: np.ndarray, n_bins: int = 5) -> float | None:
    """Computes Expected Calibration Error (ECE)."""
    if len(y_prob) == 0:
        return None
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    binids = np.digitize(y_prob, bins) - 1

    ece = 0.0
    n = len(y_prob)
    for i in range(n_bins):
        mask = binids == i
        if np.sum(mask) > 0:
            bin_acc = np.mean(y_true[mask])
            bin_conf = np.mean(y_prob[mask])
            ece += (np.sum(mask) / n) * np.abs(bin_acc - bin_conf)
    return float(ece)


def generate_reliability_curve(y_prob: np.ndarray | None = None, y_true: np.ndarray | None = None, n_bins: int = 5) -> list[dict]:
    """Generates reliability curve data points for charts."""
    if y_prob is None or y_true is None or len(y_prob) < 10 or len(y_prob) != len(y_true):
        return []
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy="uniform")
    out = []
    for pt, pp in zip(prob_true, prob_pred):
        out.append({
            "bin_center": round(float(pp), 2),
            "empirical_prob": round(float(pt), 2),
            "ideal_prob": round(float(pp), 2),
            "sample_count": int(len(y_prob) / n_bins),
        })
    return out
