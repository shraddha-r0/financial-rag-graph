from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
import logging

from langgraph.graph import StateGraph, END
from .state import GraphState, UserQuery, Answer, SQLPlan, ResultFrame, ChartSpec, TimeRange
from .nodes.intent_parser import parse_intent, IntentType, TimeGranularity
from .nodes.category_resolver import resolve_categories
from .nodes.sql_planner import generate_sql_plan
from .nodes.db_executor import execute_query as db_execute_query
from .nodes.chart_node import generate_chart_spec
from .nodes.answer_synth import generate_answer

logger = logging.getLogger(__name__)

# Type aliases for better type hints
NodeName = str
NodeFunction = callable
EdgeCondition = callable

class GraphBuilder:
    def __init__(self):
        self.graph = StateGraph(GraphState)
        self._setup_nodes()
        self._setup_edges()
        self._compiled = None

    def _setup_nodes(self):
        """Register all node functions with the graph."""
        self.graph.add_node("parse_intent", self._parse_intent)
        self.graph.add_node("resolve_categories", self._resolve_categories)
        self.graph.add_node("plan_sql", self._plan_sql)
        self.graph.add_node("execute_query", self._execute_query)
        self.graph.add_node("generate_chart", self._generate_chart)
        self.graph.add_node("synthesize_answer", self._synthesize_answer)
        self.graph.add_node("handle_error", self._handle_error)

    def _setup_edges(self):
        """Define the flow between nodes with conditional edges."""
        # Main flow
        self.graph.add_edge("parse_intent", "resolve_categories")
        self.graph.add_edge("resolve_categories", "plan_sql")
        self.graph.add_edge("plan_sql", "execute_query")
        
        # Conditional edges after query execution
        self.graph.add_conditional_edges(
            "execute_query",
            self._should_generate_chart,
            {
                "generate_chart": "generate_chart",
                "synthesize": "synthesize_answer"
            }
        )
        
        # Flow after chart generation
        self.graph.add_edge("generate_chart", "synthesize_answer")
        
        # Error handling
        self.graph.add_edge("synthesize_answer", END)
        self.graph.add_edge("handle_error", END)
        
        # Set entry point
        self.graph.set_entry_point("parse_intent")

    def compile(self):
        """Compile the graph for execution."""
        if not self._compiled:
            self._compiled = self.graph.compile()
        return self._compiled

    async def _parse_intent(self, state: GraphState) -> GraphState:
        """Parse user intent from the query text."""
        try:
            if not state.user_query or not state.user_query.get('text'):
                state.error = "No query provided"
                return state
                
            intent = parse_intent(state.user_query['text'])
            state.metadata['intent'] = intent
            logger.info(f"Parsed intent: {intent}")
            
        except Exception as e:
            state.error = f"Error parsing intent: {str(e)}"
            logger.error(state.error, exc_info=True)
            
        return state

    async def _resolve_categories(self, state: GraphState) -> GraphState:
        """Resolve and validate categories in the query."""
        try:
            if state.error:
                return state
                
            intent = state.metadata.get('intent')
            if not intent:
                state.error = "No intent found to resolve categories from"
                return state
                
            # Resolve categories using the category resolver
            if 'filters' in intent and 'category' in intent['filters']:
                categories = intent['filters']['category']
                resolved = resolve_categories(categories)
                state.metadata['resolved_categories'] = resolved
                logger.info(f"Resolved categories: {resolved}")
                
        except Exception as e:
            state.error = f"Error resolving categories: {str(e)}"
            logger.error(state.error, exc_info=True)
            
        return state

    async def _plan_sql(self, state: GraphState) -> GraphState:
        """Generate SQL plan based on the parsed intent."""
        try:
            if state.error:
                return state
                
            intent = state.metadata.get('intent')
            if not intent:
                state.error = "No intent found for SQL planning"
                return state
                
            # Generate SQL plan
            sql_plan = generate_sql_plan(intent)
            state.sql_plan = sql_plan
            state.metadata['sql'] = sql_plan.query
            state.metadata['params'] = sql_plan.params
            
            logger.info(f"Generated SQL: {sql_plan.query}")
            if sql_plan.params:
                logger.info(f"With params: {sql_plan.params}")
                
        except Exception as e:
            state.error = f"Error planning SQL: {str(e)}"
            logger.error(state.error, exc_info=True)
            
        return state

    async def _execute_query(self, state: GraphState) -> GraphState:
        """Execute the SQL query against the database."""
        try:
            if state.error:
                return state
                
            if not state.sql_plan:
                state.error = "No SQL plan to execute"
                return state
                
            # Execute the query
            db_path = str(Path("data/clean/finances.db").absolute())
            result = db_execute_query(
                sql=state.sql_plan.query,
                db_path=db_path,
                params=state.sql_plan.params
            )
            
            if result.error:
                state.error = f"Query execution failed: {result.error}"
                return state
                
            # Store results
            state.results = result
            state.metadata['results'] = [dict(row) for row in result.rows[:10]]  # Store sample for logging
            state.metadata['result_count'] = result.rowcount
            
            logger.info(f"Query executed successfully. Returned {result.rowcount} rows")
            
        except Exception as e:
            state.error = f"Error executing query: {str(e)}"
            logger.error(state.error, exc_info=True)
            
        return state

    async def _generate_chart(self, state: GraphState) -> GraphState:
        """Generate chart if requested in the query."""
        try:
            if state.error:
                return state
                
            if not state.results or not state.results.rows:
                logger.warning("No results to generate chart from")
                return state
                
            intent = state.metadata.get('intent', {})
            chart_spec = generate_chart_spec(
                results=state.results,
                intent=intent
            )
            
            if chart_spec:
                state.chart_spec = chart_spec
                state.metadata['chart_generated'] = True
                logger.info(f"Generated chart spec: {chart_spec}")
                
        except Exception as e:
            logger.warning(f"Chart generation failed: {str(e)}", exc_info=True)
            # Don't fail the whole process if chart generation fails
            
        return state

    async def _synthesize_answer(self, state: GraphState) -> GraphState:
        """Generate final answer for the user."""
        try:
            if state.error:
                answer_text = f"Error: {state.error}"
            elif not state.results or not state.results.rows:
                answer_text = "No results found matching your query."
            else:
                answer_text = generate_answer(
                    results=state.results,
                    intent=state.metadata.get('intent', {}),
                    chart_spec=state.chart_spec
                )
            
            state.answer = Answer(markdown=answer_text)
            state.answer.metadata.update(state.metadata)
            
        except Exception as e:
            state.error = f"Error generating answer: {str(e)}"
            logger.error(state.error, exc_info=True)
            state.answer = Answer(markdown=f"An error occurred: {str(e)}")
            
        return state

    async def _handle_error(self, state: GraphState) -> GraphState:
        """Handle errors in the graph."""
        if state.error:
            error_msg = state.error
            logger.error(f"Graph error: {error_msg}")
            state.answer = Answer(markdown=f"Error: {error_msg}")
        return state

    def _should_generate_chart(self, state: GraphState) -> Literal["generate_chart", "synthesize"]:
        """Determine if we should generate a chart based on the query."""
        if state.error or not state.results or not state.results.rows:
            return "synthesize"
            
        intent = state.metadata.get('intent', {})
        
        # Generate chart for time series or comparison queries
        if intent.get('intent_type') in [
            IntentType.SPENDING_OVER_TIME,
            IntentType.COMPARISON
        ]:
            return "generate_chart"
            
        # Generate chart for category breakdowns with multiple items
        if (intent.get('intent_type') == IntentType.SPENDING_BY_CATEGORY and 
            len(state.results.rows) > 1 and 
            len(state.results.rows) <= 20):  # Don't chart too many categories
            return "generate_chart"
            
        return "synthesize"

# Create a singleton instance of the graph
graph_builder = GraphBuilder()
graph = graph_builder.compile()
