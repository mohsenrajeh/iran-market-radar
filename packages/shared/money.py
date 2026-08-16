"""Canonical Money and Currency utilities for Iran Market Radar.
Ensures pure Integer/Decimal IRR arithmetic internally and unified Toman/Rial conversions for UI.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Union

# Currency conversion factor: 1 Toman = 10 Iranian Rials (IRR)
IRR_PER_TOMAN = 10


class MoneyIRR:
    """
    Canonical Immutable Money representation in Iranian Rials (IRR).
    Guarantees exact arithmetic without floating-point rounding errors.
    """
    __slots__ = ("_amount_irr",)

    def __init__(self, amount: Union[int, float, Decimal, str, "MoneyIRR"]):
        if isinstance(amount, MoneyIRR):
            self._amount_irr = amount._amount_irr
        elif isinstance(amount, Decimal):
            self._amount_irr = int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        elif isinstance(amount, (int, float, str)):
            self._amount_irr = int(round(float(amount)))
        else:
            raise TypeError(f"Cannot convert {type(amount)} to MoneyIRR")

    @property
    def rials(self) -> int:
        """Integer amount in Rials (IRR)."""
        return self._amount_irr

    @property
    def tomans(self) -> float:
        """Float amount in Tomans (for reporting only)."""
        return self._amount_irr / IRR_PER_TOMAN

    @property
    def tomans_int(self) -> int:
        """Integer amount in Tomans (truncated)."""
        return self._amount_irr // IRR_PER_TOMAN

    @property
    def million_tomans(self) -> float:
        """Amount in Million Tomans (for UI cockpit cards)."""
        return self.tomans / 1_000_000.0

    @property
    def billion_tomans(self) -> float:
        """Amount in Billion Tomans (for fund NAV)."""
        return self.tomans / 1_000_000_000.0

    def to_decimal(self) -> Decimal:
        return Decimal(self._amount_irr)

    # Arithmetic Operations
    def __add__(self, other: Union["MoneyIRR", int, float, Decimal]) -> "MoneyIRR":
        val = other.rials if isinstance(other, MoneyIRR) else int(other)
        return MoneyIRR(self._amount_irr + val)

    def __sub__(self, other: Union["MoneyIRR", int, float, Decimal]) -> "MoneyIRR":
        val = other.rials if isinstance(other, MoneyIRR) else int(other)
        return MoneyIRR(self._amount_irr - val)

    def __mul__(self, other: Union[int, float, Decimal]) -> "MoneyIRR":
        if isinstance(other, Decimal):
            return MoneyIRR(Decimal(self._amount_irr) * other)
        return MoneyIRR(round(self._amount_irr * float(other)))

    def __truediv__(self, other: Union[int, float, Decimal, "MoneyIRR"]) -> Union[float, Decimal]:
        if isinstance(other, MoneyIRR):
            return self._amount_irr / other._amount_irr if other._amount_irr != 0 else 0.0
        return self._amount_irr / float(other) if float(other) != 0 else 0.0

    def __neg__(self) -> "MoneyIRR":
        return MoneyIRR(-self._amount_irr)

    def __abs__(self) -> "MoneyIRR":
        return MoneyIRR(abs(self._amount_irr))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MoneyIRR):
            return self._amount_irr == other._amount_irr
        if isinstance(other, (int, float, Decimal)):
            return self._amount_irr == int(other)
        return False

    def __lt__(self, other: Union["MoneyIRR", int, float, Decimal]) -> bool:
        val = other.rials if isinstance(other, MoneyIRR) else int(other)
        return self._amount_irr < val

    def __le__(self, other: Union["MoneyIRR", int, float, Decimal]) -> bool:
        val = other.rials if isinstance(other, MoneyIRR) else int(other)
        return self._amount_irr <= val

    def __gt__(self, other: Union["MoneyIRR", int, float, Decimal]) -> bool:
        val = other.rials if isinstance(other, MoneyIRR) else int(other)
        return self._amount_irr > val

    def __ge__(self, other: Union["MoneyIRR", int, float, Decimal]) -> bool:
        val = other.rials if isinstance(other, MoneyIRR) else int(other)
        return self._amount_irr >= val

    def __repr__(self) -> str:
        return f"MoneyIRR({self._amount_irr:,} IRR / {self.tomans:,.1f} Toman)"

    def format_toman(self, include_unit: bool = True, decimals: int = 1) -> str:
        """Formats money into human-readable Toman string with Persian unit."""
        if decimals == 0:
            formatted = f"{self.tomans_int:,}"
        else:
            formatted = f"{self.tomans:,.{decimals}f}"
        return f"{formatted} تومان" if include_unit else formatted

    def format_rials(self, include_unit: bool = True) -> str:
        """Formats money into human-readable Rial string with Persian unit."""
        formatted = f"{self._amount_irr:,}"
        return f"{formatted} ریال" if include_unit else formatted


def tomans_to_irr(tomans: Union[int, float, Decimal]) -> MoneyIRR:
    """Helper to convert Tomans to MoneyIRR."""
    return MoneyIRR(Decimal(str(tomans)) * Decimal(IRR_PER_TOMAN))


def irr_to_tomans(irr_amount: Union[int, float, Decimal, MoneyIRR]) -> float:
    """Helper to convert IRR to Tomans."""
    if isinstance(irr_amount, MoneyIRR):
        return irr_amount.tomans
    return float(irr_amount) / IRR_PER_TOMAN
