import asyncio
from graph.build import graph
from graph.state import GraphState

async def test_query(query_text: str):
    """Test the graph with a sample query."""
    try:
        print(f"\nTesting query: {query_text}")
        
        # Initialize the graph state
        state = GraphState(
            user_query={"text": query_text},
            metadata={}
        )
        
        # Run the graph
        result = await graph.ainvoke({"state": state})
        
        # Get the final state
        final_state = result.get("state", {})
        
        # Print results
        if hasattr(final_state, 'answer') and final_state.answer:
            print("\nAnswer:")
            print("-" * 80)
            print(final_state.answer.markdown)
            print("-" * 80)
            
            # Print metadata
            if hasattr(final_state, 'metadata') and final_state.metadata:
                print("\nMetadata:")
                print("-" * 80)
                if 'sql' in final_state.metadata:
                    print("SQL Query:")
                    print(final_state.metadata['sql'])
                    if 'params' in final_state.metadata and final_state.metadata['params']:
                        print("\nParameters:", final_state.metadata['params'])
                print("\nResult Count:", final_state.metadata.get('result_count', 0))
                
        if hasattr(final_state, 'error') and final_state.error:
            print("\nError:")
            print("-" * 80)
            print(final_state.error)
            
    except Exception as e:
        print(f"Error testing query: {e}")
        import traceback
        traceback.print_exc()

# Test cases
test_queries = [
    "How much did I spend on food last month?",
    "Show me my top 5 spending categories",
    "What were my expenses by category in July 2025?",
    "Compare my spending this month to last month"
]

# Run tests
async def main():
    for query in test_queries:
        await test_query(query)
        print("\n" + "="*100 + "\n")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
