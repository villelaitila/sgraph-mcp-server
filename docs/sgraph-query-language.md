# SGraph Query Language

A domain-specific filtering and dependency query language for hierarchical software architecture models. Originally implemented in Kotlin (softagram-engine), designed for interactive architecture exploration in the Softagram UI. Now ported to Python as part of the sgraph library.

This document serves as the authoritative reference for porting the language to Python (sgraph library) and exposing it as an MCP tool.

## 1. Overview

The query language operates on **ElementGraphModel** — a hierarchical tree of code elements (files, classes, functions, directories) with directed dependency edges (imports, function calls, type references, etc.).

**Core principle:** Queries never mutate the original model. Every operation produces a new filtered *view model* that references the original.

### Three Layers

```
Input string
    │
    ▼
┌─────────────────────┐
│  Expression Parser   │   Text → AST (recursive descent, priority-based)
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│    Rule Engine       │   Orchestrates rules, manages model lifecycle
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│       Rules          │   Individual filtering operations → new view model
└─────────────────────┘
```

---

## 2. Syntax Reference

### 2.1 Element Selection

#### Exact Path (quoted)
```
"/project/src/module/file.py"
```
- Quotes required, path starts with `/`
- Case-sensitive, direct tree lookup
- Fast path in the engine (no scanning)

#### Keyword Search (unquoted)
```
phone
Config
```
- No quotes → case-insensitive partial name match
- Searches element **names** (not full paths)
- Returns all matches with their descendants
- Suffix `$`: `phone$` matches names **ending** with "phone"

#### Wildcards (within quoted paths)
```
"/project/src/*"       Single-level: direct children only
"/project/src/**"      Recursive: all descendants
```

#### Root
```
"/"                    Entire model (all root-level elements)
```

#### Allowed Characters in Keywords
```
[*/:.,=& A-ZÅÄÖŨÜa-zåäöüũ0-9_+\-{}]+(\$)?
```
Includes Nordic characters and `{}` for C/C++ merged filenames like `callbacks.{cpp,h}`.

---

### 2.2 Attribute Filtering

Elements have arbitrary key-value attributes. The special attribute `type` refers to the element's built-in type (e.g., `file`, `dir`, `class`).

| Syntax | Meaning | Example |
|--------|---------|---------|
| `@attr` | Has attribute (any value) | `@compare`, `@impact` |
| `@attr=value` | Contains match (case-insensitive) | `@type=file`, `@compare=changed` |
| `@attr="exact"` | Exact match (quoted) | `@attr-with-dash="value "` |
| `@attr!=value` | Not equals (blacklist) | `@type!=dir`, `@binary!=A` |
| `@attr>number` | Greater than (numeric) | `@loc>500`, `@incoming_dep_count>10` |
| `@attr<number` | Less than (numeric) | `@code_churn_avg<100` |
| `@attr=~"regex"` | Regex partial match | `@path=~".*\.py$"` |
| `@@attr=value` | Dependency attribute filter | `@@type=ecom`, `@@compare=added` |

**Type detection:** If all values of an attribute are numeric, comparisons use numeric semantics. Otherwise, string contains/equality.

**Comma-separated alternatives:** `@attr=val1,val2` matches either value.

---

### 2.3 Dependency Queries

#### Direct Dependency (1-hop)
```
FROM --> TO            Directed: FROM uses TO
FROM -- TO             Undirected: either direction
```

FROM and TO can be:
- Exact paths: `"/src/web" --> "/src/db"`
- Attribute expressions: `@compare=added --> "/"`
- Wildcard: `"*"` (any element, converted to null internally)
- Combined: `"/path/@attr=value"` (path + attribute condition on the endpoint)

**Spaces around operators are required:** ` --> `, ` -- `

#### Dependency Type/Attribute Filtering
```
FROM -type-> TO                 Filter by dependency type
FROM -@attr-> TO                Filter by dependency attribute existence
FROM -@attr=value-> TO          Filter by attribute + value

FROM -type- TO                  Undirected variant
```

