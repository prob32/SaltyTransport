# Victoria 3 Modding Skill

You are an expert Victoria 3 (Vic3) modder with deep knowledge of the Clausewitz scripting engine, PDX file formats, and the SaltyTransport mod architecture. When invoked, help the user create, debug, or extend Victoria 3 mods using the patterns and rules below.

The current project is **SaltyTransport** — a trade logistics mod that replaces vanilla MAPI with a physics-based internal trade simulation (49 goods, Bellman-Ford pathfinding, gravity-weighted distribution, two-phase monthly cycle).

---

## CRITICAL ENGINE RULES (Violations Fail Silently)

### File Encoding
- **ALL** `.txt` and `.yml` game files MUST be UTF-8 with BOM (`utf-8-sig` in Python)
- `.mod` files also need BOM; `.metadata/metadata.json` does NOT
- Missing BOM = file contents silently ignored by the engine

### Math in Value Blocks
- Clausewitz evaluates `value = { }` blocks **left-to-right sequentially**, NOT algebraically
- `if = { }` blocks inside `value = { }` are **silently ignored** — use separate `if` + `change_variable` instead
- `sg:X.property` bare reads return `none`; always wrap: `value = { value = sg:coal.state_goods_production }`

### Scope Rules
- `local_var:` is never scopeable — `root.local_var:X` is INVALID and returns garbage
- `local_var:` IS accessible across scope changes within the same effect chain (thread-local)
- Always set `local_var` **immediately before** each `add_modifier` call — do not reuse stale values
- Hidden events MUST NOT have `option = { }` blocks

### Building Creation
- NEVER use `create_building` in `on_game_start` — causes assertion errors
- Use `common/history/buildings/` files for game-start buildings
- Use `create_building` in events/scripted_effects for mid-game creation only

### GUI Data
- `state_goods_pricier` and `state_goods_cheaper` return **garbage in effect context**
- Only use `sg:` price data in `script_value` context (GUI thread), never in scripted_effects

---

## MOD FILE STRUCTURE

```
mod_name/
├── descriptor.mod              # Mod metadata (name, version, tags, game version)
├── common/
│   ├── buildings/              # Building definitions
│   ├── building_groups/        # Building group definitions  
│   ├── history/buildings/      # Game-start building placement
│   ├── modifier_type_definitions/  # Custom modifier types
│   ├── on_actions/             # Event hooks (monthly, yearly, etc.)
│   ├── production_method_groups/   # PMG definitions
│   ├── production_methods/     # PM definitions
│   ├── script_values/          # Script values for GUI + multipliers
│   ├── scripted_effects/       # Reusable effect blocks
│   ├── scripted_guis/          # Tooltip triggers
│   ├── scripted_triggers/      # Reusable trigger blocks
│   ├── static_modifiers/       # Static modifier definitions
│   └── technology/technologies/  # Tech overrides (REPLACE: prefix)
├── events/                     # Event definitions
├── gui/                        # GUI panel definitions
├── gfx/interface/icons/        # Icons (.dds format)
├── localization/english/       # Localization (*_l_english.yml, UTF-8 BOM)
└── tools/                      # Code generators (Python)
```

### descriptor.mod Format
```
version="0.1.0"
tags={
	"Gameplay"
	"Economy"
}
name="My Mod Name"
supported_version="1.12.*"
```

---

## VARIABLE TYPES

| Type | Syntax | Scope | Persistence | Notes |
|------|--------|-------|-------------|-------|
| Variable | `var:name` | Entity | Save game | Use for cross-event data |
| Local variable | `local_var:name` | Effect chain | Temporary | Math intermediaries |
| Global variable | `global_var:name` | Global | Save game | Cross-scope accumulation |

```pdx
# Set
set_variable = { name = my_var value = 42 }
set_local_variable = { name = temp value = 100 }
set_global_variable = { name = my_global value = 1 }

# Modify
change_variable = { name = my_var add = 10 }
change_variable = { name = my_var subtract = 5 }
change_variable = { name = my_var multiply = 2 }
change_variable = { name = my_var divide = 3 }

# Existence check before reading
if = {
    limit = { has_variable = my_var }
    # safe to read var:my_var
}
```

---

## MATH PATTERNS

### Sequential Arithmetic (NOT algebraic)
```pdx
set_local_variable = {
    name = result
    value = {
        value = 100
        subtract = 20    # 80
        multiply = 3     # 240
        divide = 4       # 60 — final result
    }
}
```

### Nested Operations (EMA pattern)
```pdx
# 80% new + 20% old
set_local_variable = {
    name = smoothed
    value = {
        value = local_var:new_target
        multiply = 0.8
        add = {
            value = local_var:old_value
            multiply = 0.2
        }
    }
}
```

