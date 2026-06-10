---
name: v3-modding
description: Victoria 3 (1.13.x) modding workflow for this repo — validation harness, offline API references, Clausewitz script and Jomini GUI patterns, performance rules, and SaltyTransport conventions. Use when editing anything under common/, events/, gui/, or localization/.
---

# Victoria 3 Modding (1.13.x)

## The loop

1. Edit. Per-good/per-metric code is NEVER edited by hand — change
   `tools/generate_goods.py` and regenerate. `--check` verifies sync.
2. `python3 tools/lint_pdx.py` — BOM + brace lint, no game files needed.
   Every `.txt`/`.gui`/`.yml` must be UTF-8 **with BOM** or the engine
   silently ignores it (the #1 silent failure).
3. `tools/validate.sh --new` — vic3-tiger against vanilla (needs game files
   at `$VIC3_GAME_DIR`); shows only regressions vs the committed baseline.
4. In-game (user runs with `-debug_mode`): check `error.log`, and after any
   game patch take the decision "Salty Transport: Run Syntax Probe"
   (variable maps are invisible to tiger and to script_docs). NOTE: Vic3's
   console has NO generic `effect` command — ship hand-fired script as
   decisions, never as console instructions.

## Offline API reference (no game install needed)

- `/ref/digests/<version>/docs/` — the game's own script_docs dumps per
  patch: `effects.log`, `triggers.log`, `event_targets.log`,
  `event_scopes.log`, `modifiers.log`, `data_types_*.txt`. **Grep these
  instead of guessing API names.** (clone: Victoria-3-Modding-Co-op/Modding-Digests)
- `/ref/digests/<version>/changes_*.md` — per-patch diffs incl. breaking changes.
- `/ref/bpm`, `/ref/cmf` — Better Politics Mod + Community Mod Framework:
  proven GUI/scripted-gui patterns to copy. `/tmp/ase/ASE-main` — Anbeeld's
  Stockpile Economy (MIT): goods-flow buildings, codegen, perf patterns.
- Exception: variable maps (1.13.7) are NOT in the docs dumps; the syntax
  reference is PDX_SCRIPTING_GUIDE.md § Variable Maps + the in-game probe.

## Script essentials (details: PDX_SCRIPTING_GUIDE.md)

- Comparisons `> >= < <= = !=` all work in triggers.
- `local_var:` survives scope changes within one effect chain but can NEVER
  be scope-prefixed (`root.local_var:x` is garbage). Use locals as cheap
  accumulators inside loops; persist once at the end.
- `if` inside `value = { }` blocks is SILENTLY IGNORED — branch outside.
- Reading `sg:`/`mg:` properties needs block syntax:
  `value = { value = sg:coal.state_goods_production }`.
- `state_goods_pricier/cheaper` are garbage in effect context (GUI-thread
  only) — compute price proxies from consumption/production instead.
- Script DB definitions: last-loaded wins (`zz_` to override). GUI types:
  FIRST-loaded wins (`000_` to override). Opposite rules.
- Game-start buildings go in `common/history/buildings/` — `create_building`
  in `on_game_start` asserts.
- Moving real goods through script = hidden/utility building + kill-all
  `_mult = -1` modifier + per-good enable modifier applied with
  `multiplier = <script value reading a local_var>`; set the local_var
  immediately before EVERY `add_modifier`.

## GUI patterns (proven in BPM/CMF/ASE)

- New windows: top-level `window` in a `.gui` file registered via
  `gui/scripted_widgets/<name>.txt` (`gui/file.gui = widget_name`) — zero
  vanilla edits. `layer = windows_layer`, `using = Window_Background` /
  `Window_Decoration`, `header_pattern` + blockoverrides.
- GUI→script: `common/scripted_guis` +
  `[GetScriptedGui('x').Execute(GuiScope.SetRoot(State.MakeScope).AddScope('param', MakeScopeFlag(...)).End)]`;
  set `ai_is_valid = { always = no }` on UI-only sguis.
- Per-item dynamic binding:
  `ScriptValue(Concatenate('prefix_', Goods.GetKey))` — generate thin
  per-good script values, never per-good widgets.
- Lists: `datamodel = "[X.MakeScope.GetList('name')]"` over a variable list;
  items are scopes (`Scope.GetState`, `Scope.GetFlagName`); guard sections
  with `DataModelHasItems(...)`.
- Scope-holding variables in GUI: `.Var('name').GetState/GetCountry/
  GetCharacter/GetValue/GetFlagName/IsSet`.
- Client-only UI state: `GetVariableSystem.Toggle/Exists/Set/Clear` — never
  gate game logic on it (not saved, not MP-synced).
- Never run heavy script from tooltip `_show` states (hover) — bind clicks.

## Performance rules

- Cache once, read many: per-cycle pre-pass into maps/vars beats recomputing
  in O(N²) pair loops (Phase B does exactly this).
- Cheap guards before iterators; skip-flags to avoid scanning inactive data.
- Batch heavy monthly work across days (frozen queue on the market owner,
  windowed by a counter — iteration order is NOT stable across days).
- Store building references in variables; never rescan `every_scope_building`.
- Clear temporaries (`remove_variable`, list clears) — saves bloat and
  lookups; absent == zero is the convention.
- error.log spam is itself a perf cost; fix every line.

## SaltyTransport specifics

- Architecture: ARCHITECTURE_V2.md (storage maps, two-phase cycle, GUI).
  Economic model: TRADE_DISTRIBUTION.md.
- Per-good state data: name-mangled VARIABLES (`stl_price_<good>`, ...) —
  the `vars` generator backend. Variable maps store values by REFERENCE
  (live-confirmed twice: local_var-sourced values die across chains, and a
  REUSED source local aliases every entry to one cell even same-chain), so
  the runtime logic uses NO maps at all; BF distances are plain variables
  on partner states. Variable LISTS of immortal targets (flags, states)
  are safe. GUI iterates the `stl_active_goods` flag list.
- Generator backend switch: `--storage=maps` exists for a future re-enable
  if probe step 9 ever reports PASS (cross-chain value persistence).
- 1.13 migration table: PDX_SCRIPTING_GUIDE.md § 1.13 Migration Notes
  (`has_port_state`, removed convoys/naval goods, straits, role triggers).