Text between arrows is interpreted as:
- Starting with `@`: attribute name (and optional `=value`)
- Otherwise: shorthand for `@type=text`

#### Chain Search (all multi-hop paths)
```
FROM ---> TO                    All directed chains
FROM --type-> TO                Chains filtered by type
```
- Finds ALL paths from FROM to TO, not just the shortest
- DFS with cycle detection, max depth 20
- Can be slow on dense graphs

#### Shortest Path (undirected BFS)
```
FROM --- TO
```
- Finds single shortest path, ignoring edge direction
- No attribute filtering
- Uses BFS (Bellman-Ford in the Kotlin implementation via JGraphT)

---

### 2.4 Logical Operators

#### AND (Sequential Filtering)
```
expr1 AND expr2
```
- Evaluates expr1 first, then applies expr2 to the **result** of expr1
- Semantics: chained filtering, not set intersection
- `result = expr2.evaluate(expr1.evaluate(model))`

#### OR (Union)
```
expr1 OR expr2
```
- Evaluates both expressions **independently** on the same input model
- Combines results via union
- `result = expr1.evaluate(model) ∪ expr2.evaluate(model)`

#### NOT (Complement)
```
NOT expr
```
- Evaluates expression against **totalModel** (the full unfiltered model)
- Subtracts result from current model
- `result = currentModel − expr.evaluate(totalModel)`

#### Parentheses
```
(expr)
```
- Controls evaluation order
- Nesting supported: `((a OR b) AND c)`

#### ONLY_USERS_OF
```
ONLY_USERS_OF("/path/to/element")
```
- Finds elements that depend **exclusively** on the given target

---

### 2.5 Parser Precedence

The parser tries expression types in this order (first match wins):

| Priority | Type | Pattern | Notes |
|----------|------|---------|-------|
| 1 | AND | `... AND ...` | Binds tighter than OR (counterintuitive) |
| 2 | OR | `... OR ...` | |
| 3 | Parentheses | `(...)` | |
| 4 | Shortest Path | `... --- ...` | Before chain/dep to avoid ambiguity |
| 5 | Chain Search | `... ---> ...` | Before dep search |
| 6 | Dep Search | `... --> ...` or `... -- ...` | |
| 7 | NOT | `NOT ...` | |
| 8 | Dep Attr | `@@attr=val` | Double @ for edges |
| 9 | Regex Match | `@attr=~"regex"` | |
| 10 | Equals | `@attr=val` | |
| 11 | Not Equals | `@attr!=val` | |
| 12 | Greater Than | `@attr>num` | |
| 13 | Less Than | `@attr<num` | |
| 14 | Only Users Of | `ONLY_USERS_OF(...)` | |
| 15 | Has Attribute | `@attr` | |
| 16 | Keyword/Path | fallback | Catches everything else |

**Precedence warning:** Because AND is tried before OR:
```
A OR B AND C  →  (A OR B) AND C    (NOT  A OR (B AND C))
```
Use parentheses to override: `A OR (B AND C)`.

---

## 3. Rule Engine (Orchestration)

The RuleEngine manages four rule slots:

| Parameter | Type | Purpose |
|-----------|------|---------|
| `expression` | Expression | Primary filter: which elements to select |
| `postFilter` | Expression | Post-filter: additional filtering on result |
| `depthRule` | DetailLevelRule | Depth limit (how many levels to show) |
| `depsRule` | DepsRule | Dependency expansion mode |

### Processing Pipeline