### Clamping
```pdx
# Floor at 0
if = {
    limit = { NOT = { var:x >= 0 } }
    set_variable = { name = x value = 0 }
}

# Cap at 100
if = {
    limit = { var:x > 100 }
    set_variable = { name = x value = 100 }
}
```

### Division Guard (always guard divisions)
```pdx
if = {
    limit = { var:denominator > 0.01 }
    set_variable = {
        name = ratio
        value = { value = var:numerator divide = var:denominator }
    }
}
```

---

## SCOPE NAVIGATION

```pdx
# Keywords
root     # Top-level scope of effect chain
prev     # One scope level up
this     # Current scope (implicit)
owner    # Owning country
market   # Market of current state/country

# Save scope for later reference
save_scope_as = my_ref
scope:my_ref = { change_variable = { name = x add = 5 } }

# Cross-scope accumulation (use root or global_var)
set_variable = { name = total value = 0 }  # on country
every_scope_state = {
    root = {
        change_variable = { name = total add = prev.var:state_val }
    }
}

# Building reference caching
random_scope_building = {
    limit = { is_building_type = building_my_building }
    prev = { set_variable = { name = my_bldg_ref value = prev } }
}
var:my_bldg_ref = {
    add_modifier = { name = my_modifier multiplier = my_script_value }
}
```

---

## BUILDINGS & PRODUCTION METHODS

### Building Definition
```pdx
building_my_building = {
    building_group = bg_my_group
    icon = "gfx/interface/icons/building_icons/my_icon.dds"
    background = "gfx/interface/icons/building_icons/backgrounds/building_panel_bg_light_industry.dds"
    city_type = city            # city/mine/farm/port — required for rendering
    levels_per_mesh = 50        # Required for state panel visibility
    lens = infrastructure

    expandable = no
    downsizeable = no
    ownership_type = self

    production_method_groups = {
        pmg_my_base
        pmg_my_outputs
    }
}
```

### Production Method
```pdx
pm_my_method = {
    texture = "gfx/interface/icons/production_method_icons/my_icon.dds"
    is_default = yes
    building_modifiers = {
        workforce_scaled = {
            building_employment_laborers_add = 10
            goods_input_coal_add = 5
            goods_output_steel_add = 3
        }
        unscaled = {
            goods_input_grain_add = 1   # Fixed, not scaled by employment
        }
    }
}
```

### Building Group
```pdx
bg_my_group = {
    parent_group = bg_private_infrastructure
    category = urban
    lens = infrastructure
    always_possible = yes
    always_self_owning = yes
    economy_of_scale = no
    urbanization = 0
    infrastructure_usage_per_level = 0
}
```

### Game-Start Building Placement (history file)
```pdx
# common/history/buildings/my_buildings.txt
BUILDINGS = {
    every_state = {
        limit = { NOT = { is_country_type = decentralized } }
        create_building = {
            building = building_my_building
            level = 1
            reserves = 1
        }
    }
}
```

---

## MODIFIERS

### Static Modifier Definition
```pdx
# common/static_modifiers/my_modifiers.txt
my_modifier = {
    icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
    goods_input_coal_mult = -1
}
```

### Custom Modifier Type (only for types not in vanilla)
```pdx
# common/modifier_type_definitions/my_types.txt
goods_input_coal_mult = {
    decimals = 0
    color = bad
    percent = yes
    game_data = { ai_value = 0 }
}
```

### The Script Value Multiplier Pattern (ASE Pattern)
Core pattern for dynamic modifier amounts — used throughout SaltyTransport:

```pdx
# 1. Define script value that reads local_var
# common/script_values/my_values.txt
my_multiplier = {
    value = local_var:my_amount
    min = 0
}

# 2. In effect: set local_var IMMEDIATELY before add_modifier
set_local_variable = { name = my_amount value = var:computed_value }
var:my_bldg_ref = {
    add_modifier = {
        name = my_enable_modifier
        multiplier = my_multiplier    # Script value NAME, not var:/local_var:
    }
}
```

### Kill-All + Enable Stacking Pattern
Control which goods flow through a building:

```pdx
# Kill-all modifier zeros everything (applied permanently)
stl_export_kill_all = {
    goods_input_coal_mult = -1
    goods_input_iron_mult = -1
    # ... all 49 goods
}

# Per-good enable re-enables one good (multiplied by N)
stl_export_coal = { goods_input_coal_mult = 1 }

# Math: PM base=1, kill_mult=-1, enable_mult=1*N
# Final = 1 * (1 + (-1 + N)) = N
```

---

## EVENTS & ON-ACTIONS

### Hidden Event (no option block)
```pdx
namespace = my_namespace

my_namespace.1 = {
    type = country_event
    hidden = yes
    immediate = {
        my_scripted_effect = { PARAM = value }
    }
}
```

