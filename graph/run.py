from typing import Dict, Any
from .state import GraphState, Answer
from .build import graph

async def run_query(query_text: str) -> Answer:
    """
    Main entry point for running a query through the financial analytics graph.
    
    Args:
        query_text: The natural language query from the user
        
    Returns:
        An Answer object containing the response to the user
    """
    try:
        # Initialize the graph state with the user's query
        initial_state = GraphState(
            user_query={"text": query_text},
            metadata={"start_time": "2025-10-23T16:01:00-03:00"}  # Using current time as example
        )
        
        # Execute the graph
        final_state = await graph.ainvoke(initial_state)
        
        # Return the answer or error message
        if final_state.error:
            return Answer(markdown=f"Error: {final_state.error}")
        return final_state.answer or Answer(markdown="No results found.")
        
    except Exception as e:
        # Handle any unexpected errors
        return Answer(markdown=f"An unexpected error occurred: {str(e)}")

# Example usage for testing
if __name__ == "__main__":
    import asyncio
    
    async def test_query():
        test_queries = [
            "Show me my spending by category last month",
            "What were my top expenses in Q3 2025?",
            "Generate a pie chart of my income sources"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            result = await run_query(query)
            print(f"Answer: {result.markdown[:200]}...")
    
    asyncio.run(test_query())
