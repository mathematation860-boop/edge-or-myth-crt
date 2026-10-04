"""
Smart Risk - "Candle Range Theory (CRT) Trading Model"
youtu.be/lGwCPn0i6ic  (1.1M views)

RULES MADE MECHANICAL (confirmed with Muhammad Ali, 2026-10-04)

A) CLASSIC CRT (the popular version the video describes first)
 Range candle : one 1-hour candle (default: the 08:00-09:00 New York candle,
                "the 1-hour candle just before the New York session opens").
 Sweep candle : the NEXT 1-hour candle trades beyond ONE side of the range
                and CLOSES back inside it. Closing outside = setup invalid.
                Sweeping both sides = no trade.
 Entry        : open of the third candle (only closed candles are used).
 Stop         : beyond the sweep candle's extreme.
 Target       : the opposite side of the range candle.

B) TREND CRT (Smart Risk's own "best" version)
 Trend        : 1H structure from confirmed 5-bar swing points. Uptrend =
                last swing high > previous swing high AND last swing low >
                previous swing low (downtrend the mirror).
 Location     : the impulse leg runs from the last swing low to the highest
                high since. The range candle must be a BEARISH candle whose
                low sits in the discount half of that leg (uptrend; mirror
                for downtrend: BULLISH candle in the premium half).
 Sweep        : next 1H candle takes the range low and CLOSES back inside.
 Entry        : on 5-minute bars after the sweep low, the first bullish fair
                value gap (low[i] > high[i-2]). Buy limit at the top of the gap,
                valid for 4 hours, cancelled if price breaks the sweep low.
 Stop         : below the gap (bottom of the FVG).
 Exit         : half closed at 1R; the other half runs to the impulse-leg
                high (the "strong level ahead") or the original stop.

COSTS: real Dukascopy bid/ask on every minute. Buys pay the ask, sells hit the
bid, +$0.05 slippage per side. Trades are walked minute by minute on real
1-minute bars; if stop and target fall inside the same minute the STOP is
assumed (conservative).
"""
import glob, numpy as np, pandas as pd

DATA = "data-dukascopy/bid_ask"   # folder with Dukascopy XAUUSD 1-minute bid/ask parquet files
SLIP = 0.05
NY = "America/New_York"


