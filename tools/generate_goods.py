#!/usr/bin/env python3
"""Generate all per-good files for SaltyTransport v0.2 (Vic3 1.13.7+).

Usage:
    python3 tools/generate_goods.py                # regenerate (storage = maps)
    python3 tools/generate_goods.py --storage=vars # legacy name-mangled variables
    python3 tools/generate_goods.py --check        # verify working tree is in sync

Outputs (UTF-8 with BOM, marked AUTO-GENERATED):
    common/static_modifiers/stl_goods_modifiers.txt
    common/static_modifiers/stl_debug_modifiers.txt
    common/modifier_type_definitions/stl_modifier_types.txt
    common/production_methods/stl_production_methods.txt
    common/scripted_effects/stl_phase_b_generated.txt
    common/scripted_effects/stl_phase_c_generated.txt
    common/script_values/stl_gui_values.txt
    localization/english/stl_l_english.yml

Storage backends (see ARCHITECTURE_V2.md section 1):
    vars  - per-good data in name-mangled variables. DEFAULT: live testing
            proved that add_to_variable_map stores its value as an event-
            target REFERENCE, not a copied number - values written from
            local_var: die when read from a different effect chain
            ("Event target link 'local_var' returned an unset scope",
            1M+ errors). set_variable copies, so vars is the safe backend
            for anything read across chains (price caches, last_*, targets).
    maps  - variable maps keyed by flag:<good> (1.13.7+). Only safe for
            same-chain data; kept for a future re-enable if the semantics
            change (probe step 9 tracks this across patches).
All emitted script accesses per-good storage exclusively through the helper
functions below, so the backend can be swapped wholesale by regenerating.
The Bellman-Ford distance map (stl_bf_dist) is hand-written and stays a map
regardless: it is written and read within a single chain, which live logs
show working.
"""

import argparse
import difflib
import io
import os
import sys

MOD_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

# ============================================================
# MASTER GOODS TABLE
# (internal_name, display_name, base_price, traded_qty, category, enabled)
#
# enabled=False: good still exists in the game's registry but is not traded
# by depots. manowars/ironclads were removed from use in 1.13 (naval rework
# builds ships from steel/engines etc. directly); their modifier types are
# still registered in 1.13.8 but nothing produces or consumes them.
# ============================================================

GOODS = [
    # STAPLE
    ("grain",            "Grain",            20,  12,  "staple",     True),
    ("fish",             "Fish",             20,  12,  "staple",     True),
    ("fabric",           "Fabric",           20,  10,  "staple",     True),
    ("wood",             "Wood",             20,  10,  "staple",     True),
    ("groceries",        "Groceries",        30,   9,  "staple",     True),
    ("clothes",          "Clothes",          30,   8,  "staple",     True),
    ("furniture",        "Furniture",        30,   8,  "staple",     True),
    ("paper",            "Paper",            30,   7,  "staple",     True),
    ("merchant_marine",  "Merchant Marine",  50,   4,  "staple",     True),
    # INDUSTRIAL
    ("coal",             "Coal",             30,   7,  "industrial", True),
    ("iron",             "Iron",             40,   5,  "industrial", True),
    ("lead",             "Lead",             40,   5,  "industrial", True),
    ("sulfur",           "Sulfur",           50,   4,  "industrial", True),
    ("hardwood",         "Hardwood",         40,   5,  "industrial", True),
    ("rubber",           "Rubber",           40,   5,  "industrial", True),
    ("oil",              "Oil",              40,   6,  "industrial", True),
    ("silk",             "Silk",             40,   5,  "industrial", True),
    ("dye",              "Dye",              40,   5,  "industrial", True),
    ("clippers",         "Clippers",         60, 3.5,  "industrial", True),
    ("steamers",         "Steamers",         70, 3.5,  "industrial", True),
    ("glass",            "Glass",            40,   5,  "industrial", True),
    ("fertilizer",       "Fertilizer",       30,   7,  "industrial", True),
    ("tools",            "Tools",            40,   5,  "industrial", True),
    ("steel",            "Steel",            50,   4,  "industrial", True),
    ("engines",          "Engines",          60,   4,  "industrial", True),
    ("explosives",       "Explosives",       50,   4,  "industrial", True),
    # MILITARY
    ("ammunition",       "Ammunition",       50,   5,  "military",   True),
    ("small_arms",       "Small Arms",       60,   4,  "military",   True),
    ("artillery",        "Artillery",        70, 3.5,  "military",   True),
    ("tanks",            "Tanks",            80,   3,  "military",   True),
    ("aeroplanes",       "Aeroplanes",       80,   3,  "military",   True),
    ("manowars",         "Man O' Wars",      70, 3.5,  "military",   False),  # removed from use in 1.13
    ("ironclads",        "Ironclads",        80, 3.5,  "military",   False),  # removed from use in 1.13
    # LUXURY
    ("meat",             "Meat",             30,   8,  "luxury",     True),
    ("fruit",            "Fruit",            30,   8,  "luxury",     True),
    ("sugar",            "Sugar",            30,   8,  "luxury",     True),
    ("tobacco",          "Tobacco",          40,   5,  "luxury",     True),
    ("liquor",           "Liquor",           30,   8,  "luxury",     True),
    ("wine",             "Wine",             50,   5,  "luxury",     True),
    ("tea",              "Tea",              50,   5,  "luxury",     True),
    ("coffee",           "Coffee",           50,   5,  "luxury",     True),
    ("opium",            "Opium",            50,   5,  "luxury",     True),
    ("porcelain",        "Porcelain",        70, 3.5,  "luxury",     True),
    ("luxury_clothes",   "Luxury Clothes",   60,   4,  "luxury",     True),
    ("luxury_furniture", "Luxury Furniture", 60,   4,  "luxury",     True),
    ("automobiles",      "Automobiles",     100,   3,  "luxury",     True),
    ("telephones",       "Telephones",       70,   4,  "luxury",     True),
    ("radios",           "Radios",           80, 3.5,  "luxury",     True),
    ("fine_art",         "Fine Art",        200, 1.5,  "luxury",     True),
]

# Vanilla-defined modifier types we must NOT redefine (1.12 empirical lists;
# 1.13.8 docs dumps register ALL goods x {input,output} x {add,mult} (see
# tools/refs_vanilla_goods_modifiers_1.13.8.txt) but definition-file presence
# still governs display metadata. Verify against vanilla files when available.)
VANILLA_INPUT_MULT = {
    "ammunition", "artillery", "oil", "radios", "small_arms", "tanks",
}
VANILLA_OUTPUT_MULT = {
    "aeroplanes", "ammunition", "artillery", "automobiles", "clippers",
    "engines", "fabric", "fruit", "hardwood", "ironclads", "liquor",
    "manowars", "oil", "radios", "silk", "small_arms", "steamers",
    "sugar", "tanks", "tools", "wine",
}
MISSING_INPUT_ADD = {
    "furniture", "tea", "coffee", "porcelain",
    "luxury_clothes", "luxury_furniture", "fine_art",
}

ICON = "gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds"
PM_TEXTURE = '"gfx/interface/icons/production_method_icons/merchant_guilds.dds"'

# Phase C tuning (mirrors ARCHITECTURE_V2.md / TRADE_DISTRIBUTION.md)
EMA_NEW = 0.8        # weight of the fresh Phase B target
EMA_OLD = 0.2        # weight of last month's applied trade
RATE_CAP = 0.9       # max growth per cycle as fraction of old value
RATE_FLOOR = 40      # minimum allowed growth (lets new routes ramp up)
DECAY = 0.8          # retained fraction per cycle when the signal disappears
MIN_TRADE = 0.5      # below this, trade rounds to zero
GOODS_PER_BATCH = 6  # Phase C goods per day (8 batches over days 21-28)

AUTOGEN = "# AUTO-GENERATED by tools/generate_goods.py -- DO NOT EDIT\n# Regenerate: python3 tools/generate_goods.py\n"

STORAGE = "vars"  # overridden by --storage


def enabled_goods():
    return [g for g in GOODS if g[5]]


def names():
    return [g[0] for g in enabled_goods()]


# ============================================================
# STORAGE ABSTRACTION
# Per-good, state-scope storage. `key` is a literal good name.
# In maps mode, data lives in variable maps keyed by flag:<good>;
# in vars mode, in name-mangled variables. The emitted script is
# equivalent either way.
# ============================================================

def s_read(map_name, key):
    """Event-target expression that reads a per-good value (current scope)."""
    if STORAGE == "maps":
        return f"variable_map({map_name}|flag:{key})"
    return f"var:{map_name}_{key}"


def s_read_scoped(scope_prefix, map_name, key):
    """Read a per-good value on another scope (e.g. scope:stl_gravity_self)."""
    if STORAGE == "maps":
        return f"{scope_prefix}.variable_map({map_name}|flag:{key})"
    return f"{scope_prefix}.var:{map_name}_{key}"


def s_has(map_name, key):
    """Trigger line: per-good value exists on current scope."""
    if STORAGE == "maps":
        return f"is_key_in_variable_map = {{ name = {map_name} key = flag:{key} }}"
    return f"has_variable = {map_name}_{key}"


def s_write(map_name, key, value_expr, indent):
    """Effect lines: write a per-good value on current scope."""
    t = "\t" * indent
    if STORAGE == "maps":
        return [f"{t}add_to_variable_map = {{ name = {map_name} key = flag:{key} value = {value_expr} }}"]
    return [f"{t}set_variable = {{ name = {map_name}_{key} value = {value_expr} }}"]


def s_remove(map_name, key, indent):
    """Effect lines: remove a per-good value on current scope (guarded)."""
    t = "\t" * indent
    if STORAGE == "maps":
        return [
            f"{t}if = {{",
            f"{t}\tlimit = {{ {s_has(map_name, key)} }}",
            f"{t}\tremove_from_variable_map = {{ name = {map_name} key = flag:{key} }}",
            f"{t}}}",
        ]
    return [
        f"{t}if = {{ limit = {{ has_variable = {map_name}_{key} }} remove_variable = {map_name}_{key} }}",
    ]


def s_clear_map(map_name, goods_list, indent):
    """Effect lines: clear a whole per-good container on current scope."""
    t = "\t" * indent
    if STORAGE == "maps":
        return [
            f"{t}if = {{",
            f"{t}\tlimit = {{ has_variable_map = {map_name} }}",
            f"{t}\tclear_variable_map = {map_name}",
            f"{t}}}",
        ]
    out = []
    for g in goods_list:
        out += s_remove(map_name, g, indent)
    return out


