# Edge or Myth #7: Candle Range Theory (CRT) on Gold

Source strategy: Smart Risk, "Candle Range Theory (CRT) Trading Model" (youtu.be/lGwCPn0i6ic, 1.1M views).
Market: XAUUSD. Data: Dukascopy 1-minute **bid and ask**, 1 Jan 2020 to 18 Sep 2026.

## The claim being tested
One candle makes a range. The next candle sweeps one side (takes the stops) and closes back inside. Trade back towards the other side of the range. Smart Risk uses the 08:00 New York 1-hour candle as the range.

## Results (real spread)

| Version | Trades | Win rate | Avg R | Total | Profit factor | Max DD |
|---|---|---|---|---|---|---|
| Classic CRT, 1H, NY 08:00 range | 563 | 44.8% | −0.061 | −34R | 0.89 | 47R |
| Smart Risk "trend CRT", 5m FVG entry, stop under the FVG | 901 | 5.0% | −0.815 | −734R | 0.16 | 733R |
| Same, stop under the sweep instead | 881 | 24.6% | −0.082 | −72R | 0.85 | 122R |
| **Failed CRT, 4H** (candle 2 CLOSES outside → trade the breakout, stop = other side of range, 1:1) | **1,313** | **52.6%** | **+0.052** | **+69R** | **1.11** | **33R** |

**Failed CRT, 4H, robustness checks:**

- **Time split.** 2020–2023 gives +0.041R per trade. 2024–2026 gives +0.066R per trade.
- **By year (average R per trade).**

  | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---|---|---|---|---|---|---|
  | +0.09 | +0.08 | −0.02 | 0.00 | +0.07 | +0.10 | +0.02 |

- **By side.** Longs make +0.108R per trade. Shorts make −0.011R per trade. Most of the edge came from gold's uptrend.
- **Spread sensitivity (average R per trade).** Zero spread: 0.064. $0.20: 0.061. $0.60: 0.044.
- **200 EMA trend filter.** It did **not** help: +0.019R per trade, max drawdown 41R. It stays in the script as an option only.
- **Worst losing streak.** 10 trades.

**Every hour of the day (classic CRT, real spread).**

- All 22 trading hours are negative.
- 08:00 and 09:00 New York are the least bad, at −0.06 and −0.02 R per trade. So Smart Risk picked the best hour; the trade itself is the problem.
- Full table: `hours.csv`.

**TradingView Strategy Tester** (OANDA:XAUUSD 4h, Jan 2023 to Oct 2026, no spread):

| Mode | Trades | Win rate | Profit factor | Net |
|---|---|---|---|---|
| Failed CRT | 612 | 52.61% | 1.301 | +9.46% |
| Original CRT | 1,214 | 45.14% | 1.024 | +0.54% |

See `TV_report.txt`.

## Honest caveat
The Failed CRT setting was the best of 32 breakout variants we tried (all of them are in `fix3.csv`, losers included). It was positive in both halves of the data, but the edge is small: about +0.05R per trade. Treat it as a candidate to forward-test, not proof.

## Method
1. All 1-minute bid/ask bars are loaded and resampled to 5m, 1H and 4H bid OHLC. New York hours use `America/New_York`, with DST.
2. Signals use **closed** candles only. Entry is the open of the next candle.
3. Every trade is walked minute by minute on real 1-minute bars:
   - Buys pay the ask and sells hit the bid, plus $0.05 slippage.
   - If the stop and the target are hit in the same minute, the **stop** counts.
   - Time-out is 5 days (4H) or 3 days (1H).
4. In-sample is 2020–2023 and out-of-sample is 2024–2026.

## Files

**Code**

| File | What it does |
|---|---|
| `crt.py` | All logic: data loading, bar building, the minute-by-minute trade walker, classic CRT, trend CRT, and the limit and breakout variants. |
| `prep.py` | Builds `cache.pkl` from the parquet files. Set `DATA` in `crt.py` to your folder first. |
| `run1.py` | Classic CRT at NY 08:00, plus trend CRT. |
| `hours.py` | Classic CRT on every hour, real and zero spread. Writes `hours.csv` and `A_allhours.csv.gz`. |
| `runB.py` | Smart Risk's trend CRT, with the stop at the FVG and at the sweep. Writes `B_summary.csv`. |
| `fix1.py`, `fix2.py`, `fix3.py` | The filter and variant sweeps. Writes `fix1.csv`, `fix2.csv` and `fix3.csv`. |
| `chk.py` | Spread sensitivity, by-year results and the final trade lists. |
| `hero2.py` | Failed CRT with and without the EMA trend filters. |

**Trade lists** (gzipped; the scripts write them as plain `.csv`)

| File | Contents |
|---|---|
| `ORIG_classic_NY8.csv.gz` | Classic CRT, NY 08:00 |
| `FIX_H4break.csv.gz` | Failed CRT, 4H (the hero) |
| `FIX_H4break_ema200.csv.gz` | Failed CRT, 4H, with the 200 EMA filter |
| `FIX_H1NYbreak.csv.gz` | Failed CRT, 1H, NY 08:00–09:00, 1:2, with EMA |
| `A08.csv.gz` | Classic CRT at 08:00 (from `run1.py`) |
| `B_fvg_all.csv.gz`, `B_sweep_all.csv.gz` | Trend CRT, all hours |
| `A_allhours.csv.gz` | Classic CRT, every hour |

**TradingView**

- `CRT_Gold_EdgeOrMyth.pine` is the free TradingView strategy (Pine v5). It switches between Original and Failed CRT, and has an RR input and EMA and hour filters.

Not financial advice. Past results do not guarantee future results.