def load_m1():
    df = pd.concat(pd.read_parquet(f) for f in sorted(glob.glob(f"{DATA}/*.parquet")))
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def bars(m1, tf):
    key = m1.ts.dt.floor(f"{tf}min")
    g = m1.groupby(key)
    b = pd.DataFrame({"o": g.bid_open.first(), "h": g.bid_high.max(), "l": g.bid_low.min(),
                      "c": g.bid_close.last()})
    idx = m1.index.to_series().groupby(key)
    b["i0"] = idx.first().values
    b["i1"] = idx.last().values + 1
    b = b[(b.i1 - b.i0) >= max(3, tf // 4)]
    b.index.name = "ts"
    b = b.reset_index()
    b["ny"] = b.ts.dt.tz_convert(NY)
    b["nyh"] = b.ny.dt.hour
    return b


class Book:
    """minute arrays + exit walker"""
    def __init__(self, m1, spread_mode="real"):
        self.ts = m1.ts.dt.tz_localize(None).to_numpy()
        self.bo, self.bh, self.bl = m1.bid_open.to_numpy(), m1.bid_high.to_numpy(), m1.bid_low.to_numpy()
        spr = (m1.ask_close - m1.bid_close).to_numpy()
        if spread_mode == "real": self.sp, self.slip = spr, SLIP
        elif spread_mode == "zero": self.sp, self.slip = np.zeros(len(m1)), 0.0
        else: self.sp, self.slip = np.full(len(m1), float(spread_mode.split(":")[1])), 0.0
        self.N = len(m1)

    def first_hit(self, m, side, stop, tgt, maxm=None):
        """from minute m, return (reason, minute, price) for a position with stop/tgt"""
        N = self.N; end = N if maxm is None else min(N, m + maxm); CH = 20000
        bh, bl, sp = self.bh, self.bl, self.sp
        while m < end:
            j = slice(m, min(end, m + CH))
            if side == 1:   # long exits on the bid
                hs = np.flatnonzero(bl[j] <= stop); ht = np.flatnonzero(bh[j] >= tgt)
            else:           # short exits on the ask
                hs = np.flatnonzero(bh[j] + sp[j] >= stop); ht = np.flatnonzero(bl[j] + sp[j] <= tgt)
            a = hs[0] if len(hs) else 10**9; t = ht[0] if len(ht) else 10**9
            if a < 10**9 or t < 10**9:
                if a <= t: return "STOP", m + a, stop - side * self.slip
                return "TARGET", m + t, tgt - side * self.slip
            m += CH
        if maxm is not None and end < N:
            px = self.bo[end] + (0 if side == 1 else self.sp[end])
            return "TIME", end, px - side * self.slip
        return None


# ---------------------------------------------------------------- A: classic
def classic(m1, h1, bk, hour=8, maxdays=3):
    out, busy = [], -1
    hrs = h1.nyh.to_numpy(); H, L, C = h1.h.to_numpy(), h1.l.to_numpy(), h1.c.to_numpy()
    for k in np.flatnonzero(hrs == hour):
        if k + 2 >= len(h1): break
        # the sweep candle must be the very next hour
        if (h1.ts[k + 1] - h1.ts[k]) != pd.Timedelta(hours=1): continue
        rh, rl = H[k], L[k]; sh, sl, sc = H[k + 1], L[k + 1], C[k + 1]
        up, dn = sh > rh, sl < rl
        if up == dn: continue                       # no sweep, or both sides
        if up and not (rl <= sc <= rh): continue     # closed outside -> invalid
        if dn and not (rl <= sc <= rh): continue
        side = -1 if up else 1
        e = int(h1.i1[k + 1])
        if e <= busy or e >= bk.N - 1: continue
        entry = bk.bo[e] + bk.sp[e] + bk.slip if side == 1 else bk.bo[e] - bk.slip
        stop = sh if side == -1 else sl
        tgt = rl if side == -1 else rh
        risk = (entry - stop) * side; reward = (tgt - entry) * side
        if risk <= 0.05 or reward <= 0.05: continue
        r = bk.first_hit(e, side, stop, tgt, maxm=maxdays * 1440)
        if r is None: break
        why, xi, xp = r
        busy = xi
        out.append(dict(ver="A", hour=hour, side="LONG" if side == 1 else "SHORT", range_ts=h1.ts[k],
                        entry_ts=pd.Timestamp(bk.ts[e]), exit_ts=pd.Timestamp(bk.ts[xi]),
                        entry=round(entry, 3), stop=round(stop, 3), target=round(tgt, 3), exit=round(xp, 3),
                        risk=round(risk, 3), reward_planned=round(reward, 3),
                        R=side * (xp - entry) / risk, reason=why, hours=round((xi - e) / 60, 1)))
    return pd.DataFrame(out)


# ---------------------------------------------------------------- B: trend
def swings(h1, n=2):
    """confirmed fractal swing points (n bars each side). Returns arrays with the
    swing value known only from bar i+n onwards (no look-ahead)."""
    H, L = h1.h.to_numpy(), h1.l.to_numpy(); N = len(h1)
    sh = np.zeros(N, bool); sl = np.zeros(N, bool)
    for i in range(n, N - n):
        if H[i] == H[i - n:i + n + 1].max(): sh[i] = True
        if L[i] == L[i - n:i + n + 1].min(): sl[i] = True
    return sh, sl


def trend_state(h1, n=2):
    """for each bar k (at its close): trend (+1/-1/0), leg low/high, using only
    swings confirmed by bar k."""
    H, L = h1.h.to_numpy(), h1.l.to_numpy(); N = len(h1)
    sh, sl = swings(h1, n)
    tr = np.zeros(N, int); legA = np.full(N, np.nan); legB = np.full(N, np.nan)
    SH, SL = [], []          # (index, value)
    for k in range(N):
        c = k - n            # swing at c becomes known at bar k
        if c >= 0:
            if sh[c]: SH.append((c, H[c]))
            if sl[c]: SL.append((c, L[c]))
        if len(SH) < 2 or len(SL) < 2: continue
        hh = SH[-1][1] > SH[-2][1]; hl = SL[-1][1] > SL[-2][1]
        lh = SH[-1][1] < SH[-2][1]; ll = SL[-1][1] < SL[-2][1]
        if hh and hl:
            tr[k] = 1
            i0 = SL[-1][0]; legA[k] = L[i0]; legB[k] = H[i0:k + 1].max()   # leg low -> highest high since
        elif lh and ll:
            tr[k] = -1
            i0 = SH[-1][0]; legA[k] = H[i0]; legB[k] = L[i0:k + 1].min()   # leg high -> lowest low since
    return tr, legA, legB


def trend_crt(m1, h1, m5, bk, hours=None, fvg_valid_h=4, maxdays=5, need_discount=True, stop_at='fvg'):
    tr, legA, legB = trend_state(h1)
    O, H, L, C = h1.o.to_numpy(), h1.h.to_numpy(), h1.l.to_numpy(), h1.c.to_numpy()
    m5t = m5.ts.dt.tz_localize(None).to_numpy(); m5h, m5l = m5.h.to_numpy(), m5.l.to_numpy()
    out, busy = [], -1
    for k in range(10, len(h1) - 2):
        t = tr[k]
        if t == 0: continue
        if hours is not None and h1.nyh[k] not in hours: continue
        if (h1.ts[k + 1] - h1.ts[k]) != pd.Timedelta(hours=1): continue
        lo, hi = (legA[k], legB[k]) if t == 1 else (legB[k], legA[k])
        mid = (lo + hi) / 2
        if t == 1:
            if not C[k] < O[k]: continue                         # bearish range candle
            if need_discount and not (lo < L[k] <= mid): continue
            sw = L[k + 1] < L[k] and L[k] <= C[k + 1] <= H[k]    # sweep low, close back inside
        else:
            if not C[k] > O[k]: continue                         # bullish range candle
            if need_discount and not (mid <= H[k] < hi): continue
            sw = H[k + 1] > H[k] and L[k] <= C[k + 1] <= H[k]
        if not sw: continue
        side = t
        if int(h1.i0[k + 1]) <= busy: continue
        # ---- M5 FVG after the sweep extreme
        s0, s1 = h1.ts[k + 1], h1.ts[k + 1] + pd.Timedelta(hours=1 + fvg_valid_h)
        a = np.searchsorted(m5t, s0.tz_localize(None).to_datetime64()); b_ = np.searchsorted(m5t, s1.tz_localize(None).to_datetime64())
        if b_ - a < 4: continue
        seg_ext = (m5l[a:a + 12].argmin() if side == 1 else m5h[a:a + 12].argmax()) + a  # sweep extreme bar
        sweep_px = m5l[seg_ext] if side == 1 else m5h[seg_ext]
        fv = None
        for i in range(max(seg_ext + 2, a + 2), b_):
            if side == 1 and m5l[i] > m5h[i - 2]: fv = (i, m5l[i], m5h[i - 2]); break   # top, bottom
            if side == -1 and m5h[i] < m5l[i - 2]: fv = (i, m5h[i], m5l[i - 2]); break  # bottom, top
        if fv is None: continue
        i, near, far = fv                       # near = edge price returns to, far = other edge
        lim = near; stop = far if stop_at == 'fvg' else sweep_px - side * 0.10
        # pending order from the close of the FVG bar
        m_start = int(np.searchsorted(bk.ts, m5t[i] + np.timedelta64(5, "m")))
        m_end = int(np.searchsorted(bk.ts, s1.tz_localize(None).to_datetime64()))
        if m_start >= m_end or m_start >= bk.N: continue
        j = slice(m_start, m_end)
        if side == 1:
            fill = np.flatnonzero(bk.bl[j] + bk.sp[j] <= lim)      # ask touches the limit
            inval = np.flatnonzero(bk.bl[j] < sweep_px)
        else:
            fill = np.flatnonzero(bk.bh[j] >= lim)                  # bid touches the limit
            inval = np.flatnonzero(bk.bh[j] + bk.sp[j] > sweep_px)
        if not len(fill): continue
        if len(inval) and inval[0] < fill[0]: continue
        e = m_start + fill[0]
        entry = lim + side * bk.slip
        risk = (entry - stop) * side
        if risk <= 0.10: continue
        tp1 = entry + side * risk
        tp2 = legB[k]
        if (tp2 - entry) * side <= risk: tp2 = tp1 + side * risk * 0.0001  # leg target must be beyond 1R
        # same-minute: check stop first inside the fill minute
        r1 = bk.first_hit(e, side, stop, tp1, maxm=maxdays * 1440)
        if r1 is None: break
        why1, x1, p1 = r1
        if why1 != "TARGET":
            R = side * (p1 - entry) / risk; why = why1; xi = x1; p2 = p1
        else:
            r2 = bk.first_hit(x1 + 1, side, stop, tp2, maxm=maxdays * 1440)
            if r2 is None: break
            why2, xi, p2 = r2
            R = 0.5 * side * (p1 - entry) / risk + 0.5 * side * (p2 - entry) / risk
            why = "TP1+" + why2
        busy = xi
        out.append(dict(ver="B", hour=int(h1.nyh[k]), side="LONG" if side == 1 else "SHORT",
                        range_ts=h1.ts[k], entry_ts=pd.Timestamp(bk.ts[e]), exit_ts=pd.Timestamp(bk.ts[xi]),
                        entry=round(entry, 3), stop=round(stop, 3), target=round(tp2, 3), tp1=round(tp1, 3),
                        exit=round(p2, 3), risk=round(risk, 3), reward_planned=round(abs(tp2 - entry), 3),
                        R=R, reason=why, hours=round((xi - e) / 60, 1)))
    return pd.DataFrame(out)


def summary(t):
    if len(t) == 0: return dict(trades=0)
    w = (t.R > 0).mean(); eq = t.R.cumsum()
    gp, gl = t.R[t.R > 0].sum(), -t.R[t.R < 0].sum()
    return dict(trades=len(t), win_rate=round(100 * w, 1), avg_R=round(t.R.mean(), 3),
                total_R=round(t.R.sum(), 1), pf=round(gp / gl, 2) if gl > 0 else np.inf,
                max_dd_R=round((eq.cummax() - eq).max(), 1), avg_risk_usd=round(t.risk.mean(), 2),
                med_hours=round(t.hours.median(), 1))


# ---------------------------------------------------------------- generalised classic (for the "fix" search)
def classic_g(b, bk, hours=None, trend=None, strong=0.0, maxdays=5, tf_h=1, stop_buf=0.0, rr_cap=None):
    """b: bars of any timeframe. hours: NY hours allowed for the RANGE candle (None = all).
    trend: array (+1/-1/0) known at the range candle close -> only trade with it.
    strong: sweep candle must close at least this fraction back inside the range
            (0 = anywhere inside, 0.5 = beyond the range midpoint)."""
    out, busy = [], -1
    H, L, C = b.h.to_numpy(), b.l.to_numpy(), b.c.to_numpy(); hrs = b.nyh.to_numpy()
    step = pd.Timedelta(hours=tf_h)
    for k in range(len(b) - 2):
        if hours is not None and hrs[k] not in hours: continue
        if (b.ts[k + 1] - b.ts[k]) != step: continue
        rh, rl = H[k], L[k]; sh, sl, sc = H[k + 1], L[k + 1], C[k + 1]
        up, dn = sh > rh, sl < rl
        if up == dn or not (rl <= sc <= rh): continue
        side = -1 if up else 1
        if trend is not None and trend[k + 1] != side: continue
        rng = rh - rl
        if rng <= 0: continue
        depth = (rh - sc) / rng if side == -1 else (sc - rl) / rng
        if depth < strong: continue
        e = int(b.i1[k + 1])
        if e <= busy or e >= bk.N - 1: continue
        entry = bk.bo[e] + bk.sp[e] + bk.slip if side == 1 else bk.bo[e] - bk.slip
        stop = (sh + stop_buf) if side == -1 else (sl - stop_buf)
        tgt = rl if side == -1 else rh
        risk = (entry - stop) * side; reward = (tgt - entry) * side
        if risk <= 0.05 or reward <= 0.05: continue
        r = bk.first_hit(e, side, stop, tgt, maxm=maxdays * 1440)
        if r is None: break
        why, xi, xp = r
        busy = xi
        out.append(dict(side="LONG" if side == 1 else "SHORT", range_ts=b.ts[k], hour=int(hrs[k]),
                        entry_ts=pd.Timestamp(bk.ts[e]), exit_ts=pd.Timestamp(bk.ts[xi]),
                        entry=round(entry, 3), stop=round(stop, 3), target=round(tgt, 3), exit=round(xp, 3),
                        risk=round(risk, 3), reward_planned=round(reward, 3),
                        R=side * (xp - entry) / risk, reason=why, hours=round((xi - e) / 60, 1)))
    return pd.DataFrame(out)


def ema_trend(b, n=200):
    e = b.c.ewm(span=n, adjust=False).mean()
    t = np.where(b.c > e, 1, -1); t[:n] = 0
    return t


def crt_limit(b, bk, hours=None, trend=None, strong=0.0, tf_h=1, entry_frac=0.0, valid_h=4,
              tgt_frac=1.0, maxdays=5, min_rr=0.0):
    """CRT with a LIMIT entry after the sweep candle closes.
    entry_frac: 0 = at the swept range edge, 0.25 = a quarter into the range, etc.
    tgt_frac  : 1 = opposite edge of the range, 0.5 = range midpoint.
    stop      : beyond the sweep candle extreme."""
    out, busy = [], -1
    H, L, C = b.h.to_numpy(), b.l.to_numpy(), b.c.to_numpy(); hrs = b.nyh.to_numpy()
    step = pd.Timedelta(hours=tf_h)
    for k in range(len(b) - 2):
        if hours is not None and hrs[k] not in hours: continue
        if (b.ts[k + 1] - b.ts[k]) != step: continue
        rh, rl = H[k], L[k]; sh, sl, sc = H[k + 1], L[k + 1], C[k + 1]
        up, dn = sh > rh, sl < rl
        if up == dn or not (rl <= sc <= rh): continue
        side = -1 if up else 1
        if trend is not None and trend[k + 1] != side: continue
        rng = rh - rl
        if rng <= 0: continue
        depth = (rh - sc) / rng if side == -1 else (sc - rl) / rng
        if depth < strong: continue
        if side == 1:
            lim = rl + entry_frac * rng; stop = sl; tgt = rl + tgt_frac * rng
        else:
            lim = rh - entry_frac * rng; stop = sh; tgt = rh - tgt_frac * rng
        m0 = int(b.i1[k + 1]); m1_ = min(bk.N, m0 + int(valid_h * 60))
        if m0 <= busy or m0 >= bk.N - 1: continue
        j = slice(m0, m1_)
        if side == 1:
            fill = np.flatnonzero(bk.bl[j] + bk.sp[j] <= lim); bad = np.flatnonzero(bk.bl[j] <= stop)
            already = bk.bo[m0] + bk.sp[m0] <= lim
        else:
            fill = np.flatnonzero(bk.bh[j] >= lim); bad = np.flatnonzero(bk.bh[j] + bk.sp[j] >= stop)
            already = bk.bo[m0] >= lim
        if already:   # price already past the limit at the open -> take the open
            e = m0; entry = bk.bo[m0] + bk.sp[m0] + bk.slip if side == 1 else bk.bo[m0] - bk.slip
        else:
            if not len(fill): continue
            if len(bad) and bad[0] < fill[0]: continue
            e = m0 + fill[0]; entry = lim + side * bk.slip
        risk = (entry - stop) * side; reward = (tgt - entry) * side
        if risk <= 0.05 or reward <= 0.05 or reward / risk < min_rr: continue
        r = bk.first_hit(e, side, stop, tgt, maxm=maxdays * 1440)
        if r is None: break
        why, xi, xp = r
        busy = xi
        out.append(dict(side="LONG" if side == 1 else "SHORT", range_ts=b.ts[k], hour=int(hrs[k]),
                        entry_ts=pd.Timestamp(bk.ts[e]), exit_ts=pd.Timestamp(bk.ts[xi]),
                        entry=round(entry, 3), stop=round(stop, 3), target=round(tgt, 3), exit=round(xp, 3),
                        risk=round(risk, 3), reward_planned=round(reward, 3),
                        R=side * (xp - entry) / risk, reason=why, hours=round((xi - e) / 60, 1)))
    return pd.DataFrame(out)


def crt_break(b, bk, hours=None, trend=None, tf_h=1, rr=1.0, stop_mode="mid", maxdays=5):
    """The case the video calls INVALID: the second candle CLOSES beyond the range.
    Trade the breakout direction at the third candle's open.
    stop_mode: 'mid' = range midpoint, 'far' = opposite side of the range, 'edge' = broken edge."""
    out, busy = [], -1
    H, L, C = b.h.to_numpy(), b.l.to_numpy(), b.c.to_numpy(); hrs = b.nyh.to_numpy()
    step = pd.Timedelta(hours=tf_h)
    for k in range(len(b) - 2):
        if hours is not None and hrs[k] not in hours: continue
        if (b.ts[k + 1] - b.ts[k]) != step: continue
        rh, rl, sc = H[k], L[k], C[k + 1]
        if sc > rh: side = 1
        elif sc < rl: side = -1
        else: continue
        if trend is not None and trend[k + 1] != side: continue
        e = int(b.i1[k + 1])
        if e <= busy or e >= bk.N - 1: continue
        entry = bk.bo[e] + bk.sp[e] + bk.slip if side == 1 else bk.bo[e] - bk.slip
        if stop_mode == "mid": stop = (rh + rl) / 2
        elif stop_mode == "far": stop = rl if side == 1 else rh
        else: stop = rh if side == 1 else rl
        risk = (entry - stop) * side
        if risk <= 0.3: continue
        tgt = entry + side * rr * risk
        r = bk.first_hit(e, side, stop, tgt, maxm=maxdays * 1440)
        if r is None: break
        why, xi, xp = r
        busy = xi
        out.append(dict(side="LONG" if side == 1 else "SHORT", range_ts=b.ts[k], hour=int(hrs[k]),
                        entry_ts=pd.Timestamp(bk.ts[e]), exit_ts=pd.Timestamp(bk.ts[xi]),
                        entry=round(entry, 3), stop=round(stop, 3), target=round(tgt, 3), exit=round(xp, 3),
                        risk=round(risk, 3), reward_planned=round(rr * risk, 3),
                        R=side * (xp - entry) / risk, reason=why, hours=round((xi - e) / 60, 1)))
    return pd.DataFrame(out)
