# Cypher Query Examples for sgraph Models

Reference guide for using the `sgraph_cypher_query` MCP tool. All examples are tested against real Softagram analysis models.

## Data Model

### Nodes (code elements)

| Node label | Meaning | Examples |
|---|---|---|
| `:file` | Source file | `session.ts`, `Program.cs`, `main.py` |
| `:dir` | Directory | `src`, `components`, `Services` |
| `:class` | Class definition | `SessionExporter`, `ApiClient` |
| `:function` | Function / method | `BuildRequest(params QQQ)`, `LoadDefault(params)` |
| `:property` | Class property / field | `name`, `value`, `config` |
| `:variable` | Variable declaration | `DEFAULT_TIMEOUT`, `router` |
| `:const` | Constant | `MAX_RETRIES`, `API_URL` |
| `:interface` | Interface definition | `IConfigLoader`, `IExporter` |
| `:interface_export` | Exported interface (TypeScript) | `SessionMetadata`, `SegmentData` |
| `:function_export` | Exported function (TypeScript) | `useAutoSave`, `useCompactTable` |
| `:class_export` | Exported class (TypeScript) | `WorkerPool` |
| `:enum` | Enum type | `SegmentationMethod` |
| `:enumvalue` | Enum member | `Manual`, `Auto` |
| `:repository` | Repository root | `softagram-live`, `CrossTranslate` |
| `:vulnerability` | Known CVE / advisory | `axios_GHSA-43fc-jf86-j433` |
| `:deprecation` | Deprecated package | `eslint deprecated in 8.57.1` |
| `(no label)` | Elements without a type attribute | External packages, intermediates |

### Relationships (dependencies)

| Relationship type | Meaning |
|---|---|
| `:import` | ES6/Python import statement |
| `:function_ref` | Function call reference |
| `:property_ref` | Property access |
| `:typeref` | Type reference (e.g., type annotation) |
| `:typeref_member` | Member type reference |
| `:inherits` | Class/interface inheritance |
| `:new` | Constructor call (`new X()`) |
| `:packagejson` | npm production dependency |
| `:dev_packagejson` | npm dev dependency |
| `:package_reference` | NuGet / .NET package reference |
| `:project_reference` | .NET project-to-project reference |
| `:sln_to_project` | .NET solution to project |
| `:targets_to` | MSBuild target reference |
| `:css_import` | CSS `@import` |
| `:re_export` | Re-export (`export { x } from ...`) |
| `:func_ref` | Alternate function reference |
| `:import_ref` | Aliased import reference |
| `:CONTAINS` | Parent-child hierarchy (only with `include_hierarchy=true`) |

### Node Properties

Every node has `name` and `path`. Additionally:

| Property | On types | Description |
|---|---|---|
| `loc` | `:file` | Lines of code |
| `line_start`, `line_end` | functions, classes | Source location |
| `access_modifier` | functions, classes | `public`, `private`, `export` |
| `params` | `:function` | Parameter signature |
| `description` | various | JSDoc / docstring text |
| `hash` | `:file` | Content hash |
| `author_count_N` | `:file` | Distinct authors in last N days (1, 7, 30, 90, 180, 365) |
| `commit_count_N` | `:file` | Commits in last N days |
| `days_since_modified` | `:file` | Staleness indicator |
| `bug_fix_ratio_N` | `:file` | Ratio of bug-fix commits in last N days |
| `architecture_modularity` | `:dir` | Modularity score (0-100) |
| `version` | external packages | Package version |
| `severity` | `:vulnerability` | `low`, `medium`, `high`, `critical` |
| `score` | `:vulnerability` | CVSS score |
| `external_id` | `:vulnerability` | GHSA / CVE identifier |
| `loc_typescript`, `loc_python`, ... | `:repository` | Per-language LOC breakdown |

### Relationship Properties

| Property | On types | Description |
|---|---|---|
| `pos` | `:import`, `:function_ref` | Source position (line:column) |
| `imported_as` | `:import` | Aliased import name |

---

## Basic Queries

### Find elements by name

