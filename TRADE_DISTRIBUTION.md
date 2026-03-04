# Salty Transport -- Trade Distribution Guide

## Overview

Salty Transport replaces Victoria 3's vanilla MAPI (Market Access Price Impact) system with
directional internal trade between states within a country. Instead of MAPI abstractly
blending prices toward a market average, a **Trade Depot** building in each state physically
buys and sells goods to move them between states.

**Version**: 0.1.0 | **Target**: Vic3 1.12.* | **Goods**: all 49 tradeable goods

---

## How It Works (High Level)

1. Every non-decentralized state gets a Trade Depot building at game start
2. Vanilla MAPI is zeroed out (via urban_planning tech override) so prices reflect only local supply/demand
3. Each month, a two-phase cycle runs across days 8-28:
   - **Phase B** (days 8-20): BFS pathfinding + gravity-weighted effective surplus accumulation + production-weighted market price + direction-aware export/import targets
   - **Phase C** (days 21-28): EMA smoothing, conservation normalization, transport cost, apply modifiers to depots
4. Depots physically buy goods (creating demand = exports) or sell goods (creating supply = imports)

The net effect: goods flow from states where they're cheap (high production) to states where
they're expensive (high consumption), weighted by infrastructure connectivity. States with
poor infrastructure connections trade less, creating realistic geographic price gradients.

---

## The Effective Surplus Model

The core economic model uses **effective surplus** to determine trade direction and magnitude.

### Price Computation

For each state, the local price is estimated from the buy/sell ratio:

```
ratio = clamp((buy - sell) / min(buy, sell), -1, +1)
local_price = BASE_PRICE x (1 + 0.75 x ratio)
```

**Price range**: 0.25x to 1.75x base price.

**Pure consumer/producer edge case**: When `min(buy, sell) ~ 0` (state only buys or only sells):
- Pure consumer (buy >> sell): price = 1.75 x base (maximum, very expensive)
- Pure producer (sell >> buy): price = 0.25 x base (minimum, very cheap)

This prevents states that produce zero of a good from being classified as exporters.

### Market Price

Production-weighted average across all reachable states in the network:

```
market_price = sum(production x local_price) / sum(production)
```

Computed incrementally during Phase B as each partner state is processed.

### Effective Surplus

```
eff = max(buy, sell) x (market_price - own_price) / market_price
```

- **eff > 0**: State is cheap relative to network -> should **export** (positive effective surplus)
- **eff < 0**: State is expensive relative to network -> should **import** (negative = import signal, stored as positive `eff_import`)
- **eff ~ 0**: State at equilibrium -> minimal trade

### Direction-Aware Targets

Phase B reads the previous month's trade direction (`stl_last_import/export`) and adjusts targets to prevent oscillation:

- **Case 1: Was importing, eff > 0 (overshoot)**: Reduce imports by `eff`. If overshoots past 0, flip excess to export.
- **Case 2: Was exporting, eff < 0 (overshoot)**: Reduce exports by `|eff|`. If overshoots past 0, flip excess to import.
- **Case 3: No existing trade**: Use raw eff signal directly.

This allows states to gradually change direction rather than oscillating between import/export each month.

---

## The Trade Depot Building

**File**: `common/buildings/stl_buildings.txt`

`building_stl_trade_depot` is a non-expandable, self-owning building with:

- 3 production method groups: base, exports, imports
- **Base PM** (`pm_stl_trade_depot_base`): 10 laborers, workforce-scaled
- **Exports PM** (`pm_stl_trade_depot_exports`): `goods_input_*_add = 1` for all 49 goods (unscaled -- depot BUYS from market)
- **Imports PM** (`pm_stl_trade_depot_imports`): `goods_output_*_add = 1` for all 49 goods + `goods_input_transportation_add = 1` (unscaled -- depot SELLS to market)

Building group `bg_stl_trade_depot` (parent: `bg_private_infrastructure`): always possible,
always self-owning, no urbanization, no infrastructure usage, no auto-expansion.

