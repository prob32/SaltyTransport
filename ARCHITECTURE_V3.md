# Salty Transport v0.3 — Price Shaping Architecture

Supersedes the v0.2 "full replacement" model (ARCHITECTURE_V2.md, kept as
history). Decisions: Trade Depot stays a visible building; all 47 goods
covered; the full-replacement model is removed, not optioned.

## The pivot in one paragraph

v0.2 zeroed MAPI and made depots the sole carrier of inter-state goods —
load-bearing script, AI confusion, and structurally unprofitable depots.
v0.3 keeps vanilla MAPI at reduced strength and uses small, capped,
zero-sum goods injections to create **distance-based local price deltas**:
goods are cheaper near accessible producers, pricier where regional demand
outweighs nearby supply. Vanilla still arbitrates the economy; the mod
shapes geography. Script failure now degrades to vanilla, not starvation.

## Engine constraints (verified against 1.13.8)

- The only price modifier type in the game is the all-goods
  `state_market_access_price_impact` (MAPI). **No per-good price modifier
  exists** — per-good shaping must be done by injecting/deleting buy/sell
  orders, i.e. the existing depot + kill-all/enable modifier machinery.
- Local pre-MAPI price = `base x (1 + 0.75 x (buy-sell)/min(buy,sell))`,
  so a target price delta maps to an order injection of
  `x = (delta / 0.75) x min(buy, sell)` (first-order; EMA absorbs error).

## Control law

Per state `s`, good `g`, each monthly cycle (machinery unchanged from v0.2:
price-cache pre-pass, queue-batched BF, gravity accumulation):

1. **Signal**: `sig = (WAD - WAS) / (WAD + WAS)` in [-1, +1].
   WAS/WAD are the existing gravity-weighted accessible supply/demand
   (partners' economy-scaled price gaps x proximity weight). WAD-dominant
   (regional scarcity) -> price up; WAS-dominant (cheap supply nearby) ->
   price down. The state's own orders are excluded — vanilla already
   prices local conditions.
2. **Target delta**: `delta = CAP_DELTA x sig`, CAP_DELTA = 0.10 (±10%).
3. **Injection target**: `x = (delta / 0.75) x min(buy, sell)` — signed.
   `x > 0`: depot buys (raises price; the v0.2 "export" side).
   `x < 0`: depot sells (lowers price; the "import" side).
   Since CAP_DELTA/0.75 ≈ 0.133 < 0.20, the volume cap (never move more
   than 20% of a state's `min(buy, sell)`) is satisfied by construction.
4. **Smoothing**: EMA toward target (50/50 — gentler than v0.2's 80/20;
   the system no longer fights its own price impact at full volume),
   growth rate cap unchanged, growth floor reduced 40 -> 5 (magnitudes
   are an order smaller).
5. **Zero-sum**: the existing conservation pass (sum of buy-side == sum of
   sell-side per good per market, heavier side scaled down) is kept
   verbatim — market-average prices stay vanilla; the mod redistributes.
6. **Decay**: unchanged (20%/cycle wind-down when the signal disappears).
7. **Transport flavor**: unchanged mechanic (sell-side injections consume
   transportation scaled by the WAS distance factor); at v0.3 magnitudes
   this is seasoning, not a budget item.

Variable semantics (`stl_eff_export/import`, `stl_last_export/import`,
WAS/WAD, access %) carry over unchanged — Phase C, the conservation pass,
the trade window and its bindings keep working without renames. What
changes in Phase B finalize: the direction-aware overshoot/flip logic is
deleted (it existed to stabilize full-volume flows; capped injections +
EMA don't need it) and replaced by the four lines of signal math. The
pre-pass additionally caches `min(buy, sell)` per good (`stl_minbs_<g>`).

## MAPI

`REPLACE:urban_planning` now applies `state_market_access_price_impact = -2`
(vanilla +5 -> net +3, a 40% nerf) instead of -5 (full zero). This is the
second balance dial: more nerf -> bigger organic gradients -> less work
for the injections. The Port Hub building (whose only job was restoring
MAPI at the world-market hub under the zeroed regime) is deleted entirely.

## Balance dials (single source: tools/generate_goods.py)

| Dial | v0.3 value | Meaning |
|------|-----------|---------|
| CAP_DELTA | 0.10 | max price delta from shaping (±10%) |
| MAPI override | -2 (net +3/5) | how much vanilla blending survives |
| VOL_CAP | 0.20 (implicit) | max injection vs state's min(buy,sell) |
| EMA | 0.5 / 0.5 | target vs last-cycle blend |
| RATE_FLOOR | 5 | min growth allowance per cycle |
| MIN_TRADE | 0.5 | below this, injection rounds to zero |

## Removed by this version

- MAPI zeroing (now a nerf); Port Hub building/group/PM/loc/management.
- Phase B direction-aware target logic (overshoot reduction, flips).
- The premise that depots are profitable businesses; they are subsidized
  utilities whose cost is bounded by the volume cap.

## Expected player reading

A state bordering the Ruhr sees coal ~10-15% cheaper than the market
average (shaping + nerfed MAPI residual); an Anatolian interior state
sees it pricier. The depot's Internal Trade window shows, per good, the
net injection ("Trade"), its target, fulfillment %, local vs network
price, and the partner breakdown explaining *why*.