```cypher
MATCH (n) WHERE n.name = 'session.ts'
RETURN n.name, n.path, labels(n)
```

### Find elements by name pattern

```cypher
MATCH (n) WHERE n.name STARTS WITH 'use'
RETURN n.name, n.path, labels(n) LIMIT 20
```

```cypher
MATCH (n) WHERE n.name CONTAINS 'Config'
RETURN n.name, labels(n) AS type, n.path LIMIT 20
```

### List all files in a directory

```cypher
MATCH (f:file) WHERE f.path STARTS WITH '/project/src/components/'
RETURN f.name, f.loc ORDER BY f.name
```

---

## Dependency Analysis

### What does a file import?

```cypher
MATCH (f:file)-[:import]->(dep)
WHERE f.name = 'session.ts'
RETURN dep.name, dep.path
```

### What imports a specific module?

```cypher
MATCH (caller)-[:import]->(target)
WHERE target.name = 'vue'
RETURN caller.name, caller.path ORDER BY caller.name
```

### Most imported targets (fan-in)

```cypher
MATCH (caller)-[:import]->(target)
RETURN target.name, count(caller) AS importers
ORDER BY importers DESC LIMIT 15
```

### Files with most imports (fan-out)

```cypher
MATCH (f:file)-[:import]->(dep)
RETURN f.name, count(dep) AS imports
ORDER BY imports DESC LIMIT 10
```

### All dependency types from a file

```cypher
MATCH (f)-[r]->(target)
WHERE f.name = 'session.ts' AND type(r) <> 'CONTAINS'
RETURN type(r) AS deptype, target.name, target.path
ORDER BY deptype
```

### Count dependencies by type

```cypher
MATCH ()-[r]->()
RETURN type(r) AS deptype, count(r) AS cnt
ORDER BY cnt DESC
```

### Does module A depend on module B?

```cypher
MATCH (a)-[r]->(b)
WHERE a.path STARTS WITH '/project/src/web/'
  AND b.path STARTS WITH '/project/src/db/'
  AND type(r) <> 'CONTAINS'
RETURN type(r) AS deptype, count(r) AS cnt
ORDER BY cnt DESC
```

### Dependencies between two specific files

```cypher
MATCH (a)-[r]->(b)
WHERE a.name = 'session.ts' AND b.name = 'types.ts'
RETURN type(r) AS deptype, count(r) AS cnt
```

---

## Transitive Dependencies

### 2-hop import chain from a file

```cypher
MATCH (a:file)-[:import*1..2]->(b)
WHERE a.name = 'session.ts'
RETURN DISTINCT b.name, b.path LIMIT 20
```

### 3-hop transitive function calls

```cypher
MATCH (a)-[:function_ref*1..3]->(b:function)
WHERE a.name = 'main.py'
RETURN DISTINCT b.name, b.path LIMIT 20
```

### Find all paths between two elements (up to 4 hops)

```cypher
MATCH path = (a)-[*1..4]->(b)
WHERE a.name = 'App.vue' AND b.name = 'session.ts'
RETURN length(path) AS hops, [n IN nodes(path) | n.name] AS chain
LIMIT 10
```

---

## Circular Dependencies

### Direct circular imports (A -> B -> A)

```cypher
MATCH (a:file)-[:import]->(b:file)-[:import]->(a)
WHERE a.path < b.path
RETURN a.name AS file1, b.name AS file2
```

### Circular dependencies at directory level

Use `include_hierarchy=true` for this:

```cypher
MATCH (d1:dir)-[:CONTAINS]->(f1:file)-[:import]->(f2:file)<-[:CONTAINS]-(d2:dir)
WHERE d1 <> d2
WITH d1, d2, count(*) AS deps
MATCH (d2)-[:CONTAINS]->(g1:file)-[:import]->(g2:file)<-[:CONTAINS]-(d1)
WITH d1, d2, deps, count(*) AS back_deps
WHERE deps > 0 AND back_deps > 0
RETURN d1.name AS dir1, d2.name AS dir2, deps AS forward, back_deps AS backward
ORDER BY forward + backward DESC
```

---

## Inheritance & Type Hierarchy

