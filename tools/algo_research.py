#!/usr/bin/env python
"""
Algorithm Research: Price-Based Import Expansion Model
======================================================
Uses real Rhone data (France, grain) to evaluate several approaches
for deciding how much to import, staying profitable with local vs market price.

Current algorithm:
  Phase A: surplus/deficit from ratio-equalization (R = total_prod/total_cons)
  Phase B: Bellman-Ford precomputation → WAS/WAD
  Phase C: trade_amount = min(deficit, reachable_supply), conservation normalize

Problem: All revenue is negative because deficit-based volume is too large.
The system imports everything it can, regardless of whether it's profitable.

Goal: Move to a "pull-based" model where each depot decides how much to import
based on price profitability, then that demand is allocated across partners
weighted by proximity, share, and price.
"""

import json
from dataclasses import dataclass
from typing import List

# =============================================================
# REAL DATA FROM RHONE (FRANCE) SCREENSHOTS
# =============================================================

# Grain details from Supply Access tooltip
GRAIN_PARTNERS = [
    {"state": "Provence",         "qty": 4.8,  "share": 6.4,  "price": 19.8, "transport": 1,  "proximity": 2.7},
    {"state": "Normandy",         "qty": 7.2,  "share": 9.7,  "price": 19.7, "transport": 3,  "proximity": 5.5},
    {"state": "Orléanais-Berry",  "qty": 4.9,  "share": 6.6,  "price": 19.8, "transport": 1,  "proximity": 3.4},
    {"state": "Maine-Anjou",      "qty": 7.9,  "share": 10.5, "price": 19.6, "transport": 2,  "proximity": 4.4},
    {"state": "Aquitaine",        "qty": 7.5,  "share": 10.0, "price": 20.2, "transport": 3,  "proximity": 5.9},
    {"state": "Burgundy",         "qty": 3.7,  "share": 4.9,  "price": 19.6, "transport": 0,  "proximity": 2.1},
    {"state": "Brittany",         "qty": 0.9,  "share": 1.2,  "price": 19.6, "transport": 0,  "proximity": 5.8},
    {"state": "Languedoc",        "qty": 1.4,  "share": 1.9,  "price": 19.7, "transport": 0,  "proximity": 3.1},
    {"state": "Auvergne-Limousin","qty": 5.6,  "share": 7.5,  "price": 19.6, "transport": 1,  "proximity": 2.9},
    {"state": "Guyenne",          "qty": 2.1,  "share": 2.8,  "price": 19.7, "transport": 0,  "proximity": 4.3},
    {"state": "Picardy",          "qty": 15.5, "share": 20.7, "price": 19.8, "transport": 8,  "proximity": 6.3},
    {"state": "Alsace-Lorraine",  "qty": 5.9,  "share": 8.0,  "price": 19.7, "transport": 2,  "proximity": 5.7},
    {"state": "Poitou-Saintonge", "qty": 6.9,  "share": 9.2,  "price": 19.7, "transport": 2,  "proximity": 4.0},
]

