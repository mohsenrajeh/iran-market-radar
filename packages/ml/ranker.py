"""Machine Learning Ranker and Probability Estimator."""
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from packages.ml.calibration import SignalProbabilityCalibrator


class MLRankerModel:
    """
    Supervised tabular ranker producing risk-adjusted edge and calibrated probability.
    Trained strictly via walk-forward splits.
    """

    def __init__(self, model_type: str = "lightgbm"):
        self.model_type = model_type
        if model_type == "lightgbm":
            self.model = LGBMClassifier(
                n_estimators=60,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                random_state=42,
                verbose=-1,
            )
        else:
            self.model = LogisticRegression(C=0.1, random_state=42)

        self.calibrator = SignalProbabilityCalibrator(method="isotonic")
        self.is_trained = False
        self.feature_names: list[str] = []

    def train_walk_forward(self, X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray, feature_names: list[str]):
        """Trains model on training window and fits calibrator on validation window."""
        self.feature_names = feature_names
        self.model.fit(X_train, y_train)

        # Predict raw probabilities on validation window
        val_probs = self.model.predict_proba(X_val)[:, 1]
        self.calibrator.fit(val_probs, y_val)
        self.is_trained = True

    def predict(self, feature_dict: dict[str, float]) -> tuple[float, float]:
        """
        Returns (raw_edge_score, calibrated_p_profit).
        """
        if not self.is_trained:
            raise RuntimeError("ML ranker is unavailable until walk-forward training and OOS calibration complete.")

        x_vec = np.array([[feature_dict.get(k, 0.0) for k in self.feature_names]], dtype=float)
        raw_p = float(self.model.predict_proba(x_vec)[0, 1])
        calibrated_p = self.calibrator.predict_p_profit(raw_p)
        return raw_p, calibrated_p