### All inheritance relationships

```cypher
MATCH (child)-[:inherits]->(parent)
RETURN child.name AS subclass, parent.name AS superclass
ORDER BY superclass
```

### Full inheritance chain (up to 3 levels)

```cypher
MATCH (c)-[:inherits*1..3]->(ancestor)
WHERE c.name = 'SessionExporter'
RETURN ancestor.name, ancestor.path
```

### Classes implementing an interface

```cypher
MATCH (impl)-[:inherits]->(iface)
WHERE iface.name CONTAINS 'IExporter'
RETURN impl.name, iface.name
```

### Most-extended base classes/interfaces

```cypher
MATCH (child)-[:inherits]->(parent)
RETURN parent.name, count(child) AS subclasses
ORDER BY subclasses DESC LIMIT 10
```

---

## Function & Method Analysis

### Most-referenced functions (hotspots)

```cypher
MATCH (caller)-[:function_ref]->(target:function)
RETURN target.name, count(caller) AS refs
ORDER BY refs DESC LIMIT 10
```

### What calls a specific function?

```cypher
MATCH (caller)-[:function_ref]->(target)
WHERE target.name CONTAINS 'BuildRequest'
RETURN caller.name, caller.path
```

### Functions that call the most other functions

```cypher
MATCH (f:function)-[:function_ref]->(target)
RETURN f.name, count(target) AS calls
ORDER BY calls DESC LIMIT 10
```

### Constructor usage (who creates instances?)

```cypher
MATCH (caller)-[:new]->(target)
RETURN target.name AS class, caller.name AS instantiated_by
```

---

## Package & External Dependencies

### npm production dependencies

```cypher
MATCH (pkg)-[:packagejson]->(dep)
RETURN dep.name, dep.version LIMIT 20
```

### npm dev dependencies

```cypher
MATCH (pkg)-[:dev_packagejson]->(dep)
RETURN dep.name LIMIT 20
```

### .NET NuGet packages

```cypher
MATCH (proj)-[:package_reference]->(pkg)
RETURN proj.name AS project, pkg.name AS package
```

### .NET project references (inter-project)

```cypher
MATCH (a)-[:project_reference]->(b)
RETURN a.name AS from_project, b.name AS to_project
```

### .NET solution structure

```cypher
MATCH (sln)-[:sln_to_project]->(proj)
RETURN sln.name AS solution, proj.name AS project
```

---

## Git Metrics & Code Health

### Large files (lines of code)

```cypher
MATCH (f:file)
WHERE f.loc > 500
RETURN f.name, f.loc, f.path
ORDER BY f.loc DESC LIMIT 20
```

### Stale files (not modified recently)

```cypher
MATCH (f:file)
WHERE f.days_since_modified > 365
RETURN f.name, f.days_since_modified, f.loc
ORDER BY f.days_since_modified DESC LIMIT 20
```

### Bus factor: single-author files with significant code

Note: git attributes are strings, use string comparison.

```cypher
MATCH (f:file)
WHERE f.author_count_365 = '1' AND f.loc > 100
RETURN f.name, f.loc, f.days_since_modified
ORDER BY f.loc DESC LIMIT 20
```

### Most actively changed files (last 90 days)

```cypher
MATCH (f:file)
WHERE f.commit_count_90 IS NOT NULL
RETURN f.name, f.commit_count_90, f.loc, f.bug_fix_ratio_90
ORDER BY f.commit_count_90 DESC LIMIT 10
```

### Bug-prone files (high bug-fix ratio)

```cypher
MATCH (f:file)
WHERE f.bug_fix_ratio_90 > '0'
RETURN f.name, f.bug_fix_ratio_90, f.commit_count_90, f.loc
ORDER BY f.bug_fix_ratio_90 DESC LIMIT 10
```

---

## Architecture & Modularity

### Module-level dependency summary

```cypher
MATCH (a:dir)-[:CONTAINS]->(af:file)-[r]->(bf:file)<-[:CONTAINS]-(b:dir)
WHERE a <> b AND type(r) <> 'CONTAINS'
RETURN a.name AS from_module, b.name AS to_module, count(r) AS deps
ORDER BY deps DESC LIMIT 20
```