# All Rhone imports from main panel
RHONE_IMPORTS = [
    {"good": "grain",      "import": 74.7,  "local": 19.9, "mkt": 19.8, "transport": 29.7, "revenue": -1118.4},
    {"good": "fabric",     "import": 75.4,  "local": 26.1, "mkt": 22.2, "transport": 79.4, "revenue": -2708.3},
    {"good": "furniture",  "import": 72.5,  "local": 26.3, "mkt": 27.0, "transport": 75.6, "revenue": -2908.2},
    {"good": "merch_mar",  "import": 4.3,   "local": 72.0, "mkt": 45.2, "transport": 4.6,  "revenue": -58.8},
    {"good": "iron",       "import": 50.6,  "local": 69.2, "mkt": 52.0, "transport": 53.2, "revenue": -1144.5},
    {"good": "sulfur",     "import": 37.4,  "local": 54.1, "mkt": 52.1, "transport": 40.0, "revenue": -1440.9},
    {"good": "dye",        "import": 0.5,   "local": 55.4, "mkt": 46.1, "transport": 0.5,  "revenue": -15.3},
    {"good": "glass",      "import": 9.4,   "local": 35.0, "mkt": 37.5, "transport": 9.7,  "revenue": -392.2},
    {"good": "fertilizer", "import": 14.2,  "local": 52.5, "mkt": 39.8, "transport": 14.9, "revenue": -385.3},
    {"good": "tools",      "import": 69.1,  "local": 46.6, "mkt": 43.2, "transport": 72.0, "revenue": -2485.1},
    {"good": "engines",    "import": 1.8,   "local": 105.0,"mkt": 79.4, "transport": 1.9,  "revenue": -26.9},
    {"good": "ammunition", "import": 13.0,  "local": 55.6, "mkt": 52.6, "transport": 14.4, "revenue": -507.5},
    {"good": "small_arms", "import": 29.7,  "local": 63.2, "mkt": 62.4, "transport": 32.3, "revenue": -1200.6},
    {"good": "meat",       "import": 39.1,  "local": 43.4, "mkt": 36.4, "transport": 41.2, "revenue": -1282.7},
    {"good": "fruit",      "import": 1.2,   "local": 52.5, "mkt": 36.5, "transport": 1.2,  "revenue": -28.8},
    {"good": "sugar",      "import": 0.4,   "local": 40.2, "mkt": 38.0, "transport": 0.4,  "revenue": -15.5},
    {"good": "liquor",     "import": 84.3,  "local": 30.5, "mkt": 30.0, "transport": 88.6, "revenue": -3304.6},
    {"good": "porcelain",  "import": 3.3,   "local": 91.1, "mkt": 79.4, "transport": 3.4,  "revenue": -91.7},
    {"good": "lux_furn",   "import": 4.9,   "local": 61.7, "mkt": 60.8, "transport": 5.1,  "revenue": -189.4},
]

TRANSPORT_PRICE = 30.0  # Base transportation price (~£30 in game)


# =============================================================
# ANALYSIS: Current System vs New Revenue (no transport in rev)
# =============================================================
def analyze_current_vs_new():
    print("=" * 80)
    print("ANALYSIS: Revenue WITHOUT transport cost deduction")
    print("=" * 80)
    print(f"{'Good':<14} {'Qty':>6} {'Local':>7} {'Mkt':>7} {'OldRev':>10} {'NewRev':>10} {'TransCost':>10}")
    print("-" * 80)

    total_old = 0
    total_new = 0
    total_transport = 0

    for row in RHONE_IMPORTS:
        qty = row["import"]
        local = row["local"]
        mkt = row["mkt"]
        transport = row["transport"]

        # Old revenue: (local - mkt) × qty - transport × transport_price
        old_rev = (local - mkt) * qty - transport * TRANSPORT_PRICE
        # New revenue: (local - mkt) × qty  (transport tracked separately)
        new_rev = (local - mkt) * qty
        transport_cost = transport * TRANSPORT_PRICE

        total_old += old_rev
        total_new += new_rev
        total_transport += transport_cost

        sign_new = "+" if new_rev >= 0 else ""
        print(f"{row['good']:<14} {qty:>6.1f} {local:>7.1f} {mkt:>7.1f} "
              f"{old_rev:>10.1f} {sign_new}{new_rev:>9.1f} {transport_cost:>10.1f}")

    print("-" * 80)
    print(f"{'TOTALS':<14} {'':>6} {'':>7} {'':>7} "
          f"{total_old:>10.1f} {total_new:>10.1f} {total_transport:>10.1f}")
    print()
    print(f"  Goods with POSITIVE new revenue: "
          f"{sum(1 for r in RHONE_IMPORTS if (r['local']-r['mkt'])*r['import'] > 0)}/{len(RHONE_IMPORTS)}")
    print(f"  Goods with NEGATIVE new revenue: "
          f"{sum(1 for r in RHONE_IMPORTS if (r['local']-r['mkt'])*r['import'] <= 0)}/{len(RHONE_IMPORTS)}")
    print()


