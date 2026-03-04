#!/usr/bin/env python
"""Generate all per-good files for the SaltyTransport mod.

Run: python tools/generate_goods.py
Outputs 8 files into the mod directory with UTF-8 BOM.
"""

import os

# ============================================================
# MASTER GOODS LIST
# (internal_name, display_name, icon_filename, category)
# Ordered: Staple > Industrial > Military > Luxury
# ============================================================

GOODS = [
    # STAPLE
    ("grain",            "Grain",            "grain.dds",            "staple"),
    ("fish",             "Fish",             "fish.dds",             "staple"),
    ("fabric",           "Fabric",           "fabric.dds",           "staple"),
    ("wood",             "Wood",             "wood.dds",             "staple"),
    ("groceries",        "Groceries",        "groceries.dds",        "staple"),
    ("clothes",          "Clothes",          "clothes.dds",          "staple"),
    ("furniture",        "Furniture",        "furniture.dds",        "staple"),
    ("paper",            "Paper",            "paper.dds",            "staple"),
    ("merchant_marine",  "Merchant Marine",  "merchant_marine.dds",  "staple"),
    # INDUSTRIAL
    ("coal",             "Coal",             "coal.dds",             "industrial"),
    ("iron",             "Iron",             "iron.dds",             "industrial"),
    ("lead",             "Lead",             "lead.dds",             "industrial"),
    ("sulfur",           "Sulfur",           "sulfur.dds",           "industrial"),
    ("hardwood",         "Hardwood",         "hardwood.dds",         "industrial"),
    ("rubber",           "Rubber",           "rubber.dds",           "industrial"),
    ("oil",              "Oil",              "oil.dds",              "industrial"),
    ("silk",             "Silk",             "silk.dds",             "industrial"),
    ("dye",              "Dye",              "dye.dds",              "industrial"),
    ("clippers",         "Clippers",         "clippers.dds",         "industrial"),
    ("steamers",         "Steamers",         "steamers.dds",         "industrial"),
    ("glass",            "Glass",            "glass.dds",            "industrial"),
    ("fertilizer",       "Fertilizer",       "fertilizer.dds",       "industrial"),
    ("tools",            "Tools",            "tools.dds",            "industrial"),
    ("steel",            "Steel",            "steel.dds",            "industrial"),
    ("engines",          "Engines",          "locomotives.dds",      "industrial"),
    ("explosives",       "Explosives",       "explosives.dds",       "industrial"),
    # MILITARY
    ("ammunition",       "Ammunition",       "ammunition.dds",       "military"),
    ("small_arms",       "Small Arms",       "small_arms.dds",       "military"),
    ("artillery",        "Artillery",        "artillery.dds",        "military"),
    ("tanks",            "Tanks",            "tanks.dds",            "military"),
    ("aeroplanes",       "Aeroplanes",       "aeroplanes.dds",       "military"),
    ("manowars",         "Man O' Wars",      "man_o_wars.dds",       "military"),
    ("ironclads",        "Ironclads",        "ironclads.dds",        "military"),
    # LUXURY
    ("meat",             "Meat",             "meat.dds",             "luxury"),
    ("fruit",            "Fruit",            "fruit.dds",            "luxury"),
    ("sugar",            "Sugar",            "sugar.dds",            "luxury"),
    ("tobacco",          "Tobacco",          "tobacco.dds",          "luxury"),
    ("liquor",           "Liquor",           "liquor.dds",           "luxury"),
    ("wine",             "Wine",             "wine.dds",             "luxury"),
    ("tea",              "Tea",              "tea.dds",              "luxury"),
    ("coffee",           "Coffee",           "coffee.dds",           "luxury"),
    ("opium",            "Opium",            "opium.dds",            "luxury"),
    ("porcelain",        "Porcelain",        "porcelain.dds",        "luxury"),
    ("luxury_clothes",   "Luxury Clothes",   "luxury_clothes.dds",   "luxury"),
    ("luxury_furniture", "Luxury Furniture", "luxury_furniture.dds", "luxury"),
    ("automobiles",      "Automobiles",      "automobiles.dds",      "luxury"),
    ("telephones",       "Telephones",       "telephones.dds",       "luxury"),
    ("radios",           "Radios",           "radios.dds",           "luxury"),
    ("fine_art",         "Fine Art",         "fine_art.dds",         "luxury"),
]

# Vanilla-defined modifier types we must NOT redefine
VANILLA_INPUT_MULT = {
    "ammunition", "artillery", "oil", "radios", "small_arms", "tanks",
}
VANILLA_OUTPUT_MULT = {
    "aeroplanes", "ammunition", "artillery", "automobiles", "clippers",
    "engines", "fabric", "fruit", "hardwood", "ironclads", "liquor",
    "manowars", "oil", "radios", "silk", "small_arms", "steamers",
    "sugar", "tanks", "tools", "wine",
}

# Goods missing goods_input_X_add in vanilla (never used as building inputs)
# We must define these ourselves for our production methods
MISSING_INPUT_ADD = {
    "furniture", "tea", "coffee", "porcelain",
    "luxury_clothes", "luxury_furniture", "fine_art",
}

# Vanilla base prices per good (from game defines)
BASE_PRICES = {
    "grain": 20, "fish": 20, "fabric": 20, "wood": 20, "groceries": 30,
    "clothes": 30, "furniture": 30, "paper": 30, "merchant_marine": 50,
    "coal": 30, "iron": 40, "lead": 40, "sulfur": 50, "hardwood": 40,
    "rubber": 40, "oil": 40, "silk": 40, "dye": 40, "clippers": 60,
    "steamers": 70, "glass": 40, "fertilizer": 30, "tools": 40,
    "steel": 50, "engines": 60, "explosives": 50,
    "ammunition": 50, "small_arms": 60, "artillery": 70, "tanks": 80,
    "aeroplanes": 80, "manowars": 70, "ironclads": 80,
    "meat": 30, "fruit": 30, "sugar": 30, "tobacco": 40, "liquor": 30,
    "wine": 50, "tea": 50, "coffee": 50, "opium": 50, "porcelain": 70,
    "luxury_clothes": 60, "luxury_furniture": 60, "automobiles": 100,
    "telephones": 70, "radios": 80, "fine_art": 200,
}

# Vanilla traded_quantity per good (from common/goods/00_goods.txt)
# Amount of good traded per unit of trade capacity
TRADED_QTY = {
    "grain": 12, "fish": 12, "fabric": 10, "wood": 10, "groceries": 9,
    "clothes": 8, "furniture": 8, "paper": 7, "merchant_marine": 4,
    "coal": 7, "iron": 5, "lead": 5, "sulfur": 4, "hardwood": 5,
    "rubber": 5, "oil": 6, "silk": 5, "dye": 5, "clippers": 3.5,
    "steamers": 3.5, "glass": 5, "fertilizer": 7, "tools": 5,
    "steel": 4, "engines": 4, "explosives": 4,
    "ammunition": 5, "small_arms": 4, "artillery": 3.5, "tanks": 3,
    "aeroplanes": 3, "manowars": 3.5, "ironclads": 3.5,
    "meat": 8, "fruit": 8, "sugar": 8, "tobacco": 5, "liquor": 8,
    "wine": 5, "tea": 5, "coffee": 5, "opium": 5, "porcelain": 3.5,
    "luxury_clothes": 4, "luxury_furniture": 4, "automobiles": 3,
    "telephones": 4, "radios": 3.5, "fine_art": 1.5,
}

