import pandas as pd
import pytest

from tracker.pricing import accrued_interest, cp_price
from tracker.portfolio import align


def test_cp_price_is_par_at_maturity():
    assert cp_price("2026-12-16", 0.03, "2026-12-16") == pytest.approx(100)


def test_cp_price_90_days():
    # Sep 17 -> Dec 16 = 90 days
    assert cp_price("2026-09-17", 0.03, "2026-12-16") == pytest.approx(100 / (1 + 0.03 * 90 / 360))


def test_accrued_is_zero_on_coupon_date():
    assert accrued_interest("2026-09-13", 0.027, 1, "2026-09-13", "2027-09-13", "ACT/ACT") == 0


def test_accrued_act_act_one_month():
    a = accrued_interest("2026-10-13", 0.027, 1, "2026-09-13", "2027-09-13", "ACT/ACT")
    assert a == pytest.approx(2.7 * 30 / 365)


def test_accrued_30_360():
    # Jun 15 -> Sep 18 = 3 months + 3 days = 93 days in 30/360
    a = accrued_interest("2026-09-18", 0.09625, 2, "2026-06-15", "2026-12-15", "30/360")
    assert a == pytest.approx(9.625 * 93 / 360)


def test_accrued_outside_period_raises():
    with pytest.raises(ValueError):
        accrued_interest("2026-09-01", 0.027, 1, "2026-09-13", "2027-09-13", "ACT/ACT")


def test_align_forward_fills_missing_days():
    s = pd.Series([1.0, 3.0], index=pd.to_datetime(["2026-09-17", "2026-09-21"]))
    idx = pd.bdate_range("2026-09-18", "2026-09-22")
    assert list(align(s, idx)) == [1.0, 3.0, 3.0]
