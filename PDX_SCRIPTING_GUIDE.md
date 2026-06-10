# Paradox Clausewitz Scripting Guide for Victoria 3 (1.13)

A practical reference for modders working with Victoria 3's scripting engine.
Covers syntax rules, common patterns, pitfalls, and working examples from the
Salty Transport mod.

> Updated for 1.13.x. Headless API reference: the Modding Co-op digests repo
> (github.com/Victoria-3-Modding-Co-op/Modding-Digests) ships the game's own
> `script_docs` dumps per patch under `<version>/docs/` — grep those instead
> of guessing. Validation: `tools/validate.sh` (vic3-tiger). Structural lint
> without game files: `python3 tools/lint_pdx.py`.

---

## Table of Contents

1. [File Encoding](#file-encoding)
2. [Variables & Scoping](#variables--scoping)
3. [Value Blocks & Math](#value-blocks--math)
4. [Conditions & Comparisons](#conditions--comparisons)
5. [Scope Navigation](#scope-navigation)
6. [State Goods Data (sg:)](#state-goods-data-sg)
7. [Market Goods Data (mg:)](#market-goods-data-mg)
8. [Buildings & Production Methods](#buildings--production-methods)
9. [Modifiers & the Multiplier Pattern](#modifiers--the-multiplier-pattern)
10. [Events & On-Actions](#events--on-actions)
11. [Technology Overrides](#technology-overrides)
12. [GUI & Script Values](#gui--script-values)
13. [Localization](#localization)
14. [Common Pitfalls](#common-pitfalls)
15. [Reference Patterns](#reference-patterns)

---

## File Encoding

**ALL** `.txt` and `.yml` game files must be UTF-8 with BOM (byte order mark: EF BB BF).

```python
# Python: write with BOM
with open(path, "w", encoding="utf-8-sig") as f:
    f.write(content)
```

- `.mod` files also need BOM
- `.metadata/metadata.json` does NOT need BOM (standard JSON)
- Missing BOM causes silent parse failures (files appear empty to the engine)

---

## Variables & Scoping

### Variable Types

| Type | Syntax | Scope | Persistence | Cross-scope |
|------|--------|-------|-------------|-------------|
| Variable | `var:name` | Entity (state/country/etc) | Persistent (save game) | Yes: `root.var:X`, `prev.var:X` |
| Local variable | `local_var:name` | Effect chain | Temporary (one call) | **NO**: `root.local_var:X` is INVALID |
| Global variable | `global_var:name` | Global | Persistent | Yes: accessible from any scope |

### Setting Variables

```
# Persistent variable on current scope
set_variable = { name = my_var value = 42 }

# Local (temporary) variable
set_local_variable = { name = temp value = 100 }

# Global variable (accessible everywhere)
set_global_variable = { name = my_global value = 1 }

# Modify existing variable
change_variable = { name = my_var add = 10 }
change_variable = { name = my_var subtract = 5 }
change_variable = { name = my_var multiply = 2 }
change_variable = { name = my_var divide = 3 }

# Same for local
change_local_variable = { name = temp add = 5 }
```

### Critical Rule: local_var Is NOT Scopeable

```
# WRONG - will cause errors or return garbage
root.local_var:my_temp       # INVALID
prev.local_var:my_temp       # INVALID

# CORRECT - local_var is always a global link
local_var:my_temp            # Works from any scope level in same effect chain
```

`local_var:` IS accessible across scope changes within the same effect chain (confirmed by ASE mod). It's like a thread-local global -- visible everywhere during the current effect execution, but cannot be prefixed with scope qualifiers.

### When to Use Which

- **`local_var:`** -- Temporary computation within one scripted effect call. No save game bloat. Use for math intermediaries, loop counters, temp results.
- **`var:`** -- Data that persists between months/events. Stored on an entity (state, country, building). Use for tracking values, caching references, cross-event communication.
- **`global_var:`** -- Data that needs to be read from any scope. Use sparingly (conservation normalization, debug flags, cross-scope accumulation).

### Variable Existence Checks

```
# Check if variable exists before reading (prevents 'none' errors)
if = {
    limit = { has_variable = my_var }
    # safe to read var:my_var
}

# Has_local_variable works for local vars
if = {
    limit = { has_local_variable = my_temp }
    # safe to read local_var:my_temp
}
```

### Variable Maps (1.13.7+)

Keyed containers — the same system as EU5. Keys are event targets (scopes or
`flag:` targets); values are numbers or targets. Local/global variants exist
(`add_to_local_variable_map`, `add_to_global_variable_map`, ...).

```
# write / overwrite one key
add_to_variable_map = { name = my_map key = flag:grain value = 42 }
add_to_variable_map = { name = my_map key = scope:some_state value = 7 }

# read (event-target link, works in triggers and value blocks)
variable_map(my_map|flag:grain) >= 10
set_local_variable = { name = x value = variable_map(my_map|flag:grain) }
scope:other.variable_map(my_map|prev)        # scoped chain + dynamic key

# existence / size / membership
has_variable_map = my_map
variable_map_size = { name = my_map value >= 3 }
is_key_in_variable_map = { name = my_map key = flag:grain }

# remove / clear / iterate
remove_from_variable_map = { name = my_map key = flag:grain }
clear_variable_map = my_map
every_key_in_variable_map = { name = my_map <effects on each key scope> }
```

**CRITICAL — values are stored by REFERENCE, not copied** (live-confirmed):
`add_to_variable_map = { ... value = local_var:x }` stores the *event
target* `local_var:x`, not the number. Reading the key from the same effect
chain works; reading it from any later chain yields
`Event target link 'local_var' returned an unset scope` and the fetch
fails. Use maps only for (a) data written and read within one chain (e.g.
pathfinding scratch), or (b) values from immortal targets (flags). For
anything persistent, use plain variables — `set_variable` copies.

**Other caveats**: maps are missing from the game's own `script_docs` dump
and from vic3-tiger (as of v1.19.0), so they cannot be machine-validated.
After each game patch, take the in-game decision "Salty Transport: Run
Syntax Probe" — it exercises every operation above (including a two-run
cross-chain persistence test, step 9) and logs PASS/FAIL lines to
debug.log. GUI data functions exist only for GLOBAL maps
(`GetVariableFromGlobalVariableMap`, `GetGlobalMapKeys`, ...); for
state/country maps, bind through script values.

---

## Value Blocks & Math

### Basic Assignment

```
# Simple value
set_variable = { name = x value = 10 }

# Value from another variable
set_variable = { name = x value = var:other }

# IMPORTANT: sg: reads need value block syntax
set_local_variable = {
    name = production
    value = { value = sg:coal.state_goods_production }  # Block syntax required
}
```

### Arithmetic in Value Blocks

Clausewitz evaluates value blocks **left-to-right, sequentially**:

```
set_local_variable = {
    name = result
    value = {
        value = 100        # result = 100
        subtract = 20      # result = 80
        multiply = 3       # result = 240
        divide = 4         # result = 60
    }
}
```

This is NOT algebraic -- it's sequential: `((100 - 20) * 3) / 4 = 60`

### Nested Operations with `add = { }`

```
set_local_variable = {
    name = ema_result
    value = {
        value = local_var:new_target
        multiply = 0.8
        add = {
            value = local_var:old_value
            multiply = 0.2
        }
    }
}
# Result: new_target * 0.8 + old_value * 0.2
```

### DANGER: `if` Inside Value Blocks

```
# WRONG - if blocks are SILENTLY IGNORED inside value = { }
set_variable = {
    name = result
    value = {
        value = 100
        if = {
            limit = { var:flag >= 1 }
            subtract = 50    # THIS MAY NEVER EXECUTE
        }
    }
}

# CORRECT - use separate statements
set_variable = { name = result value = 100 }
if = {
    limit = { var:flag >= 1 }
    change_variable = { name = result subtract = 50 }
}
```

### Clamping (Min/Max)

```
# Floor at 0
if = {
    limit = { NOT = { var:my_var >= 0 } }
    set_variable = { name = my_var value = 0 }
}

# Cap at 100
if = {
    limit = { var:my_var > 100 }
    set_variable = { name = my_var value = 100 }
}
```

### Game Defines

Access engine constants with `define:` syntax:

```
change_local_variable = {
    name = price_ratio
    multiply = define:NEconomy|PRICE_RANGE    # 0.75 in vanilla
}
```

---

## Conditions & Comparisons

### Comparison Operators

All of `>`, `>=`, `<`, `<=`, `=`, `!=` are valid in triggers (the game's own
script_docs use `state_goods_consumption < X`). NOT-inversion also works and
is common in older code:

```
var:my_var >= 10
var:my_var < 10              # supported
NOT = { var:my_var >= 10 }   # equivalent less-than idiom
```

### Boolean Logic

```
# AND (implicit - all conditions in a limit must be true)
limit = {
    var:a >= 1
    var:b >= 1
}

# OR (explicit)
limit = {
    OR = {
        var:a >= 1
        var:b >= 1
    }
}

# NOT
limit = {
    NOT = { var:a >= 1 }
}

# NAND (not all true)
limit = {
    NAND = {
        var:a >= 1
        var:b >= 1
    }
}
```

### Existence Checks

```
has_variable = my_var            # State/country var exists
has_local_variable = my_temp     # Local var exists
has_building = building_name     # State has this building type
is_building_type = building_name # Building scope matches type
```

---

## Scope Navigation

### Common Scope Chains

```
# From state -> market -> market goods
market = {
    mg:coal = {
        # market_goods_production, etc.
    }
}

# From country -> all states
every_scope_state = {
    limit = { ... }
    # state scope
}

# From country -> market -> all countries in market -> their states
market = {
    every_scope_country = {
        every_scope_state = {
            # state scope, potentially from other countries
        }
    }
}
```

### Saved Scopes

```
# Save current scope for later reference
save_scope_as = stl_gravity_self

# Reference saved scope from anywhere in the effect chain
scope:stl_gravity_self = {
    # back in the saved scope
    change_variable = { name = my_var add = 5 }
}
```

**1.13 PITFALL — do not save scopes inside nested transition blocks:**

```
# BROKEN on 1.13 (worked on 1.12): later reads give
# "Undefined event target" + "Event target link 'scope' returned an unset scope"
owner = { market = { save_scope_as = my_market } }
scope:my_market = { ... }    # fails at runtime, 100% reproducible

# WORKS: save the current scope plainly...
save_scope_as = my_origin
# ...and re-derive transitions via links where needed
market = { every_scope_country = { ... } }          # state -> its market
market = { this = scope:my_origin.market }           # compare markets
```

Confirmed live (error.log, 506 occurrences); probe step 7 tracks whether
the quirk persists across patches. Plain `save_scope_as` on the current
scope, including use inside nested iterators, works normally.

### Building References

```
# Find and cache a building reference
random_scope_building = {
    limit = { is_building_type = building_stl_trade_depot }
    prev = {
        set_variable = { name = stl_trade_depot_ref value = prev }
    }
}

# Use cached reference to apply modifiers
var:stl_trade_depot_ref = {
    add_modifier = { name = my_modifier multiplier = my_script_value }
    remove_modifier = my_other_modifier
}
```

### Scope Keywords

| Keyword | Meaning |
|---------|---------|
| `root` | Top-level scope of the effect chain |
| `prev` | Previous scope (one level up) |
| `this` | Current scope (usually implicit) |
| `scope:name` | Named saved scope |
| `owner` | Country that owns current entity |
| `market` | Market of current state/country |

---

## State Goods Data (sg:)

Access per-state goods data from state scope:

```
# WORKS in both effect and GUI context
sg:coal = {
    # state_goods_production - total production in this state
    # state_goods_consumption - total consumption in this state
}

# Reading values - MUST use value block syntax
set_local_variable = {
    name = prod
    value = { value = sg:coal.state_goods_production }
}

# WRONG - bare assignment returns 'none'
set_local_variable = { name = prod value = sg:coal.state_goods_production }
```

### Available Properties

| Property | Context | Type | Notes |
|----------|---------|------|-------|
| `state_goods_production` | Both | Numeric | Production in state |
| `state_goods_consumption` | Both | Numeric | Consumption in state |
| `state_goods_pricier` | **GUI only** | Numeric | Price % above base |
| `state_goods_cheaper` | **GUI only** | Numeric | Price % below base |
| `state_goods_has_local_goods_shortage` | Both | Boolean | Shortage flag |

**CRITICAL**: `state_goods_pricier` and `state_goods_cheaper` return **garbage values** in
effect context (monthly pulse, scripted effects). They only work correctly in script_value
context (GUI thread). This is a known engine behavior.

### Workaround for Prices in Effects

Since you can't read local prices in effect context, compute a proxy:

```
# Price proxy from buy/sell ratio
# ratio = (buy - sell) / min(buy, sell), clamped to [-1, +1]
# price = BASE x (1 + 0.75 x ratio)
```

---

## Market Goods Data (mg:)

Access market-level aggregates from market scope:

```
market = {
    mg:coal = {
        set_local_variable = { name = buy value = market_goods_buy_orders }
        set_local_variable = { name = sell value = market_goods_sell_orders }
    }
}
```

### Available Properties

| Property | Type | Description |
|----------|------|-------------|
| `market_goods_production` | Numeric | Total market production |
| `market_goods_consumption` | Numeric | Total market consumption |
| `market_goods_sell_orders` | Numeric | Total sell orders |
| `market_goods_buy_orders` | Numeric | Total buy orders |
| `market_goods_pricier` | Numeric (0-1) | Price % above base |
| `market_goods_cheaper` | Numeric (0-1) | Price % below base |
| `market_goods_exports` | Numeric | External trade exports |
| `market_goods_imports` | Numeric | External trade imports |

---

## Buildings & Production Methods

### Building Definition

```
building_my_building = {
    building_group = bg_my_group
    icon = "gfx/interface/icons/building_icons/name.dds"
    background = "gfx/interface/icons/building_icons/backgrounds/building_panel_bg_light_industry.dds"
    city_type = city          # city/mine/farm/port - REQUIRED for rendering
    levels_per_mesh = 50      # REQUIRED for state panel visibility
    lens = infrastructure     # Panel placement

    expandable = no
    downsizeable = no
    ownership_type = self

    unlocking_technologies = {
        some_tech
    }

    production_method_groups = {
        pmg_my_base
        pmg_my_outputs
    }
}
```

### Visibility Rules

A building appears as **visible** (not hidden) in the state panel when:
1. Does NOT have `buildable = no` (this makes buildings **hidden**)
2. Has `city_type` set
3. Has `levels_per_mesh` set
4. Has valid `lens` value
5. Has at least 1 level in the state

### Production Methods

```
pm_my_method = {
    texture = "gfx/interface/icons/production_method_icons/icon.dds"
    is_default = yes
    building_modifiers = {
        workforce_scaled = {
            building_employment_laborers_add = 10
            goods_input_coal_add = 5
            goods_output_steel_add = 3
        }
        unscaled = {
            # Not affected by workforce ratio
            goods_input_grain_add = 1
        }
    }
}
```

### Building Groups

```
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

### Building Creation

```
# Game start: use history files (NOT on_game_start)
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

# Mid-game: use create_building in events/effects
create_building = {
    building = building_my_building
    level = 1
    reserves = 1
}
```

**WARNING**: Never use `create_building` inside `on_game_start` -- causes assertion errors. Always use history files for game-start buildings.

---

## Modifiers & the Multiplier Pattern

### Static Modifiers

```
# common/static_modifiers/my_modifiers.txt
my_modifier = {
    icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
    goods_input_coal_mult = -1    # Building-level modifier
}
```

### Modifier Type Definitions

Only define modifiers that **don't exist in vanilla**:

```
# common/modifier_type_definitions/my_types.txt
goods_input_coal_mult = {
    decimals = 0
    color = bad
    percent = yes
    game_data = {
        ai_value = 0
    }
}
```

### Applying Modifiers

```
# Permanent modifier (days = -1)
building_scope = {
    add_modifier = {
        name = my_modifier
        days = -1              # Never expires
    }
}

# With multiplier (from script value)
set_local_variable = { name = my_amount value = 42 }
building_scope = {
    add_modifier = {
        name = my_modifier
        multiplier = my_script_value    # Script value NAME, not var:!
    }
}

# Remove modifier
building_scope = {
    remove_modifier = my_modifier
}
```

### The Script Value Multiplier Pattern (ASE Pattern)

This is the core pattern for dynamic modifier amounts:

```
# 1. Define script value that reads a local var
# common/script_values/my_values.txt
my_multiplier = {
    value = local_var:my_computed_amount
    min = 0
}

# 2. In your effect: set the local var, then apply modifier
set_local_variable = {
    name = my_computed_amount
    value = 42    # Your computed amount
}
var:my_building_ref = {
    add_modifier = {
        name = my_enable_modifier
        multiplier = my_multiplier    # Script value NAME
    }
}
```

**CRITICAL**: The `multiplier` parameter takes a **script value name**, not `var:X` or `local_var:X`. The script value reads the local var at evaluation time.

**CRITICAL**: You MUST `set_local_variable` **immediately before** each `add_modifier` call. The local var must be fresh for each application.

### Kill-All + Enable Modifier Stacking

Pattern for dynamically controlling goods flow per-building:

```
# Kill-all: zeros everything
stl_export_kill_all = {
    goods_input_coal_mult = -1
    goods_input_iron_mult = -1
    # ... all goods
}

# Per-good enable: re-enables one good
stl_export_coal = {
    goods_input_coal_mult = 1
}

# Math: PM base=1, kill_mult=-1, enable_mult=1 x N
# Final = 1 x (1 + (-1 + 1*N)) = N
```

---

## Events & On-Actions

### Event Definition

```
namespace = my_namespace

my_namespace.1 = {
    type = country_event
    hidden = yes              # IMPORTANT: hidden events must NOT have option = { }
    immediate = {
        # All effects run here
        my_scripted_effect = { PARAM = value }
    }
}
```

### Scheduling Events

```
# From another event or effect
trigger_event = { id = my_namespace.1 }          # Immediate
trigger_event = { id = my_namespace.1 days = 5 } # Delayed by 5 days
```

### On-Actions

```
# common/on_actions/my_on_actions.txt

# Monthly trigger (no scope)
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

# Yearly per-country (country scope)
on_yearly_pulse_country = {
    on_actions = { my_yearly_action }
}
```

### Key On-Actions

| On-Action | Scope | Fires |
|-----------|-------|-------|
| `on_game_start` | None | Once at start |
| `on_monthly_pulse` | None | Every month |
| `on_yearly_pulse_country` | Country | Every year per country |
| `on_building_built` | Building | When building constructed |
| `on_acquired_technology` | Country | When tech researched |

---

## Technology Overrides

Use `REPLACE:` prefix to override vanilla tech:

```
REPLACE:urban_planning = {
    era = era_1
    texture = "gfx/interface/icons/invention_icons/urban_planning.dds"
    category = society
    modifier = {
        state_market_access_price_impact = -5    # Zeroes MAPI
    }
    unlocking_technologies = {
        urbanization
    }
    ai_weight = { value = 2 }
}
```

**Key**: `REPLACE:` completely replaces the vanilla definition. You must include ALL fields.

---

## GUI & Script Values

### Script Values for GUI Data Binding

```
# common/script_values/my_values.txt
# Scope: state (set by GuiScope)

my_gui_value = {
    value = 0
    if = {
        limit = { has_variable = my_data }
        add = var:my_data
    }
}

# Safe division
my_gui_ratio = {
    value = 0
    if = {
        limit = {
            has_variable = my_numerator
            has_variable = my_denominator
            var:my_denominator > 0
        }
        add = var:my_numerator
        divide = var:my_denominator
    }
}
```

### GUI-Context Reads

Script values evaluated in GUI context can read `sg:` price data that effects cannot:

```
stl_gui_local_price_coal = {
    value = 1
    sg:coal = { add = state_goods_pricier }
    multiply = 30    # base price
}
```

### Scripted GUIs (Tooltip Triggers)

```
# common/scripted_guis/my_guis.txt
my_tooltip = {
    scope = state
    is_shown = { always = yes }
    effect = {
        # Runs when tooltip is triggered (click/hover)
        my_scripted_effect = { GOODS = coal }
    }
}
```

### GUI Visibility

```
# In .gui files, use is_shown with script values
widget = {
    visible = "[GreaterThan_int32(GetScriptedValue('my_gui_value'), '(int32)0')]"
}
```

---

## Localization

### File Format

```yml
l_english:
 my_key:0 "My display text"
 my_building:0 "Trade Depot"
 my_modifier:0 "Export: Coal"
```

- Files must be UTF-8 with BOM
- Filename must end with `_l_english.yml`
- Located in `localization/english/`

### Special Characters

```yml
# Use literal characters, NOT Python unicode escapes
my_currency:0 "Cost: £50"          # CORRECT
my_currency:0 "Cost: \u00a350"     # WRONG - causes "Illegal localization break character"
```

### Dynamic Text

```yml
my_text:0 "Production: [State.GetScriptedValue('my_gui_value')|v1]"
my_goods:0 "[GetGoods('coal').GetName]"
```

---

## Common Pitfalls

### 1. Silent Failures

Many Clausewitz errors fail silently. The game will load and run, but your logic doesn't work:

| Issue | Symptom | Fix |
|-------|---------|-----|
| Missing BOM | File contents ignored | Always write UTF-8 with BOM |
| `if` in `value = { }` | Conditional math never runs | Use separate `set_variable` + `if` blocks |
| Bare `sg:X.property` | Returns 'none' | Use `value = { value = sg:X.property }` |
| `root.local_var:X` | Returns garbage | Never scope-prefix local_var |
| `while = { count = N }` | Silently fails | Use frontier list or unrolled loops |

### 2. Scope Confusion

```
# WRONG - where does this variable go?
every_scope_state = {
    set_variable = { name = my_total value = 0 }  # Set on EACH state!
}

# CORRECT - accumulate on country scope
set_variable = { name = my_total value = 0 }  # Country scope
every_scope_state = {
    root = {
        change_variable = { name = my_total add = prev.var:state_value }
    }
}

# EVEN BETTER - use global_var for cross-scope accumulation
set_global_variable = { name = my_total value = 0 }
market = {
    every_scope_country = {
        every_scope_state = {
            set_global_variable = {
                name = my_total
                value = { value = global_var:my_total add = var:my_value }
            }
        }
    }
}
```

### 3. Stale Variables

```
# WRONG - local_var may contain stale value from previous iteration
var:building_ref = {
    add_modifier = { name = my_mod multiplier = my_script_value }
}

# CORRECT - always set local_var immediately before add_modifier
set_local_variable = { name = my_amount value = var:computed_value }
var:building_ref = {
    add_modifier = { name = my_mod multiplier = my_script_value }
}
```

### 4. Price Data Context

```
# WRONG - returns garbage in effect context
my_scripted_effect = {
    set_local_variable = { name = price value = { value = sg:coal.state_goods_pricier } }
    # price is GARBAGE
}

# CORRECT - use sg: price data only in script_values (GUI context)
my_script_value = {
    value = 1
    sg:coal = { add = state_goods_pricier }
    multiply = 30
}
```

### 5. Building Creation Timing

```
# WRONG - causes assertion errors
on_game_start = {
    effect = {
        every_state = {
            create_building = { building = my_building level = 1 }  # CRASH
        }
    }
}

# CORRECT - use history file
# common/history/buildings/my_buildings.txt
BUILDINGS = {
    every_state = {
        create_building = { building = my_building level = 1 reserves = 1 }
    }
}
```

### 6. Division by Zero

Always guard divisions:

```
if = {
    limit = { var:denominator > 0.01 }
    set_variable = {
        name = ratio
        value = { value = var:numerator divide = var:denominator }
    }
}
```

### 7. GUI maximumsize

```
# WRONG - causes "Trying to reshape data model with negative offset -1"
maximumsize = { 440 -1 }

# CORRECT - use large finite value
maximumsize = { 440 2000 }
```

---

## Reference Patterns

### Batch Processing Pattern

Process large workloads across multiple days to avoid lag:

```
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
        limit = { var:batch_idx >= 1 NOT = { var:batch_idx >= 2 } }
        # Process batch 1
    }
    # ... more batches

    change_variable = { name = batch_idx add = 1 }
}
```

### EMA (Exponential Moving Average) Pattern

Smooth a value over time to prevent oscillation:

```
# EMA: blend 80% new + 20% old
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

### Rate Cap Pattern

Limit how fast a value can grow per cycle:

```
# Max 90% increase, floor 40
set_local_variable = {
    name = rate_cap
    value = { value = local_var:old_value multiply = 0.9 }
}
if = {
    limit = { NOT = { local_var:rate_cap >= 40 } }
    set_local_variable = { name = rate_cap value = 40 }
}
set_local_variable = {
    name = cap_upper
    value = { value = local_var:old_value add = local_var:rate_cap }
}
if = {
    limit = { local_var:new_value > local_var:cap_upper }
    set_local_variable = { name = new_value value = local_var:cap_upper }
}
```

### Conservation Normalization Pattern

Ensure totals balance (e.g., exports = imports):

```
# 1. Accumulate totals (use global_var for cross-scope)
set_global_variable = { name = sum_a value = 0 }
set_global_variable = { name = sum_b value = 0 }
market = {
    every_scope_country = {
        every_scope_state = {
            # accumulate into sum_a and sum_b
        }
    }
}

# 2. Compute scale factors
set_global_variable = { name = norm_a value = 1 }
set_global_variable = { name = norm_b value = 1 }
if = {
    limit = { global_var:sum_b > global_var:sum_a }
    set_global_variable = {
        name = norm_b
        value = { value = global_var:sum_a divide = global_var:sum_b }
    }
}

# 3. Apply: remove modifier, scale, re-apply
# IMPORTANT: set_local_variable before each add_modifier
```

### Bellman-Ford (Shortest Path) Pattern

Graph pathfinding using iterative relaxation:

```
# Initialize: source distance = 0, all others = infinity (no var)
save_scope_as = bf_source
set_variable = { name = stl_bf_dist value = 0 }

# Relaxation pass (repeat 7x for 7-hop reach)
every_scope_state = {
    limit = { has_variable = stl_bf_dist }
    every_neighbouring_state = {
        # edge_weight = friction
        # if source_dist + edge_weight < current_dist: update
    }
}
```

---

## 1.13 Migration Notes

| Pre-1.13 | 1.13.x | Notes |
|----------|--------|-------|
| `has_port` (state) | `has_port_state` | also new: `has_port_country`, `has_port_market` |
| convoys | gone | Merchant Marine covers civilian shipping; Supply Ships cover military |
| Man-o-War / Ironclad goods | removed from use | modifier types still registered; nothing produces/consumes them |
| `is_ruler` / `is_heir` | `is_ruler_of_own_country` / `is_heir_of_own_country` | character role rework |
| canals (`canal_type`) | straits (`common/strait_definitions`) | canal *buildings* remain |
| — | variable maps | added in hotfix 1.13.7 (see section above) |
| — | journal entry `widget = {}` GUI injection | sanctioned custom-GUI anchor points |

GUI files modified by 1.13 (full-file overrides of these are stale):
`building_details_panel.gui`, `goods_panel.gui`, `market_panel.gui`,
`production_methods.gui`, `topbar.gui`, and more. Prefer scripted widgets
(`gui/scripted_widgets/`) and `000_`-prefixed type overrides (GUI types are
first-loaded-wins, opposite of script's last-wins).

---

## Running Script By Hand / Useful Console Commands

**Vic3's console has NO generic effect-runner** (`effect ...` is a CK3
command; Vic3 replies "Unknown command"). To fire arbitrary script in-game,
ship it as a **decision** (`common/decisions`, country scope, one click in
the country panel) or a debug-gated event. This mod does exactly that:

- "Salty Transport: Run Syntax Probe" — variable-map syntax probe
- "Salty Transport: Toggle Debug Modifiers" — stl_debug_mode toggle

Console commands that DO exist (with `-debug_mode`):

```
script_docs      # dump effects/triggers/scopes docs to Documents/.../docs
DumpDataTypes    # dump GUI data types/functions to the same place
gui_editor       # inspect the widget tree (do NOT save from it)
switchlanguage english   # force-reload localization
observe          # release control / observer mode
```

Logs land in `Documents/Paradox Interactive/Victoria 3/logs/`:
`error.log` (script errors — keep at zero), `debug.log` (debug_log output).

---

## Reference Mods

| Mod | Workshop ID | Useful For |
|-----|------------|------------|
| ASE (Anbeeld's Stockpile Economy) | 3604047737 | Kill-all pattern, script_value multiplier, goods data access |
| LLWA (Logistics & Waterways) | 3032533792 | MAPI modifiers, building syntax, history files |
| ZTR (Zero to Ruler) | 3472248460 | 1.12 building patterns, REPLACE: tech syntax |