BOM = "\ufeff"
ICON = "gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds"
MOD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_file(rel_path, content):
    """Write content with UTF-8 BOM to MOD_ROOT/rel_path."""
    path = os.path.join(MOD_ROOT, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(content)
    print(f"  wrote {rel_path} ({len(content.splitlines())} lines)")


def names():
    """Return list of internal good names."""
    return [g[0] for g in GOODS]


# ============================================================
# 1. GOODS MODIFIERS
# ============================================================
def gen_goods_modifiers():
    lines = [
        "# ========================================",
        "# KILL-ALL MODIFIERS",
        "# Applied to every trade depot to zero out all goods flow",
        "# Then per-good enables are stacked on top with multiplier",
        "# ========================================",
        "",
        "# Zeros all export inputs (building buying from local market)",
        "stl_export_kill_all = {",
        f"\ticon = {ICON}",
    ]
    for g in names():
        lines.append(f"\tgoods_input_{g}_mult = -1")
    lines += ["}", ""]

    lines += [
        "# Zeros all import outputs (building selling to local market)",
        "# Also zeros transportation input (PM base = 1, kill-all zeros it)",
        "stl_import_kill_all = {",
        f"\ticon = {ICON}",
    ]
    for g in names():
        lines.append(f"\tgoods_output_{g}_mult = -1")
    lines.append("\tgoods_input_transportation_mult = -1")
    lines += ["}", ""]

    lines += [
        "# ========================================",
        "# PER-GOOD EXPORT ENABLES",
        "# ========================================",
        "",
    ]
    for g in names():
        lines += [
            f"stl_export_{g} = {{",
            f"\ticon = {ICON}",
            f"\tgoods_input_{g}_mult = 1",
            "}",
            "",
        ]

    lines += [
        "# ========================================",
        "# PER-GOOD IMPORT ENABLES",
        "# ========================================",
        "",
    ]
    for g in names():
        lines += [
            f"stl_import_{g} = {{",
            f"\ticon = {ICON}",
            f"\tgoods_output_{g}_mult = 1",
            "}",
            "",
        ]

    lines += [
        "# ========================================",
        "# PER-GOOD TRANSPORT COST MODIFIERS",
        "# Separate from import enables so transport can scale independently.",
        "# Each modifier adds transportation input; applied with multiplier =",
        "# import_volume x distance_factor (from stl_transport_multiplier).",
        "# PM base = 1 transportation (from goods_input_transportation_add = 1 in PM).",
        "# Kill-all zeros it (goods_input_transportation_mult = -1): final = 1x(1-1) = 0.",
        "# Each stl_transport_$GOOD adds back via _add: final = 0 + sum(transport_amounts).",
        "# ========================================",
        "",
    ]
    for g in names():
        lines += [
            f"stl_transport_{g} = {{",
            f"\ticon = {ICON}",
            "\tgoods_input_transportation_add = 1",
            "}",
            "",
        ]

    write_file(r"common\static_modifiers\stl_goods_modifiers.txt", "\n".join(lines))


# ============================================================
# 2. DEBUG MODIFIERS
# ============================================================
def gen_debug_modifiers():
    lines = [
        "# ========================================",
        "# DEBUG MODIFIERS FOR GRAVITY DIAGNOSTICS",
        "# Toggle: effect set_global_variable = { name = stl_debug_mode value = 1 }",
        "# ========================================",
        "",
    ]
    for g in names():
        lines += [
            f"stl_debug_base_{g} = {{",
            f"\ticon = {ICON}",
            "\tbuilding_employment_laborers_add = 0.001",
            "}",
            "",
        ]
    for g in names():
        lines += [
            f"stl_debug_access_{g} = {{",
            f"\ticon = {ICON}",
            "\tbuilding_employment_laborers_add = 0.001",
            "}",
            "",
        ]

    write_file(r"common\static_modifiers\stl_debug_modifiers.txt", "\n".join(lines))


# ============================================================
# 3. MODIFIER TYPE DEFINITIONS
# ============================================================
def gen_modifier_types():
    lines = [
        "# Modifier types not defined in vanilla.",
        "# _mult types needed for kill-all and per-good trade modifiers.",
        "# _add types needed for PM unscaled goods (some missing from vanilla).",
        "",
        "# === goods_input_*_mult (for kill-all) ===",
        "",
    ]
    for g in names():
        if g not in VANILLA_INPUT_MULT:
            lines += [
                f"goods_input_{g}_mult = {{",
                "\tdecimals = 0",
                "\tcolor = bad",
                "\tpercent = yes",
                "\tgame_data = {",
                "\t\tai_value = 0",
                "\t}",
                "}",
                "",
            ]

    # Transportation mult (not defined in vanilla, needed for kill-all)
    lines += [
        "goods_input_transportation_mult = {",
        "\tdecimals = 1",
        "\tcolor = bad",
        "\tpercent = yes",
        "\tgame_data = {",
        "\t\tai_value = 0",
        "\t}",
        "}",
        "",
        "# === goods_output_*_mult ===",
        "",
    ]
    for g in names():
        if g not in VANILLA_OUTPUT_MULT:
            lines += [
                f"goods_output_{g}_mult = {{",
                "\tdecimals = 1",
                "\tcolor = good",
                "\tpercent = yes",
                "\tgame_data = {",
                "\t\tai_value = 0",
                "\t}",
                "}",
                "",
            ]

    # Some goods_input_X_add types are missing from vanilla
    # (goods never used as building inputs in vanilla PMs).
    # We need them for our unscaled PM goods definitions.
    lines += [
        "# === goods_input_*_add (missing from vanilla) ===",
        "",
    ]
    for g in names():
        if g in MISSING_INPUT_ADD:
            lines += [
                f"goods_input_{g}_add = {{",
                "\tdecimals = 1",
                "\tcolor = good",
                "\tgame_data = {",
                "\t\tai_value = 0",
                "\t}",
                "}",
                "",
            ]

    write_file(r"common\modifier_type_definitions\stl_modifier_types.txt", "\n".join(lines))


# ============================================================
# 4. PRODUCTION METHODS
# ============================================================
def gen_production_methods():
    lines = [
        "# Base PM - minimal employment to keep building functional",
        "pm_stl_trade_depot_base = {",
        '\ttexture = "gfx/interface/icons/production_method_icons/merchant_guilds.dds"',
        "\tis_default = yes",
        "\tbuilding_modifiers = {",
        "\t\tworkforce_scaled = {",
        "\t\t\tbuilding_employment_laborers_add = 10",
        "\t\t}",
        "\t}",
        "}",
        "",
        "# Exports PM - building INPUTS goods from local market",
        "# unscaled so base = exactly 1.0 (no workforce ratio amplification)",
        "pm_stl_trade_depot_exports = {",
        '\ttexture = "gfx/interface/icons/production_method_icons/merchant_guilds.dds"',
        "\tis_default = yes",
        "\tbuilding_modifiers = {",
        "\t\tunscaled = {",
    ]
    for g in names():
        lines.append(f"\t\t\tgoods_input_{g}_add = 1")
    lines += [
        "\t\t}",
        "\t}",
        "}",
        "",
        "# Imports PM - building OUTPUTS goods into local market",
        "# unscaled so base = exactly 1.0 (no workforce ratio amplification)",
        "pm_stl_trade_depot_imports = {",
        '\ttexture = "gfx/interface/icons/production_method_icons/merchant_guilds.dds"',
        "\tis_default = yes",
        "\tbuilding_modifiers = {",
        "\t\tunscaled = {",
    ]
    for g in names():
        lines.append(f"\t\t\tgoods_output_{g}_add = 1")
    lines.append("\t\t\tgoods_input_transportation_add = 1")
    lines += [
        "\t\t}",
        "\t}",
        "}",
        "",
    ]

    # === Port Hub PM (restores 100% MAPI in world market hub states) ===
    lines += [
        "# ========================================",
        "# PORT HUB PRODUCTION METHOD",
        "# Restores 100% MAPI in world market hub states",
        "# Counteracts the -5 from urban_planning tech override",
        "# ========================================",
        "",
        "pm_stl_port_hub_base = {",
        '\ttexture = "gfx/interface/icons/production_method_icons/merchant_guilds.dds"',
        "\tis_default = yes",
        "\tstate_modifiers = {",
        "\t\tunscaled = {",
        "\t\t\tstate_market_access_price_impact = 5",
        "\t\t}",
        "\t}",
        "}",
        "",
    ]

    write_file(r"common\production_methods\stl_production_methods.txt", "\n".join(lines))


# ============================================================
# 5. GUI SCRIPT VALUES
# ============================================================
def gen_gui_values():
    sv = lambda var: (
        f"{{ value = 0 if = {{ limit = {{ has_variable = {var} }} add = var:{var} }} }}"
    )
    sv_div = lambda var, d: (
        f"{{ value = 0 if = {{ limit = {{ has_variable = {var} }} add = var:{var} divide = {d} }} }}"
    )

    lines = [
        "# ========================================",
        "# GUI DATA BINDING SCRIPT VALUES",
        "# Scope: state (via GuiScope.SetRoot(Building.GetState.MakeScope))",
        "# ========================================",
        "",
        "# === Per-good: effective export (price-based, from Phase B) ===",
    ]
    for g in names():
        lines.append(f"stl_gui_surplus_{g} = {sv(f'stl_eff_export_{g}')}")
    lines += ["", "# === Per-good: effective import (price-based, from Phase B) ==="]
    for g in names():
        lines.append(f"stl_gui_deficit_{g} = {sv(f'stl_eff_import_{g}')}")
    lines += ["", "# === Per-good: WAS (Weighted Accessible Supply, /100) ==="]
    for g in names():
        lines.append(f"stl_gui_was_{g} = {sv_div(f'stl_was_{g}', 100)}")
    lines += ["", "# === Per-good: WAD (Weighted Accessible Demand, /100) ==="]
    for g in names():
        lines.append(f"stl_gui_wad_{g} = {sv_div(f'stl_wad_{g}', 100)}")
    lines += ["", "# === Per-good: final applied trade amounts ==="]
    for g in names():
        lines.append(f"stl_gui_export_{g} = {sv(f'stl_last_export_{g}')}")
    lines += [""]
    for g in names():
        lines.append(f"stl_gui_import_{g} = {sv(f'stl_last_import_{g}')}")
    lines += ["", "# === Per-good: transport amount (units of transportation consumed) ==="]
    for g in names():
        lines.append(f"stl_gui_transport_{g} = {sv(f'stl_transport_{g}')}")
    lines += ["", "# === Per-good: local price — computed live from GUI-context sg: reads ==="]
    lines.append("# local_price = BASE × (1 + state_goods_pricier)")
    lines.append("# pricier > 0 when above base, < 0 when below. cheaper = -pricier (mirror).")
    lines.append("# These reads ONLY work in script_value/GUI context, NOT in effect context.")
    for g in names():
        bp = BASE_PRICES[g]
        lines.append(
            f"stl_gui_local_price_{g} = {{ value = 1"
            f" sg:{g} = {{ add = state_goods_pricier }}"
            f" multiply = {bp} }}"
        )
    lines += ["", "# === Per-good: market-wide equilibrium price (from buy/sell orders) ==="]
    for g in names():
        lines.append(f"stl_gui_market_price_{g} = {sv(f'stl_market_price_{g}')}")
    lines += ["", "# === Per-good: transport cost = transport_units × transport_price (live) ==="]
    for g in names():
        lines.append(
            f"stl_gui_cost_{g} = {{ value = stl_gui_transport_{g}"
            f" multiply = stl_gui_transport_price }}"
        )
    lines += ["", "# === Per-good: import revenue = (local - avg_source) × qty (live) ==="]
    lines.append("# Buy at weighted avg source price, sell at local price")
    lines.append("# Transport cost tracked separately (stl_gui_cost_X) — not deducted from revenue")
    for g in names():
        lines.append(
            f"stl_gui_revenue_{g} = {{"
            f" value = stl_gui_local_price_{g}"
            f" subtract = stl_gui_weighted_avg_price_{g}"
            f" multiply = stl_gui_import_{g}"
            f" }}"
        )
    lines += ["", "# === Per-good: export revenue = (avg_dest - local) × qty (live) ==="]
    lines.append("# Sell at weighted avg destination price, buy at local price")
    for g in names():
        lines.append(
            f"stl_gui_revenue_export_{g} = {{"
            f" value = stl_gui_weighted_avg_price_export_{g}"
            f" subtract = stl_gui_local_price_{g}"
            f" multiply = stl_gui_export_{g}"
            f" }}"
        )

    # Weighted average market price from trade partners (imports)
    # Falls back to market equilibrium price if tooltip hasn't been triggered yet
    sv_fb = lambda primary, fallback: (
        f"{{ value = 0"
        f" if = {{ limit = {{ has_variable = {primary} }} add = var:{primary} }}"
        f" if = {{ limit = {{ NOT = {{ has_variable = {primary} }} has_variable = {fallback} }} add = var:{fallback} }}"
        f" }}"
    )
    lines += ["", "# === Per-good: weighted avg price from import partners (fallback: market price) ==="]
    for g in names():
        lines.append(f"stl_gui_weighted_avg_price_{g} = {sv_fb(f'stl_weighted_avg_price_{g}', f'stl_market_price_{g}')}")
    lines += ["", "# === Per-good: weighted avg price from export partners (fallback: market price) ==="]
    for g in names():
        lines.append(f"stl_gui_weighted_avg_price_export_{g} = {sv_fb(f'stl_weighted_avg_price_export_{g}', f'stl_market_price_{g}')}")

    lines += ["", "# === Per-good: Access % ==="]
    for g in names():
        lines.append(f"stl_gui_access_pct_export_{g} = {sv(f'stl_access_pct_export_{g}')}")
    lines += [""]
    for g in names():
        lines.append(f"stl_gui_access_pct_import_{g} = {sv(f'stl_access_pct_import_{g}')}")

    # Direct GUI-context reads for price debug tooltip
    lines += ["", "# === Direct GUI-context sg:/mg: reads (for local price tooltip) ==="]
    # state_goods_pricier read directly from sg: scope
    for g in names():
        lines.append(f"stl_gui_direct_pricier_{g} = {{ value = 0 sg:{g} = {{ add = state_goods_pricier }} }}")
    lines += [""]
    # state_goods_cheaper read directly
    for g in names():
        lines.append(f"stl_gui_direct_cheaper_{g} = {{ value = 0 sg:{g} = {{ add = state_goods_cheaper }} }}")
    lines += [""]
    # market_goods_pricier from market scope
    for g in names():
        lines.append(f"stl_gui_direct_mg_pricier_{g} = {{ value = 0 market = {{ mg:{g} = {{ add = market_goods_pricier }} }} }}")
    lines += [""]
    # market_goods_cheaper from market scope
    for g in names():
        lines.append(f"stl_gui_direct_mg_cheaper_{g} = {{ value = 0 market = {{ mg:{g} = {{ add = market_goods_cheaper }} }} }}")

    # Partner count + utility
    lines += [
        "",
        "# === Trade partner count ===",
        "stl_gui_partner_count = { value = 0 if = { limit = { has_variable = stl_partner_count } add = var:stl_partner_count } }",
        "",
        "# === Utility: depot exists ===",
        "stl_gui_has_depot = {",
        "\tvalue = 0",
        "\tif = {",
        "\t\tlimit = { has_variable = stl_trade_depot_ref }",
        "\t\tadd = 1",
        "\t}",
        "}",
        "",
        "# === Section visibility ===",
        "stl_gui_any_import = {",
        "\tvalue = 0",
    ]
    for g in names():
        lines.append(f"\tif = {{ limit = {{ has_variable = stl_eff_import_{g} }} if = {{ limit = {{ var:stl_eff_import_{g} > 0 }} add = 1 }} }}")
    lines += [
        "}",
        "stl_gui_any_export = {",
        "\tvalue = 0",
    ]
    for g in names():
        lines.append(f"\tif = {{ limit = {{ has_variable = stl_eff_export_{g} }} if = {{ limit = {{ var:stl_eff_export_{g} > 0 }} add = 1 }} }}")
    lines += [
        "}",
        "",
        "# === Infrastructure flags ===",
        "stl_gui_has_rail = { value = 0 if = { limit = { has_building = building_railway } add = 1 } }",
        "stl_gui_has_river = { value = 0 if = { limit = { stl_has_river = yes } add = 1 } }",
        "",
        "# ========================================",
        "# TOOLTIP DISPLAY VALUES (partner-state scope)",
        "# ========================================",
        "stl_gui_display_wv = { value = 0 if = { limit = { has_variable = stl_display_wv } add = var:stl_display_wv divide = 100 } }",
        "stl_gui_display_friction = { value = 0 if = { limit = { has_variable = stl_display_friction } add = var:stl_display_friction } }",
        "stl_gui_display_weight = { value = 0 if = { limit = { has_variable = stl_display_weight } add = var:stl_display_weight } }",
        "stl_gui_display_contribution_pct = { value = 0 if = { limit = { has_variable = stl_display_contribution_pct } add = var:stl_display_contribution_pct } }",
        "stl_gui_display_has_rail = { value = 0 if = { limit = { has_variable = stl_display_has_rail } add = var:stl_display_has_rail } }",
        "stl_gui_display_has_river = { value = 0 if = { limit = { has_variable = stl_display_has_river } add = var:stl_display_has_river } }",
        "",
        "# === Tooltip aggregates (depot-state scope) ===",
        "stl_gui_display_partner_count = { value = 0 if = { limit = { has_variable = stl_display_partner_count } add = var:stl_display_partner_count } }",
        "stl_gui_display_is_import = { value = 0 if = { limit = { has_variable = stl_display_is_import } add = var:stl_display_is_import } }",
        "stl_gui_display_contribution_qty = { value = 0 if = { limit = { has_variable = stl_display_contribution_qty } add = var:stl_display_contribution_qty } }",
        "stl_gui_display_source_price = { value = 0 if = { limit = { has_variable = stl_display_source_price } add = var:stl_display_source_price } }",
        "# Good index for tooltip (set by scripted_gui, read by partner price display)",
        "stl_gui_display_good_idx = { value = 0 if = { limit = { has_variable = stl_display_good_idx } add = var:stl_display_good_idx } }",
        "",
        "# === Per-good partner local price (runs on partner state scope in GUI) ===",
    ]
    for idx, g in enumerate(names(), start=1):
        bp = BASE_PRICES[g]
        lines.append(
            f"stl_gui_partner_price_{g} = {{ value = 1"
            f" sg:{g} = {{ add = state_goods_pricier }}"
            f" multiply = {bp} }}"
        )
    lines += [
        "",
        "# Transport cost per partner (stored by tooltip effects)",
        "stl_gui_display_transport = { value = 0 if = { limit = { has_variable = stl_display_transport } add = var:stl_display_transport } }",
        "",
        "# === Transport good local price (live GUI-context, same formula as other goods) ===",
        "stl_gui_transport_price = { value = 1 sg:transportation = { add = state_goods_pricier } multiply = 30 }",
        "",
    ]

    write_file(r"common\script_values\stl_gui_values.txt", "\n".join(lines))


# ============================================================
# 6. SCRIPTED GUIS
# ============================================================
def gen_scripted_guis():
    lines = [
        "# ========================================",
        "# SALTY TRANSPORT - Scripted GUIs",
        "# Triggered by tooltip _show/_hide in trade info panel.",
        "# ========================================",
        "",
        "# ===== IMPORT SHOW =====",
        "",
    ]
    for idx, g in enumerate(names(), start=1):
        bp = BASE_PRICES[g]
        tq = TRADED_QTY[g]
        lines += [
            f"stl_show_import_{g} = {{",
            "\tscope = state",
            "\teffect = {",
            f"\t\tstl_build_import_display = {{ GOODS = {g} BASE = {bp} TQ = {tq} }}",
            f"\t\tset_variable = {{ name = stl_display_good_idx value = {idx} }}",
            "\t}",
            "\tis_shown = { always = yes }",
            "\tis_valid = { always = yes }",
            "\tai_is_valid = { always = no }",
            "}",
            "",
        ]

    lines += [
        "# ===== EXPORT SHOW =====",
        "",
    ]
    for idx, g in enumerate(names(), start=1):
        bp = BASE_PRICES[g]
        lines += [
            f"stl_show_export_{g} = {{",
            "\tscope = state",
            "\teffect = {",
            f"\t\tstl_build_export_display = {{ GOODS = {g} BASE = {bp} }}",
            f"\t\tset_variable = {{ name = stl_display_good_idx value = {idx} }}",
            "\t}",
            "\tis_shown = { always = yes }",
            "\tis_valid = { always = yes }",
            "\tai_is_valid = { always = no }",
            "}",
            "",
        ]

    lines += [
        "# ===== CLEAR =====",
        "",
        "stl_clear_display = {",
        "\tscope = state",
        "\teffect = {",
        "\t\tstl_clear_display_lists = yes",
        "\t}",
        "\tis_shown = { always = yes }",
        "\tis_valid = { always = yes }",
        "\tai_is_valid = { always = no }",
        "}",
        "",
    ]

    write_file(r"common\scripted_guis\stl_scripted_guis.txt", "\n".join(lines))


# ============================================================
# 7. TRADE INFO PANEL GUI
# ============================================================
def _gui_scope(sv_name):
    """Standard GUI scope accessor for a script value."""
    return f"GuiScope.SetRoot(Building.GetState.MakeScope).ScriptValue('{sv_name}')"

def _partner_scope(sv_name):
    """Partner-state scope accessor."""
    return f"GuiScope.SetRoot(State.MakeScope).ScriptValue('{sv_name}')"

def gen_trade_panel():
    L = []  # accumulate lines

    # === Header ===
    L += [
        "# ========================================",
        "# SALTY TRANSPORT - Trade Info Panel v7",
        "#",
        "# Auto-generated by tools/generate_goods.py",
        "# Infrastructure friction + transport cost system, 49 tradeable goods.",
        "# ========================================",
        "",
        "@stl_panel_w = 550",
        "@stl_row_h = 38",
        "@stl_col_good = 130",
        "@stl_col_import = 65",
        "@stl_col_local = 70",
        "@stl_col_market = 75",
        "@stl_col_transport = 70",
        "@stl_col_revenue = 100",
        "",
        "types stl_trade_panel",
        "{",
    ]

    # === Tooltip wrapper types ===
    L.append("\t# =====================================================================")
    L.append("\t# ACCESS TOOLTIP WRAPPER TYPES")
    L.append("\t# =====================================================================")
    L.append("")

    for g in names():
        for direction in ("import", "export"):
            L.append(f"\ttype stl_tt_{direction}_{g} = TooltipWidgetType {{")
            L.append(f'\t\tstate = {{ name = _show on_start = "[GetScriptedGui(\'stl_show_{direction}_{g}\').Execute(GuiScope.SetRoot(Building.GetState.MakeScope).End)]" }}')
            L.append(f'\t\tstate = {{ name = _hide on_start = "[GetScriptedGui(\'stl_clear_display\').Execute(GuiScope.SetRoot(Building.GetState.MakeScope).End)]" }}')
            L.append('\t\tblockoverride "tooltip_content_after" { stl_access_tooltip_body = {} }')
            L.append("\t}")
        L.append("")

    # === Shared access tooltip body ===
    L += [
        "\t# =====================================================================",
        "\t# SHARED ACCESS TOOLTIP BODY",
        "\t# =====================================================================",
        "",
        "\ttype stl_access_tooltip_body = flowcontainer {",
        "\t\tdirection = vertical",
        "\t\tminimumsize = { 420 0 }",
        "\t\tmaximumsize = { 440 2000 }",
        "\t\tmargin = { 8 4 }",
        "\t\tspacing = 4",
        "",
        "\t\t# Header",
        "\t\tflowcontainer = {",
        "\t\t\tdirection = vertical",
        "\t\t\tspacing = 2",
        "\t\t\ttextbox = {",
        f'\t\t\t\tvisible = "[GreaterThan_CFixedPoint({_gui_scope("stl_gui_display_is_import")}, \'(CFixedPoint)0\')]"',
        '\t\t\t\traw_text = "#bold Trade Partners — Supply Access#!"',
        "\t\t\t\tautoresize = yes",
        "\t\t\t\tfontsize = 16",
        "\t\t\t}",
        "\t\t\ttextbox = {",
        f'\t\t\t\tvisible = "[Not(GreaterThan_CFixedPoint({_gui_scope("stl_gui_display_is_import")}, \'(CFixedPoint)0\'))]"',
        '\t\t\t\traw_text = "#bold Trade Partners — Demand Access#!"',
        "\t\t\t\tautoresize = yes",
        "\t\t\t\tfontsize = 16",
        "\t\t\t}",
        "\t\t\ttextbox = {",
        f'\t\t\t\traw_text = "[{_gui_scope("stl_gui_display_partner_count")}|v0] partners connected"',
        "\t\t\t\tautoresize = yes",
        "\t\t\t\tfontsize = 13",
        "\t\t\t\tfontcolor = { 0.7 0.7 0.6 1 }",
        "\t\t\t\tmargin_bottom = 2",
        "\t\t\t}",
        "\t\t}",
        "",
        "\t\t# Column headers",
        "\t\tflowcontainer = {",
        "\t\t\tdirection = horizontal",
        "\t\t\tspacing = 4",
        '\t\t\ttextbox = { raw_text = "#bold State#!" size = { 110 20 } fontsize = 13 fontcolor = { 0.6 0.6 0.5 1 } }',
        '\t\t\ttextbox = { raw_text = "#bold Qty#!" size = { 45 20 } align = right|nobaseline fontsize = 13 fontcolor = { 0.6 0.6 0.5 1 } }',
        '\t\t\ttextbox = { raw_text = "#bold Share#!" size = { 50 20 } align = right|nobaseline fontsize = 13 fontcolor = { 0.6 0.6 0.5 1 } }',
        '\t\t\ttextbox = { raw_text = "#bold Price#!" size = { 50 20 } align = right|nobaseline fontsize = 13 fontcolor = { 0.6 0.6 0.5 1 } }',
        f'\t\t\ttextbox = {{ visible = "[GreaterThan_CFixedPoint({_gui_scope("stl_gui_display_is_import")}, \'(CFixedPoint)0\')]" raw_text = "#bold Transport#!" size = {{ 60 20 }} align = right|nobaseline fontsize = 13 fontcolor = {{ 0.6 0.6 0.5 1 }} }}',
        '\t\t\ttextbox = { raw_text = "#bold Proximity#!" size = { 60 20 } align = right|nobaseline fontsize = 13 fontcolor = { 0.6 0.6 0.5 1 } }',
        "\t\t}",
        "",
        "\t\t# Partner list",
        '\t\tdynamicgridbox = {',
        '\t\t\tdatamodel = "[Building.GetState.MakeScope.GetList(\'stl_display_partners\')]"',
        "\t\t\titem = {",
        "\t\t\t\tflowcontainer = {",
        '\t\t\t\t\tdatacontext = "[Scope.GetState]"',
        "\t\t\t\t\tdirection = horizontal",
        "\t\t\t\t\tspacing = 4",
        "\t\t\t\t\tmargin_left = 2",
        '\t\t\t\t\ttextbox = { raw_text = "[State.GetName]" size = { 110 20 } fontsize = 14 elide = right }',
    ]

    # Contribution qty + % with color + source price + transport + friction
    ps = _partner_scope
    L += [
        f'\t\t\t\t\ttextbox = {{ raw_text = "[{ps("stl_gui_display_contribution_qty")}|v1]" size = {{ 45 20 }} align = right|nobaseline fontsize = 14 }}',
        f'\t\t\t\t\ttextbox = {{ visible = "[GreaterThan_CFixedPoint({ps("stl_gui_display_contribution_pct")}, \'(CFixedPoint)4.9\')]" raw_text = "#G [{ps("stl_gui_display_contribution_pct")}|1]%#!" size = {{ 50 20 }} align = right|nobaseline fontsize = 14 }}',
        f'\t\t\t\t\ttextbox = {{ visible = "[And(GreaterThan_CFixedPoint({ps("stl_gui_display_contribution_pct")}, \'(CFixedPoint)0.9\'), Not(GreaterThan_CFixedPoint({ps("stl_gui_display_contribution_pct")}, \'(CFixedPoint)4.9\')))]" raw_text = "#Y [{ps("stl_gui_display_contribution_pct")}|1]%#!" size = {{ 50 20 }} align = right|nobaseline fontsize = 14 }}',
        f'\t\t\t\t\ttextbox = {{ visible = "[Not(GreaterThan_CFixedPoint({ps("stl_gui_display_contribution_pct")}, \'(CFixedPoint)0.9\'))]" raw_text = "#R [{ps("stl_gui_display_contribution_pct")}|1]%#!" size = {{ 50 20 }} align = right|nobaseline fontsize = 14 }}',
        # Per-good partner local price (only the matching good is visible)
        "\t\t\t\t\twidget = {",
        "\t\t\t\t\t\tsize = { 50 20 }",
    ]
    gs = _gui_scope  # depot state scope for reading good_idx
    for idx, g in enumerate(names(), start=1):
        bp = BASE_PRICES[g]
        L.append(
            f'\t\t\t\t\t\ttextbox = {{ visible = "[EqualTo_CFixedPoint({gs("stl_gui_display_good_idx")}, \'(CFixedPoint){idx}\')]"'
            f' raw_text = "@money![{ps(f"stl_gui_partner_price_{g}")}|v1]"'
            f' size = {{ 50 20 }} align = right|nobaseline fontsize = 14 }}'
        )
    L += [
        "\t\t\t\t\t}",
        f'\t\t\t\t\ttextbox = {{ visible = "[GreaterThan_CFixedPoint({_gui_scope("stl_gui_display_is_import")}, \'(CFixedPoint)0\')]" raw_text = "[{ps("stl_gui_display_transport")}|0]" size = {{ 60 20 }} align = right|nobaseline fontsize = 14 }}',
        f'\t\t\t\t\ttextbox = {{ raw_text = "[{ps("stl_gui_display_friction")}|1]" size = {{ 60 20 }} align = right|nobaseline fontsize = 14 fontcolor = {{ 0.7 0.7 0.6 1 }} }}',
    ]

    L += [
        "\t\t\t\t}",
        "\t\t\t}",
        "\t\t}",
        "",
        "\t\t# Legend",
        "\t\twidget = { size = { 5 4 } }",
        f'\t\ttextbox = {{ visible = "[GreaterThan_CFixedPoint({_gui_scope("stl_gui_display_is_import")}, \'(CFixedPoint)0\')]" raw_text = "#i Transport = Qty x Proximity  |  Lower = better path#!" autoresize = yes fontsize = 12 fontcolor = {{ 0.6 0.6 0.5 1 }} }}',
        "\t}",
        "",
    ]

    # === Main panel type ===
    L += [
        "\t# =====================================================================",
        "\t# MAIN PANEL",
        "\t# =====================================================================",
        "",
        "\ttype stl_trade_info_section = flowcontainer {",
        "\t\tdirection = vertical",
        "\t\tusing = default_list_position",
        "\t\tminimumsize = { @stl_panel_w 0 }",
        "\t\tmargin_bottom = 10",
        "",
        "\t\t# Header: Trade Distribution",
        "\t\tdefault_header_2texts = {",
        '\t\t\tblockoverride "text1" { text = "STL_TRADE_DISTRIBUTION" }',
        '\t\t\tblockoverride "right" {',
        "\t\t\t\tflowcontainer = {",
        "\t\t\t\t\tparentanchor = right|vcenter",
        "\t\t\t\t\tmargin_right = 15",
        "\t\t\t\t\tspacing = 5",
        '\t\t\t\t\ttextbox = { text = "STL_NETWORK_SUMMARY" autoresize = yes fontsize = 16 fontcolor = { 0.7 0.7 0.6 1 } }',
        f'\t\t\t\t\ttextbox = {{ raw_text = "#bold [{_gui_scope("stl_gui_partner_count")}|v0]#! partners" autoresize = yes fontsize = 16 }}',
        "\t\t\t\t}",
        "\t\t\t}",
        "\t\t}",
        "",
    ]

    # === IMPORTS SECTION ===
    _gen_section(L, "import", "deficit", "stl_gui_any_import", "stl_imports_expanded",
                 "STL_SECTION_IMPORTS", "Import", "#R")

    # === EXPORTS SECTION ===
    _gen_section(L, "export", "surplus", "stl_gui_any_export", "stl_exports_expanded",
                 "STL_SECTION_EXPORTS", "Export", "#G")

    # Close panel and types
    L += ["\t}", "}",  ""]

    write_file(r"gui\stl_trade_info_panel.gui", "\n".join(L))


def _gen_section(L, direction, base_var, any_sv, toggle_var, section_loc, calc_label, trade_color):
    """Generate an Imports or Exports section with per-good cards.

    Import columns: Good | Import | Local £ | Mkt £ | Transport | Revenue
    Export columns: Good | Export | Local £ | Mkt £ | Revenue
    """
    gs = _gui_scope
    is_import = direction == "import"

    L += [
        f"\t\t# ===== {'IMPORTS' if is_import else 'EXPORTS'} SECTION =====",
        "\t\tflowcontainer = {",
        "\t\t\tdirection = vertical",
        f'\t\t\tvisible = "[GreaterThan_CFixedPoint({gs(any_sv)}, \'(CFixedPoint)0\')]"',
        "",
        "\t\t\tsection_header_button = {",
        "\t\t\t\tparentanchor = right",
        "\t\t\t\tposition = { 0 2 }",
        "\t\t\t\tsize = { @stl_panel_w 38 }",
        f'\t\t\t\tblockoverride "left_text" {{ text = "{section_loc}" }}',
        f'\t\t\t\tblockoverride "onclick" {{ onclick = "[GetVariableSystem.Toggle(\'{toggle_var}\')]" }}',
        f'\t\t\t\tblockoverride "onclick_showmore" {{ visible = "[Not(GetVariableSystem.Exists(\'{toggle_var}\'))]" }}',
        f'\t\t\t\tblockoverride "onclick_showless" {{ visible = "[GetVariableSystem.Exists(\'{toggle_var}\')]" }}',
        "\t\t\t}",
        "",
        "\t\t\tflowcontainer = {",
        f'\t\t\t\tvisible = "[GetVariableSystem.Exists(\'{toggle_var}\')]"',
        "\t\t\t\tdirection = vertical",
        "\t\t\t\tmargin = { 8 4 }",
        "\t\t\t\tspacing = 2",
        "",
        "\t\t\t\t# Column headers",
        "\t\t\t\tflowcontainer = {",
        "\t\t\t\t\tdirection = horizontal",
        "\t\t\t\t\tminimumsize = { @stl_panel_w 24 }",
        "\t\t\t\t\tspacing = 4",
        "\t\t\t\t\tmargin_left = 4",
        '\t\t\t\t\ttextbox = { text = "STL_COL_GOOD" size = { @stl_col_good 24 } fontsize = 14 fontcolor = { 0.7 0.7 0.6 1 } }',
        f'\t\t\t\t\ttextbox = {{ text = "STL_HEADER_{"IMPORT" if is_import else "EXPORT"}" size = {{ @stl_col_import 24 }} align = right|nobaseline fontsize = 14 fontcolor = {{ 0.7 0.7 0.6 1 }} }}',
        '\t\t\t\t\ttextbox = { text = "STL_HEADER_LOCAL_PRICE" size = { @stl_col_local 24 } align = right|nobaseline fontsize = 14 fontcolor = { 0.7 0.7 0.6 1 } }',
        '\t\t\t\t\ttextbox = { text = "STL_HEADER_MARKET_PRICE" size = { @stl_col_market 24 } align = right|nobaseline fontsize = 14 fontcolor = { 0.7 0.7 0.6 1 } }',
    ]
    if is_import:
        L.append('\t\t\t\t\ttextbox = { text = "STL_HEADER_TRANSPORT" size = { @stl_col_transport 24 } align = right|nobaseline fontsize = 14 fontcolor = { 0.7 0.7 0.6 1 } }')
    L.append('\t\t\t\t\ttextbox = { text = "STL_HEADER_REVENUE" size = { @stl_col_revenue 24 } align = right|nobaseline fontsize = 14 fontcolor = { 0.7 0.7 0.6 1 } }')
    L += [
        "\t\t\t\t}",
        "",
    ]

    # Per-good cards
    for g_name, g_display, g_icon, g_cat in GOODS:
        sv_base = f"stl_gui_{base_var}_{g_name}"
        sv_access = f"stl_gui_access_pct_{direction}_{g_name}"
        sv_trade = f"stl_gui_{direction}_{g_name}"
        sv_transport = f"stl_gui_transport_{g_name}"
        sv_revenue = f"stl_gui_revenue_{g_name}" if is_import else f"stl_gui_revenue_export_{g_name}"
        sv_local_price = f"stl_gui_local_price_{g_name}"
        sv_market_price = f"stl_gui_weighted_avg_price_{g_name}" if is_import else f"stl_gui_weighted_avg_price_export_{g_name}"
        sv_market_price_fallback = f"stl_gui_market_price_{g_name}"
        tt_type = f"stl_tt_{direction}_{g_name}"

        L.append(f"\t\t\t\t### {g_display.upper()} {'IMPORT' if is_import else 'EXPORT'} CARD")
        L.append(f"\t\t\t\tbutton = {{")
        L.append(f"\t\t\t\t\tsize = {{ @stl_panel_w @stl_row_h }}")
        L.append(f'\t\t\t\t\tvisible = "[GreaterThan_CFixedPoint({gs(sv_base)}, \'(CFixedPoint)0\')]"')
        L.append(f"\t\t\t\t\tusing = default_button")
        L.append(f'\t\t\t\t\tonclick = "[InformationPanelBar.OpenGoodsStatePanel(Building.GetState, GetGoods(\'{g_name}\'))]"')
        L.append(f"\t\t\t\t\tusing = select_button_sound")
        L.append(f"\t\t\t\t\tflowcontainer = {{")
        L.append(f"\t\t\t\t\t\tdirection = horizontal")
        L.append(f"\t\t\t\t\t\tparentanchor = vcenter")
        L.append(f"\t\t\t\t\t\tspacing = 4")
        L.append(f"\t\t\t\t\t\tmargin_left = 4")

        # ---- Good column ----
        L.append(f"\t\t\t\t\t\twidget = {{")
        L.append(f"\t\t\t\t\t\t\tsize = {{ @stl_col_good 34 }}")
        L.append(f"\t\t\t\t\t\t\ttextbox = {{ raw_text = \"#bold [GetGoods('{g_name}').GetName]#!\" size = {{ @stl_col_good 34 }} parentanchor = vcenter fontsize = 17 align = left|nobaseline elide = right }}")
        L.append(f"\t\t\t\t\t\t}}")

        # ---- Import/Export amount column ----
        L.append(f"\t\t\t\t\t\twidget = {{")
        L.append(f"\t\t\t\t\t\t\tsize = {{ @stl_col_import 34 }}")
        L.append(f'\t\t\t\t\t\t\ttooltipwidget = {{ {tt_type} = {{}} }}')
        L.append(f'\t\t\t\t\t\t\ttextbox = {{ raw_text = "{trade_color} #bold [{gs(sv_trade)}|v1]#!#!" parentanchor = right|vcenter autoresize = yes fontsize = 17 }}')
        L.append(f"\t\t\t\t\t\t}}")

        # ---- Local Price column (with debug tooltip) ----
        bp = BASE_PRICES[g_name]
        sv_dir_pricier = f"stl_gui_direct_pricier_{g_name}"
        sv_dir_cheaper = f"stl_gui_direct_cheaper_{g_name}"
        sv_market = f"stl_gui_market_price_{g_name}"
        local_tt = (
            f'flowcontainer = {{ direction = vertical margin = {{ 8 6 }} minimumsize = {{ 320 0 }} spacing = 2 '
            f'textbox = {{ raw_text = "#bold Local Price: [GetGoods(\'{g_name}\').GetName]#!" autoresize = yes fontsize = 16 }} '
            f'widget = {{ size = {{ 5 4 }} }} '
            f'textbox = {{ raw_text = "#bold Formula:#! BASE × (1 + pricier)" autoresize = yes fontsize = 14 }} '
            f'textbox = {{ raw_text = "  base = {bp}  pricier = [{gs(sv_dir_pricier)}|3]" autoresize = yes fontsize = 13 fontcolor = {{ 0.7 0.7 0.6 1 }} }} '
            f'textbox = {{ raw_text = "  = {bp} × (1 + [{gs(sv_dir_pricier)}|3])" autoresize = yes fontsize = 13 fontcolor = {{ 0.7 0.7 0.6 1 }} }} '
            f'textbox = {{ raw_text = "  = @money![{gs(sv_local_price)}|v3]" autoresize = yes fontsize = 15 }} '
            f'widget = {{ size = {{ 5 4 }} }} '
            f'textbox = {{ raw_text = "#bold Market price#! (buy/sell equilibrium):" autoresize = yes fontsize = 14 }} '
            f'textbox = {{ raw_text = "  = @money![{gs(sv_market)}|v3]" autoresize = yes fontsize = 14 }} '
            f'}}'
        )
        L.append(f'\t\t\t\t\t\twidget = {{')
        L.append(f"\t\t\t\t\t\t\tsize = {{ @stl_col_local 34 }}")
        L.append(f'\t\t\t\t\t\t\ttooltipwidget = {{ TooltipWidgetType = {{ blockoverride "tooltip_content_after" {{ {local_tt} }} }} }}')
        L.append(f'\t\t\t\t\t\t\ttextbox = {{ raw_text = "@money![{gs(sv_local_price)}|v1]" parentanchor = right|vcenter autoresize = yes fontsize = 17 }}')
        L.append(f"\t\t\t\t\t\t}}")

        # ---- Market Price column (weighted avg of trade partner prices) ----
        mkt_tt_label = "import sources" if is_import else "export destinations"
        L.append(f'\t\t\t\t\t\twidget = {{')
        L.append(f"\t\t\t\t\t\t\tsize = {{ @stl_col_market 34 }}")
        L.append(f'\t\t\t\t\t\t\ttooltipwidget = {{ TooltipWidgetType = {{ blockoverride "tooltip_content_after" {{ flowcontainer = {{ direction = vertical margin = {{ 8 4 }} minimumsize = {{ 280 0 }} spacing = 2 textbox = {{ raw_text = "#bold Weighted Avg Source Price#!" autoresize = yes fontsize = 16 }} textbox = {{ raw_text = "Average of local prices across {mkt_tt_label}, weighted by production share and proximity." autoresize = yes fontsize = 14 }} textbox = {{ raw_text = "Closer partners with more surplus have more influence." autoresize = yes fontsize = 13 fontcolor = {{ 0.6 0.6 0.5 1 }} }} textbox = {{ raw_text = "Hover the quantity column to refresh from current partner data." autoresize = yes fontsize = 13 fontcolor = {{ 0.6 0.6 0.5 1 }} }} }} }} }} }}')
        L.append(f'\t\t\t\t\t\t\ttextbox = {{ raw_text = "@money![{gs(sv_market_price)}|v1]" parentanchor = right|vcenter autoresize = yes fontsize = 17 }}')
        L.append(f"\t\t\t\t\t\t}}")

        # ---- Transport column (imports only, with transportation icon) ----
        if is_import:
            L.append(f"\t\t\t\t\t\twidget = {{")
            L.append(f"\t\t\t\t\t\t\tsize = {{ @stl_col_transport 34 }}")
            L.append(f'\t\t\t\t\t\t\ttooltipwidget = {{ TooltipWidgetType = {{ blockoverride "tooltip_content_after" {{ flowcontainer = {{ direction = vertical margin = {{ 8 6 }} minimumsize = {{ 280 0 }} spacing = 2 textbox = {{ raw_text = "#bold Transport: [GetGoods(\'{g_name}\').GetName]#!" autoresize = yes fontsize = 16 }} widget = {{ size = {{ 5 4 }} }} textbox = {{ raw_text = "Import amount: #bold [{gs(sv_trade)}|v1]#!" autoresize = yes fontsize = 15 }} textbox = {{ raw_text = "Distance factor: max_WAS / WAS" autoresize = yes fontsize = 14 fontcolor = {{ 0.7 0.7 0.6 1 }} }} textbox = {{ raw_text = "Transport = Import x Distance Factor" autoresize = yes fontsize = 14 fontcolor = {{ 0.7 0.7 0.6 1 }} }} widget = {{ size = {{ 5 4 }} }} textbox = {{ raw_text = "#bold Result: [{gs(sv_transport)}|v1] units#!" autoresize = yes fontsize = 16 }} }} }} }} }}')
            L.append(f"\t\t\t\t\t\t\tflowcontainer = {{")
            L.append(f"\t\t\t\t\t\t\t\tparentanchor = right|vcenter")
            L.append(f"\t\t\t\t\t\t\t\tdirection = horizontal")
            L.append(f"\t\t\t\t\t\t\t\tspacing = 2")
            L.append(f'\t\t\t\t\t\t\t\ticon = {{ texture = "gfx/interface/icons/goods_icons/transportation.dds" size = {{ 20 20 }} parentanchor = vcenter }}')
            L.append(f'\t\t\t\t\t\t\t\ttextbox = {{ raw_text = "#Y [{gs(sv_transport)}|v1]#!" parentanchor = vcenter autoresize = yes fontsize = 17 }}')
            L.append(f"\t\t\t\t\t\t\t}}")
            L.append(f"\t\t\t\t\t\t}}")

        # ---- Revenue column (both imports and exports) ----
        if is_import:
            rev_tooltip = f'flowcontainer = {{ direction = vertical margin = {{ 8 4 }} minimumsize = {{ 300 0 }} spacing = 2 textbox = {{ raw_text = "#bold Import Revenue#!" autoresize = yes fontsize = 16 }} widget = {{ size = {{ 5 3 }} }} textbox = {{ raw_text = "Local Price: @money![{gs(sv_local_price)}|v1]" autoresize = yes fontsize = 15 }} textbox = {{ raw_text = "Avg Source Price: @money![{gs(sv_market_price)}|v1]" autoresize = yes fontsize = 15 }} textbox = {{ raw_text = "Import Qty: [{gs(sv_trade)}|v1]" autoresize = yes fontsize = 15 }} widget = {{ size = {{ 5 3 }} }} textbox = {{ raw_text = "Qty x (LocalPrice - AvgSourcePrice)" autoresize = yes fontsize = 13 fontcolor = {{ 0.7 0.7 0.6 1 }} }} }}'
        else:
            rev_tooltip = f'flowcontainer = {{ direction = vertical margin = {{ 8 4 }} minimumsize = {{ 300 0 }} spacing = 2 textbox = {{ raw_text = "#bold Export Revenue#!" autoresize = yes fontsize = 16 }} widget = {{ size = {{ 5 3 }} }} textbox = {{ raw_text = "Avg Dest Price: @money![{gs(sv_market_price)}|v1]" autoresize = yes fontsize = 15 }} textbox = {{ raw_text = "Local Price: @money![{gs(sv_local_price)}|v1]" autoresize = yes fontsize = 15 }} textbox = {{ raw_text = "Export Qty: [{gs(sv_trade)}|v1]" autoresize = yes fontsize = 15 }} widget = {{ size = {{ 5 3 }} }} textbox = {{ raw_text = "(Qty x AvgDestPrice) - (Qty x LocalPrice)" autoresize = yes fontsize = 13 fontcolor = {{ 0.7 0.7 0.6 1 }} }} }}'
        L.append(f"\t\t\t\t\t\twidget = {{")
        L.append(f"\t\t\t\t\t\t\tsize = {{ @stl_col_revenue 34 }}")
        L.append(f'\t\t\t\t\t\t\ttooltipwidget = {{ TooltipWidgetType = {{ blockoverride "tooltip_content_after" {{ {rev_tooltip} }} }} }}')
        # Green if positive, red if zero or negative
        L.append(f'\t\t\t\t\t\t\ttextbox = {{ visible = "[GreaterThan_CFixedPoint({gs(sv_revenue)}, \'(CFixedPoint)0\')]" raw_text = "#G +@money![{gs(sv_revenue)}|v1]#!" parentanchor = right|vcenter autoresize = yes fontsize = 17 }}')
        L.append(f'\t\t\t\t\t\t\ttextbox = {{ visible = "[Not(GreaterThan_CFixedPoint({gs(sv_revenue)}, \'(CFixedPoint)0\'))]" raw_text = "#R @money![{gs(sv_revenue)}|v1]#!" parentanchor = right|vcenter autoresize = yes fontsize = 17 }}')
        L.append(f"\t\t\t\t\t\t}}")

        # Close flowcontainer + button
        L.append(f"\t\t\t\t\t}}")
        L.append(f"\t\t\t\t}}")
        L.append("")

    # Close inner flowcontainer, outer flowcontainer
    L += ["\t\t\t}", "\t\t}", ""]


# ============================================================
# 8. LOCALIZATION
# ============================================================
def gen_localization():
    lines = [
        "l_english:",
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
        # Port Hub loc keys
        ' building_stl_port_hub:0 "Port Hub"',
        ' building_stl_port_hub_desc:0 "A coastal trade hub that maintains full market access, connecting the internal trade network to the world market."',
        ' bg_stl_port_hub:0 "Port Hub"',
        ' pm_stl_port_hub_base:0 "World Market Connection"',
        ' pmg_stl_port_hub_base:0 "Operations"',
    ]

    # Per-good export/import/transport modifiers
    for g_name, g_display, _, _ in GOODS:
        lines.append(f' stl_export_{g_name}:0 "{g_display} Exports"')
    for g_name, g_display, _, _ in GOODS:
        lines.append(f' stl_import_{g_name}:0 "{g_display} Imports"')
    for g_name, g_display, _, _ in GOODS:
        lines.append(f' stl_transport_{g_name}:0 "{g_display} Transport"')

    # Debug modifiers
    for g_name, g_display, _, _ in GOODS:
        lines.append(f' stl_debug_base_{g_name}:0 "[DBG] {g_display} Base Trade"')
    for g_name, g_display, _, _ in GOODS:
        lines.append(f' stl_debug_access_{g_name}:0 "[DBG] {g_display} Gravity Access"')

    # UI labels
    lines += [
        ' STL_TRADE_DISTRIBUTION:0 "Trade Distribution"',
        ' STL_HEADER_ROLE:0 "Role"',
        ' STL_HEADER_AMOUNT:0 "Amount"',
        ' STL_HEADER_IMPORT:0 "Import"',
        ' STL_HEADER_EXPORT:0 "Export"',
        ' STL_HEADER_LOCAL_PRICE:0 "Local £"',
        ' STL_HEADER_MARKET_PRICE:0 "Mkt £"',
        ' STL_HEADER_TRANSPORT:0 "Transport"',
        ' STL_HEADER_REVENUE:0 "Revenue"',
        ' STL_HEADER_ACCESS:0 "Access"',
        ' STL_HEADER_BASE:0 "Base"',
        ' STL_HEADER_TRADE:0 "Trade"',
        ' STL_ROLE_EXPORT:0 "Export"',
        ' STL_ROLE_IMPORT:0 "Import"',
        ' STL_ROLE_EXPORT_TT:0 "This state produces more than it consumes. The surplus is exported to other states via gravity-weighted distribution."',
        ' STL_ROLE_IMPORT_TT:0 "This state consumes more than it produces. The deficit is filled by imports from other states via gravity-weighted distribution."',
        ' STL_SECTION_IMPORTS:0 "Imports"',
        ' STL_SECTION_EXPORTS:0 "Exports"',
        ' STL_SECTION_IMPORTS_TT:0 "Goods this state consumes more than it produces. Deficit is filled by gravity-weighted imports from trade partners."',
        ' STL_SECTION_EXPORTS_TT:0 "Goods this state produces more than it consumes. Surplus is exported via gravity-weighted distribution to trade partners."',
        ' STL_COL_GOOD:0 "Good"',
        ' STL_NETWORK_SUMMARY:0 "Network:"',
        ' STL_ACCESS_TT:0 "Access shows what percentage of your base trade need is fulfilled by connected partners. Proximity is based on infrastructure friction along the best path — railways, rivers and ports reduce friction. Green (75%+) = well-connected, Yellow (50-74%) = moderate, Red (<50%) = poorly connected."',
    ]

    write_file(r"localization\english\stl_l_english.yml", "\n".join(lines))


# ============================================================
# MAIN
# ============================================================
def main():
    print(f"Generating files into: {MOD_ROOT}")
    print(f"Goods count: {len(GOODS)}")
    print()

    gen_goods_modifiers()
    gen_debug_modifiers()
    gen_modifier_types()
    gen_production_methods()
    gen_gui_values()
    gen_scripted_guis()
    gen_trade_panel()
    gen_localization()

    gen_phase_b_effects()

    print()
    print("Done!")


# ============================================================
# 9. PHASE B GENERATED EFFECTS
# ============================================================
def gen_phase_b_effects():
    """Generate Phase B inner-loop effects for effective_surplus model.

    Production-weighted market price:
      market_price = sum(production × local_price) / sum(production)
      Includes all reachable partners + origin state.
      Consumption affects prices implicitly via buy/sell ratio.

    Effective surplus per partner:
      eff_surp = max(buy,sell) × (market_price - source_price) / market_price
      Positive → cheap partner → WAS (import supply)
      Negative → expensive partner → WAD (export demand)

    Origin effective surplus (computed in finalize):
      eff = max(own_buy,own_sell) × (market_price - own_price) / market_price
      Stored as stl_eff_export / stl_eff_import for Phase C.

    stl_phase_b_zero_was_wad: zeros all accumulators
    stl_phase_b_accumulate_all_goods: per-partner WAS/WAD + wavg sums
    stl_phase_b_finalize_prices: adds origin to wavg, computes market_price,
        computes origin eff_export/eff_import for Phase C
    """
    lines = [
        "# ========================================",
        "# PHASE B GENERATED EFFECTS — EFFECTIVE SURPLUS MODEL",
        "#",
        "# Auto-generated by tools/generate_goods.py",
        "# DO NOT EDIT — regenerate with: python tools/generate_goods.py",
        "#",
        "# Production-weighted market price:",
        "#   market_price = sum(production x local_price) / sum(production)",
        "#   Includes all reachable partners + origin state.",
        "#   Consumption affects prices implicitly via buy/sell ratio.",
        "#",
        "# Effective surplus per partner:",
        "#   eff_surp = max(buy,sell) x (market_price - source_price) / market_price",
        "#   Positive: partner is cheap -> accumulates into WAS (import supply)",
        "#   Negative: partner is expensive -> accumulates into WAD (export demand)",
        "#",
        "# Gravity weighting:",
        "#   WAS += eff_surp x (100 - bf_dist)",
        "#   WAD += |eff_surp| x (100 - bf_dist)",
        "#   max_WAS/max_WAD = |eff_surp| x 100 (theoretical max at zero distance)",
        "#",
        "# Origin effective surplus (finalize):",
        "#   stl_eff_export = amount this state should export (cheap vs market)",
        "#   stl_eff_import = amount this state should import (expensive vs market)",
        "# ========================================",
        "",
        "# Zero WAS, WAD, wavg accumulators, and effective export/import for all goods.",
        "# Called at the start of Phase B processing for each origin state.",
        "# Scope: state",
        "stl_phase_b_zero_was_wad = {",
    ]
    for g in names():
        lines.append(f"\tset_variable = {{ name = stl_was_{g} value = 0 }}")
        lines.append(f"\tset_variable = {{ name = stl_wad_{g} value = 0 }}")
        lines.append(f"\tset_variable = {{ name = stl_max_was_{g} value = 0 }}")
        lines.append(f"\tset_variable = {{ name = stl_max_wad_{g} value = 0 }}")
        lines.append(f"\tset_variable = {{ name = stl_wavg_psum_{g} value = 0 }}")
        lines.append(f"\tset_variable = {{ name = stl_wavg_wsum_{g} value = 0 }}")
        lines.append(f"\tset_variable = {{ name = stl_eff_export_{g} value = 0 }}")
        lines.append(f"\tset_variable = {{ name = stl_eff_import_{g} value = 0 }}")
    lines.append("}")
    lines.append("")

    # Accumulate all goods effect — effective surplus model
    lines += [
        "# Accumulate WAS/WAD and production-weighted price sums for all 49 goods",
        "# from a single partner.",
        "#",
        "# For each good with economic activity (max(buy,sell) > 0):",
        "#   1. Compute source_price from partner's buy/sell ratio",
        "#   2. Add partner's production x source_price to wavg sums",
        "#   3. Compute effective_surplus using last month's market_price",
        "#   4. If positive (cheap): accumulate into WAS (gravity-weighted)",
        "#   5. If negative (expensive): accumulate into WAD (gravity-weighted)",
        "#",
        "# Scope: partner state (inside every_scope_state iteration)",
        "# Required saved scope: stl_gravity_self = origin state",
        "# Required local_var: stl_pw = weight (100 - bf_dist)",
        "stl_phase_b_accumulate_all_goods = {",
    ]
    for g in names():
        bp = BASE_PRICES[g]
        lines.append(f"\t# --- {g} (base {bp}) ---")

        # Read partner's buy/sell
        lines.append(f"\tset_local_variable = {{ name = stl_src_buy value = {{ value = sg:{g}.state_goods_consumption }} }}")
        lines.append(f"\tset_local_variable = {{ name = stl_src_sell value = {{ value = sg:{g}.state_goods_production }} }}")

        # economy_scale = max(buy, sell)
        lines.append(f"\tset_local_variable = {{ name = stl_econ_scale value = local_var:stl_src_buy }}")
        lines.append(f"\tif = {{")
        lines.append(f"\t\tlimit = {{ local_var:stl_src_sell > local_var:stl_src_buy }}")
        lines.append(f"\t\tset_local_variable = {{ name = stl_econ_scale value = local_var:stl_src_sell }}")
        lines.append(f"\t}}")

        # Guard: skip if no economic activity
        lines.append(f"\tif = {{")
        lines.append(f"\t\tlimit = {{ local_var:stl_econ_scale > 0.01 }}")

        # Compute source_price: BASE x (1 + 0.75 x clamp((buy-sell)/min(buy,sell), +/-1))
        lines.append(f"\t\tset_local_variable = {{ name = stl_src_price value = {bp} }}")
        lines.append(f"\t\tset_local_variable = {{ name = stl_min_bs value = local_var:stl_src_buy }}")
        lines.append(f"\t\tif = {{")
        lines.append(f"\t\t\tlimit = {{ NOT = {{ local_var:stl_src_sell >= local_var:stl_src_buy }} }}")
        lines.append(f"\t\t\tset_local_variable = {{ name = stl_min_bs value = local_var:stl_src_sell }}")
        lines.append(f"\t\t}}")
        lines.append(f"\t\tif = {{")
        lines.append(f"\t\t\tlimit = {{ local_var:stl_min_bs > 0.01 }}")
        lines.append(f"\t\t\tset_local_variable = {{")
        lines.append(f"\t\t\t\tname = stl_src_ratio")
        lines.append(f"\t\t\t\tvalue = {{ value = local_var:stl_src_buy subtract = local_var:stl_src_sell divide = local_var:stl_min_bs }}")
        lines.append(f"\t\t\t}}")
        lines.append(f"\t\t\tif = {{ limit = {{ local_var:stl_src_ratio > 1 }} set_local_variable = {{ name = stl_src_ratio value = 1 }} }}")
        lines.append(f"\t\t\tif = {{ limit = {{ NOT = {{ local_var:stl_src_ratio >= -1 }} }} set_local_variable = {{ name = stl_src_ratio value = -1 }} }}")
        lines.append(f"\t\t\tset_local_variable = {{")
        lines.append(f"\t\t\t\tname = stl_src_price")
        lines.append(f"\t\t\t\tvalue = {{ value = local_var:stl_src_ratio multiply = 0.75 add = 1 multiply = {bp} }}")
        lines.append(f"\t\t\t}}")
        lines.append(f"\t\t}}")
        # Edge: min(buy, sell) ≈ 0 → use extreme price
        # Pure consumer (sell ≈ 0): max price = 1.75 × base
        # Pure producer (buy ≈ 0): min price = 0.25 × base
        lines.append(f"\t\telse = {{")
        lines.append(f"\t\t\tif = {{")
        lines.append(f"\t\t\t\tlimit = {{ local_var:stl_src_buy > local_var:stl_src_sell }}")
        lines.append(f"\t\t\t\tset_local_variable = {{ name = stl_src_price value = {{ value = 1.75 multiply = {bp} }} }}")
        lines.append(f"\t\t\t}}")
        lines.append(f"\t\t\tif = {{")
        lines.append(f"\t\t\t\tlimit = {{ NOT = {{ local_var:stl_src_buy > local_var:stl_src_sell }} }}")
        lines.append(f"\t\t\t\tset_local_variable = {{ name = stl_src_price value = {{ value = 0.25 multiply = {bp} }} }}")
        lines.append(f"\t\t\t}}")
        lines.append(f"\t\t}}")

        # Wavg intermediaries: production-weighted (computed before scope change)
        # weight = partner production, value = production x source_price
        lines.append(f"\t\tset_local_variable = {{ name = stl_price_wt value = local_var:stl_src_sell }}")
        lines.append(f"\t\tset_local_variable = {{ name = stl_temp_wp value = {{ value = local_var:stl_price_wt multiply = local_var:stl_src_price }} }}")

        # Enter origin scope for market price and accumulation
        lines.append(f"\t\tscope:stl_gravity_self = {{")

        # Accumulate wavg (all partners with production > 0)
        lines.append(f"\t\t\tif = {{")
        lines.append(f"\t\t\t\tlimit = {{ local_var:stl_price_wt > 0.01 }}")
        lines.append(f"\t\t\t\tchange_variable = {{ name = stl_wavg_psum_{g} add = local_var:stl_temp_wp }}")
        lines.append(f"\t\t\t\tchange_variable = {{ name = stl_wavg_wsum_{g} add = local_var:stl_price_wt }}")
        lines.append(f"\t\t\t}}")

        # Market price estimate (last month or base price fallback)
        lines.append(f"\t\t\tset_local_variable = {{ name = stl_mkt_est value = {bp} }}")
        lines.append(f"\t\t\tif = {{")
        lines.append(f"\t\t\t\tlimit = {{ has_variable = stl_market_price_{g} }}")
        lines.append(f"\t\t\t\tset_local_variable = {{ name = stl_mkt_est value = var:stl_market_price_{g} }}")
        lines.append(f"\t\t\t}}")

        # Guard against zero/tiny market price (prevents division by zero)
        lines.append(f"\t\t\tif = {{")
        lines.append(f"\t\t\t\tlimit = {{ local_var:stl_mkt_est > 0.01 }}")

        # Effective surplus: (mkt - src) / mkt x econ_scale
        # Clausewitz left-to-right: mkt - src = diff, /mkt = ratio, x econ = final
        lines.append(f"\t\t\t\tset_local_variable = {{")
        lines.append(f"\t\t\t\t\tname = stl_eff_surp")
        lines.append(f"\t\t\t\t\tvalue = {{")
        lines.append(f"\t\t\t\t\t\tvalue = local_var:stl_mkt_est")
        lines.append(f"\t\t\t\t\t\tsubtract = local_var:stl_src_price")
        lines.append(f"\t\t\t\t\t\tdivide = local_var:stl_mkt_est")
        lines.append(f"\t\t\t\t\t\tmultiply = local_var:stl_econ_scale")
        lines.append(f"\t\t\t\t\t}}")
        lines.append(f"\t\t\t\t}}")

        # If eff > 0: cheap partner -> WAS (import supply)
        lines.append(f"\t\t\t\tif = {{")
        lines.append(f"\t\t\t\t\tlimit = {{ local_var:stl_eff_surp > 0 }}")
        lines.append(f"\t\t\t\t\tset_local_variable = {{ name = stl_wv value = {{ value = local_var:stl_eff_surp multiply = local_var:stl_pw }} }}")
        lines.append(f"\t\t\t\t\tset_local_variable = {{ name = stl_max_wv value = {{ value = local_var:stl_eff_surp multiply = 100 }} }}")
        lines.append(f"\t\t\t\t\tchange_variable = {{ name = stl_was_{g} add = local_var:stl_wv }}")
        lines.append(f"\t\t\t\t\tchange_variable = {{ name = stl_max_was_{g} add = local_var:stl_max_wv }}")
        lines.append(f"\t\t\t\t}}")

        # If eff < 0: expensive partner -> WAD (export demand)
        lines.append(f"\t\t\t\tif = {{")
        lines.append(f"\t\t\t\t\tlimit = {{ NOT = {{ local_var:stl_eff_surp >= 0 }} }}")
        lines.append(f"\t\t\t\t\tset_local_variable = {{ name = stl_neg_eff value = {{ value = 0 subtract = local_var:stl_eff_surp }} }}")
        lines.append(f"\t\t\t\t\tset_local_variable = {{ name = stl_wv value = {{ value = local_var:stl_neg_eff multiply = local_var:stl_pw }} }}")
        lines.append(f"\t\t\t\t\tset_local_variable = {{ name = stl_max_wv value = {{ value = local_var:stl_neg_eff multiply = 100 }} }}")
        lines.append(f"\t\t\t\t\tchange_variable = {{ name = stl_wad_{g} add = local_var:stl_wv }}")
        lines.append(f"\t\t\t\t\tchange_variable = {{ name = stl_max_wad_{g} add = local_var:stl_max_wv }}")
        lines.append(f"\t\t\t\t}}")

        lines.append(f"\t\t\t}}")  # close mkt_est > 0.01 guard
        lines.append(f"\t\t}}")  # close scope:stl_gravity_self
        lines.append(f"\t}}")  # close econ_scale > 0.01 guard

    lines.append("}")
    lines.append("")

    # Finalize: add origin to wavg, compute market_price, compute origin eff_export/eff_import
    lines += [
        "# Finalize: production-weighted market price + origin effective surplus.",
        "#",
        "# 1. Adds origin's own production x local_price to wavg sums",
        "# 2. market_price = sum(prod x price) / sum(prod)",
        "# 3. Computes origin's effective surplus:",
        "#    eff = max(buy,sell) x (market_price - own_price) / market_price",
        "#    eff > 0: state is cheap -> stl_eff_export (should export)",
        "#    eff < 0: state is expensive -> stl_eff_import (should import)",
        "# Phase C reads stl_eff_export/stl_eff_import for trade decisions.",
        "#",
        "# If no production in network (wsum = 0), market_price retains",
        "# its previous value as fallback (NOT zeroed by Phase C).",
        "# Scope: state (origin, same as stl_gravity_self)",
        "stl_phase_b_finalize_prices = {",
    ]
    for g in names():
        bp = BASE_PRICES[g]
        lines.append(f"\t# --- {g} ---")

        # Read origin's own buy/sell
        lines.append(f"\tset_local_variable = {{ name = stl_own_buy value = {{ value = sg:{g}.state_goods_consumption }} }}")
        lines.append(f"\tset_local_variable = {{ name = stl_own_sell value = {{ value = sg:{g}.state_goods_production }} }}")

        # Compute origin's source_price
        lines.append(f"\tset_local_variable = {{ name = stl_own_price value = {bp} }}")
        lines.append(f"\tset_local_variable = {{ name = stl_min_bs value = local_var:stl_own_buy }}")
        lines.append(f"\tif = {{")
        lines.append(f"\t\tlimit = {{ NOT = {{ local_var:stl_own_sell >= local_var:stl_own_buy }} }}")
        lines.append(f"\t\tset_local_variable = {{ name = stl_min_bs value = local_var:stl_own_sell }}")
        lines.append(f"\t}}")
        lines.append(f"\tif = {{")
        lines.append(f"\t\tlimit = {{ local_var:stl_min_bs > 0.01 }}")
        lines.append(f"\t\tset_local_variable = {{")
        lines.append(f"\t\t\tname = stl_own_ratio")
        lines.append(f"\t\t\tvalue = {{ value = local_var:stl_own_buy subtract = local_var:stl_own_sell divide = local_var:stl_min_bs }}")
        lines.append(f"\t\t}}")
        lines.append(f"\t\tif = {{ limit = {{ local_var:stl_own_ratio > 1 }} set_local_variable = {{ name = stl_own_ratio value = 1 }} }}")
        lines.append(f"\t\tif = {{ limit = {{ NOT = {{ local_var:stl_own_ratio >= -1 }} }} set_local_variable = {{ name = stl_own_ratio value = -1 }} }}")
        lines.append(f"\t\tset_local_variable = {{")
        lines.append(f"\t\t\tname = stl_own_price")
        lines.append(f"\t\t\tvalue = {{ value = local_var:stl_own_ratio multiply = 0.75 add = 1 multiply = {bp} }}")
        lines.append(f"\t\t}}")
        lines.append(f"\t}}")
        # Edge: min(buy, sell) ≈ 0 → use extreme price
        lines.append(f"\telse = {{")
        lines.append(f"\t\tif = {{")
        lines.append(f"\t\t\tlimit = {{ local_var:stl_own_buy > local_var:stl_own_sell }}")
        lines.append(f"\t\t\tset_local_variable = {{ name = stl_own_price value = {{ value = 1.75 multiply = {bp} }} }}")
        lines.append(f"\t\t}}")
        lines.append(f"\t\tif = {{")
        lines.append(f"\t\t\tlimit = {{ NOT = {{ local_var:stl_own_buy > local_var:stl_own_sell }} }}")
        lines.append(f"\t\t\tset_local_variable = {{ name = stl_own_price value = {{ value = 0.25 multiply = {bp} }} }}")
        lines.append(f"\t\t}}")
        lines.append(f"\t}}")

        # Add origin's production to wavg sums (production-weighted market price)
        lines.append(f"\tif = {{")
        lines.append(f"\t\tlimit = {{ local_var:stl_own_sell > 0.01 }}")
        lines.append(f"\t\tchange_variable = {{ name = stl_wavg_psum_{g} add = {{ value = local_var:stl_own_sell multiply = local_var:stl_own_price }} }}")
        lines.append(f"\t\tchange_variable = {{ name = stl_wavg_wsum_{g} add = local_var:stl_own_sell }}")
        lines.append(f"\t}}")

        # Compute market_price = wavg
        lines.append(f"\tif = {{")
        lines.append(f"\t\tlimit = {{ var:stl_wavg_wsum_{g} > 0.01 }}")
        lines.append(f"\t\tset_variable = {{")
        lines.append(f"\t\t\tname = stl_weighted_avg_price_{g}")
        lines.append(f"\t\t\tvalue = {{")
        lines.append(f"\t\t\t\tvalue = var:stl_wavg_psum_{g}")
        lines.append(f"\t\t\t\tdivide = var:stl_wavg_wsum_{g}")
        lines.append(f"\t\t\t}}")
        lines.append(f"\t\t}}")
        lines.append(f"\t\tset_variable = {{ name = stl_market_price_{g} value = var:stl_weighted_avg_price_{g} }}")
        lines.append(f"\t}}")

        # Compute origin's effective surplus for Phase C (perfect competition target)
        # Trade depot represents competitive traders who trade until profit = 0
        # Target = full price-equalizing quantity (not marginal)
        # Phase C EMA + rate cap handle convergence speed
        # economy_scale = max(own_buy, own_sell)
        lines.append(f"\tset_local_variable = {{ name = stl_own_econ value = local_var:stl_own_buy }}")
        lines.append(f"\tif = {{")
        lines.append(f"\t\tlimit = {{ local_var:stl_own_sell > local_var:stl_own_buy }}")
        lines.append(f"\t\tset_local_variable = {{ name = stl_own_econ value = local_var:stl_own_sell }}")
        lines.append(f"\t}}")

        lines.append(f"\tif = {{")
        lines.append(f"\t\tlimit = {{ local_var:stl_own_econ > 0.01 has_variable = stl_market_price_{g} var:stl_market_price_{g} > 0.01 }}")
        # eff = own_econ x (market - own_price) / market
        lines.append(f"\t\tset_local_variable = {{")
        lines.append(f"\t\t\tname = stl_own_eff")
        lines.append(f"\t\t\tvalue = {{")
        lines.append(f"\t\t\t\tvalue = var:stl_market_price_{g}")
        lines.append(f"\t\t\t\tsubtract = local_var:stl_own_price")
        lines.append(f"\t\t\t\tdivide = var:stl_market_price_{g}")
        lines.append(f"\t\t\t\tmultiply = local_var:stl_own_econ")
        lines.append(f"\t\t\t}}")
        lines.append(f"\t\t}}")
        # --- Direction-aware target computation ---
        # eff > 0: state is cheap (price signal says export)
        # eff < 0: state is expensive (price signal says import)
        # BUT: if state has existing trade in the opposite direction,
        # REDUCE that trade instead of flipping. This prevents oscillation
        # when prices slightly overshoot equalization.
        # Phase B writes the FULL TARGET (not residual). Phase C just EMAs toward it.

        # Read previous trade direction
        lines.append(f"\t\tset_local_variable = {{ name = stl_prev_imp value = 0 }}")
        lines.append(f"\t\tif = {{")
        lines.append(f"\t\t\tlimit = {{ has_variable = stl_last_import_{g} }}")
        lines.append(f"\t\t\tset_local_variable = {{ name = stl_prev_imp value = var:stl_last_import_{g} }}")
        lines.append(f"\t\t}}")
        lines.append(f"\t\tset_local_variable = {{ name = stl_prev_exp value = 0 }}")
        lines.append(f"\t\tif = {{")
        lines.append(f"\t\t\tlimit = {{ has_variable = stl_last_export_{g} }}")
        lines.append(f"\t\t\tset_local_variable = {{ name = stl_prev_exp value = var:stl_last_export_{g} }}")
        lines.append(f"\t\t}}")

        # Case 1: Was importing
        lines.append(f"\t\tif = {{")
        lines.append(f"\t\t\tlimit = {{ local_var:stl_prev_imp > 0.5 }}")
        # eff > 0 (overshoot): reduce imports by eff amount
        lines.append(f"\t\t\tif = {{")
        lines.append(f"\t\t\t\tlimit = {{ local_var:stl_own_eff > 0 }}")
        lines.append(f"\t\t\t\tset_variable = {{")
        lines.append(f"\t\t\t\t\tname = stl_eff_import_{g}")
        lines.append(f"\t\t\t\t\tvalue = {{ value = local_var:stl_prev_imp subtract = local_var:stl_own_eff }}")
        lines.append(f"\t\t\t\t}}")
        # Overshoot past 0: flip excess to export
        lines.append(f"\t\t\t\tif = {{")
        lines.append(f"\t\t\t\t\tlimit = {{ NOT = {{ var:stl_eff_import_{g} >= 0 }} }}")
        lines.append(f"\t\t\t\t\tset_variable = {{ name = stl_eff_export_{g} value = {{ value = 0 subtract = var:stl_eff_import_{g} }} }}")
        lines.append(f"\t\t\t\t\tset_variable = {{ name = stl_eff_import_{g} value = 0 }}")
        lines.append(f"\t\t\t\t}}")
        lines.append(f"\t\t\t}}")
        # eff <= 0 (still in deficit): increase imports
        lines.append(f"\t\t\tif = {{")
        lines.append(f"\t\t\t\tlimit = {{ NOT = {{ local_var:stl_own_eff > 0 }} }}")
        lines.append(f"\t\t\t\tset_variable = {{")
        lines.append(f"\t\t\t\t\tname = stl_eff_import_{g}")
        lines.append(f"\t\t\t\t\tvalue = {{ value = local_var:stl_prev_imp subtract = local_var:stl_own_eff }}")
        lines.append(f"\t\t\t\t}}")
        # Note: subtract of negative = add. prev_imp + |eff| = larger import target
        lines.append(f"\t\t\t}}")
        lines.append(f"\t\t}}")

        # Case 2: Was exporting
        lines.append(f"\t\tif = {{")
        lines.append(f"\t\t\tlimit = {{ NOT = {{ local_var:stl_prev_imp > 0.5 }} local_var:stl_prev_exp > 0.5 }}")
        # eff < 0 (overshoot): reduce exports by |eff| amount
        lines.append(f"\t\t\tif = {{")
        lines.append(f"\t\t\t\tlimit = {{ NOT = {{ local_var:stl_own_eff >= 0 }} }}")
        lines.append(f"\t\t\t\tset_variable = {{")
        lines.append(f"\t\t\t\t\tname = stl_eff_export_{g}")
        lines.append(f"\t\t\t\t\tvalue = {{ value = local_var:stl_prev_exp add = local_var:stl_own_eff }}")
        lines.append(f"\t\t\t\t}}")
        # Note: eff < 0, so prev_exp + eff = prev_exp - |eff| = reduced
        # Overshoot past 0: flip excess to import
        lines.append(f"\t\t\t\tif = {{")
        lines.append(f"\t\t\t\t\tlimit = {{ NOT = {{ var:stl_eff_export_{g} >= 0 }} }}")
        lines.append(f"\t\t\t\t\tset_variable = {{ name = stl_eff_import_{g} value = {{ value = 0 subtract = var:stl_eff_export_{g} }} }}")
        lines.append(f"\t\t\t\t\tset_variable = {{ name = stl_eff_export_{g} value = 0 }}")
        lines.append(f"\t\t\t\t}}")
        lines.append(f"\t\t\t}}")
        # eff >= 0 (still in surplus): increase exports
        lines.append(f"\t\t\tif = {{")
        lines.append(f"\t\t\t\tlimit = {{ local_var:stl_own_eff >= 0 }}")
        lines.append(f"\t\t\t\tset_variable = {{")
        lines.append(f"\t\t\t\t\tname = stl_eff_export_{g}")
        lines.append(f"\t\t\t\t\tvalue = {{ value = local_var:stl_prev_exp add = local_var:stl_own_eff }}")
        lines.append(f"\t\t\t\t}}")
        lines.append(f"\t\t\t}}")
        lines.append(f"\t\t}}")

        # Case 3: No existing trade — use raw signal
        lines.append(f"\t\tif = {{")
        lines.append(f"\t\t\tlimit = {{ NOT = {{ local_var:stl_prev_imp > 0.5 }} NOT = {{ local_var:stl_prev_exp > 0.5 }} }}")
        lines.append(f"\t\t\tif = {{")
        lines.append(f"\t\t\t\tlimit = {{ local_var:stl_own_eff > 0 }}")
        lines.append(f"\t\t\t\tset_variable = {{ name = stl_eff_export_{g} value = local_var:stl_own_eff }}")
        lines.append(f"\t\t\t}}")
        lines.append(f"\t\t\tif = {{")
        lines.append(f"\t\t\t\tlimit = {{ NOT = {{ local_var:stl_own_eff >= 0 }} }}")
        lines.append(f"\t\t\t\tset_variable = {{ name = stl_eff_import_{g} value = {{ value = 0 subtract = local_var:stl_own_eff }} }}")
        lines.append(f"\t\t\t}}")
        lines.append(f"\t\t}}")

        lines.append(f"\t}}")

    lines.append("}")
    lines.append("")

    write_file(r"common\scripted_effects\stl_phase_b_generated.txt", "\n".join(lines))


if __name__ == "__main__":
    main()