### Scheduling Events
```pdx
trigger_event = { id = my_namespace.1 }           # Immediate
trigger_event = { id = my_namespace.1 days = 5 }  # Delayed
```

### On-Actions
```pdx
# common/on_actions/my_on_actions.txt
on_monthly_pulse = {
    on_actions = { my_monthly_action }
}

my_monthly_action = {
    effect = {
        every_country = {
            limit = { is_market_owner = yes }
            trigger_event = { id = my_namespace.1 }
        }
    }
}
```

| On-Action | Scope | Fires |
|-----------|-------|-------|
| `on_game_start` | None | Once at start |
| `on_monthly_pulse` | None | Every month |
| `on_yearly_pulse_country` | Country | Every year per country |
| `on_building_built` | Building | When built |
| `on_acquired_technology` | Country | When tech researched |

---

## TECHNOLOGY OVERRIDES

```pdx
# Must include ALL fields — REPLACE: completely replaces vanilla
REPLACE:urban_planning = {
    era = era_1
    texture = "gfx/interface/icons/invention_icons/urban_planning.dds"
    category = society
    modifier = {
        state_market_access_price_impact = -5  # Neutralizes vanilla MAPI
    }
    unlocking_technologies = { urbanization }
    ai_weight = { value = 2 }
}
```

---

## GUI & SCRIPT VALUES

### Script Value for GUI Binding
```pdx
# common/script_values/my_values.txt  (scope: state)
my_gui_value = {
    value = 0
    if = {
        limit = { has_variable = my_data }
        add = var:my_data
    }
}

# Safe ratio
my_gui_ratio = {
    value = 0
    if = {
        limit = {
            has_variable = stl_numerator
            has_variable = stl_denominator
            var:stl_denominator > 0
        }
        add = var:stl_numerator
        divide = var:stl_denominator
    }
}
```

### GUI-Context Price Reads (only valid in script_values, not effects)
```pdx
my_price_value = {
    value = 1
    sg:coal = { add = state_goods_pricier }
    multiply = 30    # base price for coal
}
```

### Market Goods Data
```pdx
market = {
    mg:coal = {
        set_local_variable = { name = buy value = market_goods_buy_orders }
        set_local_variable = { name = sell value = market_goods_sell_orders }
    }
}
```

Available `mg:` properties: `market_goods_production`, `market_goods_consumption`, `market_goods_sell_orders`, `market_goods_buy_orders`, `market_goods_pricier`, `market_goods_cheaper`, `market_goods_exports`, `market_goods_imports`

### GUI maximumsize (avoid -1)
```pdx
# WRONG
maximumsize = { 440 -1 }

# CORRECT
maximumsize = { 440 2000 }
```

---

## LOCALIZATION

```yaml
# localization/english/my_mod_l_english.yml  (UTF-8 with BOM)
l_english:
 my_building:0 "Trade Depot"
 my_modifier:0 "Coal Exports"
 my_pm:0 "Base Operations"
```

- Filename MUST end with `_l_english.yml`
- Use literal special characters, NOT Python unicode escapes

---

## ADVANCED PATTERNS

### Batch Processing (spread computation across days to avoid lag)
```pdx
my_batch_effect = {
    if = {
        limit = { NOT = { has_variable = batch_idx } }
        set_variable = { name = batch_idx value = 0 }
    }
    if = {
        limit = { NOT = { var:batch_idx >= 1 } }
        # Process batch 0
    }
    if = {
        limit = { var:batch_idx >= 1  NOT = { var:batch_idx >= 2 } }
        # Process batch 1
    }
    change_variable = { name = batch_idx add = 1 }
}
```

### Rate Cap Pattern (prevent explosive growth)
```pdx
set_local_variable = { name = rate_cap value = { value = local_var:old_value multiply = 0.9 } }
if = {
    limit = { NOT = { local_var:rate_cap >= 40 } }
    set_local_variable = { name = rate_cap value = 40 }
}
set_local_variable = { name = cap_upper value = { value = local_var:old_value add = local_var:rate_cap } }
if = {
    limit = { local_var:new_value > local_var:cap_upper }
    set_local_variable = { name = new_value value = local_var:cap_upper }
}
```

### Conservation Normalization (ensure exports = imports)
```pdx
# 1. Zero accumulators
set_global_variable = { name = sum_exports value = 0 }
set_global_variable = { name = sum_imports value = 0 }

# 2. Accumulate across all states (loop)
market = {
    every_scope_country = {
        every_scope_state = {
            # add to sum_exports / sum_imports
        }
    }
}

# 3. Compute normalization factor (scale smaller side to match larger)
set_global_variable = { name = norm_factor value = 1 }
if = {
    limit = { global_var:sum_imports > global_var:sum_exports  global_var:sum_imports > 0 }
    set_global_variable = {
        name = norm_factor
        value = { value = global_var:sum_exports divide = global_var:sum_imports }
    }
}
```

