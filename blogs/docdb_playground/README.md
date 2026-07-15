# DocumentDB Playground User Guide

How to use DocumentDB Playground to test queries against a live Amazon DocumentDB cluster.

## Important Disclaimers

> **Do not enter sensitive or confidential data.** Do not use DocumentDB Playground with production data, personally identifiable information (PII), credentials, proprietary business data, or any information subject to confidentiality obligations. Use synthetic or anonymized data only.

> **You are responsible for validating all output.** Users maintain full responsibility for code review, correctness verification, security validation, and any consequences of applying queries or indexes to production systems. DocumentDB Playground does not validate queries for security, performance impact, or correctness against your specific data.

## Overview

DocumentDB Playground is a browser-based tool for testing queries against a live Amazon DocumentDB cluster using the MongoDB Query Language (MQL). Define a data model, write a query, and run it against a live Amazon DocumentDB cluster - all in one interface.

- DocumentDB Playground connects to a live Amazon DocumentDB endpoint - queries execute against real infrastructure.
- Write operations (`insert`, `update`, `delete`, `drop`) are not supported.
- DDL operations such as `createCollection` are not supported.
- The use of variables (e.g. `var state = db.states.findOne({"name": "New York"});`) is not supported.

## Panels

The interface is divided into multiple panels.

## Data Model (Input)

Content must use the `collections` assignment format:

```
collections = {
  "orders": [
    { "_id": 1, "customerId": "C001", "status": "shipped", "total": 149.99 },
    { "_id": 2, "customerId": "C002", "status": "pending", "total": 74.50 }
  ]
}
```

To define multiple collections, add more keys to the object:

```
collections = {
  "customers": [
    { "_id": "C001", "name": "Alice" }
  ],
  "orders": [
    { "_id": 1, "customerId": "C001", "total": 149.99 }
  ]
}
```

### Collection limits

| Constraint | Value |
| --- | --- |
| Max collections per request | 5 |
| Collection name characters | Alphanumeric and underscores only |
| Max collection name length | 57 characters |
| Reserved prefix | `system.` prefix is not allowed |

> **Important - required format:** The data model must start with `collections = { ... }`.

## Query (Input)

All queries must use the MQL shell format:

```
db.<collection>.<operation>(...)
```

### Supported operations

| Operation | Example |
| --- | --- |
| `find()` | `db.orders.find({ status: "shipped" })` |
| `aggregate()` | `db.orders.aggregate([{ $match: { status: "shipped" } }])` |
| `explain()` | `db.orders.find({}).explain("executionStats")` |

> **Restriction:** Write operations are not supported.

### Using explain()

`explain()` can be used with `find()` or `aggregate()` and accepts one of the following verbosity modes:

| Mode | Example |
| --- | --- |
| none | `db.orders.find({}).explain()` |
| `"queryPlanner"` | `db.orders.find({}).explain("queryPlanner")` |
| `"executionStats"` | `db.orders.find({}).explain("executionStats")` |

## Indexes (Input)

Each index must use `createIndex` format:

```
db.<collection>.createIndex({ field: 1 })
```

Examples:

```
// Single-field ascending index
db.orders.createIndex({ status: 1 })

// Compound index
db.orders.createIndex({ customerId: 1, status: 1, total: -1 })

// Geospatial index (required for any geospatial query)
db.locations.createIndex({ coordinates: "2dsphere" })
```

Leave the Indexes panel empty to run queries without custom indexes

## Results (Output)

After running a query, the Results panel displays the returned documents as formatted JSON. There is no default limit on the number of documents returned - results are bounded by the 15-second query timeout and any `.limit()` you include in your query.

> **Tip:** Use `.limit()` to control result size when working with large collections.

## Sample Data

Select a sample from the Select data model dropdown in the Data Model panel to auto-populate the editor. The Query panel is pre-populated with a basic `find({})` against the first collection in the model.

| Sample | Description |
| --- | --- |
| `ECommerce` | Orders, customers, and product data for an online store. |
| `Social Media` | Users, posts, and engagement data for a social platform. |
| `Games` | Game library data with scores and player profiles. |

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| Word wrap | Off | Wraps long lines in all editors instead of scrolling horizontally. |
| Visual mode | - | Switch between light and dark themes. |

## Rate & Session Limits

### Rate limits

| Limit | Value |
| --- | --- |
| Request rate per IP | 30 requests / minute |

### Per-request limits

The following limits apply to each individual query.

| Limit | Value |
| --- | --- |
| Max queries per session | 500 |
| Max data per request | 1 MB |
| Max collections per request | 5 |
| Query execution timeout | 15 seconds |

### Session limits

| Limit | Value |
| --- | --- |
| Session inactivity timeout | 30 minutes |
| Session absolute timeout | 2 hours |
| Session on page exit | Immediately flushed |

> **Note:** There is no way to save or restore a session. Copy the contents of the Data Model, Query, and Indexes panels before leaving the page if you want to preserve your work.

## Limitations

### Data model

- Must use the `collections = { ... }` assignment syntax.
- Values must be arrays of valid JSON/BSON documents.
- Maximum of 5 collections per request.
- Collection names must be alphanumeric or underscore, up to 57 characters; the `system.` prefix is reserved and not allowed.
- Total serialized size of collection data must not exceed 1 MB per request.

### Query panel

- Only `find()`, `aggregate()`, and `explain()` are supported.
- Query must use the format `db.<collection>.<operation>(...)`.
- Only one query can be run at a time.

### Indexes panel

- Only `createIndex` is accepted.
- Each statement must use the format `db.<collection>.createIndex(...)`.

### Unsupported operators and stages

While the following operators and aggregation stages are supported by Amazon DocumentDB, they are not supported in DocumentDB Playground.

| Operator / Stage | Category |
| --- | --- |
| `$out` | Aggregation |
| `$merge` | Aggregation |
| `$vectorSearch` | Aggregation |
| `$changeStream` | Change stream |
| `$currentOp` | Admin |
| `$collStats` | Admin |
| `$indexStats` | Admin |

> **Note - geospatial queries:** Any geospatial query requires a geospatial index to be defined in the Indexes panel before the query runs (`$geoIntersects`, `$near`, `$nearSphere`, etc.).
>
> ```
> db.locations.createIndex({ coordinates: "2dsphere" })
> ```

---

*DocumentDB Playground — Updated July 2026*
