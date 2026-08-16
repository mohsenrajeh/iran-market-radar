"""Unit tests for probability calibration, Brier score, and ECE."""
import numpy as np
from packages.ml.calibration import SignalProbabilityCalibrator, calculate_brier_score, calculate_ece


def test_probability_calibrator_fitting():
    # Synthetic validation set: raw scores vs binary outcomes
    rng = np.random.RandomState(42)
    scores = rng.uniform(0.1, 0.9, 200)
    # Higher score -> higher probability of win
    probs = 1.0 / (1.0 + np.exp(-4.0 * (scores - 0.5)))
    labels = rng.binomial(1, probs)

    calibrator = SignalProbabilityCalibrator(method="isotonic")
    calibrator.fit(scores, labels)

    assert calibrator.is_fitted is True
    p_low = calibrator.predict_p_profit(0.2)
    p_high = calibrator.predict_p_profit(0.8)

    assert 0.0 <= p_low <= 1.0
    assert 0.0 <= p_high <= 1.0
    assert p_high > p_low


def test_brier_and_ece_metrics():
    y_prob = np.array([0.8, 0.7, 0.2, 0.1])
    y_true = np.array([1, 1, 0, 0])
    brier = calculate_brier_score(y_prob, y_true)
    ece = calculate_ece(y_prob, y_true, n_bins=2)

    assert brier < 0.10
    assert ece >= 0.0
