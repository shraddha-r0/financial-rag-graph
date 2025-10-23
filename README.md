# Financial Analytics with Natural Language

## 🚀 Overview
**Financial Analytics with Natural Language** is an AI-powered application that allows users to query their financial data using natural language. The application processes these queries through a series of specialized nodes, each responsible for a specific part of the pipeline, from understanding the user's intent to generating insightful visualizations.

## 🏗️ Architecture
The application is built using a modular, node-based architecture where each node performs a specific function in the query processing pipeline. The system is designed to be extensible, allowing for easy addition of new capabilities and integrations.

## 🔍 Node Descriptions

### 1. Intent Parser Node
**Purpose**: Understands the user's natural language query and extracts structured intent.
- Identifies query type (e.g., spending analysis, category breakdown)
- Extracts time ranges, categories, and other filters
- Determines the appropriate visualization type

### 2. Category Resolver Node
**Purpose**: Maps user-provided category names to standardized categories.
- Handles synonyms and variations (e.g., "food" → "Dining")
- Supports fuzzy matching for misspelled categories
- Maintains a knowledge base of common financial categories

### 3. SQL Planner Node
**Purpose**: Translates the structured intent into optimized SQL queries.
- Generates database-specific SQL
- Handles date ranges, aggregations, and filtering
- Optimizes queries for performance

### 4. Database Executor Node
**Purpose**: Executes the generated SQL queries against the financial database.
- Handles database connections and transactions
- Processes query results into a standardized format
- Implements pagination and result limiting

### 5. Chart Generator Node
**Purpose**: Creates visualizations from query results.
- Supports multiple chart types (bar, line, pie)
- Handles time-series and categorical data
- Applies consistent styling and theming

### 6. Answer Synthesizer Node
**Purpose**: Combines data and visualizations into a coherent response.
- Generates natural language summaries
- Includes relevant charts and tables
- Provides context and insights

### 7. Error Handler Node
**Purpose**: Manages errors and edge cases.
- Provides user-friendly error messages
- Suggests alternative queries
- Logs errors for debugging

## 🛠️ Technologies Used
- **Backend**: Python 3.11+
- **Natural Language Processing**: OpenAI GPT models
- **Database**: SQLite (with support for other SQL databases)
- **Data Visualization**: Matplotlib, Plotly
- **API**: FastAPI
- **Testing**: Pytest

## 🔄 Data Flow
1. User submits a natural language query
2. Intent Parser extracts structured intent
3. Category Resolver normalizes category names
4. SQL Planner generates optimized queries
5. Database Executor retrieves the data
6. Chart Generator creates visualizations
7. Answer Synthesizer combines everything into a response
8. Error Handler manages any issues that arise

## 📦 Dependencies
- Python 3.11+
- OpenAI API key
- Required Python packages (see `requirements.txt`)

## 🚧 Development Status
This project is currently in active development. Features and APIs may change as the project evolves.

## 🤝 Contributing
Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License
[Specify your license here]