(Requires `include_hierarchy=true`)

### Directory modularity scores

```cypher
MATCH (d:dir)
WHERE d.architecture_modularity IS NOT NULL
RETURN d.name, d.architecture_modularity
ORDER BY d.architecture_modularity DESC LIMIT 15
```

### Repository-level language breakdown

```cypher
MATCH (r:repository)
RETURN r.name,
       r.loc_typescript, r.loc_csharp, r.loc_python,
       r.loc_vuejs_component, r.loc_javascript
```

### Total LOC per directory

```cypher
MATCH (d:dir)-[:CONTAINS]->(f:file)
WHERE f.loc IS NOT NULL
RETURN d.name, count(f) AS files, sum(toInteger(f.loc)) AS total_loc
ORDER BY total_loc DESC LIMIT 15
```

(Requires `include_hierarchy=true`)

---

## Security & Vulnerabilities

### All known vulnerabilities

```cypher
MATCH (v:vulnerability)
RETURN v.name, v.severity, v.score, v.external_id
ORDER BY v.score DESC
```

### High-severity vulnerabilities only

```cypher
MATCH (v:vulnerability)
WHERE v.severity = 'high' OR v.severity = 'critical'
RETURN v.name, v.severity, v.score, v.external_id
```

### Deprecated packages

```cypher
MATCH (d:deprecation)
RETURN d.name, d.alternative, d.path
```

---

## Hierarchy Queries

These require `include_hierarchy=true`.

### What does a directory contain?

```cypher
MATCH (d:dir)-[:CONTAINS]->(child)
WHERE d.name = 'src'
RETURN child.name, labels(child) AS type
ORDER BY child.name
```

### Multi-level containment (dir -> dir -> file)

```cypher
MATCH (d:dir)-[:CONTAINS*1..2]->(f:file)
WHERE d.name = 'src'
RETURN f.name, f.path LIMIT 20
```

### Deep nesting: find files buried N levels deep

```cypher
MATCH path = (root:dir)-[:CONTAINS*4..6]->(f:file)
WHERE root.name = 'src'
RETURN length(path) AS depth, f.name, f.path
ORDER BY depth DESC LIMIT 10
```

### Find orphan files (in no recognized directory)

```cypher
MATCH (f:file)
WHERE NOT ()-[:CONTAINS]->(f)
RETURN f.name, f.path LIMIT 10
```

---

## Aggregation & Statistics

### Dependency count per file (combined fan-in + fan-out)

```cypher
MATCH (f:file)-[r]->()
WHERE type(r) <> 'CONTAINS'
WITH f, count(r) AS fan_out
OPTIONAL MATCH ()-[r2]->(f)
WHERE type(r2) <> 'CONTAINS'
RETURN f.name, fan_out, count(r2) AS fan_in
ORDER BY fan_out + fan_in DESC LIMIT 15
```

### Element type distribution

```cypher
MATCH (n)
RETURN labels(n) AS type, count(n) AS cnt
ORDER BY cnt DESC
```

### Files per directory

```cypher
MATCH (d:dir)-[:CONTAINS]->(f:file)
RETURN d.name, count(f) AS file_count
ORDER BY file_count DESC LIMIT 15
```

(Requires `include_hierarchy=true`)

---

## Performance Tips

1. **`include_hierarchy=false` (default)** is significantly faster. Only enable for `:CONTAINS` queries.
2. **Use `LIMIT`** — always add a limit, especially on first exploration.
3. **Variable-length paths `*1..N`** — keep N small (2-4). Large N on dense graphs is slow.
4. **Filter early** — put `WHERE` conditions on the first `MATCH` pattern, not after collecting everything.
5. **Prefer `STARTS WITH`** over `CONTAINS` for path prefix filtering — it's faster.
6. **String attributes** — git metrics (`author_count_365`, etc.) are stored as strings. Use string comparison or `toInteger()` for aggregation.
7. **First query is slower** — the Cypher backend builds an in-memory index on first use. Subsequent queries on the same model are fast.