# ============================================================
# OUTPUT
# ============================================================

_generated = {}  # rel_path -> content (used by --check)


def write_file(rel_path, content):
    rel_path = rel_path.replace("\\", "/")
    _generated[rel_path] = content
    if CHECK_MODE:
        return
    path = os.path.join(MOD_ROOT, *rel_path.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write(content)
    print(f"  wrote {rel_path} ({len(content.splitlines())} lines)")


# ============================================================
# 1. GOODS MODIFIERS (kill-all + per-good enables + transport)
# ============================================================

def gen_goods_modifiers():
    L = [AUTOGEN,
         "# Kill-all modifiers zero every goods flow on the depot;",
         "# per-good enables are stacked on top with a runtime multiplier.",
         "",
         "stl_export_kill_all = {",
         f"\ticon = {ICON}"]
    for g in names():
        L.append(f"\tgoods_input_{g}_mult = -1")
    L += ["}", "",
          "stl_import_kill_all = {",
          f"\ticon = {ICON}"]
    for g in names():
        L.append(f"\tgoods_output_{g}_mult = -1")
    L.append("\tgoods_input_transportation_mult = -1")
    L += ["}", "", "# === per-good export enables (depot buys from local market) ===", ""]
    for g in names():
        L += [f"stl_export_{g} = {{", f"\ticon = {ICON}", f"\tgoods_input_{g}_mult = 1", "}", ""]
    L += ["# === per-good import enables (depot sells to local market) ===", ""]
    for g in names():
        L += [f"stl_import_{g} = {{", f"\ticon = {ICON}", f"\tgoods_output_{g}_mult = 1", "}", ""]
    L += ["# === per-good transport cost (adds transportation input) ===",
          "# PM base = 1 transportation; kill-all zeroes it; these add back",
          "# import_volume x distance_factor via stl_transport_multiplier.", ""]
    for g in names():
        L += [f"stl_transport_{g} = {{", f"\ticon = {ICON}", "\tgoods_input_transportation_add = 1", "}", ""]
    write_file("common/static_modifiers/stl_goods_modifiers.txt", "\n".join(L))


# ============================================================
# 2. DEBUG MODIFIERS
# ============================================================

def gen_debug_modifiers():
    L = [AUTOGEN,
         "# Diagnostic modifiers, applied only when stl_debug_mode global = 1.",
         "# Toggle via the decision: Salty Transport: Toggle Debug Modifiers",
         ""]
    for g in names():
        L += [f"stl_debug_base_{g} = {{", f"\ticon = {ICON}", "\tbuilding_employment_laborers_add = 0.001", "}", ""]
    for g in names():
        L += [f"stl_debug_access_{g} = {{", f"\ticon = {ICON}", "\tbuilding_employment_laborers_add = 0.001", "}", ""]
    write_file("common/static_modifiers/stl_debug_modifiers.txt", "\n".join(L))


# ============================================================
# 3. MODIFIER TYPE DEFINITIONS
# ============================================================

def gen_modifier_types():
    L = [AUTOGEN,
         "# Modifier types not defined in vanilla 1.12 definition files.",
         "# 1.13.8 registers all goods modifier types in script_docs; these",
         "# definitions only affect display metadata and are harmless if",
         "# vanilla now also defines them.",
         ""]
    for g in names():
        if g not in VANILLA_INPUT_MULT:
            L += [f"goods_input_{g}_mult = {{",
                  "\tdecimals = 0", "\tcolor = bad", "\tpercent = yes",
                  "\tgame_data = {", "\t\tai_value = 0", "\t}", "}", ""]
    L += ["goods_input_transportation_mult = {",
          "\tdecimals = 1", "\tcolor = bad", "\tpercent = yes",
          "\tgame_data = {", "\t\tai_value = 0", "\t}", "}", ""]
    for g in names():
        if g not in VANILLA_OUTPUT_MULT:
            L += [f"goods_output_{g}_mult = {{",
                  "\tdecimals = 1", "\tcolor = good", "\tpercent = yes",
                  "\tgame_data = {", "\t\tai_value = 0", "\t}", "}", ""]
    for g in names():
        if g in MISSING_INPUT_ADD:
            L += [f"goods_input_{g}_add = {{",
                  "\tdecimals = 1", "\tcolor = good",
                  "\tgame_data = {", "\t\tai_value = 0", "\t}", "}", ""]
    write_file("common/modifier_type_definitions/stl_modifier_types.txt", "\n".join(L))


# ============================================================
# 4. PRODUCTION METHODS
# ============================================================

def gen_production_methods():
    L = [AUTOGEN,
         "# Base PM - minimal employment to keep the building functional",
         "pm_stl_trade_depot_base = {",
         f"\ttexture = {PM_TEXTURE}",
         "\tis_default = yes",
         "\tbuilding_modifiers = {",
         "\t\tworkforce_scaled = {",
         "\t\t\tbuilding_employment_laborers_add = 10",
         "\t\t}",
         "\t}",
         "}", "",
         "# Exports PM - depot INPUTS goods from the local market.",
         "# unscaled so base = exactly 1.0 (no workforce-ratio amplification)",
         "pm_stl_trade_depot_exports = {",
         f"\ttexture = {PM_TEXTURE}",
         "\tis_default = yes",
         "\tbuilding_modifiers = {",
         "\t\tunscaled = {"]
    for g in names():
        L.append(f"\t\t\tgoods_input_{g}_add = 1")
    L += ["\t\t}", "\t}", "}", "",
          "# Imports PM - depot OUTPUTS goods into the local market.",
          "pm_stl_trade_depot_imports = {",
          f"\ttexture = {PM_TEXTURE}",
          "\tis_default = yes",
          "\tbuilding_modifiers = {",
          "\t\tunscaled = {"]
    for g in names():
        L.append(f"\t\t\tgoods_output_{g}_add = 1")
    L += ["\t\t\tgoods_input_transportation_add = 1",
          "\t\t}", "\t}", "}", "",
          "# Port hub: restores 100% MAPI in the world-market hub state,",
          "# counteracting the -5 from the urban_planning tech override.",
          "pm_stl_port_hub_base = {",
          f"\ttexture = {PM_TEXTURE}",
          "\tis_default = yes",
          "\tstate_modifiers = {",
          "\t\tunscaled = {",
          "\t\t\tstate_market_access_price_impact = 5",
          "\t\t}",
          "\t}",
          "}", ""]
    write_file("common/production_methods/stl_production_methods.txt", "\n".join(L))


# ============================================================
# 5. PHASE B GENERATED EFFECTS
#    pre-pass price cache + per-pair accumulate + finalize
# ============================================================

def _emit_price_block(L, base, buy_lv, sell_lv, price_lv, indent):
    """Emit price-from-buy/sell-ratio computation into local var price_lv."""
    t = "\t" * indent
    hi = round(1.75 * base, 2)
    lo = round(0.25 * base, 2)
    L += [
        f"{t}set_local_variable = {{ name = {price_lv} value = {base} }}",
        f"{t}set_local_variable = {{ name = stl_min_bs value = local_var:{buy_lv} }}",
        f"{t}if = {{",
        f"{t}\tlimit = {{ NOT = {{ local_var:{sell_lv} >= local_var:{buy_lv} }} }}",
        f"{t}\tset_local_variable = {{ name = stl_min_bs value = local_var:{sell_lv} }}",
        f"{t}}}",
        f"{t}if = {{",
        f"{t}\tlimit = {{ local_var:stl_min_bs > 0.01 }}",
        f"{t}\tset_local_variable = {{ name = stl_ratio value = {{ value = local_var:{buy_lv} subtract = local_var:{sell_lv} divide = local_var:stl_min_bs }} }}",
        f"{t}\tif = {{ limit = {{ local_var:stl_ratio > 1 }} set_local_variable = {{ name = stl_ratio value = 1 }} }}",
        f"{t}\tif = {{ limit = {{ NOT = {{ local_var:stl_ratio >= -1 }} }} set_local_variable = {{ name = stl_ratio value = -1 }} }}",
        f"{t}\tset_local_variable = {{ name = {price_lv} value = {{ value = local_var:stl_ratio multiply = 0.75 add = 1 multiply = {base} }} }}",
        f"{t}}}",
        f"{t}else = {{",
        f"{t}\t# pure consumer looks expensive, pure producer looks cheap",
        f"{t}\tif = {{ limit = {{ local_var:{buy_lv} > local_var:{sell_lv} }} set_local_variable = {{ name = {price_lv} value = {hi} }} }}",
        f"{t}\tif = {{ limit = {{ NOT = {{ local_var:{buy_lv} > local_var:{sell_lv} }} }} set_local_variable = {{ name = {price_lv} value = {lo} }} }}",
        f"{t}}}",
    ]


def gen_phase_b():
    L = [AUTOGEN,
         "# PHASE B v2 (see ARCHITECTURE_V2.md sections 1-3)",
         "#",
         "# stl_cache_state_prices    - pre-pass: price/econ/prod cached per state",
         "# stl_phase_b_zero_locals   - zero per-origin local accumulators",
         "# stl_phase_b_accumulate_all_goods - per-pair: read partner cache, accumulate",
         "# stl_phase_b_finalize_prices      - per-origin: market price + targets",
         "#",
         "# The pair loop reads only cached values; sg: engine reads happen once",
         "# per state per cycle (pre-pass), not once per pair (v0.1 behaviour).",
         ""]

    # ---- pre-pass: cache prices ----
    L += ["# Cache local price estimate, economy scale and production for all goods.",
          "# Scope: state. Run once per state on the first Phase B day.",
          "stl_cache_state_prices = {"]
    L += s_clear_map("stl_price", names(), 1)
    L += s_clear_map("stl_econ", names(), 1)
    L += s_clear_map("stl_prod", names(), 1)
    for (g, _disp, base, _tq, _cat, _en) in enabled_goods():
        L.append(f"\t# --- {g} (base {base}) ---")
        L += [
            f"\tset_local_variable = {{ name = stl_buy value = {{ value = sg:{g}.state_goods_consumption }} }}",
            f"\tset_local_variable = {{ name = stl_sell value = {{ value = sg:{g}.state_goods_production }} }}",
            "\tset_local_variable = { name = stl_e value = local_var:stl_buy }",
            "\tif = {",
            "\t\tlimit = { local_var:stl_sell > local_var:stl_buy }",
            "\t\tset_local_variable = { name = stl_e value = local_var:stl_sell }",
            "\t}",
            "\tif = {",
            "\t\tlimit = { local_var:stl_e > 0.01 }",
        ]
        _emit_price_block(L, base, "stl_buy", "stl_sell", "stl_p", 2)
        L += s_write("stl_price", g, "local_var:stl_p", 2)
        L += s_write("stl_econ", g, "local_var:stl_e", 2)
        L += [
            "\t\tif = {",
            "\t\t\tlimit = { local_var:stl_sell > 0.01 }",
        ]
        L += s_write("stl_prod", g, "local_var:stl_sell", 3)
        L += ["\t\t}",
              "\t}"]
    L += ["}", ""]

    # ---- zero local accumulators ----
    L += ["# Zero the per-origin local accumulators (live for one effect chain).",
          "stl_phase_b_zero_locals = {"]
    for g in names():
        for acc in ("was", "maxwas", "wad", "maxwad", "psum", "wsum"):
            L.append(f"\tset_local_variable = {{ name = stl_acc_{acc}_{g} value = 0 }}")
    L += ["}", ""]

    # ---- per-pair accumulate ----
    L += ["# Accumulate WAS/WAD and market-price sums for all goods from one",
          "# partner state. Scope: partner state. Requires:",
          "#   scope:stl_gravity_self = origin state",
          "#   local_var:stl_pw       = proximity weight (100 - friction)",
          "stl_phase_b_accumulate_all_goods = {"]
    for (g, _disp, base, _tq, _cat, _en) in enabled_goods():
        L += [
            f"\t# --- {g} ---",
            "\tif = {",
            f"\t\tlimit = {{ {s_has('stl_econ', g)} }}",
            f"\t\tset_local_variable = {{ name = stl_pp value = {s_read('stl_price', g)} }}",
            "\t\t# market price accumulation (production-weighted)",
            "\t\tif = {",
            f"\t\t\tlimit = {{ {s_has('stl_prod', g)} }}",
            f"\t\t\tset_local_variable = {{ name = stl_wp value = {{ value = {s_read('stl_prod', g)} multiply = local_var:stl_pp }} }}",
            f"\t\t\tchange_local_variable = {{ name = stl_acc_psum_{g} add = local_var:stl_wp }}",
            f"\t\t\tchange_local_variable = {{ name = stl_acc_wsum_{g} add = {s_read('stl_prod', g)} }}",
            "\t\t}",
            "\t\t# effective surplus vs origin's last-cycle market price",
            f"\t\tset_local_variable = {{ name = stl_mkt value = {base} }}",
            "\t\tif = {",
            f"\t\t\tlimit = {{ scope:stl_gravity_self = {{ {s_has('stl_market_price', g)} }} }}",
            f"\t\t\tset_local_variable = {{ name = stl_mkt value = {s_read_scoped('scope:stl_gravity_self', 'stl_market_price', g)} }}",
            "\t\t}",
            "\t\tif = {",
            "\t\t\tlimit = { local_var:stl_mkt > 0.01 }",
            f"\t\t\tset_local_variable = {{ name = stl_eff value = {{ value = local_var:stl_mkt subtract = local_var:stl_pp divide = local_var:stl_mkt multiply = {s_read('stl_econ', g)} }} }}",
            "\t\t\tif = {",
            "\t\t\t\tlimit = { local_var:stl_eff > 0 }",
            "\t\t\t\tset_local_variable = { name = stl_wv value = { value = local_var:stl_eff multiply = local_var:stl_pw } }",
            f"\t\t\t\tchange_local_variable = {{ name = stl_acc_was_{g} add = local_var:stl_wv }}",
            "\t\t\t\tset_local_variable = { name = stl_mwv value = { value = local_var:stl_eff multiply = 100 } }",
            f"\t\t\t\tchange_local_variable = {{ name = stl_acc_maxwas_{g} add = local_var:stl_mwv }}",
            "\t\t\t}",
            "\t\t\tif = {",
            "\t\t\t\tlimit = { NOT = { local_var:stl_eff >= 0 } }",
            "\t\t\t\tset_local_variable = { name = stl_neg value = { value = 0 subtract = local_var:stl_eff } }",
            "\t\t\t\tset_local_variable = { name = stl_wv value = { value = local_var:stl_neg multiply = local_var:stl_pw } }",
            f"\t\t\t\tchange_local_variable = {{ name = stl_acc_wad_{g} add = local_var:stl_wv }}",
            "\t\t\t\tset_local_variable = { name = stl_mwv value = { value = local_var:stl_neg multiply = 100 } }",
            f"\t\t\t\tchange_local_variable = {{ name = stl_acc_maxwad_{g} add = local_var:stl_mwv }}",
            "\t\t\t}",
            "\t\t}",
            "\t}",
        ]
    L += ["}", ""]

    # ---- finalize ----
    L += ["# Finalize one origin: fold own state into the market price, compute",
          "# the direction-aware export/import targets, persist gravity scores.",
          "# Scope: origin state (after the partner loop).",
          "stl_phase_b_finalize_prices = {"]
    for (g, _disp, base, _tq, _cat, _en) in enabled_goods():
        L += [
            f"\t# --- {g} ---",
            "\t# fold own production x own cached price into the weighted average",
            "\tif = {",
            f"\t\tlimit = {{ {s_has('stl_prod', g)} {s_has('stl_price', g)} }}",
            f"\t\tset_local_variable = {{ name = stl_wp value = {{ value = {s_read('stl_prod', g)} multiply = {s_read('stl_price', g)} }} }}",
            f"\t\tchange_local_variable = {{ name = stl_acc_psum_{g} add = local_var:stl_wp }}",
            f"\t\tchange_local_variable = {{ name = stl_acc_wsum_{g} add = {s_read('stl_prod', g)} }}",
            "\t}",
            "\t# market price (only overwritten when computable; else last cycle's stands)",
            "\tif = {",
            f"\t\tlimit = {{ local_var:stl_acc_wsum_{g} > 0.01 }}",
            f"\t\tset_local_variable = {{ name = stl_mkt value = {{ value = local_var:stl_acc_psum_{g} divide = local_var:stl_acc_wsum_{g} }} }}",
        ]
        L += [line for line in s_write("stl_market_price", g, "local_var:stl_mkt", 2)]
        L += [
            "\t}",
            "\t# persist gravity scores for Phase C + GUI",
        ]
        L += s_write("stl_was", g, f"local_var:stl_acc_was_{g}", 1)
        L += s_write("stl_max_was", g, f"local_var:stl_acc_maxwas_{g}", 1)
        L += s_write("stl_wad", g, f"local_var:stl_acc_wad_{g}", 1)
        L += s_write("stl_max_wad", g, f"local_var:stl_acc_maxwad_{g}", 1)
        L += [
            "\t# own effective surplus -> direction-aware targets",
            "\tset_local_variable = { name = stl_own_eff value = 0 }",
            "\tset_local_variable = { name = stl_have_eff value = 0 }",
            "\tif = {",
            f"\t\tlimit = {{ {s_has('stl_econ', g)} {s_has('stl_price', g)} {s_has('stl_market_price', g)} }}",
            f"\t\tset_local_variable = {{ name = stl_mkt value = {s_read('stl_market_price', g)} }}",
            "\t\tif = {",
            "\t\t\tlimit = { local_var:stl_mkt > 0.01 }",
            f"\t\t\tset_local_variable = {{ name = stl_own_eff value = {{ value = local_var:stl_mkt subtract = {s_read('stl_price', g)} divide = local_var:stl_mkt multiply = {s_read('stl_econ', g)} }} }}",
            "\t\t\tset_local_variable = { name = stl_have_eff value = 1 }",
            "\t\t}",
            "\t}",
            "\t# previous applied trade (for direction persistence)",
            "\tset_local_variable = { name = stl_prev_exp value = 0 }",
            "\tif = {",
            f"\t\tlimit = {{ {s_has('stl_last_export', g)} }}",
            f"\t\tset_local_variable = {{ name = stl_prev_exp value = {s_read('stl_last_export', g)} }}",
            "\t}",
            "\tset_local_variable = { name = stl_prev_imp value = 0 }",
            "\tif = {",
            f"\t\tlimit = {{ {s_has('stl_last_import', g)} }}",
            f"\t\tset_local_variable = {{ name = stl_prev_imp value = {s_read('stl_last_import', g)} }}",
            "\t}",
            "\tset_local_variable = { name = stl_tgt_exp value = 0 }",
            "\tset_local_variable = { name = stl_tgt_imp value = 0 }",
            "\tif = {",
            "\t\tlimit = { local_var:stl_have_eff >= 1 }",
            "\t\t# Case 1: was importing -> adjust import target by eff (flip on overshoot)",
            "\t\tif = {",
            f"\t\t\tlimit = {{ local_var:stl_prev_imp > {MIN_TRADE} }}",
            "\t\t\tset_local_variable = { name = stl_tgt_imp value = { value = local_var:stl_prev_imp subtract = local_var:stl_own_eff } }",
            "\t\t\tif = {",
            "\t\t\t\tlimit = { NOT = { local_var:stl_tgt_imp >= 0 } }",
            "\t\t\t\tset_local_variable = { name = stl_tgt_exp value = { value = 0 subtract = local_var:stl_tgt_imp } }",
            "\t\t\t\tset_local_variable = { name = stl_tgt_imp value = 0 }",
            "\t\t\t}",
            "\t\t}",
            "\t\t# Case 2: was exporting -> adjust export target by eff (flip on overshoot)",
            "\t\tif = {",
            f"\t\t\tlimit = {{ NOT = {{ local_var:stl_prev_imp > {MIN_TRADE} }} local_var:stl_prev_exp > {MIN_TRADE} }}",
            "\t\t\tset_local_variable = { name = stl_tgt_exp value = { value = local_var:stl_prev_exp add = local_var:stl_own_eff } }",
            "\t\t\tif = {",
            "\t\t\t\tlimit = { NOT = { local_var:stl_tgt_exp >= 0 } }",
            "\t\t\t\tset_local_variable = { name = stl_tgt_imp value = { value = 0 subtract = local_var:stl_tgt_exp } }",
            "\t\t\t\tset_local_variable = { name = stl_tgt_exp value = 0 }",
            "\t\t\t}",
            "\t\t}",
            "\t\t# Case 3: no existing trade -> raw signal",
            "\t\tif = {",
            f"\t\t\tlimit = {{ NOT = {{ local_var:stl_prev_imp > {MIN_TRADE} }} NOT = {{ local_var:stl_prev_exp > {MIN_TRADE} }} }}",
            "\t\t\tif = {",
            "\t\t\t\tlimit = { local_var:stl_own_eff > 0 }",
            "\t\t\t\tset_local_variable = { name = stl_tgt_exp value = local_var:stl_own_eff }",
            "\t\t\t}",
            "\t\t\tif = {",
            "\t\t\t\tlimit = { NOT = { local_var:stl_own_eff >= 0 } }",
            "\t\t\t\tset_local_variable = { name = stl_tgt_imp value = { value = 0 subtract = local_var:stl_own_eff } }",
            "\t\t\t}",
            "\t\t}",
            "\t}",
            "\t# persist targets (sparse: only meaningful values keep a key)",
            "\tif = {",
            "\t\tlimit = { local_var:stl_tgt_exp > 0.005 }",
        ]
        L += s_write("stl_eff_export", g, "local_var:stl_tgt_exp", 2)
        L += ["\t}",
              "\tif = {",
              "\t\tlimit = { NOT = { local_var:stl_tgt_exp > 0.005 } }"]
        L += s_remove("stl_eff_export", g, 2)
        L += ["\t}",
              "\tif = {",
              "\t\tlimit = { local_var:stl_tgt_imp > 0.005 }"]
        L += s_write("stl_eff_import", g, "local_var:stl_tgt_imp", 2)
        L += ["\t}",
              "\tif = {",
              "\t\tlimit = { NOT = { local_var:stl_tgt_imp > 0.005 } }"]
        L += s_remove("stl_eff_import", g, 2)
        L += ["\t}"]
    L += ["}", ""]
    write_file("common/scripted_effects/stl_phase_b_generated.txt", "\n".join(L))


# ============================================================
# 6. PHASE C GENERATED EFFECTS
# ============================================================

def gen_phase_c():
    g = "$GOODS$"
    L = [AUTOGEN,
         "# PHASE C v2 (see ARCHITECTURE_V2.md section 4)",
         "# Dispatcher batches goods across days 21-28; stl_phase_c_good does",
         "# EMA + rate cap + decay, conservation normalization, transport cost",
         "# and GUI bookkeeping for one good across the whole market.",
         ""]

    # ---- dispatcher ----
    L += ["# Scope: country (market owner)",
          "stl_phase_c_batch = {",
          "\tif = {",
          "\t\tlimit = { NOT = { has_variable = stl_phase_c_batch_idx } }",
          "\t\tset_variable = { name = stl_phase_c_batch_idx value = 0 }",
          "\t}"]
    goods_list = names()
    batches = [goods_list[i:i + GOODS_PER_BATCH] for i in range(0, len(goods_list), GOODS_PER_BATCH)]
    # 8 Phase C days are scheduled; merge any overflow into the last batch
    while len(batches) > 8:
        batches[-2] += batches[-1]
        batches.pop()
    for i, batch in enumerate(batches):
        L.append(f"\t# ===== batch {i}: {', '.join(batch)} =====")
        if i == 0:
            L.append(f"\tif = {{")
            L.append(f"\t\tlimit = {{ NOT = {{ var:stl_phase_c_batch_idx >= 1 }} }}")
        elif i == len(batches) - 1:
            L.append(f"\tif = {{")
            L.append(f"\t\tlimit = {{ var:stl_phase_c_batch_idx >= {i} }}")
        else:
            L.append(f"\tif = {{")
            L.append(f"\t\tlimit = {{ var:stl_phase_c_batch_idx >= {i} NOT = {{ var:stl_phase_c_batch_idx >= {i + 1} }} }}")
        for good in batch:
            L.append(f"\t\tstl_phase_c_good = {{ GOODS = {good} }}")
        L.append("\t}")
    L += ["\tchange_variable = { name = stl_phase_c_batch_idx add = 1 }",
          "}", ""]

    # ---- per-good worker (parameterized) ----
    def has(m):
        return s_has(m, g)

    def read(m):
        return s_read(m, g)

    def write(m, val, ind):
        return s_write(m, g, val, ind)

    def remove(m, ind):
        return s_remove(m, g, ind)

    L += ["# Scope: country (market owner). GOODS = good key.",
          "stl_phase_c_good = {",
          "",
          "\t# ===== clear old modifiers (refs were refreshed on day 8) =====",
          "\tmarket = {",
          "\t\tevery_scope_country = {",
          "\t\t\tevery_scope_state = {",
          "\t\t\t\tlimit = {",
          "\t\t\t\t\thas_variable = stl_trade_depot_ref",
          "\t\t\t\t\thas_building = building_stl_trade_depot",
          "\t\t\t\t}",
          "\t\t\t\tvar:stl_trade_depot_ref = {",
          f"\t\t\t\t\tremove_modifier = stl_export_{g}",
          f"\t\t\t\t\tremove_modifier = stl_import_{g}",
          f"\t\t\t\t\tremove_modifier = stl_transport_{g}",
          f"\t\t\t\t\tremove_modifier = stl_debug_base_{g}",
          f"\t\t\t\t\tremove_modifier = stl_debug_access_{g}",
          "\t\t\t\t}"]
    L += remove("stl_transport", 4)
    L += ["\t\t\t}",
          "\t\t}",
          "\t}",
          "",
          "\t# ===== sub-pass 3d: per-state trade amounts =====",
          "\tmarket = {",
          "\t\tevery_scope_country = {",
          "\t\t\tevery_scope_state = {",
          "\t\t\t\tlimit = {",
          "\t\t\t\t\thas_variable = stl_trade_depot_ref",
          "\t\t\t\t\thas_building = building_stl_trade_depot",
          "\t\t\t\t}",
          "",
          "\t\t\t\t# previous applied trade (EMA input), then reset",
          "\t\t\t\tset_local_variable = { name = stl_old_export value = 0 }",
          "\t\t\t\tif = {",
          f"\t\t\t\t\tlimit = {{ {has('stl_last_export')} }}",
          f"\t\t\t\t\tset_local_variable = {{ name = stl_old_export value = {read('stl_last_export')} }}",
          "\t\t\t\t}",
          "\t\t\t\tset_local_variable = { name = stl_old_import value = 0 }",
          "\t\t\t\tif = {",
          f"\t\t\t\t\tlimit = {{ {has('stl_last_import')} }}",
          f"\t\t\t\t\tset_local_variable = {{ name = stl_old_import value = {read('stl_last_import')} }}",
          "\t\t\t\t}"]
    L += remove("stl_last_export", 4)
    L += remove("stl_last_import", 4)
    # exporters
    L += ["",
          "\t\t\t\t# --- exporters ---",
          "\t\t\t\tif = {",
          "\t\t\t\t\tlimit = {",
          f"\t\t\t\t\t\t{has('stl_eff_export')}",
          f"\t\t\t\t\t\t{has('stl_max_wad')}",
          f"\t\t\t\t\t\t{read('stl_eff_export')} > 0",
          f"\t\t\t\t\t\t{read('stl_max_wad')} > 0.01",
          "\t\t\t\t\t}",
          f"\t\t\t\t\tset_local_variable = {{ name = stl_trade_amount value = {read('stl_eff_export')} }}",
          "\t\t\t\t\t# EMA toward the Phase B target",
          "\t\t\t\t\tset_local_variable = {",
          "\t\t\t\t\t\tname = stl_trade_amount",
          "\t\t\t\t\t\tvalue = {",
          "\t\t\t\t\t\t\tvalue = local_var:stl_trade_amount",
          f"\t\t\t\t\t\t\tmultiply = {EMA_NEW}",
          "\t\t\t\t\t\t\tadd = {",
          "\t\t\t\t\t\t\t\tvalue = local_var:stl_old_export",
          f"\t\t\t\t\t\t\t\tmultiply = {EMA_OLD}",
          "\t\t\t\t\t\t\t}",
          "\t\t\t\t\t\t}",
          "\t\t\t\t\t}",
          "\t\t\t\t\t# rate cap",
          f"\t\t\t\t\tset_local_variable = {{ name = stl_rate_cap value = {{ value = local_var:stl_old_export multiply = {RATE_CAP} }} }}",
          "\t\t\t\t\tif = {",
          f"\t\t\t\t\t\tlimit = {{ NOT = {{ local_var:stl_rate_cap >= {RATE_FLOOR} }} }}",
          f"\t\t\t\t\t\tset_local_variable = {{ name = stl_rate_cap value = {RATE_FLOOR} }}",
          "\t\t\t\t\t}",
          "\t\t\t\t\tset_local_variable = { name = stl_cap_up value = { value = local_var:stl_old_export add = local_var:stl_rate_cap } }",
          "\t\t\t\t\tif = {",
          "\t\t\t\t\t\tlimit = { local_var:stl_trade_amount > local_var:stl_cap_up }",
          "\t\t\t\t\t\tset_local_variable = { name = stl_trade_amount value = local_var:stl_cap_up }",
          "\t\t\t\t\t}"]
    L += [line for line in write("stl_last_export", "local_var:stl_trade_amount", 5)]
    L += ["\t\t\t\t\tvar:stl_trade_depot_ref = {",
          "\t\t\t\t\t\tadd_modifier = {",
          f"\t\t\t\t\t\t\tname = stl_export_{g}",
          "\t\t\t\t\t\t\tmultiplier = stl_trade_multiplier",
          "\t\t\t\t\t\t}",
          "\t\t\t\t\t}",
          "\t\t\t\t\tif = {",
          "\t\t\t\t\t\tlimit = { global_var:stl_debug_mode >= 1 }",
          f"\t\t\t\t\t\tset_local_variable = {{ name = stl_debug_base value = {read('stl_eff_export')} }}",
          "\t\t\t\t\t\tvar:stl_trade_depot_ref = {",
          f"\t\t\t\t\t\t\tadd_modifier = {{ name = stl_debug_base_{g} multiplier = stl_debug_base_multiplier }}",
          "\t\t\t\t\t\t}",
          f"\t\t\t\t\t\tset_local_variable = {{ name = stl_debug_access value = {{ value = {read('stl_wad')} divide = {read('stl_max_wad')} }} }}",
          "\t\t\t\t\t\tvar:stl_trade_depot_ref = {",
          f"\t\t\t\t\t\t\tadd_modifier = {{ name = stl_debug_access_{g} multiplier = stl_debug_access_multiplier }}",
          "\t\t\t\t\t\t}",
          "\t\t\t\t\t}",
          "\t\t\t\t}"]
    # importers (mirror)
    L += ["",
          "\t\t\t\t# --- importers ---",
          "\t\t\t\tif = {",
          "\t\t\t\t\tlimit = {",
          f"\t\t\t\t\t\t{has('stl_eff_import')}",
          f"\t\t\t\t\t\t{has('stl_max_was')}",
          f"\t\t\t\t\t\t{read('stl_eff_import')} > 0",
          f"\t\t\t\t\t\t{read('stl_max_was')} > 0.01",
          "\t\t\t\t\t}",
          f"\t\t\t\t\tset_local_variable = {{ name = stl_trade_amount value = {read('stl_eff_import')} }}",
          "\t\t\t\t\tset_local_variable = {",
          "\t\t\t\t\t\tname = stl_trade_amount",
          "\t\t\t\t\t\tvalue = {",
          "\t\t\t\t\t\t\tvalue = local_var:stl_trade_amount",
          f"\t\t\t\t\t\t\tmultiply = {EMA_NEW}",
          "\t\t\t\t\t\t\tadd = {",
          "\t\t\t\t\t\t\t\tvalue = local_var:stl_old_import",
          f"\t\t\t\t\t\t\t\tmultiply = {EMA_OLD}",
          "\t\t\t\t\t\t\t}",
          "\t\t\t\t\t\t}",
          "\t\t\t\t\t}",
          f"\t\t\t\t\tset_local_variable = {{ name = stl_rate_cap value = {{ value = local_var:stl_old_import multiply = {RATE_CAP} }} }}",
          "\t\t\t\t\tif = {",
          f"\t\t\t\t\t\tlimit = {{ NOT = {{ local_var:stl_rate_cap >= {RATE_FLOOR} }} }}",
          f"\t\t\t\t\t\tset_local_variable = {{ name = stl_rate_cap value = {RATE_FLOOR} }}",
          "\t\t\t\t\t}",
          "\t\t\t\t\tset_local_variable = { name = stl_cap_up value = { value = local_var:stl_old_import add = local_var:stl_rate_cap } }",
          "\t\t\t\t\tif = {",
          "\t\t\t\t\t\tlimit = { local_var:stl_trade_amount > local_var:stl_cap_up }",
          "\t\t\t\t\t\tset_local_variable = { name = stl_trade_amount value = local_var:stl_cap_up }",
          "\t\t\t\t\t}"]
    L += [line for line in write("stl_last_import", "local_var:stl_trade_amount", 5)]
    L += ["\t\t\t\t\tvar:stl_trade_depot_ref = {",
          "\t\t\t\t\t\tadd_modifier = {",
          f"\t\t\t\t\t\t\tname = stl_import_{g}",
          "\t\t\t\t\t\t\tmultiplier = stl_trade_multiplier",
          "\t\t\t\t\t\t}",
          "\t\t\t\t\t}",
          "\t\t\t\t\tif = {",
          "\t\t\t\t\t\tlimit = { global_var:stl_debug_mode >= 1 }",
          f"\t\t\t\t\t\tset_local_variable = {{ name = stl_debug_base value = {read('stl_eff_import')} }}",
          "\t\t\t\t\t\tvar:stl_trade_depot_ref = {",
          f"\t\t\t\t\t\t\tadd_modifier = {{ name = stl_debug_base_{g} multiplier = stl_debug_base_multiplier }}",
          "\t\t\t\t\t\t}",
          f"\t\t\t\t\t\tset_local_variable = {{ name = stl_debug_access value = {{ value = {read('stl_was')} divide = {read('stl_max_was')} }} }}",
          "\t\t\t\t\t\tvar:stl_trade_depot_ref = {",
          f"\t\t\t\t\t\t\tadd_modifier = {{ name = stl_debug_access_{g} multiplier = stl_debug_access_multiplier }}",
          "\t\t\t\t\t\t}",
          "\t\t\t\t\t}",
          "\t\t\t\t}"]
    # decay
    L += ["",
          "\t\t\t\t# --- gradual decay when the Phase B signal disappears ---",
          "\t\t\t\tif = {",
          "\t\t\t\t\tlimit = {",
          f"\t\t\t\t\t\tlocal_var:stl_old_export > {MIN_TRADE}",
          f"\t\t\t\t\t\tNOT = {{ {has('stl_last_export')} }}",
          f"\t\t\t\t\t\tNOT = {{ {has('stl_last_import')} }}",
          "\t\t\t\t\t}",
          f"\t\t\t\t\tset_local_variable = {{ name = stl_trade_amount value = {{ value = local_var:stl_old_export multiply = {DECAY} }} }}",
          "\t\t\t\t\tif = {",
          f"\t\t\t\t\t\tlimit = {{ local_var:stl_trade_amount > {MIN_TRADE} }}"]
    L += [line for line in write("stl_last_export", "local_var:stl_trade_amount", 6)]
    L += ["\t\t\t\t\t\tvar:stl_trade_depot_ref = {",
          "\t\t\t\t\t\t\tadd_modifier = {",
          f"\t\t\t\t\t\t\t\tname = stl_export_{g}",
          "\t\t\t\t\t\t\t\tmultiplier = stl_trade_multiplier",
          "\t\t\t\t\t\t\t}",
          "\t\t\t\t\t\t}",
          "\t\t\t\t\t}",
          "\t\t\t\t}",
          "\t\t\t\tif = {",
          "\t\t\t\t\tlimit = {",
          f"\t\t\t\t\t\tlocal_var:stl_old_import > {MIN_TRADE}",
          f"\t\t\t\t\t\tNOT = {{ {has('stl_last_import')} }}",
          f"\t\t\t\t\t\tNOT = {{ {has('stl_last_export')} }}",
          "\t\t\t\t\t}",
          f"\t\t\t\t\tset_local_variable = {{ name = stl_trade_amount value = {{ value = local_var:stl_old_import multiply = {DECAY} }} }}",
          "\t\t\t\t\tif = {",
          f"\t\t\t\t\t\tlimit = {{ local_var:stl_trade_amount > {MIN_TRADE} }}"]
    L += [line for line in write("stl_last_import", "local_var:stl_trade_amount", 6)]
    L += ["\t\t\t\t\t\tvar:stl_trade_depot_ref = {",
          "\t\t\t\t\t\t\tadd_modifier = {",
          f"\t\t\t\t\t\t\t\tname = stl_import_{g}",
          "\t\t\t\t\t\t\t\tmultiplier = stl_trade_multiplier",
          "\t\t\t\t\t\t\t}",
          "\t\t\t\t\t\t}",
          "\t\t\t\t\t}",
          "\t\t\t\t}",
          "\t\t\t}",
          "\t\t}",
          "\t}"]
    # conservation
    L += ["",
          "\t# ===== sub-pass 3d.5: conservation normalization =====",
          "\tset_global_variable = { name = stl_sum_exports value = 0 }",
          "\tset_global_variable = { name = stl_sum_imports value = 0 }",
          "\tmarket = {",
          "\t\tevery_scope_country = {",
          "\t\t\tevery_scope_state = {",
          "\t\t\t\tlimit = {",
          "\t\t\t\t\thas_variable = stl_trade_depot_ref",
          "\t\t\t\t\thas_building = building_stl_trade_depot",
          "\t\t\t\t}",
          "\t\t\t\tif = {",
          f"\t\t\t\t\tlimit = {{ {has('stl_last_export')} }}",
          "\t\t\t\t\tset_global_variable = {",
          "\t\t\t\t\t\tname = stl_sum_exports",
          f"\t\t\t\t\t\tvalue = {{ value = global_var:stl_sum_exports add = {read('stl_last_export')} }}",
          "\t\t\t\t\t}",
          "\t\t\t\t}",
          "\t\t\t\tif = {",
          f"\t\t\t\t\tlimit = {{ {has('stl_last_import')} }}",
          "\t\t\t\t\tset_global_variable = {",
          "\t\t\t\t\t\tname = stl_sum_imports",
          f"\t\t\t\t\t\tvalue = {{ value = global_var:stl_sum_imports add = {read('stl_last_import')} }}",
          "\t\t\t\t\t}",
          "\t\t\t\t}",
          "\t\t\t}",
          "\t\t}",
          "\t}",
          "\tset_global_variable = { name = stl_norm_export value = 1 }",
          "\tset_global_variable = { name = stl_norm_import value = 1 }",
          "\tif = {",
          "\t\tlimit = {",
          "\t\t\tglobal_var:stl_sum_exports > 0",
          "\t\t\tglobal_var:stl_sum_imports > 0",
          "\t\t}",
          "\t\tif = {",
          "\t\t\tlimit = { global_var:stl_sum_imports > global_var:stl_sum_exports }",
          "\t\t\tset_global_variable = {",
          "\t\t\t\tname = stl_norm_import",
          "\t\t\t\tvalue = { value = global_var:stl_sum_exports divide = global_var:stl_sum_imports }",
          "\t\t\t}",
          "\t\t}",
          "\t\tif = {",
          "\t\t\tlimit = { global_var:stl_sum_exports > global_var:stl_sum_imports }",
          "\t\t\tset_global_variable = {",
          "\t\t\t\tname = stl_norm_export",
          "\t\t\t\tvalue = { value = global_var:stl_sum_imports divide = global_var:stl_sum_exports }",
          "\t\t\t}",
          "\t\t}",
          "\t}",
          "\tif = {",
          "\t\tlimit = {",
          "\t\t\tNOT = { global_var:stl_sum_exports > 0 }",
          "\t\t\tglobal_var:stl_sum_imports > 0",
          "\t\t}",
          "\t\tset_global_variable = { name = stl_norm_import value = 0 }",
          "\t}",
          "\tif = {",
          "\t\tlimit = {",
          "\t\t\tglobal_var:stl_sum_exports > 0",
          "\t\t\tNOT = { global_var:stl_sum_imports > 0 }",
          "\t\t}",
          "\t\tset_global_variable = { name = stl_norm_export value = 0 }",
          "\t}",
          "\tif = {",
          "\t\tlimit = {",
          "\t\t\tOR = {",
          "\t\t\t\tNOT = { global_var:stl_norm_export >= 1 }",
          "\t\t\t\tNOT = { global_var:stl_norm_import >= 1 }",
          "\t\t\t}",
          "\t\t}",
          "\t\tmarket = {",
          "\t\t\tevery_scope_country = {",
          "\t\t\t\tevery_scope_state = {",
          "\t\t\t\t\tlimit = {",
          "\t\t\t\t\t\thas_variable = stl_trade_depot_ref",
          "\t\t\t\t\t\thas_building = building_stl_trade_depot",
          "\t\t\t\t\t}",
          "\t\t\t\t\t# scale exports down",
          "\t\t\t\t\tif = {",
          "\t\t\t\t\t\tlimit = {",
          f"\t\t\t\t\t\t\t{has('stl_last_export')}",
          "\t\t\t\t\t\t\tNOT = { global_var:stl_norm_export >= 1 }",
          "\t\t\t\t\t\t}",
          "\t\t\t\t\t\tvar:stl_trade_depot_ref = {",
          f"\t\t\t\t\t\t\tremove_modifier = stl_export_{g}",
          "\t\t\t\t\t\t}",
          f"\t\t\t\t\t\tset_local_variable = {{ name = stl_scaled value = {{ value = {read('stl_last_export')} multiply = global_var:stl_norm_export }} }}",
          "\t\t\t\t\t\tif = {",
          f"\t\t\t\t\t\t\tlimit = {{ local_var:stl_scaled > {MIN_TRADE} }}"]
    L += [line for line in write("stl_last_export", "local_var:stl_scaled", 7)]
    L += ["\t\t\t\t\t\t\tset_local_variable = { name = stl_trade_amount value = local_var:stl_scaled }",
          "\t\t\t\t\t\t\tvar:stl_trade_depot_ref = {",
          "\t\t\t\t\t\t\t\tadd_modifier = {",
          f"\t\t\t\t\t\t\t\t\tname = stl_export_{g}",
          "\t\t\t\t\t\t\t\t\tmultiplier = stl_trade_multiplier",
          "\t\t\t\t\t\t\t\t}",
          "\t\t\t\t\t\t\t}",
          "\t\t\t\t\t\t}",
          "\t\t\t\t\t\telse = {",
          "\t\t\t\t\t\t\t# rounds to zero: drop it entirely (no phantom flows)"]
    L += [line for line in remove("stl_last_export", 7)]
    L += ["\t\t\t\t\t\t}",
          "\t\t\t\t\t}",
          "\t\t\t\t\t# scale imports down",
          "\t\t\t\t\tif = {",
          "\t\t\t\t\t\tlimit = {",
          f"\t\t\t\t\t\t\t{has('stl_last_import')}",
          "\t\t\t\t\t\t\tNOT = { global_var:stl_norm_import >= 1 }",
          "\t\t\t\t\t\t}",
          "\t\t\t\t\t\tvar:stl_trade_depot_ref = {",
          f"\t\t\t\t\t\t\tremove_modifier = stl_import_{g}",
          "\t\t\t\t\t\t}",
          f"\t\t\t\t\t\tset_local_variable = {{ name = stl_scaled value = {{ value = {read('stl_last_import')} multiply = global_var:stl_norm_import }} }}",
          "\t\t\t\t\t\tif = {",
          f"\t\t\t\t\t\t\tlimit = {{ local_var:stl_scaled > {MIN_TRADE} }}"]
    L += [line for line in write("stl_last_import", "local_var:stl_scaled", 7)]
    L += ["\t\t\t\t\t\t\tset_local_variable = { name = stl_trade_amount value = local_var:stl_scaled }",
          "\t\t\t\t\t\t\tvar:stl_trade_depot_ref = {",
          "\t\t\t\t\t\t\t\tadd_modifier = {",
          f"\t\t\t\t\t\t\t\t\tname = stl_import_{g}",
          "\t\t\t\t\t\t\t\t\tmultiplier = stl_trade_multiplier",
          "\t\t\t\t\t\t\t\t}",
          "\t\t\t\t\t\t\t}",
          "\t\t\t\t\t\t}",
          "\t\t\t\t\t\telse = {",
          "\t\t\t\t\t\t\t# rounds to zero: drop it entirely (fixes v0.1 phantom transport)"]
    L += [line for line in remove("stl_last_import", 7)]
    L += ["\t\t\t\t\t\t}",
          "\t\t\t\t\t}",
          "\t\t\t\t}",
          "\t\t\t}",
          "\t\t}",
          "\t}"]
    # transport
    L += ["",
          "\t# ===== sub-pass 3d.75: distance-based transport cost (importers) =====",
          "\tmarket = {",
          "\t\tevery_scope_country = {",
          "\t\t\tevery_scope_state = {",
          "\t\t\t\tlimit = {",
          "\t\t\t\t\thas_variable = stl_trade_depot_ref",
          "\t\t\t\t\thas_building = building_stl_trade_depot",
          f"\t\t\t\t\t{has('stl_last_import')}",
          f"\t\t\t\t\t{has('stl_was')}",
          f"\t\t\t\t\t{read('stl_was')} > 0.01",
          "\t\t\t\t}",
          "\t\t\t\t# cost factor = max_WAS / WAS, clamped to [1, 10]",
          f"\t\t\t\tset_local_variable = {{ name = stl_distance_factor value = {{ value = {read('stl_max_was')} divide = {read('stl_was')} }} }}",
          "\t\t\t\tif = {",
          "\t\t\t\t\tlimit = { NOT = { local_var:stl_distance_factor >= 1 } }",
          "\t\t\t\t\tset_local_variable = { name = stl_distance_factor value = 1 }",
          "\t\t\t\t}",
          "\t\t\t\tif = {",
          "\t\t\t\t\tlimit = { local_var:stl_distance_factor > 10 }",
          "\t\t\t\t\tset_local_variable = { name = stl_distance_factor value = 10 }",
          "\t\t\t\t}",
          f"\t\t\t\tset_local_variable = {{ name = stl_transport_amount value = {{ value = {read('stl_last_import')} multiply = local_var:stl_distance_factor }} }}"]
    L += [line for line in write("stl_transport", "local_var:stl_transport_amount", 4)]
    L += ["\t\t\t\tvar:stl_trade_depot_ref = {",
          "\t\t\t\t\tadd_modifier = {",
          f"\t\t\t\t\t\tname = stl_transport_{g}",
          "\t\t\t\t\t\tmultiplier = stl_transport_multiplier",
          "\t\t\t\t\t}",
          "\t\t\t\t}",
          "\t\t\t}",
          "\t\t}",
          "\t}"]
    # access % + active goods bookkeeping
    L += ["",
          "\t# ===== sub-pass 3e: access % + active-goods list for the GUI =====",
          "\tmarket = {",
          "\t\tevery_scope_country = {",
          "\t\t\tevery_scope_state = {",
          "\t\t\t\tlimit = {",
          "\t\t\t\t\thas_variable = stl_trade_depot_ref",
          "\t\t\t\t\thas_building = building_stl_trade_depot",
          "\t\t\t\t}",
          "\t\t\t\tif = {",
          f"\t\t\t\t\tlimit = {{ {has('stl_eff_export')} {has('stl_last_export')} {read('stl_eff_export')} > 0.01 }}",
          f"\t\t\t\t\tset_local_variable = {{ name = stl_acc_pct value = {{ value = {read('stl_last_export')} divide = {read('stl_eff_export')} multiply = 100 }} }}",
          "\t\t\t\t\tif = { limit = { local_var:stl_acc_pct > 100 } set_local_variable = { name = stl_acc_pct value = 100 } }",
          "\t\t\t\t\tif = { limit = { NOT = { local_var:stl_acc_pct >= 0 } } set_local_variable = { name = stl_acc_pct value = 0 } }"]
    L += [line for line in write("stl_access_export", "local_var:stl_acc_pct", 5)]
    L += ["\t\t\t\t}",
          "\t\t\t\tif = {",
          f"\t\t\t\t\tlimit = {{ OR = {{ NOT = {{ {has('stl_eff_export')} }} NOT = {{ {has('stl_last_export')} }} }} }}"]
    L += [line for line in remove("stl_access_export", 5)]
    L += ["\t\t\t\t}",
          "\t\t\t\tif = {",
          f"\t\t\t\t\tlimit = {{ {has('stl_eff_import')} {has('stl_last_import')} {read('stl_eff_import')} > 0.01 }}",
          f"\t\t\t\t\tset_local_variable = {{ name = stl_acc_pct value = {{ value = {read('stl_last_import')} divide = {read('stl_eff_import')} multiply = 100 }} }}",
          "\t\t\t\t\tif = { limit = { local_var:stl_acc_pct > 100 } set_local_variable = { name = stl_acc_pct value = 100 } }",
          "\t\t\t\t\tif = { limit = { NOT = { local_var:stl_acc_pct >= 0 } } set_local_variable = { name = stl_acc_pct value = 0 } }"]
    L += [line for line in write("stl_access_import", "local_var:stl_acc_pct", 5)]
    L += ["\t\t\t\t}",
          "\t\t\t\tif = {",
          f"\t\t\t\t\tlimit = {{ OR = {{ NOT = {{ {has('stl_eff_import')} }} NOT = {{ {has('stl_last_import')} }} }} }}"]
    L += [line for line in remove("stl_access_import", 5)]
    L += ["\t\t\t\t}",
          "\t\t\t\t# membership in the GUI's active-goods list",
          "\t\t\t\tif = {",
          "\t\t\t\t\tlimit = {",
          "\t\t\t\t\t\tOR = {",
          f"\t\t\t\t\t\t\t{has('stl_last_export')}",
          f"\t\t\t\t\t\t\t{has('stl_last_import')}",
          "\t\t\t\t\t\t}",
          f"\t\t\t\t\t\tNOT = {{ is_target_in_variable_list = {{ name = stl_active_goods target = flag:{g} }} }}",
          "\t\t\t\t\t}",
          f"\t\t\t\t\tadd_to_variable_list = {{ name = stl_active_goods target = flag:{g} }}",
          "\t\t\t\t}",
          "\t\t\t\tif = {",
          "\t\t\t\t\tlimit = {",
          f"\t\t\t\t\t\tNOT = {{ {has('stl_last_export')} }}",
          f"\t\t\t\t\t\tNOT = {{ {has('stl_last_import')} }}",
          f"\t\t\t\t\t\tis_target_in_variable_list = {{ name = stl_active_goods target = flag:{g} }}",
          "\t\t\t\t\t}",
          f"\t\t\t\t\tremove_list_variable = {{ name = stl_active_goods target = flag:{g} }}",
          "\t\t\t\t}",
          "\t\t\t}",
          "\t\t}",
          "\t}",
          "}", ""]
    write_file("common/scripted_effects/stl_phase_c_generated.txt", "\n".join(L))


# ============================================================
# 7. GUI SCRIPT VALUES (thin readers over storage)
# ============================================================

GUI_METRICS = [
    # (script value suffix, storage container)
    ("surplus",       "stl_eff_export"),
    ("deficit",       "stl_eff_import"),
    ("export",        "stl_last_export"),
    ("import",        "stl_last_import"),
    ("transport",     "stl_transport"),
    ("access_export", "stl_access_export"),
    ("access_import", "stl_access_import"),
    ("market_price",  "stl_market_price"),
    ("local_price",   "stl_price"),
]


def gen_gui_values():
    L = [AUTOGEN,
         "# Thin per-good readers for GUI data binding.",
         "# Scope: state (via GuiScope.SetRoot(...State.MakeScope))",
         "# Bound from gui as: ScriptValue(Concatenate('stl_gui_<metric>_', Goods.GetKey))",
         ""]
    for (suffix, container) in GUI_METRICS:
        L.append(f"# === {suffix} ({container}) ===")
        for g in names():
            L.append(
                f"stl_gui_{suffix}_{g} = {{ value = 0 if = {{ limit = {{ {s_has(container, g)} }} add = {s_read(container, g)} }} }}"
            )
        L.append("")
    # combined per-row metrics so the GUI never does math in brackets
    L.append("# === trade (last_export - last_import, signed) ===")
    for g in names():
        L.append(
            f"stl_gui_trade_{g} = {{ value = 0"
            f" if = {{ limit = {{ {s_has('stl_last_export', g)} }} add = {s_read('stl_last_export', g)} }}"
            f" if = {{ limit = {{ {s_has('stl_last_import', g)} }} subtract = {s_read('stl_last_import', g)} }} }}"
        )
    L.append("")
    L.append("# === target (eff_export - eff_import, signed) ===")
    for g in names():
        L.append(
            f"stl_gui_target_{g} = {{ value = 0"
            f" if = {{ limit = {{ {s_has('stl_eff_export', g)} }} add = {s_read('stl_eff_export', g)} }}"
            f" if = {{ limit = {{ {s_has('stl_eff_import', g)} }} subtract = {s_read('stl_eff_import', g)} }} }}"
        )
    L.append("")
    L.append("# === access (whichever side is active; at most one is) ===")
    for g in names():
        L.append(
            f"stl_gui_access_{g} = {{ value = 0"
            f" if = {{ limit = {{ {s_has('stl_access_export', g)} }} add = {s_read('stl_access_export', g)} }}"
            f" if = {{ limit = {{ {s_has('stl_access_import', g)} }} add = {s_read('stl_access_import', g)} }} }}"
        )
    L.append("")
    write_file("common/script_values/stl_gui_values.txt", "\n".join(L))


# ============================================================
# 8. PARTNER DISPLAY (tooltip builder + per-good scripted GUIs)
# The builder is GOODS-parameterized; the GUI dispatches to the per-good
# scripted GUIs via GetScriptedGui(Concatenate('stl_show_import_', Goods.GetKey))
# (ASE's proven pattern). Reads the Phase B caches through the storage
# helpers; only stl_bf_dist stays a literal map (same-chain use).
# ============================================================

def gen_tooltip():
    g = "$GOODS$"

    def has(m):
        return s_has(m, g)

    def read(m):
        return s_read(m, g)

    L = [AUTOGEN,
         "# Partner breakdown for one good, computed ON CLICK (never on hover).",
         "# Direction comes from var:stl_display_is_import on the depot state",
         "# (set by the per-good scripted GUIs in stl_scripted_guis_generated.txt).",
         "",
         "# Scope: depot state.",
         "stl_build_partner_display_for = {",
         "\tsave_scope_as = stl_depot_state",
         "",
         "\tstl_clear_display_lists = yes",
         "\tset_variable = { name = stl_display_total_wv value = 0 }",
         "\tset_variable = { name = stl_display_partner_count value = 0 }",
         "",
         "\t# origin's network price for this good (no data -> no partners)",
         "\tset_local_variable = { name = stl_origin_mkt value = 0 }",
         "\tif = {",
         f"\t\tlimit = {{ {has('stl_market_price')} }}",
         f"\t\tset_local_variable = {{ name = stl_origin_mkt value = {read('stl_market_price')} }}",
         "\t}",
         "\tif = {",
         "\t\tlimit = { local_var:stl_origin_mkt > 0.01 }",
         "",
         "\t\tstl_run_bellman_ford = yes",
         "",
         "\t\towner = {",
         "\t\t\tmarket = {",
         "\t\t\t\tevery_scope_country = {",
         "\t\t\t\t\tevery_scope_state = {",
         "\t\t\t\t\t\tlimit = {",
         "\t\t\t\t\t\t\thas_variable = stl_trade_depot_ref",
         "\t\t\t\t\t\t\tNOT = { this = scope:stl_depot_state }",
         "\t\t\t\t\t\t\thas_variable = stl_bf_dist",
         "\t\t\t\t\t\t\tNOT = { var:stl_bf_dist >= 100 }",
         f"\t\t\t\t\t\t\t{has('stl_econ')}",
         "\t\t\t\t\t\t}",
         "",
         "\t\t\t\t\t\t# proximity weight (stl_bf_dist is a variable on the partner)",
         "\t\t\t\t\t\tset_local_variable = {",
         "\t\t\t\t\t\t\tname = stl_pw",
         "\t\t\t\t\t\t\tvalue = {",
         "\t\t\t\t\t\t\t\tvalue = 100",
         "\t\t\t\t\t\t\t\tsubtract = var:stl_bf_dist",
         "\t\t\t\t\t\t\t}",
         "\t\t\t\t\t\t}",
         "\t\t\t\t\t\tif = {",
         "\t\t\t\t\t\t\tlimit = { local_var:stl_pw > 0 }",
         "",
         f"\t\t\t\t\t\t\tset_local_variable = {{ name = stl_pp value = {read('stl_price')} }}",
         f"\t\t\t\t\t\t\tset_local_variable = {{ name = stl_pe value = {read('stl_econ')} }}",
         "\t\t\t\t\t\t\tset_local_variable = {",
         "\t\t\t\t\t\t\t\tname = stl_eff",
         "\t\t\t\t\t\t\t\tvalue = {",
         "\t\t\t\t\t\t\t\t\tvalue = local_var:stl_origin_mkt",
         "\t\t\t\t\t\t\t\t\tsubtract = local_var:stl_pp",
         "\t\t\t\t\t\t\t\t\tdivide = local_var:stl_origin_mkt",
         "\t\t\t\t\t\t\t\t\tmultiply = local_var:stl_pe",
         "\t\t\t\t\t\t\t\t}",
         "\t\t\t\t\t\t\t}",
         "",
         "\t\t\t\t\t\t\tset_local_variable = { name = stl_wv value = 0 }",
         "\t\t\t\t\t\t\tif = {",
         "\t\t\t\t\t\t\t\tlimit = {",
         "\t\t\t\t\t\t\t\t\tscope:stl_depot_state = { var:stl_display_is_import >= 1 }",
         "\t\t\t\t\t\t\t\t\tlocal_var:stl_eff > 0",
         "\t\t\t\t\t\t\t\t}",
         "\t\t\t\t\t\t\t\tset_local_variable = { name = stl_wv value = { value = local_var:stl_eff multiply = local_var:stl_pw } }",
         "\t\t\t\t\t\t\t}",
         "\t\t\t\t\t\t\tif = {",
         "\t\t\t\t\t\t\t\tlimit = {",
         "\t\t\t\t\t\t\t\t\tscope:stl_depot_state = { NOT = { var:stl_display_is_import >= 1 } }",
         "\t\t\t\t\t\t\t\t\tNOT = { local_var:stl_eff >= 0 }",
         "\t\t\t\t\t\t\t\t}",
         "\t\t\t\t\t\t\t\tset_local_variable = { name = stl_neg value = { value = 0 subtract = local_var:stl_eff } }",
         "\t\t\t\t\t\t\t\tset_local_variable = { name = stl_wv value = { value = local_var:stl_neg multiply = local_var:stl_pw } }",
         "\t\t\t\t\t\t\t}",
         "",
         "\t\t\t\t\t\t\tif = {",
         "\t\t\t\t\t\t\t\tlimit = { local_var:stl_wv > 0.01 }",
         "\t\t\t\t\t\t\t\tset_variable = { name = stl_display_wv value = local_var:stl_wv }",
         "\t\t\t\t\t\t\t\tset_variable = { name = stl_display_source_price value = local_var:stl_pp }",
         "\t\t\t\t\t\t\t\tset_variable = { name = stl_display_friction value = var:stl_bf_dist }",
         "\t\t\t\t\t\t\t\tset_variable = { name = stl_display_weight value = local_var:stl_pw }",
         "\t\t\t\t\t\t\t\tset_variable = { name = stl_display_has_rail value = 0 }",
         "\t\t\t\t\t\t\t\tif = {",
         "\t\t\t\t\t\t\t\t\tlimit = { has_building = building_railway }",
         "\t\t\t\t\t\t\t\t\tset_variable = { name = stl_display_has_rail value = 1 }",
         "\t\t\t\t\t\t\t\t}",
         "\t\t\t\t\t\t\t\tset_variable = { name = stl_display_has_river value = 0 }",
         "\t\t\t\t\t\t\t\tif = {",
         "\t\t\t\t\t\t\t\t\tlimit = { stl_has_river = yes }",
         "\t\t\t\t\t\t\t\t\tset_variable = { name = stl_display_has_river value = 1 }",
         "\t\t\t\t\t\t\t\t}",
         "\t\t\t\t\t\t\t\tscope:stl_depot_state = {",
         "\t\t\t\t\t\t\t\t\tadd_to_variable_list = { name = stl_display_partners target = prev }",
         "\t\t\t\t\t\t\t\t\tchange_variable = { name = stl_display_total_wv add = prev.var:stl_display_wv }",
         "\t\t\t\t\t\t\t\t\tchange_variable = { name = stl_display_partner_count add = 1 }",
         "\t\t\t\t\t\t\t\t}",
         "\t\t\t\t\t\t\t}",
         "\t\t\t\t\t\t}",
         "\t\t\t\t\t}",
         "\t\t\t\t}",
         "\t\t\t}",
         "\t\t}",
         "",
         "\t\tstl_cleanup_bf_dist = yes",
         "",
         "\t\t# second pass: contribution %",
         "\t\tif = {",
         "\t\t\tlimit = { var:stl_display_total_wv > 0.01 }",
         "\t\t\tevery_in_list = {",
         "\t\t\t\tvariable = stl_display_partners",
         "\t\t\t\tset_variable = {",
         "\t\t\t\t\tname = stl_display_contribution_pct",
         "\t\t\t\t\tvalue = {",
         "\t\t\t\t\t\tvalue = var:stl_display_wv",
         "\t\t\t\t\t\tdivide = scope:stl_depot_state.var:stl_display_total_wv",
         "\t\t\t\t\t\tmultiply = 100",
         "\t\t\t\t\t}",
         "\t\t\t\t}",
         "\t\t\t}",
         "\t\t}",
         "\t}",
         "",
         "\tclear_saved_scope = stl_depot_state",
         "}",
         "",
         "# Remove display data from previous use. Scope: depot state",
         "stl_clear_display_lists = {",
         "\tevery_in_list = {",
         "\t\tvariable = stl_display_partners",
         "\t\tremove_variable = stl_display_wv",
         "\t\tremove_variable = stl_display_source_price",
         "\t\tremove_variable = stl_display_friction",
         "\t\tremove_variable = stl_display_weight",
         "\t\tremove_variable = stl_display_contribution_pct",
         "\t\tremove_variable = stl_display_has_rail",
         "\t\tremove_variable = stl_display_has_river",
         "\t}",
         "\tclear_variable_list = stl_display_partners",
         "}",
         ""]
    write_file("common/scripted_effects/stl_tooltip_generated.txt", "\n".join(L))


def gen_partner_sguis():
    L = [AUTOGEN,
         "# Per-good partner-display scripted GUIs. Bound from the trade window:",
         "#   [GetScriptedGui(Concatenate('stl_show_import_', Goods.GetKey))",
         "#       .Execute(GuiScope.SetRoot(State.MakeScope).End)]",
         ""]
    for g in names():
        for (direction, flag) in (("import", 1), ("export", 0)):
            L += [
                f"stl_show_{direction}_{g} = {{",
                "\tscope = state",
                "\teffect = {",
                f"\t\tset_variable = {{ name = stl_display_is_import value = {flag} }}",
                f"\t\tstl_build_partner_display_for = {{ GOODS = {g} }}",
                "\t}",
                "\tis_shown = { always = yes }",
                "\tis_valid = { always = yes }",
                "\tai_is_valid = { always = no }",
                "}",
                "",
            ]
    write_file("common/scripted_guis/stl_scripted_guis_generated.txt", "\n".join(L))


# ============================================================
# 9. LOCALIZATION
# ============================================================

def gen_localization():
    L = ["l_english:",
         ' building_stl_trade_depot:0 "Trade Depot"',
         ' building_stl_trade_depot_desc:0 "A logistics hub that manages the flow of goods between states via the internal trade network."',
         ' bg_stl_trade_depot:0 "Trade Depots"',
         ' pm_stl_trade_depot_base:0 "Depot Operations"',
         ' pm_stl_trade_depot_exports:0 "Export Handling"',
         ' pm_stl_trade_depot_imports:0 "Import Handling"',
         ' pmg_stl_trade_depot_base:0 "Operations"',
         ' pmg_stl_trade_depot_exports:0 "Exports"',
         ' pmg_stl_trade_depot_imports:0 "Imports"',
         ' stl_export_kill_all:0 "Export Baseline"',
         ' stl_import_kill_all:0 "Import Baseline"',
         ' building_stl_port_hub:0 "Port Hub"',
         ' building_stl_port_hub_desc:0 "A coastal trade hub that maintains full market access, connecting the internal trade network to the world market."',
         ' bg_stl_port_hub:0 "Port Hub"',
         ' pm_stl_port_hub_base:0 "World Market Connection"',
         ' pmg_stl_port_hub_base:0 "Operations"',
         "",
         " # === Trade window ===",
         ' stl_trade_window_title:0 "Internal Trade"',
         ' stl_trade_window_exports:0 "Exports"',
         ' stl_trade_window_imports:0 "Imports"',
         ' stl_trade_window_col_good:0 "Goods"',
         ' stl_trade_window_col_amount:0 "Trade"',
         ' stl_trade_window_col_target:0 "Target"',
         ' stl_trade_window_col_access:0 "Access"',
         ' stl_trade_window_col_local:0 "Local"',
         ' stl_trade_window_col_market:0 "Network"',
         ' stl_trade_window_col_transport:0 "Transport"',
         ' stl_trade_window_no_trade:0 "This state is not currently trading any goods."',
         ' stl_trade_window_open:0 "Open Internal Trade"',
         ' stl_trade_window_refresh:0 "Recalculate trade partners"',
         ' stl_trade_window_partners:0 "Trade Partners"',
         ' stl_trade_window_col_partner:0 "State"',
         ' stl_trade_window_col_friction:0 "Friction"',
         ' stl_trade_window_col_weight:0 "Proximity"',
         ' stl_trade_window_col_price:0 "Price"',
         ' stl_trade_window_col_share:0 "Share"',
         ' stl_trade_window_btn_import_tt:0 "Show where imports of this good come from"',
         ' stl_trade_window_btn_export_tt:0 "Show where exports of this good go"',
         ' stl_trade_window_clear:0 "Clear"',
         "",
         " # === debug decisions ===",
         ' stl_run_probe_decision:0 "Salty Transport: Run Syntax Probe"',
         ' stl_run_probe_decision_desc:0 "Exercises every variable-map operation the mod relies on and writes PASS/FAIL lines to debug.log. Run once per game patch; see ARCHITECTURE_V2.md."',
         ' stl_run_probe_decision_tooltip:0 "Writes STL PROBE results to logs/debug.log"',
         ' stl_toggle_debug_decision:0 "Salty Transport: Toggle Debug Modifiers"',
         ' stl_toggle_debug_decision_desc:0 "Shows diagnostic base/access modifiers on every Trade Depot. Purely informational; applied on the next Phase C day."',
         ' stl_toggle_debug_decision_tooltip:0 "Toggles stl_debug_mode for depot diagnostics"',
         ""]
    for (g, disp, _b, _t, _c, _en) in enabled_goods():
        L.append(f' stl_export_{g}:0 "{disp} Exports"')
    for (g, disp, _b, _t, _c, _en) in enabled_goods():
        L.append(f' stl_import_{g}:0 "{disp} Imports"')
    for (g, disp, _b, _t, _c, _en) in enabled_goods():
        L.append(f' stl_transport_{g}:0 "{disp} Transport"')
    for (g, disp, _b, _t, _c, _en) in enabled_goods():
        L.append(f' stl_debug_base_{g}:0 "DEBUG Base: {disp}"')
    for (g, disp, _b, _t, _c, _en) in enabled_goods():
        L.append(f' stl_debug_access_{g}:0 "DEBUG Access: {disp}"')
    L.append("")
    # loc for the modifier TYPES we define (vanilla pattern: "@coal! Coal input")
    L.append(" # === custom modifier type names ===")
    for (g, disp, _b, _t, _c, _en) in enabled_goods():
        if g not in VANILLA_INPUT_MULT:
            L.append(f' goods_input_{g}_mult:0 "@{g}! {disp} input"')
            L.append(f' goods_input_{g}_mult_desc:0 ""')
    L.append(' goods_input_transportation_mult:0 "@transportation! Transportation input"')
    L.append(' goods_input_transportation_mult_desc:0 ""')
    for (g, disp, _b, _t, _c, _en) in enabled_goods():
        if g not in VANILLA_OUTPUT_MULT:
            L.append(f' goods_output_{g}_mult:0 "@{g}! {disp} output"')
            L.append(f' goods_output_{g}_mult_desc:0 ""')
    for (g, disp, _b, _t, _c, _en) in enabled_goods():
        if g in MISSING_INPUT_ADD:
            L.append(f' goods_input_{g}_add:0 "@{g}! {disp} input"')
            L.append(f' goods_input_{g}_add_desc:0 ""')
    L.append("")
    write_file("localization/english/stl_l_english.yml", "\n".join(L))


# ============================================================
# MAIN
# ============================================================

GENERATORS = [
    gen_goods_modifiers,
    gen_debug_modifiers,
    gen_modifier_types,
    gen_production_methods,
    gen_phase_b,
    gen_phase_c,
    gen_gui_values,
    gen_tooltip,
    gen_partner_sguis,
    gen_localization,
]

CHECK_MODE = False


def main():
    global STORAGE, CHECK_MODE
    p = argparse.ArgumentParser()
    p.add_argument("--storage", choices=["maps", "vars"], default="vars")
    p.add_argument("--check", action="store_true",
                   help="verify generated files match the working tree")
    args = p.parse_args()
    STORAGE = args.storage
    CHECK_MODE = args.check

    print(f"SaltyTransport generator (storage={STORAGE}, goods={len(names())} enabled / {len(GOODS)} total)")
    for gen in GENERATORS:
        gen()

    if CHECK_MODE:
        bad = 0
        for rel, content in _generated.items():
            path = os.path.join(MOD_ROOT, *rel.split("/"))
            try:
                with io.open(path, "r", encoding="utf-8-sig") as f:
                    on_disk = f.read()
            except FileNotFoundError:
                print(f"MISSING: {rel}")
                bad += 1
                continue
            if on_disk != content:
                print(f"STALE: {rel}")
                for line in list(difflib.unified_diff(
                        on_disk.splitlines(), content.splitlines(),
                        fromfile=f"disk/{rel}", tofile=f"gen/{rel}", lineterm=""))[:12]:
                    print(f"  {line}")
                bad += 1
        if bad:
            print(f"--check FAILED: {bad} file(s) out of sync")
            sys.exit(1)
        print("--check OK: all generated files in sync")


if __name__ == "__main__":
    main()
