"""Point-in-time machine learning dataset builder."""
import numpy as np
from packages.feature_engine.indicators import compute_symbol_features
from packages.market_rules.fees import calculate_net_return


def build_point_in_time_dataset(
    all_symbol_bars: dict[str, list[dict]],
    all_client_types: dict[str, list[dict]] | None = None,
    horizon_sessions: int = 5,
    min_profit_threshold: float = 0.015,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Builds tabular (X, y) training datasets strictly respecting point-in-time rules.
    Signal at timestamp T uses features computed up to bar T.
    Execution enters at bar T+1 and exits at bar T+1+horizon.
    Net return deducts realistic Iranian transaction costs.
    """
    X_rows = []
    y_labels = []
    feature_names = []

    for symbol, bars in all_symbol_bars.items():
        n = len(bars)
        if n < 40 + horizon_sessions:
            continue

        ct_list = all_client_types.get(symbol, []) if all_client_types else []

        for i in range(30, n - horizon_sessions - 1):
            sub_bars = bars[: i + 1]
            sub_ct = ct_list[: i + 1] if ct_list else []

            feat_dict = compute_symbol_features(sub_bars, sub_ct)
            if not feature_names:
                feature_names = sorted(list(feat_dict.keys()))

            row_vector = [feat_dict[k] for k in feature_names]

            # Label calculation: entry at bar i+1 open/close, exit at bar i+1+horizon close
            entry_price = bars[i + 1]["open"] if bars[i + 1]["open"] > 0 else bars[i + 1]["close"]
            exit_price = bars[i + 1 + horizon_sessions]["close"]

            net_ret = calculate_net_return(entry_price, exit_price, instrument_class="equity")
            label = 1 if net_ret > min_profit_threshold else 0

            X_rows.append(row_vector)
            y_labels.append(label)

    if not X_rows:
        return np.array([]), np.array([]), feature_names

    return np.array(X_rows, dtype=float), np.array(y_labels, dtype=int), feature_names