# =============================================================
# MODEL A: "Marginal Profitability Cap"
#
# For each good, compute the maximum import qty that stays
# profitable: import until local_price drops to source_price.
# This is purely price-driven — ignore deficit/surplus entirely.
# =============================================================
def model_a_marginal_cap():
    print("=" * 80)
    print("MODEL A: Marginal Profitability Cap")
    print("  Import only if local > avg_source, cap at break-even point")
    print("  Max profitable import ~ margin_ratio x current_import")
    print("=" * 80)

    # For grain, use partner-level data
    print("\n--- Grain Detail (per-partner) ---")
    local_price = 19.9
    print(f"Rhone local price: £{local_price}")
    print(f"{'Partner':<20} {'Price':>7} {'Margin':>8} {'Profitable?':>12}")
    print("-" * 50)
    for p in GRAIN_PARTNERS:
        margin = local_price - p["price"]
        profitable = "YES" if margin > 0 else "NO"
        print(f"{p['state']:<20} {p['price']:>7.1f} {margin:>8.1f} {profitable:>12}")

    print(f"\n--- All Goods (aggregated) ---")
    print(f"{'Good':<14} {'CurQty':>8} {'Margin':>8} {'MarginRatio':>12} {'Decision':>12}")
    print("-" * 60)
    for row in RHONE_IMPORTS:
        margin = row["local"] - row["mkt"]
        margin_ratio = margin / row["mkt"] if row["mkt"] > 0 else 0
        decision = "IMPORT" if margin > 0 else "SKIP"
        print(f"{row['good']:<14} {row['import']:>8.1f} {margin:>8.1f} "
              f"{margin_ratio:>11.1%} {decision:>12}")
    print()


# =============================================================
# MODEL B: "Revenue-Target Pull"
#
# Each depot decides import volume to achieve target revenue.
# target_import = max(0, (local_price - source_price) / local_price × deficit)
# Positive margin → import up to full deficit
# Zero/negative margin → don't import
# =============================================================
def model_b_revenue_target():
    print("=" * 80)
    print("MODEL B: Revenue-Target Pull (deficit-scaled by margin)")
    print("  import = deficit × clamp(margin_ratio, 0, 1)")
    print("  margin_ratio = (local - source) / local")
    print("=" * 80)
    print(f"{'Good':<14} {'CurQty':>8} {'Margin%':>9} {'NewQty':>8} {'Reduction':>10}")
    print("-" * 60)
    for row in RHONE_IMPORTS:
        margin = row["local"] - row["mkt"]
        margin_ratio = max(0, min(1, margin / row["local"])) if row["local"] > 0 else 0
        new_qty = row["import"] * margin_ratio
        reduction = row["import"] - new_qty
        print(f"{row['good']:<14} {row['import']:>8.1f} {margin_ratio:>8.1%} "
              f"{new_qty:>8.1f} {reduction:>10.1f}")
    print()


