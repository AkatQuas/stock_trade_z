from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .compute import (compute_atr, compute_cci14_cci84, compute_pit_and_trap,
                      compute_rsi)
from .parallel_utils import parallel_select_helper


class ATRVolatilitySelector:
    """Flag stocks whose ATR/price exceeds a relative threshold."""

    def __init__(self, atr_window: int = 14, rel_threshold: float = 0.05, min_history: int = 30) -> None:
        self.atr_window = atr_window
        self.rel_threshold = rel_threshold
        self.min_history = min_history

    def _passes_filters(self, hist: pd.DataFrame) -> bool:
        if hist is None or len(hist) < self.min_history:
            return False
        atr = compute_atr(hist, self.atr_window)
        atr_latest = float(atr.iloc[-1])
        price = float(hist["close"].iloc[-1])
        if price <= 0:
            return False
        return (atr_latest / price) >= self.rel_threshold

    def select(self, date: pd.Timestamp, data: Dict[str, pd.DataFrame]) -> List[str]:
        tasks = []
        for code, df in data.items():
            hist = df[df["date"] <= date]
            if hist.empty:
                continue
            tasks.append((code, hist))

        # Use multiprocessing; fallback inside helper
        return parallel_select_helper(self, tasks)


class RSIExtremesSelector:
    """Flag extreme RSI values (oversold or overbought) as risk signals."""

    def __init__(self, rsi_window: int = 14, low_thresh: float = 20.0, high_thresh: float = 80.0, min_history: int = 30) -> None:
        self.rsi_window = rsi_window
        self.low_thresh = low_thresh
        self.high_thresh = high_thresh
        self.min_history = min_history

    def _passes_filters(self, hist: pd.DataFrame) -> bool:
        if hist is None or len(hist) < self.min_history:
            return False
        rsi = compute_rsi(hist, self.rsi_window)
        rsi_latest = float(rsi.iloc[-1])
        return (rsi_latest <= self.low_thresh) or (rsi_latest >= self.high_thresh)

    def select(self, date: pd.Timestamp, data: Dict[str, pd.DataFrame]) -> List[str]:
        tasks = []
        for code, df in data.items():
            hist = df[df["date"] <= date]
            if hist.empty:
                continue
            tasks.append((code, hist))

        return parallel_select_helper(self, tasks)


class MADeclineSelector:
    """Flag stocks where short MA is below long MA and the long MA slope is negative."""

    def __init__(self, short_ma: int = 5, long_ma: int = 50, slope_days: int = 5, min_history: int = 60) -> None:
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.slope_days = slope_days
        self.min_history = min_history

    @staticmethod
    def _slope_negative(series: pd.Series, days: int) -> bool:
        if len(series.dropna()) < days + 1:
            return False
        y = series.dropna().astype(float).iloc[-(days + 1):]
        # simple linear slope: last - first
        return (float(y.iloc[-1]) - float(y.iloc[0])) < 0

    def _passes_filters(self, hist: pd.DataFrame) -> bool:
        if hist is None or len(hist) < self.min_history:
            return False
        close = hist["close"].astype(float)
        ma_s = close.rolling(window=self.short_ma).mean()
        ma_l = close.rolling(window=self.long_ma).mean()
        if pd.isna(ma_s.iloc[-1]) or pd.isna(ma_l.iloc[-1]):
            return False
        # short MA below long MA and long MA slope negative
        return (ma_s.iloc[-1] < ma_l.iloc[-1]) and self._slope_negative(ma_l, self.slope_days)

    def select(self, date: pd.Timestamp, data: Dict[str, pd.DataFrame]) -> List[str]:
        tasks = []
        for code, df in data.items():
            hist = df[df["date"] <= date]
            if hist.empty:
                continue
            tasks.append((code, hist))

        return parallel_select_helper(self, tasks)

class TopTrapSelector:
    def __init__(
            self,

        cci_overbought_threshold: float = 100.0,
        cci_extreme_overbought_threshold: float = 200.0,
    ) -> None:
        self.cci_overbought_threshold= cci_overbought_threshold
        self.cci_extreme_overbought_threshold = cci_extreme_overbought_threshold

    def _passes_filters(self, hist: pd.DataFrame) -> bool:
        hist = compute_pit_and_trap(hist)
        hist = compute_cci14_cci84(hist)
        # CCI Sell Signals (overbought)
        hist['cci14_overbought_sell'] = np.where(hist['CCI14'] > self.cci_overbought_threshold, 1, 0)
        hist['cci14_extreme_overbought_sell'] = np.where(hist['CCI14'] > self.cci_extreme_overbought_threshold, 1, 0)
        hist['cci84_overbought_sell'] = np.where(hist['CCI84'] > self.cci_overbought_threshold, 1, 0)

        cci_overbought = hist['cci14_overbought_sell'].iloc[-1] == 1 or hist['cci14_extreme_overbought_sell'].iloc[-1] == 1 or hist['cci84_overbought_sell'].iloc[-1] == 1

        if cci_overbought and hist['top_trap_sell'].iloc[-1] == 120:
            return True
        return False


class VolumeSelloffSelector:
    """Flag heavy sell-off: big volume spike while price drops."""

    def __init__(self, lookback_n: int = 20, vol_multiple: float = 2.0, drop_pct: float = 0.03, min_history: int = 25) -> None:
        self.lookback_n = lookback_n
        self.vol_multiple = vol_multiple
        self.drop_pct = drop_pct
        self.min_history = min_history

    def _passes_filters(self, hist: pd.DataFrame) -> bool:
        if hist is None or len(hist) < self.min_history:
            return False
        today = hist.iloc[-1]
        prev = hist.iloc[-2]
        try:
            v_today = float(today.get("volume", 0))
            c_today = float(today.get("close", 0))
            c_prev = float(prev.get("close", 0))
        except Exception:
            return False
        vol_hist = hist["volume"].iloc[-(self.lookback_n + 1):-1].replace(0, np.nan).dropna().astype(float)
        if vol_hist.empty:
            return False
        avg_vol = float(vol_hist.mean())
        if avg_vol <= 0:
            return False
        price_drop = 0.0
        if c_prev > 0:
            price_drop = (c_prev - c_today) / c_prev
        return (v_today >= self.vol_multiple * avg_vol) and (price_drop >= self.drop_pct)

    def select(self, date: pd.Timestamp, data: Dict[str, pd.DataFrame]) -> List[str]:
        picks: List[str] = []
        for code, df in data.items():
            hist = df[df["date"] <= date]
            if hist.empty:
                continue
            try:
                if self._passes_filters(df):
                    picks.append(code)
            except Exception:
                continue
        return picks
