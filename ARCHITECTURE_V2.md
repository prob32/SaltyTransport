# Salty Transport v0.2 — Architecture

Target: **Victoria 3 1.13.7+** (requires variable maps, added in hotfix 1.13.7).
Predecessor docs: `TRADE_DISTRIBUTION.md` describes the v0.1 (1.12) economic
model, which v0.2 keeps; this document describes what changes structurally.

## Goals

1. Port to 1.13.x (`has_port_state`, urban_planning re-sync, metadata, goods list).
2. Rearchitect per-good storage on **variable maps** keyed by goods flags.
3. Kill the O(N²) Phase B price recomputation with a per-state price cache.
4. Replace the codegen GUI with a standalone window + datamodel binding.
5. Make the cycle robust for markets of any size and survive ownership churn.

## 1. Data model: variable maps

Per-good state data moves from name-mangled variables
(`stl_eff_export_grain`, … ≈ 550 vars/state) to **maps keyed by `flag:<good>`**:

| Map (state scope)   | Value                                            | Written by |
|---------------------|--------------------------------------------------|------------|
| `stl_price`         | cached local price estimate                      | B pre-pass |
| `stl_econ`          | cached economy scale `max(buy, sell)`            | B pre-pass |
| `stl_eff_export`    | direction-aware export target                    | B finalize |
| `stl_eff_import`    | direction-aware import target                    | B finalize |
| `stl_was` / `stl_max_was` | gravity supply score / max                 | B accumulate |
| `stl_wad` / `stl_max_wad` | gravity demand score / max                 | B accumulate |
| `stl_wavg_psum` / `stl_wavg_wsum` | market-price accumulators          | B accumulate |
| `stl_market_price`  | production-weighted network price                | B finalize |
| `stl_last_export` / `stl_last_import` | applied trade (EMA input)      | C |
| `stl_transport`     | transport amount for GUI                         | C |
| `stl_access_export` / `stl_access_import` | access % for GUI           | C |

Plus one **variable list** per state, `stl_active_goods` (flag targets), holding
the goods with any nonzero trade — the GUI iterates this instead of 49 fixed rows.

Bellman-Ford distances move from a `stl_bf_dist` variable scattered across
partner states to a map **on the origin**: `stl_bf_dist` keyed by state scopes.
Cleanup becomes `clear_variable_map`, and concurrent tooltips can no longer
collide with the monthly cycle.

Access patterns (1.13.7 API):
- write: `add_to_variable_map = { name = X key = <target> value = <value> }`
- read: `variable_map(X|<key>)` (event-target link, usable like `var:`)
- iterate: `every_key_in_variable_map = { name = X ... }`
- clear: `clear_variable_map = X` / `remove_from_variable_map`

**Risk + fallback.** Variable maps are absent from the game's own `script_docs`
dump and from vic3-tiger v1.19.0, so they cannot be machine-validated yet.
Mitigations: (a) `common/scripted_effects/stl_probe.txt` ships a syntax probe
that exercises every map operation and logs results — fire it via the
decision "Salty Transport: Run Syntax Probe" before trusting a build;
(b) `tools/generate_goods.py` has a `STORAGE` switch
(`maps` | `vars`) that regenerates the entire storage layer in the legacy
name-mangled form if maps misbehave; hand-written files access storage only
through generated helper effects so the switch is total.

## 2. Monthly cycle (unchanged shape, hardened mechanics)

The two-phase cycle stays (B: days 8–20, C: days 21–28), but state batching is
**queue-based** instead of iteration-order-window based:

- Day 8: market owner builds `stl_phase_b_queue` (variable list of all depot
  states in the market) and computes `stl_batch_size = ceil(len / 13)`.
- Each Phase B day: pop up to `stl_batch_size` states from the queue, process
  each. Any market size is covered exactly once; mid-cycle conquest at worst
  delays a state to next month instead of double/never processing it.

Phase C keeps 8 goods-batches/day. Depot building refs are refreshed **once**
per cycle (day 8), not once per good per state (was 49× redundant).

## 3. Phase B v2: price cache pre-pass

v0.1 recomputed every partner's 49 prices for every origin (O(states²·goods)).
v0.2 splits Phase B per day into:

1. **Pre-pass** (first Phase B day only): every depot state computes, once per
   good: local price estimate + economy scale → `stl_price` / `stl_econ` maps.
   O(states·goods).