# =============================================================
# MODEL C: "Step-Expansion with Profitability Gate"
#
# Closest to the plan's description. Each month:
#   - If revenue > 0: increase import by step_size (expand)
#   - If revenue ≈ 0: hold steady
#   - If revenue < 0: decrease import by step_size (contract)
# Step_size = fraction of deficit (e.g., 10%)
#
# Simulates convergence over multiple months.
# =============================================================
def model_c_step_expansion():
    print("=" * 80)
    print("MODEL C: Step-Expansion with Profitability Gate")
    print("  Monthly: if profitable → expand 10%, if unprofitable → contract 10%")
    print("  Simulates 12 months of convergence")
    print("=" * 80)

    STEP = 0.10  # 10% step per month
    MONTHS = 12

    # Simulate grain
    local = 19.9
    avg_source = 19.75  # proximity-weighted avg of partner prices
    deficit = 74.7  # current full deficit-based import

    print(f"\n--- Grain Simulation ---")
    print(f"Local: £{local}, Avg Source: £{avg_source}, Deficit: {deficit}")
    print(f"{'Month':>5} {'Import':>8} {'Revenue':>10} {'Action':>10}")
    print("-" * 40)

    current_import = deficit
    for month in range(1, MONTHS + 1):
        revenue = (local - avg_source) * current_import
        if revenue > 0:
            action = "EXPAND"
            current_import = min(deficit, current_import * (1 + STEP))
        elif revenue < -1:  # small tolerance
            action = "CONTRACT"
            current_import = max(0, current_import * (1 - STEP))
        else:
            action = "HOLD"
        print(f"{month:>5} {current_import:>8.1f} {revenue:>10.1f} {action:>10}")

    # Simulate fabric (large margin: local 26.1 vs mkt 22.2)
    print(f"\n--- Fabric Simulation ---")
    local_f = 26.1
    avg_f = 22.2
    deficit_f = 75.4
    current_f = deficit_f
    print(f"Local: £{local_f}, Avg Source: £{avg_f}, Deficit: {deficit_f}")
    print(f"{'Month':>5} {'Import':>8} {'Revenue':>10} {'Action':>10}")
    print("-" * 40)
    for month in range(1, MONTHS + 1):
        revenue = (local_f - avg_f) * current_f
        if revenue > 0:
            action = "EXPAND"
            current_f = min(deficit_f, current_f * (1 + STEP))
        elif revenue < -1:
            action = "CONTRACT"
            current_f = max(0, current_f * (1 - STEP))
        else:
            action = "HOLD"
        print(f"{month:>5} {current_f:>8.1f} {revenue:>10.1f} {action:>10}")

    # Simulate glass (negative margin: local 35.0 vs mkt 37.5)
    print(f"\n--- Glass Simulation (negative margin) ---")
    local_g = 35.0
    avg_g = 37.5
    deficit_g = 9.4
    current_g = deficit_g
    print(f"Local: £{local_g}, Avg Source: £{avg_g}, Deficit: {deficit_g}")
    print(f"{'Month':>5} {'Import':>8} {'Revenue':>10} {'Action':>10}")
    print("-" * 40)
    for month in range(1, MONTHS + 1):
        revenue = (local_g - avg_g) * current_g
        if revenue > 0:
            action = "EXPAND"
            current_g = min(deficit_g, current_g * (1 + STEP))
        elif revenue < -1:
            action = "CONTRACT"
            current_g = max(0, current_g * (1 - STEP))
        else:
            action = "HOLD"
        print(f"{month:>5} {current_g:>8.1f} {revenue:>10.1f} {action:>10}")
    print()


