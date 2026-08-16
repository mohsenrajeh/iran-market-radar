import pytest
from decimal import Decimal
from packages.shared.money import MoneyIRR, tomans_to_irr, irr_to_tomans

def test_money_irr_creation_and_arithmetic():
    m1 = MoneyIRR(1_000_000)
    m2 = MoneyIRR(500_000)
    
    assert (m1 + m2).rials == 1_500_000
    assert (m1 - m2).rials == 500_000
    assert (m1 * 2).rials == 2_000_000
    assert (m1 / 2) == 500_000.0
    assert m1.tomans == 100_000.0

def test_toman_rial_conversion():
    m = tomans_to_irr(10_000_000_000)
    assert m.rials == 100_000_000_000
    assert irr_to_tomans(100_000_000_000) == 10_000_000_000.0

def test_format_toman_display():
    m = MoneyIRR(100_000_000_000)
    assert "تومان" in m.format_toman()
    assert "ریال" in m.format_rials()