```
1. NODE SELECTION (expression)
   │
   ├─ Exact path → fast lookup, expand descendants
   └─ Other → expression.evaluate(model) → filtered model
   │
2. DEPENDENCY EXPANSION (depsRule)
   │
   ├─ level=0: None (just the matched elements)
   ├─ level=1: Internal deps only (within matched hierarchy)
   └─ level≥2: External deps (recursive)
       ├─ direction=FROM: incoming (who calls this?)
       ├─ direction=TO: outgoing (what does this use?)
       └─ direction=TO_FROM: both directions
   │
3. DETAIL LEVEL (depthRule)
   │
   ├─ depth=N: limit tree to N levels
   ├─ depthExpression: dynamic filter by type (e.g., @type=file)
   └─ Dependencies rewired to nearest visible ancestor
   │
4. POST-FILTER (postFilter)
   │
   └─ postFilter.evaluate(result) → final model
```

### View Model Pattern

```
totalModel (complete, unfiltered)
    │
    ├── filteredModel1 (expression filter)
    │       .totalModel → references original
    │       .highlightElements → matched elements
    │
    └── filteredModel2 (AND chain / post-filter)
            .totalModel → references original
            .highlightElements → this stage's matches
```

Key properties:
- `totalModel`: always the original unfiltered model (for NOT complement)
- `highlightElements`: elements the active filter selected ("in focus")
- `hasAllNodes`: false after filtering
- Descendant inclusion: most rules automatically include descendants of matches

---

## 4. Rule Details

### NodeContentFilteringRule (keyword/path lookup)

Three modes:
1. **Root `/`**: expand all direct children + descendants
2. **Exact path**: direct lookup, supports `*` (single-level) and `**` (recursive) wildcards
3. **Keyword**: case-insensitive partial name match, `$` suffix for ends-with

### AttributeContentFilteringRule (attribute filtering)

- Auto-detects numeric vs string attributes
- Whitelist mode: `@attr=value` (include matching)
- Blacklist mode: `@attr!=value` (exclude matching)
- Handles combined whitelist + blacklist
- Operates on highlight elements if available (scoped filtering)

### DependencyRule (direct deps: -->, --)

- Locates FROM and TO elements in totalModel
- Directed search: iterates outgoing from FROM or incoming from TO (chooses based on depth heuristic)
- Undirected search: iterates both directions
- Supports attribute restrictions on endpoints (`/path/@attr=value`)
- Returns MatchObjects with matched associations

### DependencyChainRule (transitive chains: --->)

- Recursive DFS from FROM, looking for TO or its ancestors
- Cycle prevention via `alreadyProcessed` set
- Max recursion depth: 20
- On success: constructs all intermediate elements and associations
- Uses exception-based signaling (`ChainFound`) to break recursion

### UndirectedShortestPathRule (BFS: ---)

- For leaf elements: builds JGraphT `SimpleGraph`, runs Bellman-Ford
- For non-leaf elements: falls back to undirected DependencyRule
- Returns single shortest path (not all paths)
- No attribute filtering

### DetailLevelRule (depth limiting)

Two modes:
1. **Static depth** (integer): slash-count-based pruning
2. **Dynamic** (@type expression): filter by element type, rewire dependencies to nearest visible ancestor

Dependency rewiring: when a node is pruned, its edges are moved to its nearest visible parent.

---

## 5. Real-World Query Examples

### Basic Navigation
```
phone                                      Search by keyword
"/sf/app/phone"                            Exact path lookup
"/sf/app/*"                                Direct children of /sf/app
"/sf/app/**"                               All descendants of /sf/app
```

### Attribute Filtering
```
@type=file                                 All files
@loc>500                                   Large files (>500 LOC)
@compare=changed                           Changed elements (in diff model)
@compare=added                             Added elements
@author_count_365=1                        Single-author elements
```

### Direct Dependencies
```
"/src/web" --> "/src/db"                   Web module depends on DB?
"/" --> @compare=added                     What uses newly added elements?
@compare=changed --> "/"                   What do changed elements depend on?
"/A" -import-> "/B"                        Only import-type deps from A to B
@compare=added -@compare-> "/"             New deps from added elements
```

### Transitive Analysis
```
"/a" ---> "/b"                             All chains from a to b
"/ext/header.h" ---> "/ext/target"         Transitive include chains
```