2. **Pair accumulate**: for each origin popped from the queue, run BF once,
   then for each reachable partner read the *cached* price/econ and do only
   the per-good surplus math (compare vs origin's last-cycle market price,
   accumulate WAS/WAD/wavg). The inner loop shrinks from ~90 generated lines
   per good to ~12.
3. **Finalize**: as v0.1 (own price into wavg, market price, direction-aware
   targets) but reading cached own-price.

Net effect: the dominant cost drops roughly an order of magnitude and the
`sg:` engine reads drop from 2·goods·states² to 2·goods·states.

## 4. Phase C v2 fixes

- **Dead code removed**: the unused `stl_price_ratio` block in the transport
  sub-pass (the modifier's cost is already paid in real transportation goods).
- **Phantom transport fix**: when conservation normalization scales an import
  below the 0.5 modifier threshold it now zeroes `stl_last_import` so the
  transport sub-pass cannot charge for goods that are not flowing.
- **Decay/flip logic**: unchanged (it lives in Phase B finalize + Phase C decay).
- **No-fallback rule documented**: states without Phase B data do not trade
  that month (the stale "uniform fallback" comments are gone along with
  `stl_uniform_fallback.txt` / `stl_trade_distribution.txt` placeholder files).

## 5. Port hub

`stl_ensure_port_hub_for_market` no longer trusts a one-shot flag. Each month
the market owner scans for an existing `building_stl_port_hub` in the market
(cached ref, re-validated); creates one in a `has_port_state = yes` state if
missing; removes duplicates if markets merged. The `stl_port_hub_placed` flag
is gone.

## 6. GUI architecture

Old: full-file override of `building_details_panel.gui` (4,352 lines) + a
5,246-line generated panel with 98 per-good tooltip types. All deleted.

New (BPM/CMF patterns):
- `gui/scripted_widgets/stl_widgets.txt` registers `gui/stl_trade_window.gui`
  as a standalone movable window (`layer = windows_layer`), toggled via
  `GetVariableSystem` (client-only UI state; game logic never depends on it).
- The window's goods table is a `datamodel` over the selected state's
  `stl_active_goods` list; each row binds values with
  `ScriptValue(Concatenate('stl_gui_<metric>_', Goods.GetKey))` — the
  generated GUI script values become one-liners that read the maps.
- Partner-breakdown tooltips read **last-cycle Phase B data** (friction map,
  contribution) instead of running Bellman-Ford on hover. A per-state
  "refresh" button runs BF once on click via a scripted_gui.
- Depot building panel integration is a minimal `000_`-prefixed **type
  override** (first-loaded-wins) that adds an "open trade window" button —
  finalized once vanilla 1.13 gui sources are available for the exact type
  names.

## 7. Validation workflow

- `tools/validate.sh` wraps vic3-tiger v1.19.0 (`--baseline` / `--new` modes,
  `vic3-tiger.conf` filters variable-map false positives).
- Requires vanilla game files at `$VIC3_GAME_DIR` (not redistributable — never
  commit them).
- `tools/generate_goods.py --check` verifies generated files are in sync with
  the generator (CI-able).
- In-game: `events/stl_probe.txt` syntax probe + `-debug_mode` `error.log`
  round-trips.

## 8. Vanilla 1.13 verification results (resolved against 1.13.8 files)

1. `REPLACE:urban_planning` — vanilla 1.13 definition is byte-identical to
   the 1.12 one our override reproduces; no change needed.
2. Goods roster — manowars/ironclads still exist in `00_goods.txt` but no
   vanilla PM produces or consumes them; they stay `enabled=False` in the
   generator (inert either way, flip the flag if a mod revives them).
3. Depot panel button — `gui/000_stl_building_panel.gui` overrides
   `building_auto_expand_toggle` (first-loaded-wins), wrapping the verbatim
   vanilla body in a flowcontainer plus a depot-only button that opens the
   trade window. Re-sync the copied body after game patches.
4. vic3-tiger v1.19.0 validates the mod with **zero findings** against the
   1.13.8 tree (empty baseline committed). Blind spot: variable-map syntax
   is unparseable to tiger; those files are covered by `tools/lint_pdx.py`
   plus the in-game probe, and the filters are documented in
   `vic3-tiger.conf` for removal once tiger gains map support.