# =============================================================
# MODEL D: "Instant Profitability Cap" (Recommended)
#
# Simplest and most robust for Clausewitz.
# For each good, in Phase C:
#   1. Compute local_price (already have market_price as proxy)
#   2. Compute avg_source_price (weighted avg from tooltip or fallback)
#   3. margin = local - avg_source
#   4. If margin <= 0: import = 0 (skip this good)
#   5. If margin > 0: import = min(deficit, margin_cap)
#      where margin_cap is limited by how much we can import
#      before local_price drops to avg_source_price
#
# The import volume is then allocated across partners proportionally
# to their (proximity × surplus) contribution (same as current WV weighting).
#
# Advantages:
#   - Single pass, no convergence needed
#   - Uses real prices (when available from tooltip hover)
#   - Falls back to market equilibrium price (always available)
#   - Conservation normalization still applies
#   - Transport tracked separately as cost, not penalty
#
# Key change vs current:
#   - CURRENT: import = min(deficit, reachable_supply) → always imports full amount
#   - NEW: import = min(deficit, reachable_supply) × profit_factor
#     where profit_factor = clamp((local - avg_source) / local, 0, 1)
# =============================================================
def model_d_instant_cap():
    print("=" * 80)
    print("MODEL D: Instant Profitability Cap (RECOMMENDED)")
    print("  profit_factor = clamp((local - avg_source) / local, 0, 1)")
    print("  new_import = old_import × profit_factor")
    print("  Transport tracked separately, not deducted from trade volume")
    print("=" * 80)
    print(f"{'Good':<14} {'CurQty':>8} {'Local':>7} {'AvgSrc':>7} {'Factor':>8} {'NewQty':>8} {'NewRev':>10}")
    print("-" * 78)

    total_new_rev = 0
    total_transport_cost = 0
    for row in RHONE_IMPORTS:
        local = row["local"]
        avg_src = row["mkt"]  # using mkt as proxy for avg_source
        margin = local - avg_src
        factor = max(0, min(1, margin / local)) if local > 0 else 0
        new_qty = row["import"] * factor
        new_rev = margin * new_qty
        # Transport scales proportionally
        new_transport = row["transport"] * factor
        transport_cost = new_transport * TRANSPORT_PRICE

        total_new_rev += new_rev
        total_transport_cost += transport_cost

        print(f"{row['good']:<14} {row['import']:>8.1f} {local:>7.1f} {avg_src:>7.1f} "
              f"{factor:>7.1%} {new_qty:>8.1f} {new_rev:>10.1f}")

    print("-" * 78)
    print(f"Total new revenue: £{total_new_rev:,.1f}")
    print(f"Total transport cost: £{total_transport_cost:,.1f}")
    print(f"Net (revenue - transport): £{total_new_rev - total_transport_cost:,.1f}")
    print()

    # Clausewitz implementation sketch
    print("--- Clausewitz Implementation (Phase C change) ---")
    print("""
CURRENT Phase C sub-pass 3d (importers):
  trade_amount = min(deficit, reachable_supply)

NEW Phase C sub-pass 3d (importers):
  trade_amount = min(deficit, reachable_supply)
  # Price-gate: scale by profit margin
  profit_factor = clamp((market_price - weighted_avg_source) / market_price, 0, 1)
  trade_amount = trade_amount × profit_factor

NOTE: In effect context, we only have market_price (not local_price).
  market_price ≈ local_price within a state (same market equilibrium).
  weighted_avg_source comes from tooltip (stl_weighted_avg_price_$GOODS$),
  or falls back to market_price (which gives factor ≈ 0 → no trade).

  This means: first hover triggers tooltip → stores weighted_avg →
  next Phase C uses it for the profit gate. Before first hover,
  market_price is used for both → factor = 0 → conservative default.

  ALTERNATIVE: Precompute weighted_avg_source in Phase C itself
  by iterating partners with surplus and accumulating
  sum(surplus × weight × source_price) / sum(surplus × weight).
  This would work without tooltip dependency.
""")


# =============================================================
# MODEL E: "Precomputed Source Price in Phase C"
#
# Enhancement to Model D that eliminates tooltip dependency.
# In Phase C, before setting trade amounts, iterate all partners
# to compute weighted average source price directly.
# =============================================================
def model_e_precomputed():
    print("=" * 80)
    print("MODEL E: Phase C Precomputed Source Price (Model D without tooltip dependency)")
    print("=" * 80)
    print("""
Phase C would need an ADDITIONAL pass before sub-pass 3d:

  Sub-pass 3c (NEW): Compute weighted avg source price per importer

  For each state with deficit > 0:
    weighted_sum = 0
    weight_sum = 0
    For each reachable state with surplus > 0:
      # Weight = surplus × proximity (same as WV in tooltip)
      w = surplus × (max_WAS or equivalent proximity metric)
      weighted_sum += w × source_market_price
      weight_sum += w
    weighted_avg_source = weighted_sum / weight_sum
    Store as stl_avg_source_price_$GOODS$ on state

COST: O(states²) per good — expensive but runs once/month.
  With 49 goods and ~50 states per market: 49 × 50 × 50 = 122,500 iterations
  In Clausewitz: nested every_scope_state — could be VERY slow.

VERDICT: Too expensive for Clausewitz. Model D's tooltip-dependent approach
  is better — weighted_avg_source is computed once on hover (cheap),
  persists for the month, and Phase C reads it.

  For the FIRST month (before any hover), use market_price as fallback.
  Since local ≈ market for most goods, factor ≈ 0, which is correct
  (don't trade until you have price data).
""")


