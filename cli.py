#!/usr/bin/env python3
"""
Financial Analytics CLI

A command-line interface for querying financial data and generating visualizations.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent))

from graph.build import GraphBuilder
from graph.run import run_query
from graph.nodes.logger import QueryLogger

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the query logger
query_logger = QueryLogger()

async def process_query(query: str, debug: bool = False) -> None:
    """
    Process a single query and display the results.
    
    Args:
        query: The natural language query to process
        debug: Whether to show debug information
    """
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Execute the query
        result = await run_query(query)
        end_time = asyncio.get_event_loop().time()
        
        # Display the results
        print("\n" + "=" * 80)
        print(f"QUERY: {query}")
        print("-" * 80)
        print(result.markdown)
        
        # Log the query
        query_logger.log_query(
            query=query,
            intent=result.metadata.get("intent", {}),
            sql=result.metadata.get("sql", ""),
            params=result.metadata.get("params", {}),
            results=result.metadata.get("results", []),
            start_time=start_time,
            end_time=end_time,
            chart_path=result.chart_path,
            metadata={
                "query_type": result.metadata.get("intent", {}).get("intent_type"),
                "result_count": len(result.metadata.get("results", [])),
                "execution_time_ms": int((end_time - start_time) * 1000)
            }
        )
        
        # Show debug info if requested
        if debug:
            print("\n" + "-" * 80)
            print("DEBUG INFO:")
            print(f"Query ID: {query_logger.get_recent_queries(1)[0]['query_id']}")
            print(f"Execution time: {int((end_time - start_time) * 1000)}ms")
            
            if result.chart_path:
                print(f"Chart saved to: {result.chart_path}")
            
            print("Log file:", query_logger.log_file.absolute())
        
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=debug)
        print(f"\nError: {str(e)}")
        if debug:
            import traceback
            traceback.print_exc()

async def interactive_mode(debug: bool = False) -> None:
    """Run the CLI in interactive mode."""
    print("Financial Analytics CLI - Interactive Mode")
    print("Type 'exit' or 'quit' to exit.\n")
    
    while True:
        try:
            query = input("Enter your query: ").strip()
            
            if query.lower() in ('exit', 'quit'):
                break
                
            if not query:
                continue
                
            await process_query(query, debug)
            
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=debug)
            print(f"Error: {str(e)}")

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Financial Analytics CLI")
    parser.add_argument(
        "query", 
        nargs="?",
        help="The query to execute (optional, will start interactive mode if not provided)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug output"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the appropriate mode
    if args.query:
        asyncio.run(process_query(args.query, args.debug))
    else:
        asyncio.run(interactive_mode(args.debug))

if __name__ == "__main__":
    main()
