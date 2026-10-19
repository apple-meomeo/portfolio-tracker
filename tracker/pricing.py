"""Pricing formulas for instruments that need more than a quoted price."""
import pandas as pd


def _days_30_360(start: pd.Timestamp, end: pd.Timestamp) -> int:
    """Day count under the 30/360 (bond basis) convention."""
    d1 = min(start.day, 30)
    d2 = min(end.day, 30) if d1 == 30 else end.day
    return 360 * (end.year - start.year) + 30 * (end.month - start.month) + (d2 - d1)


def accrued_interest(on, coupon, freq, last_coupon, next_coupon, day_count) -> float:
    """Accrued interest on date `on`, in % of par (same unit as a bond's quoted price).

    coupon: annual coupon rate, e.g. 0.027 for 2.70%
    freq: coupons per year (1 = annual, 2 = semi-annual)
    day_count: "ACT/ACT" (German government bonds) or "30/360" (most USD corporate bonds)
    """
    on, last, nxt = pd.Timestamp(on), pd.Timestamp(last_coupon), pd.Timestamp(next_coupon)
    if not last <= on <= nxt:
        raise ValueError(f"{on.date()} is outside the coupon period {last.date()} -> {nxt.date()}")
    if day_count == "ACT/ACT":
        return 100 * coupon / freq * (on - last).days / (nxt - last).days
    if day_count == "30/360":
        return 100 * coupon * _days_30_360(last, on) / 360
    raise ValueError(f"Unknown day count: {day_count}")


def cp_price(on, yield_, maturity) -> float:
    """Price (per 100 of nominal) of a money-market discount instrument, ACT/360.

    A NEU CP pays 100 at maturity; today it is worth 100 discounted at its yield.
    """
    days = (pd.Timestamp(maturity) - pd.Timestamp(on)).days
    return 100 / (1 + yield_ * days / 360)
