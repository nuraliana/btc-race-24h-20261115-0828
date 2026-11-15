"""Dip-sniper v2: a long-only mean-reversion bot for the make.fun BTC race
btc-race-24h-20261115-0828.

What the new dev window taught us
---------------------------------
This race's dev window (24 h, 1,440 one-minute bars of CBBTC/USDC) is a
different regime from the previous race's: it falls 400 bps peak to trough,
its 1-minute returns are wider (sd ~12 bps, extremes +72/-79 bps), and its
sharp drops do NOT bounce within the hour -- a 15-bar drop of 100 bps is
flat-to-down over the next 15-60 bars (median -1 to -72 bps) and only
recovers over 120-240 bars (median +146/+175 bps). The previous race's
bot (15-bar drop, 60-bar hold) loses 26.44 USDC here: it buys the dip,
waits one hour, and sells before the recovery arrives.

So this version fades a LONGER, DEEPER drop and waits LONGER for the
bounce:

  * Enter flat when the close fell >= 120 bps over the last 20 closes.
    A 20-bar window (not 15) needs a sustained slide, not one bad minute,
    and 120 bps (not 100) keeps the bot out of the small dips that just
    grind lower: at 80 bps the same bot loses 69.60 USDC on this window.
  * Hold up to 180 bars (3 hours) for the recovery instead of 60.
    120 bars is too short (-14.88 USDC), 240 gives the gains back
    (-5.37 USDC); 180 is the sweet spot (+10.05 USDC).
  * Take profit at +200 bps over cost, stop loss at -300 bps.
    200 bps beats 150 (-3.40 USDC) and 250 (-3.69 USDC) at the same hold.
  * Never enter after scored bar 1,380: a fresh position there would pay
    a round trip for no time to earn it back.

Robustness (grade-local on the new dev window, full harness engine):
the winning point is a plateau, not a spike -- every neighbour is also
positive: drop 110/115/120/125/130 bps gives +6.84/+7.75/+10.05/+10.05/
+7.36 USDC; take-profit 175/200/225 bps gives +4.43/+10.05/+10.05;
hold 150/180/210 bars gives +2.06/+10.05/+4.16. The stop loss never
fires on this window (300 vs 500 bps give identical results); it is
kept as a guardrail for the live race, not as a tuned parameter.

Verified grade of THIS file (grade-local, new kit, process driver):
net PnL +10.054447 USDC, 4 trades (2 round trips, win rate 50%), max
drawdown 4.18%, fees 1.594224 USDC, net PnL at 2x fees +8.443761 USDC,
0 rejected orders, action_log_sha256
0e4b1516980cce109ef3d356c1a852822d3e5630d9a9f47e904a8a9694cba513,
and two executions reproduce byte for byte, so the bot is
deterministic. Dev gate (net PnL > 0) passes.

Costs: a full-size round trip costs ~26 bps (4 bps fee + 2 bps
slippage + ~7 bps impact per side), so the bot only trades when the
move it fades is several times that cost. All decisions use exact
integer cross-multiplication on integer closes: no floats, no clock,
no environment, no randomness -- two runs give byte-identical orders.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"
DROP_LOOKBACK_BARS = 20      # bars over which the entry drop is measured
DROP_TRIGGER_BPS = 120       # enter when the close fell >= 120 bps
TAKE_PROFIT_BPS = 200        # exit: position value >= cost + 200 bps
STOP_LOSS_BPS = 300          # exit: position value <= cost - 300 bps
MAX_HOLD_BARS = 180          # exit: sell after 180 bars held (3 hours)
ENTRY_CUTOFF_BAR = 1380      # scored-window bars after which no new entry
MAX_SLIPPAGE_BPS = 100       # bound on the move from the latest close
MIN_CASH_QUOTE_UNITS = 1_000_000  # 1 USDC, in quote units


def _sell_all(held_qty):
    """One order: sell the whole position, slippage-bounded."""
    return [{"side": "sell", "symbol": SYMBOL, "qty": held_qty,
             "max_slippage_bps": MAX_SLIPPAGE_BPS}]


def _buy_all(cash):
    """One order: buy with all cash, slippage-bounded."""
    return [{"side": "buy", "symbol": SYMBOL,
             "notional_quote_units": cash,
             "max_slippage_bps": MAX_SLIPPAGE_BPS}]


class DipSniper:
    """Keeps the close history and the entry bar of the live position.

    The SDK state only remembers the latest bar, so the bot tracks its
    own closes (oldest first) and the batch sequence where the position
    first appeared, which is what the hold limit counts from.
    """

    def __init__(self):
        self.closes = []
        self.entry_seq = None

    def note_bar(self, state):
        bar = state.latest.get(SYMBOL)
        if bar is not None:
            self.closes.append(int(bar["c"]))

    def dropped_enough(self):
        """True when the close fell >= DROP_TRIGGER_BPS over the lookback."""
        if len(self.closes) < DROP_LOOKBACK_BARS + 1:
            return False
        now = self.closes[-1]
        then = self.closes[-1 - DROP_LOOKBACK_BARS]
        return now * 10_000 <= then * (10_000 - DROP_TRIGGER_BPS)

    def exit_order(self, state, held):
        """Sell order if any exit fires, else None.

        Take-profit and stop-loss compare the marked value against the
        position cost with exact integer arithmetic; the time exit counts
        bars held since the fill, not since the decision.
        """
        if self.entry_seq is None:
            self.entry_seq = state.seq
        value = state.value(SYMBOL, held.qty)
        cost = held.cost
        if value * 10_000 >= cost * (10_000 + TAKE_PROFIT_BPS):
            return _sell_all(held.qty)
        if value * 10_000 <= cost * (10_000 - STOP_LOSS_BPS):
            return _sell_all(held.qty)
        if state.seq - self.entry_seq >= MAX_HOLD_BARS:
            return _sell_all(held.qty)
        return None

    def on_batch(self, state, batch):
        self.note_bar(state)
        if state.warming_up:
            return []

        held = state.positions.get(SYMBOL)
        if held is not None:
            order = self.exit_order(state, held)
            if order is not None:
                self.entry_seq = None
                return order
            return []

        self.entry_seq = None
        if state.seq - state.warmup_bars > ENTRY_CUTOFF_BAR:
            return []
        if self.dropped_enough() and state.cash >= MIN_CASH_QUOTE_UNITS:
            return _buy_all(state.cash)
        return []


makefun_bars.run(DipSniper().on_batch)