### Kill-All + Enable Pattern

The depot uses the ASE (Anbeeld's Stockpile Economy) modifier pattern:

1. **Kill-all modifiers** (`stl_export_kill_all`, `stl_import_kill_all`) are applied permanently
   (`days = -1`), setting every `goods_input_*_mult = -1` and `goods_output_*_mult = -1`.
   This zeroes all base goods flow.

2. **Per-good enable modifiers** (e.g. `stl_export_coal`) set `goods_input_coal_mult = 1`.
   Applied with `multiplier = N`, the net effect is: `-1 + (1 * N) = N - 1` units of goods flow.

3. The `multiplier` is provided by the script value `stl_trade_multiplier`, which reads
   `local_var:stl_trade_amount` (set fresh each month by Phase C before applying the modifier).

### Modifier Math

**Export (goods_input via _mult):**
```
PM base = 1
Kill-all: goods_input_X_mult = -1
Per-good: goods_input_X_mult = 1, multiplier = N

Final = 1 x (1 + (-1 + 1*N)) = 1 x N = N
```

**Import (goods_output via _mult):**
Same math: `1 x (1 + (-1 + 1*N)) = N`

**Transport cost (goods_input_transportation via _add):**
```
PM base = 1 (goods_input_transportation_add = 1)
Kill-all: goods_input_transportation_mult = -1  ->  1 x (1-1) = 0
Per-good: goods_input_transportation_add = 1, multiplier = T

Final = 0 + 1*T = T
```

**Files involved**:
- `common/static_modifiers/stl_goods_modifiers.txt` -- kill-all + per-good modifiers (all 49 goods)
- `common/modifier_type_definitions/stl_modifier_types.txt` -- registers custom `_mult` and `_add` types not in vanilla
- `common/script_values/stl_script_values.txt` -- `stl_trade_multiplier`, `stl_transport_multiplier`
- `common/production_methods/stl_production_methods.txt` -- base/export/import PMs
- `common/production_method_groups/stl_pmgs.txt` -- PM groups

---

## MAPI Neutralization

**File**: `common/technology/technologies/stl_tech_overrides.txt`

Uses `REPLACE:urban_planning` to override the vanilla urban_planning technology. Adds:

```
state_market_access_price_impact = -5
```

This zeroes MAPI's price blending effect (`+5` vanilla + `-5` override = 0), ensuring
state prices reflect only local organic supply/demand plus Trade Depot activity.

---

## Initialization Flow

### Game Start
**File**: `common/history/buildings/stl_global.txt`

1. `create_building` places a level-1 Trade Depot in every non-decentralized state
2. Triggers Event 1 (initialization) immediately for every country
3. Triggers Events 3, 4 (the two-phase cycle) for market owners only, staggered by day

### Event 1: Initialization
**Files**: `events/stl_events.txt` + `common/scripted_effects/stl_building_management.txt`

`stl_initialize_all_depots` iterates every state:
- If `stl_trade_depot_ref` variable is missing, the state hasn't been initialized
- Creates the building if it doesn't exist (mid-game safety net for newly acquired states)
- Caches a reference to the building in `var:stl_trade_depot_ref` for fast access
- Applies permanent kill-all modifiers (`days = -1`)
- Idempotent: skips states that already have a cached depot reference

### Ongoing Triggers
**File**: `common/on_actions/stl_on_actions.txt`

- **Monthly pulse**: Re-runs init (idempotent) + schedules two-phase cycle (Events 3, 4)
- **Yearly pulse**: Re-runs init safety net (Event 1 only)
- Only **market owners** run the distribution events

### Events
**File**: `events/stl_events.txt`

| Event | Phase | Effect |
|-------|-------|--------|
| `stl_events.1` | Init | `stl_initialize_all_depots` |
| `stl_events.3` | Phase B | `stl_phase_b_run` |
| `stl_events.4` | Phase C | `stl_phase_c_batch` |

All events are hidden with no UI.

---

## Two-Phase Monthly Distribution Cycle

### Phase B: Bellman-Ford + Gravity + Effective Surplus (Days 8-20)

**Files**:
- `common/scripted_effects/stl_distance_cache.txt` -- Bellman-Ford pathfinding
- `common/scripted_effects/stl_gravity_calculation.txt` -- Phase B orchestration
- `common/scripted_effects/stl_phase_b_generated.txt` -- Auto-generated per-good WAS/WAD accumulation + price computation

Processes ~8 states per day across 13 days (capacity for ~104 states). Uses
`var:stl_bf_batch_counter` to track progress.

**Key optimization**: Loop inversion. Instead of running Bellman-Ford once per state per good
(49 x N states), run Bellman-Ford **once per state** and then accumulate WAS/WAD for all 49
goods in a single pass. This is a 49x reduction in pathfinding work.

For each state (the "origin"):

#### Step 1: Bellman-Ford Pathfinding (`stl_run_bellman_ford`)

Computes shortest-path infrastructure friction from the origin to every reachable state:
- 7 relaxation passes (covers paths up to 7 hops)
- Edge weight = infrastructure friction per state: `max(1, 5 x (infra_usage / infra))`
  - Spare infrastructure capacity -> friction ~ 1
  - Fully utilized -> friction = 5
  - Over-capacity -> friction > 5
  - No infrastructure at all -> friction = 10 (hard penalty)
- Stores cumulative friction in `var:stl_bf_dist` on each reachable state

#### Step 2: WAS/WAD + Price Accumulation (`stl_phase_b_process_state`)

For every reachable partner state (those with a `stl_bf_dist` value):

```
proximity_weight = max(0, 100 - cumulative_friction)
```

Then, for all 49 goods simultaneously:

1. **Compute partner's local price** from buy/sell ratio (or extreme price if pure consumer/producer)
2. **Accumulate market price sums**: `wavg_psum += partner_production x partner_price`, `wavg_wsum += partner_production`
3. **Compute effective surplus** from last month's market price:
   - `eff = econ_scale x (market_price - source_price) / market_price`
4. **If eff > 0** (cheap partner): accumulate into **WAS** (Weighted Accessible Supply):
   - `WAS += eff x proximity_weight`, `max_WAS += eff x 100`
5. **If eff < 0** (expensive partner): accumulate into **WAD** (Weighted Accessible Demand):
   - `WAD += |eff| x proximity_weight`, `max_WAD += |eff| x 100`

#### Step 3: Finalize (`stl_phase_b_finalize_prices`)

For the origin state:
1. Add origin's own production x price to wavg sums
2. Compute `market_price = wavg_psum / wavg_wsum`
3. Compute origin's effective surplus: `eff = econ x (market - own) / market`
4. **Direction-aware target** (see Effective Surplus Model above):
   - Existing trade: reduce/flip based on eff direction
   - New trade: use raw eff

#### Step 4: Cleanup (`stl_cleanup_bf_dist`)

Removes temporary `stl_bf_dist` variables from all states to prepare for the next origin.

### Phase C: EMA + Conservation + Transport + Apply (Days 21-28)

**File**: `common/scripted_effects/stl_phase_c_effects.txt`

49 goods processed in 8 batches of ~6 goods each. Entry point `stl_phase_c_batch` calls
`stl_phase_c_good = { GOODS = <name> }` for each good.

For each good, per state:

#### Sub-pass 3d: Per-State Trade Amounts

1. **Clear old modifiers** (so old values stay active until replaced)
2. **Save old trade values** as local vars (for EMA), then zero tracking vars
3. **Exporters** (has `stl_eff_export > 0` and valid WAD):
   - Base = Phase B target (`stl_eff_export`)
   - No demand cap -- exports grow freely (limited by natural equilibrium + conservation)
   - **EMA 20/80**: `trade = 0.8 x target + 0.2 x old_export`
   - **Rate cap**: Max 90% increase per cycle, floor 40 for new/small routes
   - Store in `stl_last_export` + apply modifier
4. **Importers** (has `stl_eff_import > 0` and valid WAS):
   - Same EMA + rate cap pattern
   - Store in `stl_last_import` + apply modifier
5. **Gradual decay**: When trade signal disappears but old trade exists:
   - Decay at 80%/cycle (20% reduction each month)
   - Stops when below 0.5 (rounds to zero)
   - **Direction-flip guard**: Do NOT decay if the state has flipped to the opposite direction

#### Sub-pass 3d.5: Conservation Normalization

Ensures `sum(exports) = sum(imports)` across the entire market:

1. **Accumulate** `sum_exports` and `sum_imports` using `global_var` (cross-scope access)
2. **If imbalanced**: Scale the larger side down:
   - `norm_export = min(1, sum_imports / sum_exports)`
   - `norm_import = min(1, sum_exports / sum_imports)`
3. **Edge cases**: If one side is zero, zero the other entirely
4. **Re-apply scaled modifiers**: Remove old modifier, scale `stl_last_*`, re-apply with `set_local_variable` before each `add_modifier`

This guarantees zero-sum: no goods are created or destroyed by the depot network.

#### Sub-pass 3d.75: Transport Cost

Importers pay distance-based transport cost:

```
distance_factor = max_WAS / WAS    (clamped to [1, 10])
transport_amount = import_volume x distance_factor
```

- max_WAS = sum of `eff x 100` (all partners at max proximity)
- WAS = sum of `eff x actual_proximity` (gravity-weighted)
- Ratio measures average distance: close -> ~1x, distant -> up to 10x

Transport uses local transportation market price computed from buy/sell orders.

#### Sub-pass 3e: Access % for GUI

```
access_pct = (last_trade / eff_target) x 100    (clamped 0-100)
```

Shows how much of the price-equalizing target is actually being traded.

---

## Infrastructure Friction Model

The Bellman-Ford pathfinding uses infrastructure utilization as edge weights:

```
friction = max(1, 5 x (infra_usage / infra))
```

| Scenario | Friction | Meaning |
|----------|----------|---------|
| Spare capacity | ~1 | Nearly free to traverse |
| Balanced (usage = infra) | 5 | Moderate cost |
| Over-capacity (2x usage) | 10 | Expensive |
| No infrastructure | 10 | Hard penalty |

Cumulative friction is summed along the path. The trade weight between two states is:

```
proximity_weight = max(0, 100 - cumulative_friction)
```

States with cumulative friction >= 100 are effectively unreachable. Rails, rivers, and ports
contribute infrastructure capacity, so states with better infrastructure have lower friction
and stronger trade connections.

---

## Convergence Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| EMA blend | 80% target / 20% old | Smooth convergence to Phase B target |
| Rate cap | 90% of old value per cycle | Prevents explosive growth |
| Rate floor | 40 units | Allows new/small routes to ramp up |
| Decay rate | 80% per cycle (20% reduction) | Graceful wind-down when signal disappears |
| Decay threshold | 0.5 minimum | Below this, trade stops entirely |
| Transport factor | 1-10x range | Distance penalty for importers |
| Extreme price | 0.25x-1.75x base | Proxy for pure producers/consumers |
| Price ratio | clamp to [-1, +1] | Prevents division overflow |

---

## GUI: Trade Info Panel

**Files**:
- `gui/stl_trade_info_panel.gui` -- Auto-generated panel layout
- `common/scripted_guis/stl_scripted_guis.txt` -- Per-good tooltip triggers
- `common/scripted_effects/stl_tooltip_effects.txt` -- Display list building
- `common/script_values/stl_gui_values.txt` -- Data binding values

The Trade Depot's building detail panel shows:
- **Exports section**: Lists each good being exported, showing target, access %, trade amount, revenue
- **Imports section**: Lists each good being imported, showing target, access %, trade amount, transport cost, revenue
- **Tooltips**: Clicking a good runs an on-demand Bellman-Ford to show trade partners,
  per-partner friction, weight, and contribution percentage
- **Price data**: Local price (live from sg:), market price (from Phase B), weighted avg partner price

GUI visibility is driven by `stl_gui_any_export` / `stl_gui_any_import` script values.

---

## Debug Mode

**Files**:
- `common/static_modifiers/stl_debug_modifiers.txt` -- Per-good diagnostic modifiers
- `common/scripted_triggers/stl_triggers.txt` -- `stl_is_debug_mode` trigger
- `common/script_values/stl_script_values.txt` -- debug multiplier values

Toggle via console: `effect set_global_variable = { name = stl_debug_mode value = 1 }`

When enabled, Phase C applies additional diagnostic modifiers showing:
- `stl_debug_base_*`: Phase B target (eff_export or eff_import value)
- `stl_debug_access_*`: Gravity accessibility weight (WAS/max_WAS or WAD/max_WAD ratio)

These appear as modifier tooltips on the Trade Depot building for debugging purposes.

---

## Code Generation

**File**: `tools/generate_goods.py`

A Python script that generates repetitive mod files for all 49 goods. Outputs are UTF-8
BOM encoded. Generated files are marked with `# AUTO-GENERATED` headers.

### Running the Generator

```bash
cd "C:\Users\PatPC\Documents\Paradox Interactive\Victoria 3\mod\SaltyTransport"
python tools/generate_goods.py
```

### Master Data Tables

The generator contains three master tables that must be kept in sync with vanilla:

| Table | Purpose |
|-------|---------|
| `GOODS` | List of (internal_name, display_name, icon, category) for all 49 goods |
| `BASE_PRICES` | Vanilla base price per good (from `common/goods/00_goods.txt`) |
| `TRADED_QTY` | Vanilla traded_quantity per good (unused currently but available) |
| `VANILLA_INPUT_MULT` | Goods with existing `_input_mult` types in vanilla (don't redefine) |
| `VANILLA_OUTPUT_MULT` | Goods with existing `_output_mult` types in vanilla (don't redefine) |
| `MISSING_INPUT_ADD` | Goods without `_input_add` types in vanilla (must define ourselves) |

### Generated Files

| Output | Content |
|--------|---------|
| `stl_goods_modifiers.txt` | Kill-all + per-good enable + transport modifiers |
| `stl_debug_modifiers.txt` | Debug diagnostic modifiers |
| `stl_modifier_types.txt` | Custom modifier type definitions |
| `stl_production_methods.txt` | Export/import PMs for Trade Depot + Port Hub MAPI restore |
| `stl_gui_values.txt` | Script values for GUI data binding |
| `stl_scripted_guis.txt` | Per-good tooltip triggers |
| `stl_trade_info_panel.gui` | Trade info panel layout |
| `stl_l_english.yml` | Localization strings |
| `stl_phase_b_generated.txt` | Phase B: zero/accumulate/finalize effects for all 49 goods |

### Phase B Generation Details

The generator produces the most complex output: `stl_phase_b_generated.txt` (~10,800 lines).
This contains three effects:

1. **`stl_phase_b_zero_all_goods`**: Zeros all per-state Phase B variables (WAS, WAD, max_WAS, max_WAD, wavg sums, eff_export, eff_import) for all 49 goods.

2. **`stl_phase_b_accumulate_all_goods`**: For each of the 49 goods, in a single partner-state iteration:
   - Read partner's buy/sell orders
   - Compute partner's local price (with extreme price edge case)
   - Accumulate production-weighted price sums
   - Compute effective surplus from last month's market price
   - If positive: add to WAS (gravity-weighted)
   - If negative: add to WAD (gravity-weighted)

3. **`stl_phase_b_finalize_prices`**: For the origin state:
   - Add origin's own production to wavg sums
   - Compute market_price = wavg
   - Compute origin's effective surplus
   - Direction-aware target with overshoot-to-flip

### Goods Categories (49 total)

- **Staple** (9): grain, fish, fabric, wood, groceries, clothes, furniture, paper, merchant_marine
- **Industrial** (17): coal, iron, lead, sulfur, hardwood, rubber, oil, silk, dye, clippers, steamers, glass, fertilizer, tools, steel, engines, explosives
- **Military** (7): ammunition, small_arms, artillery, tanks, aeroplanes, manowars, ironclads
- **Luxury** (16): meat, fruit, sugar, tobacco, liquor, wine, tea, coffee, opium, porcelain, luxury_clothes, luxury_furniture, automobiles, telephones, radios, fine_art

---

## File Reference

| File | Purpose |
|------|---------|
| `descriptor.mod` | Mod metadata (v0.1.0, targets 1.12.*) |
| **Buildings** | |
| `common/buildings/stl_buildings.txt` | Trade Depot building definition |
| `common/building_groups/stl_building_groups.txt` | Building group (private infrastructure) |
| `common/production_methods/stl_production_methods.txt` | Base, exports, imports PMs (49 goods) |
| `common/production_method_groups/stl_pmgs.txt` | PM groups |
| **Modifiers** | |
| `common/static_modifiers/stl_goods_modifiers.txt` | Kill-all + per-good enable + transport modifiers |
| `common/static_modifiers/stl_debug_modifiers.txt` | Debug diagnostic modifiers |
| `common/modifier_type_definitions/stl_modifier_types.txt` | Custom `_mult` and `_add` types |
| **Scripts** | |
| `common/script_values/stl_script_values.txt` | `stl_trade_multiplier`, debug values |
| `common/script_values/stl_gui_values.txt` | GUI data binding (auto-generated) |
| `common/scripted_triggers/stl_triggers.txt` | `stl_is_debug_mode`, `stl_has_river` |
| `common/scripted_guis/stl_scripted_guis.txt` | Per-good tooltip triggers (auto-generated) |
| **Scripted Effects** | |
| `common/scripted_effects/stl_building_management.txt` | Depot creation, init, kill-all application |
| `common/scripted_effects/stl_distance_cache.txt` | Bellman-Ford pathfinding |
| `common/scripted_effects/stl_gravity_calculation.txt` | Phase B: BF orchestration + WAS/WAD |
| `common/scripted_effects/stl_phase_b_generated.txt` | Phase B: per-good accumulation (auto-generated) |
| `common/scripted_effects/stl_phase_c_effects.txt` | Phase C: EMA + conservation + transport + apply |
| `common/scripted_effects/stl_tooltip_effects.txt` | Tooltip display list building |
| **Tech / History / Events** | |
| `common/technology/technologies/stl_tech_overrides.txt` | MAPI neutralization via urban_planning |
| `common/history/buildings/stl_global.txt` | Game-start depot creation + event triggers |
| `common/on_actions/stl_on_actions.txt` | Monthly/yearly triggers |
| `events/stl_events.txt` | Events 1, 3, 4 (init + two-phase cycle) |
| **GUI** | |
| `gui/stl_trade_info_panel.gui` | Trade info panel (auto-generated) |
| `gui/building_details_panel.gui` | Building details panel integration |
| **Assets** | |
| `gfx/interface/icons/building_icons/stl_trade_depot.dds` | Building icon |
| `localization/english/stl_l_english.yml` | Localization strings (auto-generated) |
| **Tools** | |
| `tools/generate_goods.py` | Code generation for all 49 goods |

---

## Variable Reference

### Country-scope variables (market owner)
| Variable | Set in | Description |
|----------|--------|-------------|
| `stl_phase_c_batch_idx` | Phase C | Batch counter (0-7) |
| `stl_bf_batch_counter` | Phase B | Bellman-Ford batch counter |

### Global variables (cross-scope, temporary)
| Variable | Set in | Description |
|----------|--------|-------------|
| `stl_sum_exports` | Phase C | Sum of export amounts (conservation normalization) |
| `stl_sum_imports` | Phase C | Sum of import amounts (conservation normalization) |
| `stl_norm_export` | Phase C | Export normalization factor (0-1) |
| `stl_norm_import` | Phase C | Import normalization factor (0-1) |
| `stl_debug_mode` | Console | Debug mode toggle (1 = on) |

### State-scope variables
| Variable | Set in | Description |
|----------|--------|-------------|
| `stl_trade_depot_ref` | Init | Cached reference to this state's Trade Depot building |
| `stl_last_export_$GOODS$` | Phase C | This month's applied export amount (next month's anti-oscillation) |
| `stl_last_import_$GOODS$` | Phase C | This month's applied import amount (next month's anti-oscillation) |
| `stl_eff_export_$GOODS$` | Phase B | Direction-aware export target for Phase C |
| `stl_eff_import_$GOODS$` | Phase B | Direction-aware import target for Phase C |
| `stl_was_$GOODS$` | Phase B | Weighted Accessible Supply (gravity score for importers) |
| `stl_max_was_$GOODS$` | Phase B | Max WAS (at full proximity weight 100) |
| `stl_wad_$GOODS$` | Phase B | Weighted Accessible Demand (gravity score for exporters) |
| `stl_max_wad_$GOODS$` | Phase B | Max WAD (at full proximity weight 100) |
| `stl_market_price_$GOODS$` | Phase B | Production-weighted average price across reachable network |
| `stl_wavg_psum_$GOODS$` | Phase B | Weighted avg numerator (sum of production x price) |
| `stl_wavg_wsum_$GOODS$` | Phase B | Weighted avg denominator (sum of production) |
| `stl_transport_$GOODS$` | Phase C | Transport amount (import_volume x distance_factor) |
| `stl_access_pct_export_$GOODS$` | Phase C | GUI: export access percentage |
| `stl_access_pct_import_$GOODS$` | Phase C | GUI: import access percentage |
| `stl_bf_dist` | Phase B | Bellman-Ford cumulative friction (temporary, cleaned up) |
| `stl_partner_count` | Phase B | Number of reachable trade partners |

### Display-scope variables (tooltip, temporary)
| Variable | Description |
|----------|-------------|
| `stl_display_partners` | List of partner states for tooltip |
| `stl_display_wv` | Partner's base value (surplus or deficit) |
| `stl_display_friction` | Cumulative BF friction to partner |
| `stl_display_weight` | Trade weight (100 - friction) |
| `stl_display_contribution_pct` | Partner's % contribution to total WAS/WAD |
| `stl_display_has_rail` | Partner has railway |
| `stl_display_has_river` | Partner has navigable river |

---

## Design Decisions & Solved Issues

### Why no export cap?
Exports grow freely (no `max_WAD/100` cap). This is because:
1. Natural equilibrium limits: as a state exports more, its local price rises, reducing eff
2. EMA + rate cap prevent explosive growth
3. Conservation normalization ensures sum(exports) = sum(imports)

An asymmetric cap on exports caused importers to be starved of supply.

### Why direction-aware targets?
Without direction awareness, states would oscillate between importing and exporting each month. The direction-aware target system:
1. Resists direction changes when price differences are small (reduces existing trade instead)
2. Allows direction flips when price differences are large (overshoot past 0 flips direction)
3. Gradual decay handles edge cases where Phase B signals disappear temporarily

### Why extreme prices for pure consumers/producers?
When a state has `min(buy, sell) = 0`, the standard price formula doesn't fire (division by zero). Defaulting to base price caused pure consumers to be classified as exporters (market > base = positive eff). The extreme price proxy ensures:
- Pure consumers always look expensive -> import signal
- Pure producers always look cheap -> export signal

### Why production-weighted market price?
Simple average would give equal weight to tiny producers and large ones. Production-weighted average means the "market price" is dominated by major production centers, which is more economically realistic.

### Why global_var for conservation?
Clausewitz `var:` is scoped to the current entity (state/country). Conservation normalization needs to accumulate across all states and then read the result back. `global_var` is accessible from any scope, solving the cross-scope communication problem.
