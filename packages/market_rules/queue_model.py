"""Conservative queue-fill and execution risk models for Iranian price limits."""
from dataclasses import dataclass


@dataclass
class ExecutionFeasibility:
    fill_probability_score: float  # 0 to 100
    is_locked_limit_up: bool       # صف خرید سنگین
    is_locked_limit_down: bool     # صف فروش سنگین
    risk_flags_fa: list[str]


def evaluate_execution_feasibility(
    last_price: float,
    allowed_min: float,
    allowed_max: float,
    bid_queue_volume: int = 0,
    ask_queue_volume: int = 0,
    avg_daily_volume: int = 1_000_000,
) -> ExecutionFeasibility:
    """
    Evaluates whether a buy or sell order can realistically execute.
    In Iran markets, when a stock is locked at +5% upper limit with millions in buy queue,
    fill probability is very low (صف خرید).
    """
    flags_fa: list[str] = []
    fill_prob = 90.0
    is_limit_up = False
    is_limit_down = False

    # Upper limit check
    if allowed_max > 0 and abs(last_price - allowed_max) / allowed_max < 0.002:
        is_limit_up = True
        # If huge queue compared to avg daily volume
        queue_ratio = bid_queue_volume / max(1, avg_daily_volume)
        if queue_ratio > 0.5:
            fill_prob = max(10.0, 50.0 - (queue_ratio * 30.0))
            flags_fa.append("نماد در صف خرید قفل است؛ احتمال انجام سفارش در ورود بسیار پایین است")
        else:
            fill_prob = 65.0
            flags_fa.append("قیمت در آستانه سقف مجاز روزانه قرار دارد")

    # Lower limit check
    elif allowed_min > 0 and abs(last_price - allowed_min) / allowed_min < 0.002:
        is_limit_down = True
        fill_prob = 85.0  # Buying is easy, but exiting later might be hard
        flags_fa.append("نماد در صف فروش یا کف قیمت روزانه است؛ ریسک عدم امکان خروج سریع")

    return ExecutionFeasibility(
        fill_probability_score=round(fill_prob, 1),
        is_locked_limit_up=is_limit_up,
        is_locked_limit_down=is_limit_down,
        risk_flags_fa=flags_fa,
    )