# =============================================================
# PARTNER ALLOCATION
# =============================================================
def analyze_partner_allocation():
    print("=" * 80)
    print("PARTNER ALLOCATION: How import volume distributes across partners")
    print("=" * 80)

    # Current allocation (WV-based: surplus × proximity_weight)
    # Show how grain's 74.7 total import distributes vs a reduced 30.0
    total_wv = sum(
        p["qty"] * (100 - p["proximity"])  # WV ≈ surplus × (100 - friction)
        for p in GRAIN_PARTNERS
    )

    print(f"\n--- Current WV Allocation (grain, total import = 74.7) ---")
    print(f"{'Partner':<20} {'WV':>8} {'Share%':>8} {'Qty':>8}")
    print("-" * 48)
    for p in GRAIN_PARTNERS:
        wv = p["qty"] * (100 - p["proximity"])
        share = wv / total_wv if total_wv > 0 else 0
        qty = share * 74.7
        print(f"{p['state']:<20} {wv:>8.1f} {share:>7.1%} {qty:>8.1f}")

    # Model D reduced allocation
    # If profit_factor = 0.5%, new total = 0.37
    local = 19.9
    avg_src = 19.75
    factor = max(0, min(1, (local - avg_src) / local))
    new_total = 74.7 * factor
    print(f"\n--- Model D Reduced Allocation (grain, factor={factor:.3f}, total={new_total:.1f}) ---")
    print(f"{'Partner':<20} {'Share%':>8} {'NewQty':>8}")
    print("-" * 40)
    for p in GRAIN_PARTNERS:
        wv = p["qty"] * (100 - p["proximity"])
        share = wv / total_wv if total_wv > 0 else 0
        qty = share * new_total
        print(f"{p['state']:<20} {share:>7.1%} {qty:>8.2f}")
    print()


# =============================================================
# SUMMARY & RECOMMENDATIONS
# =============================================================
def summary():
    print("=" * 80)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 80)
    print("""
1. REVENUE CHANGE (Implemented):
   - Transport cost REMOVED from revenue formula
   - Revenue = (local_price - avg_source_price) × qty
   - Transport tracked separately in Transport column
   - This makes revenue meaningful: positive = profitable trade route

2. PROXIMITY-WEIGHTED MARKET PRICE (Implemented):
   - Mkt £ now uses sum(qty × proximity × price) / sum(qty × proximity)
   - Closer partners influence the average more
   - More accurate reflection of effective purchase price

3. RECOMMENDED ALGORITHM: Model D - "Instant Profitability Cap"

   Phase C change (importers only):
   BEFORE: trade_amount = min(deficit, reachable_supply)
   AFTER:  trade_amount = min(deficit, reachable_supply) × profit_factor
           profit_factor = clamp((market_price - avg_source) / market_price, 0, 1)

   - Uses stl_weighted_avg_price_$GOODS$ from tooltip (hover-triggered)
   - Falls back to market_price (gives factor ≈ 0 → conservative)
   - Profitable routes (local > source): factor > 0 → trade flows
   - Unprofitable routes (local ≤ source): factor = 0 → no trade
   - Big margin → more trade; small margin → less trade

   PULL-ONLY: The importer decides volume. Export side picks up
   whatever the importers want (conservation normalization
   already handles this).

   NO convergence needed. NO step-expansion. Single-pass.

4. IMPLEMENTATION PLAN:
   a. In Phase C sub-pass 3d (importers section):
      - After computing stl_trade_amount = min(deficit, reachable)
      - Read stl_weighted_avg_price_$GOODS$ (if exists, else market_price)
      - Compute profit_factor = clamp((market_price - avg_source) / market_price, 0, 1)
      - Multiply: stl_trade_amount *= profit_factor

   b. Export side: REMOVE the independent export calculation
      - Exports should ONLY respond to import demand
      - Conservation normalization already scales exports = imports
      - The exporter's role is passive: "I have surplus, take what you need"

   c. Transport stays as-is: distance_factor × import_qty
      - Transport is a cost, not a trade limiter
      - The profit_factor already limits unprofitable routes
""")


# =============================================================
# MAIN
# =============================================================
if __name__ == "__main__":
    analyze_current_vs_new()
    model_a_marginal_cap()
    model_b_revenue_target()
    model_c_step_expansion()
    model_d_instant_cap()
    model_e_precomputed()
    analyze_partner_allocation()
    summary()
