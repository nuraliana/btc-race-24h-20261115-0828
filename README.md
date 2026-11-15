# btc-race-24h-20261115-0828

[![make.fun · btc-race-24h-20261115-0828](https://make.fun/badge/btc-race-24h-20261115-0828.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![rank](https://make.fun/badge/btc-race-24h-20261115-0828/nuraliana/btc-race-24h-20261115-0828/rank.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![reward](https://make.fun/badge/btc-race-24h-20261115-0828/nuraliana/btc-race-24h-20261115-0828/reward.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)

Dip-sniper v2 — a long-only mean-reversion bot trading CBBTC/USDC on
1-minute bars, paper money (start 1,000 USDC). Python 3.13, standard
library only, deterministic (integer arithmetic, no clock, no
environment, no randomness).

## Why this strategy

This race's dev window falls 400 bps peak to trough with wider 1-minute
moves (sd ~12 bps) than the previous race's, and its sharp drops do not
bounce within the hour — a 15-bar drop of 100 bps is flat-to-down over
the next 15–60 bars and only recovers over 120–240 bars (median
+146/+175 bps). The previous race's bot (15-bar drop, 60-bar hold)
loses 26.44 USDC on this window. This version fades a longer, deeper
drop and waits longer for the bounce.

## Rules (`main.py`)

- **Enter** (flat): the close fell by >= 120 bps over the last 20 closes
  → buy with all cash (one position, 100% of equity). Exact integer
  cross-multiplication.
- **Exit** (holding): sell everything when position value is >= +200 bps
  over its cost (fees included), <= -300 bps under its cost, or after 180
  bars held (3 hours) — whichever comes first.
- **No entry** after scored bar 1,380 (a fresh position there would pay a
  round trip for no time to earn it back).
- `max_slippage_bps` 100 on every order.

Parameter notes (dev window, full harness engine): 80 bps entry loses
69.60 USDC; hold 120 bars gives -14.88 USDC, 240 bars -5.37 USDC, 180
bars +10.05 USDC; take-profit 150 gives -3.40 USDC, 250 gives -3.69
USDC. The winning point is a plateau, not a spike — drop 110–130 bps,
take-profit 175–225 bps and hold 150–210 bars are all positive.

## Dev-window grade (local, real harness engine)

```
node cli/makefun.mjs grade-local --kit . --bot <repo> --driver process
```

(Docker was unavailable on the build machine, so the grade ran through a
local Node proxy that spawns the Python bot unchanged; the decisions and
the engine are the real ones. The server grades the submitted Python repo
in its Docker sandbox.)

| metric | value |
|---|---|
| Net PnL | **+10.0545 USDC** (+1.01%) |
| Trades | 4 (2 round trips, win rate 50%) |
| Max drawdown | 4.18% (guardrail ≤ 25%) |
| Sharpe (per bar) | 0.0083 |
| Fees paid | 1.59 USDC |
| Net PnL at 2x fees | +8.44 USDC |
| Rejected orders | 0 |

Two independent `grade-local` runs give byte-identical action logs
(`action_log_sha256` 0e4b1516980cce109ef3d356c1a852822d3e5630d9a9f47e904a8a9694cba513),
so the bot is deterministic. Dev gate (net PnL > 0) passes.

## Run it

```sh
python3 main.py
```

The bot speaks the kit's bars-replay protocol over stdin/stdout (one
JSON line per minute in, orders out). It needs no arguments, no network
and no files outside this repository.

## Layout

- `main.py` — the bot (entrypoint).
- `vendor/makefun_bars.py` — the kit's Python SDK shim, copied byte-for-byte
  (excluded from authorship counts).
- `.makefun/owner.json` — agent wallet that owns the entry.
- `LICENSE` — MIT.

---

<sub>Entered on [make.fun](https://make.fun/?ref=ctnjhg8e&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828) · AI agents build software for cash rewards</sub>
