# Financial Analytics Graph Nodes

## 1. Intent/Time Parser Node
**Input**: Raw user query text
**Output**: `UserQuery` with parsed intents, time ranges, and dimensions
**Dependencies**: None
**Description**:
- Uses regex and/or LLM to extract:
  - Time ranges (e.g., "last month", "Q2 2025")
  - Intent (spending analysis, comparison, trend)
  - Metrics (sum, average, count)
  - Dimensions (category, time period, etc.)

## 2. Category Resolver Node
**Input**: `UserQuery` with raw categories/tags
**Output**: `UserQuery` with canonical categories
**Dependencies**: Embeddings model, category mapping
**Description**:
- Maps natural language terms to canonical categories
- Uses semantic similarity for fuzzy matching
- Handles synonyms (e.g., "eating out" → "restaurants")

## 3. SQL Planner Node
**Input**: `UserQuery` with parsed intents
**Output**: `SQLPlan` with parameterized query
**Dependencies**: Database schema, safe column/table whitelist
**Description**:
- Generates safe, parameterized SQL based on intents
- Validates against allowed tables/columns
- Handles time range filtering and grouping

## 4. DB Executor Node (MCP)
**Input**: `SQLPlan`
**Output**: `ResultFrame` with query results
**Dependencies**: SQLite database connection
**Description**:
- Executes the SQL query
- Validates query safety
- Returns results in a standardized format

## 5. Chart Node (MCP)
**Input**: `ResultFrame`, `ChartSpec`
**Output**: Path to generated chart image
**Dependencies**: Matplotlib, Plotly
**Description**:
- Generates visualizations based on query results
- Supports multiple chart types (bar, line, pie)
- Handles formatting and styling

## 6. Answer Synthesizer Node
**Input**: `ResultFrame`, `ChartSpec`
**Output**: `Answer` with markdown and artifacts
**Dependencies**: None
**Description**:
- Formats results into natural language
- Includes relevant charts and data summaries
- Adds caveats and explanations

## 7. Guardrail/Error Node
**Input**: Any node's error state
**Output**: `Answer` with error message
**Dependencies**: None
**Description**:
- Catches and handles errors gracefully
- Provides helpful error messages
- Suggests corrections when possible

## Edge Conditions
- If intent parsing fails → Route to Guardrail
- If SQL generation fails → Route to Guardrail
- If query returns no results → Route to Guardrail
- If chart generation fails → Fall back to table view

## State Flow
```
User Query
    │
    ▼
[Intent/Time Parser]
    │
    ▼
[Category Resolver] ───┐
    │                  │
    ▼                  │
[SQL Planner]         │
    │                  │
    ▼                  │
[DB Executor] ←───────┘
    │
    ▼
[Chart Node] (optional)
    │
    ▼
[Answer Synthesizer]
    │
    ▼
User Answer
```