### Shortest Path
```
"/module/child1" --- "/module/child2"      Shortest path between elements
```

### Composite Queries
```
"/sf/app" AND @type=file                   Files under /sf/app
"/sf/app" AND NOT @type=dir                Non-directories under /sf/app
"/sf/app" AND @binary_attribute=A          Elements in /sf/app with attr A
(@HSE=2 OR xyz) AND (@IDO)                 Complex multi-condition
"/" AND NOT "/ext"                         Everything except /ext
@compare=added OR @compare=removed         Union of added and removed
```

### Change Impact Analysis (compound query from ChangeGraphService)
```
@_attr_diff_hash
OR "/" --> @_attr_diff_hash
OR "/" --> @compare=added
OR "/" --> @compare=removed
OR @compare=added -@compare-> "/"
OR @compare=removed -@compare-> "/"
OR @compare=changed -@compare-> "/"
OR @compare=added
OR @compare=removed
```

This single query finds: modified files, their users, dependencies targeting new/removed elements, changed dependencies, and all added/removed elements.

---

## 6. Comparison: SGraph QL vs Cypher

| Aspect | SGraph QL | Cypher |
|--------|-------------|--------|
| **Design goal** | Architecture filtering & exploration | General graph querying |
| **Model** | Hierarchical tree + edges | Flat labeled property graph |
| **Paradigm** | Filter-based (whittle down model) | Match-based (pattern extraction) |
| **Hierarchy** | Native (paths, descendants auto-included) | Explicit `:CONTAINS` edges |
| **Output** | Filtered sub-model (tree + edges) | Tabular result set (DataFrame) |
| **Transitive** | `---> ` (all chains, DFS) | `*1..N` (variable-length paths) |
| **Shortest path** | `---` (built-in) | Requires `shortestPath()` function |
| **Aggregation** | None (model-based) | `count()`, `sum()`, `GROUP BY` |
| **Attribute filter** | `@attr=value` (first-class) | `WHERE n.attr = value` |
| **Dep type filter** | `-type->` (inline) | `[:type]` (relationship pattern) |
| **Change analysis** | `@compare=added/changed/removed` | Manual attribute checks |
| **Performance** | Fast (native model traversal) | Slower (sPyCy, index build) |
| **Standardization** | Proprietary | openCypher standard |

**When to use which:**
- **SGraph QL**: architecture exploration, filtering views, change impact, dependency arrows between modules — anything that produces a *sub-model* as output
- **Cypher**: aggregation, counting, complex joins, tabular reports, transitive queries with depth control

---

## 7. Porting Strategy: Kotlin → Python

### What Exists in Python (sgraph library)

| Capability | Python status | Location |
|------------|--------------|----------|
| Element tree traversal | Done | `SElement.traverseElements()` |
| Path-based element lookup | Done | `SGraph.findElementFromPath()` |
| Keyword name search | Done | `ModelApi.getElementsByName()` |
| Outgoing/incoming iteration | Done | `SElement.outgoing`, `.incoming` |
| Subgraph extraction | Done | `ModelApi.filter_model()` |
| Dependency between sets | Done | `ModelApi.query_dependencies_between()` |
| Attribute access | Done | `SElement.attrs`, `.getType()` |
| Cypher backend | Done | `sgraph.cypher` |
| CLI filter (name + deps) | Partial | `sgraph.cli.filter` |
| Expression parser | **Not started** | — |
| Rule engine | **Not started** | — |
| View model pattern | **Not started** | — |

### Proposed Architecture

```
sgraph/query/
    __init__.py          # Public API: query(model, expression_str) → SGraph
    parser.py            # Expression parser (recursive descent)
    expressions.py       # Expression AST nodes (dataclasses)
    rules.py             # Rule implementations
    engine.py            # Rule engine orchestration
```

### Implementation Priority (by impact)

