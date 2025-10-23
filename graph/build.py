from typing import Any, Dict, List, Literal, TypedDict, Union, Annotated
from langgraph.graph import StateGraph, END
from .state import GraphState, UserQuery, Answer, SQLPlan, ResultFrame, ChartSpec

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

    # Node implementations (stubs to be implemented)
    async def _parse_intent(self, state: GraphState) -> GraphState:
        """Parse user intent from the query text."""
        # TODO: Implement intent parsing
        return state

    async def _resolve_categories(self, state: GraphState) -> GraphState:
        """Resolve and validate categories in the query."""
        # TODO: Implement category resolution
        return state

    async def _plan_sql(self, state: GraphState) -> GraphState:
        """Generate SQL plan based on the parsed intent."""
        # TODO: Implement SQL planning
        return state

    async def _execute_query(self, state: GraphState) -> GraphState:
        """Execute the SQL query against the database."""
        # TODO: Implement query execution
        return state

    async def _generate_chart(self, state: GraphState) -> GraphState:
        """Generate chart if requested in the query."""
        # TODO: Implement chart generation
        return state

    async def _synthesize_answer(self, state: GraphState) -> GraphState:
        """Generate final answer for the user."""
        # TODO: Implement answer synthesis
        return state

    async def _handle_error(self, state: GraphState) -> GraphState:
        """Handle errors in the graph."""
        # TODO: Implement error handling
        return state

    # Conditional edge functions
    def _should_generate_chart(self, state: GraphState) -> Literal["generate_chart", "synthesize"]:
        """Determine if we should generate a chart based on the query."""
        # TODO: Implement chart decision logic
        return "synthesize"

# Create a singleton instance of the graph
graph_builder = GraphBuilder()
graph = graph_builder.compile()
