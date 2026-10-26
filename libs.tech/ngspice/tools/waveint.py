#!/usr/bin/env python3
"""Canonical piecewise-linear waveform integration for TR10 research reports.

Interpolate both window boundaries, split at every zero crossing, and keep
net/gross/positive/negative separately. Units are value-unit times time-unit.
Multi-window reports must use check_partition/integrate_partition before
comparing with a whole-window result. No Boolean-mask endpoint clipping.
"""
from __future__ import annotations

import bisect
import math
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Integral:
    net: float
    gross: float
    positive: float
    negative: float


def _agree(a, b, scale):
    return abs(a - b) <= 128 * sys.float_info.epsilon * max(scale, 1e-300)


def integrate(times, values, start, stop):
    if len(times) != len(values) or len(times) < 2:
        raise ValueError("integration requires equal time/value arrays with at least two points")
    if not all(math.isfinite(v) for v in times) or not all(math.isfinite(v) for v in values):
        raise ValueError("non-finite waveform")
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("waveform time must be strictly increasing")
    if not (math.isfinite(start) and math.isfinite(stop) and times[0] <= start < stop <= times[-1]):
        raise ValueError("window must be non-empty and fully contained in the actual trace")
    first = max(0, bisect.bisect_right(times, start) - 1)
    last = min(len(times) - 1, bisect.bisect_left(times, stop))
    nets, grosses, positives, negatives = [], [], [], []
    for index in range(first, last):
        ta, tb = times[index], times[index + 1]
        a, b = max(start, ta), min(stop, tb)
        if b <= a:
            continue
        va, vb = values[index], values[index + 1]
        slope = (vb - va) / (tb - ta)
        ya, yb = va + slope * (a - ta), va + slope * (b - ta)
        duration = b - a
        net = (ya + yb) * duration / 2
        if ya >= 0 and yb >= 0:
            positive, negative = net, 0.0
            gross = net
        elif ya <= 0 and yb <= 0:
            positive, negative = 0.0, -net
            gross = -net
        else:
            # Integrate the two triangles separately; abs(net) is not gross.
            fraction = abs(ya) / (abs(ya) + abs(yb))
            first_area = abs(ya) * duration * fraction / 2
            second_area = abs(yb) * duration * (1 - fraction) / 2
            gross = first_area + second_area
            positive, negative = ((first_area, second_area) if ya > 0
                                  else (second_area, first_area))
        nets.append(net)
        grosses.append(gross)
        positives.append(positive)
        negatives.append(negative)
    result = Integral(math.fsum(nets), math.fsum(grosses),
                      math.fsum(positives), math.fsum(negatives))
    if not all(math.isfinite(v) for v in (result.net, result.gross, result.positive, result.negative)):
        raise ValueError("non-finite integral")
    scale = max(result.gross, result.positive, result.negative, abs(result.net))
    if not _agree(result.net, result.positive - result.negative, scale):
        raise ArithmeticError("signed integral identity failed")
    if not _agree(result.gross, result.positive + result.negative, scale):
        raise ArithmeticError("gross integral identity failed")
    return result


def check_partition(windows, start, stop):
    if not math.isfinite(start) or not math.isfinite(stop) or stop <= start:
        raise ValueError("invalid requested partition extent")
    ordered = sorted(windows)
    if not ordered:
        raise ValueError("empty partition")
    tolerance = 64 * sys.float_info.epsilon * max(abs(start), abs(stop), 1e-300)
    previous = start
    for left, right in ordered:
        if not math.isfinite(left) or not math.isfinite(right) or right <= left:
            raise ValueError("invalid partition window")
        if abs(left - previous) > tolerance:
            raise ValueError(f"partition gap/overlap at {previous!r} -> {left!r}")
        previous = right
    if abs(previous - stop) > tolerance:
        raise ValueError("partition does not cover the requested final boundary")


def integrate_partition(times, values, start, stop, windows):
    check_partition(windows, start, stop)
    whole = integrate(times, values, start, stop)
    parts = [integrate(times, values, a, b) for a, b in windows]
    for field in ("net", "gross", "positive", "negative"):
        total = math.fsum(getattr(part, field) for part in parts)
        if not _agree(getattr(whole, field), total, whole.gross):
            raise ArithmeticError(f"partition additivity failed for {field}")
    return whole, parts


def _self_test():
    import unittest
    class AnalyticWindows(unittest.TestCase):
        def test_constant_clipped_boundaries(self):
            result = integrate((0, 1, 2), (3, 3, 3), 0.2, 1.8)
            self.assertAlmostEqual(result.net, 4.8)
            self.assertAlmostEqual(result.gross, 4.8)
        def test_linear_off_grid_window(self):
            self.assertAlmostEqual(integrate((0, 2), (0, 2), 0.5, 1.5).net, 1.0)
        def test_zero_crossing_keeps_both_signed_energies(self):
            result = integrate((0, 2), (-2, 2), 0, 2)
            self.assertAlmostEqual(result.net, 0)
            self.assertAlmostEqual(result.gross, 2)
            self.assertAlmostEqual(result.positive, 1)
            self.assertAlmostEqual(result.negative, 1)
        def test_triangle_area(self):
            self.assertAlmostEqual(integrate((0, 1, 2), (0, 2, 0), 0, 2).net, 2)
        def test_clipped_short_pulse(self):
            self.assertAlmostEqual(integrate((0, 1, 1.1, 1.2, 2), (0, 0, 1, 0, 0), 1.05, 1.15).net, 0.075)
        def test_full_signed_partition_additivity(self):
            whole, parts = integrate_partition((0, 1, 2), (-1, 2, -3), 0, 2, ((0, 0.73), (0.73, 2)))
            self.assertAlmostEqual(whole.net, math.fsum(part.net for part in parts))
            self.assertAlmostEqual(whole.gross, math.fsum(part.gross for part in parts))
        def test_missing_one_ns_is_not_a_valid_partition(self):
            with self.assertRaises(ValueError):
                check_partition(((0, 20e-9), (21e-9, 40e-9)), 0, 40e-9)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AnalyticWindows)
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    _self_test()