| Phase | Features | Dependencies | Effort |
|-------|----------|-------------|--------|
| **P1** | Keyword + exact path, `@attr=value`, AND/OR/NOT, parentheses | SElement, SGraph | Small |
| **P2** | `-->` and `--` (direct deps), `-type->` filtering | P1 + ModelApi | Medium |
| **P3** | `@attr>N`, `@attr<N`, `@attr!=value`, `@attr=~"regex"`, `@@attr` | P1 | Small |
| **P4** | `--->` (chain search), `---` (shortest path) | P2 + graph algo | Medium |
| **P5** | Depth rule, post-filter, highlight elements, view model | P1-P4 | Large |

### Key Simplification for MCP

The MCP tool doesn't need the full view model pattern (that's for the UI). The MCP version can:

1. Parse the expression string
2. Evaluate it against the model → produce a filtered SGraph
3. Serialize the result as JSON (elements + associations)

No need for: highlight elements, depth expression, UI-specific rewiring, incremental model updates.

### Proposed MCP Tool Schema

```python
class SGraphQueryInput(BaseModel):
    model_id: Optional[str] = None
    expression: str = Field(
        description='SGraph query expression. Examples: '
        '"/src/web" --> "/src/db", '
        '@type=file AND @loc>500, '
        '"/" AND NOT "/External"'
    )
    deps_level: int = Field(
        default=0,
        description="0=no deps, 1=internal, 2=direct external, 3=transitive"
    )
    direction: Literal["from", "to", "both"] = Field(
        default="both",
        description="Dependency direction (for deps_level >= 2)"
    )
    detail_level: Optional[int] = Field(
        default=None,
        description="Max hierarchy depth in result (None=unlimited)"
    )
```

---

## 8. Source Files (Kotlin, softagram-engine)

| File | Purpose |
|------|---------|
| `expressions/Expression.kt` | Parser entry point, cascading dispatch |
| `expressions/Operator.kt` | Operator enum (`-->`, `--`, `--->`, `---`, etc.) |
| `expressions/KeywordOrExactPathExpression.kt` | Keyword/path fallback parser |
| `expressions/DepSearchExpression.kt` | `-->` and `--` parser |
| `expressions/ChainSearchExpression.kt` | `--->` parser |
| `expressions/UndirectedShortestPathExpression.kt` | `---` parser |
| `expressions/AndExpression.kt` | AND parser + sequential eval |
| `expressions/OrExpression.kt` | OR parser + union eval |
| `expressions/NotExpression.kt` | NOT parser + complement eval |
| `expressions/ParExpression.kt` | Parentheses grouping |
| `expressions/EqualsExpression.kt` | `@attr=value` |
| `expressions/NotEqualsExpression.kt` | `@attr!=value` |
| `expressions/GtExpression.kt` | `@attr>number` |
| `expressions/LtExpression.kt` | `@attr<number` |
| `expressions/RegExpMatchesToAttributeExpression.kt` | `@attr=~"regex"` |
| `expressions/DepAttrEqualsExpression.kt` | `@@attr=value` (edge attrs) |
| `expressions/HasAttrExpression.kt` | `@attr` (existence) |
| `expressions/OnlyDependsOnExpression.kt` | `ONLY_USERS_OF(...)` |
| `rule/RuleEngine.kt` | Orchestration, dependency expansion |
| `rule/NodeContentFilteringRule.kt` | Name/path filtering |
| `rule/AttributeContentFilteringRule.kt` | Attribute value filtering |
| `rule/DependencyRule.kt` | Direct dep matching |
| `rule/DependencyChainRule.kt` | Transitive chain DFS |
| `rule/UndirectedShortestPathRule.kt` | BFS shortest path |
| `rule/DetailLevelRule.kt` | Depth limiting + dep rewiring |
| `rule/DepsRule.kt` | Dependency mode enum |
| `rule/OnlyDependsOnRule.kt` | Exclusive dependency rule |
| `tests/.../ExpressionTest.kt` | Parser unit tests |
| `tests/.../RuleEngineTest.kt` | Integration tests (750+ lines) |