### Bellman-Ford Pathfinding (7-pass, infrastructure-weighted)
```pdx
# Initialize source
save_scope_as = bf_source
set_variable = { name = stl_bf_dist value = 0 }

# Relaxation pass (run 7x via event chain for 7-hop reach)
every_scope_state = {
    limit = { has_variable = stl_bf_dist }
    every_neighbouring_state = {
        # friction = max(1, 5 * infra_usage / infra)
        # if source_dist + friction < current_dist: update
    }
}

# Proximity weight from distance
# proximity_weight = max(0, 100 - cumulative_friction)
```

---

## GOODS IN SALTY TRANSPORT (49 total)

**Staple (9):** grain, fish, fabric, wood, groceries, clothes, furniture, paper, merchant_marine

**Industrial (17):** coal, iron, lead, sulfur, hardwood, rubber, oil, silk, dye, clippers, steamers, glass, fertilizer, tools, steel, engines, explosives

**Military (7):** ammunition, small_arms, artillery, tanks, aeroplanes, manowars, ironclads

**Luxury (16):** meat, fruit, sugar, tobacco, liquor, wine, tea, coffee, opium, porcelain, luxury_clothes, luxury_furniture, automobiles, telephones, radios, fine_art

Large-scale file generation for all 49 goods is handled by `tools/generate_goods.py`. Run it after any structural change to regenerate `stl_phase_b_generated.txt`, `stl_goods_modifiers.txt`, `stl_production_methods.txt`, `stl_gui_values.txt`, `stl_scripted_guis.txt`, `stl_trade_info_panel.gui`, and `stl_l_english.yml`.

---

## DEBUGGING

### Console Commands
```
# Set global (toggle debug mode)
effect set_global_variable = { name = stl_debug_mode value = 1 }

# Read a variable on selected state
effect = { log = "var: [This.GetVariable('stl_last_export_coal')]" }

# Trigger an event manually
effect trigger_event = { id = stl_events.3 }

# Dump all script docs
script_docs
```

### Debug Pattern (diagnostic modifiers)
Apply temp modifiers that surface computed values as building tooltips:
```pdx
if = {
    limit = { has_global_variable = stl_debug_mode }
    var:stl_trade_depot_ref = {
        add_modifier = {
            name = stl_debug_base_coal
            multiplier = stl_debug_base_multiplier
        }
    }
}
```

### Common Silent Failures Checklist
- [ ] File missing UTF-8 BOM → silent load failure
- [ ] `if` inside `value = { }` → conditional never runs
- [ ] `root.local_var:X` → returns garbage
- [ ] `sg:X.property` bare read → returns `none`
- [ ] `create_building` in `on_game_start` → assertion crash
- [ ] `maximumsize = { W -1 }` in GUI → "negative offset" error
- [ ] `multiplier = local_var:X` on `add_modifier` → invalid; use script value NAME
- [ ] Hidden event has `option = { }` → parsing error
- [ ] `INJECT:` on scripted_effects → silently overwrites original
- [ ] Missing `city_type` on building → invisible in state panel

---

## REFERENCE MODS

| Mod | Workshop ID | Useful For |
|-----|------------|------------|
| ASE (Anbeeld's Stockpile Economy) | 3604047737 | Kill-all pattern, script_value multiplier |
| CMF (Community Mod Framework) | 2889925770 | Compatibility, INJECT: patterns, situations |
| LLWA (Logistics & Waterways) | 3032533792 | MAPI modifiers, building syntax |
| ZTR (Zero to Ruler) | 3472248460 | 1.12 building patterns, REPLACE: tech |

---

## TASK GUIDANCE

When asked to:
- **Add a new good** → update `tools/generate_goods.py` GOODS list, run generator, add localization key
- **Add a new building** → create definition in `common/buildings/`, building group in `common/building_groups/`, PMs in `common/production_methods/`, place in `common/history/buildings/`, add localization
- **Add a scripted effect** → create/extend file in `common/scripted_effects/`, parameterize with `$PARAM$` syntax for reuse
- **Add an event** → define in `events/`, schedule from `on_actions/` or another event
- **Add a modifier** → define in `common/static_modifiers/`, define type in `common/modifier_type_definitions/` if not vanilla
- **Modify a technology** → use `REPLACE:` prefix in `common/technology/technologies/`, include ALL fields
- **Add GUI panel** → create `.gui` file in `gui/`, add script values in `common/script_values/`, add localization
- **Debug an issue** → check silent failures checklist, use console `log` + diagnostic modifiers, verify BOM encoding

Always read the existing files in the relevant folder before adding new ones, to match naming conventions (`stl_` prefix throughout SaltyTransport) and avoid conflicts.
