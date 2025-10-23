"""
Test script to verify database connection and models.
"""
import sqlite3
from pathlib import Path
import pandas as pd
from graph.state import (
    UserQuery, SQLPlan, ResultFrame, ChartSpec, Answer, GraphState,
    TimeRange, IntentType, ChartType, TableType
)

# Database path
DB_PATH = Path("data/clean/finances.db")

def test_database_connection():
    """Test the database connection and basic queries."""
    print("🔍 Testing database connection...")
    
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"✅ Found tables: {', '.join(tables)}")
        
        # Test expenses table
        cursor.execute("SELECT COUNT(*) FROM expenses;")
        count = cursor.fetchone()[0]
        print(f"✅ Found {count} expense records")
        
        # Test a sample query
        cursor.execute("""
            SELECT category, SUM(expense) as total 
            FROM expenses 
            GROUP BY category 
            ORDER BY total DESC 
            LIMIT 5;
        """)
        print("\nTop 5 spending categories:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}: ${row[1]:,.2f}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_models():
    """Test the Pydantic models with sample data."""
    print("\n🧪 Testing models...")
    
    # Test TimeRange
    time_range = TimeRange.from_string("last month")
    print(f"✅ Created TimeRange: {time_range.label} ({time_range.start_date} to {time_range.end_date})")
    
    # Test UserQuery
    user_query = UserQuery(
        text="Show me my spending on groceries last month",
        intent=IntentType.SPENDING_BY_CATEGORY,
        time_range=time_range,
        categories=["Groceries"],
        metrics=["total_spend", "transaction_count"],
        dimensions=["category"]
    )
    print(f"✅ Created UserQuery: {user_query.intent}")
    
    # Test SQLPlan
    sql_plan = SQLPlan.from_user_query(user_query)
    print(f"✅ Generated SQL:\n{sql_plan.query}")
    
    # Test executing the query
    try:
        conn = sqlite3.connect(DB_PATH)
        results = ResultFrame.from_sql(conn, sql_plan.query, sql_plan.params)
        print(f"✅ Query executed successfully, found {results.rowcount} rows")
        
        # Test Answer with chart
        if results.rowcount > 0:
            df = results.to_pandas()
            print("\nQuery results:")
            print(df.head())
            
            # Create a chart
            chart_spec = ChartSpec(
                chart_type=ChartType.BAR,
                x_axis="category",
                y_axis="total_spend",
                title="Spending by Category",
                y_label="Total Spend"
            )
            
            answer = Answer(markdown="# Spending Analysis\n")
            chart_path = answer.add_chart(chart_spec, df, "Spending by Category")
            print(f"✅ Generated chart: {chart_path}")
            
            # Add a table
            answer.add_table(df, "Detailed Spending", "Breakdown of expenses by category")
            print(f"✅ Added table to answer")
            
            # Save the answer
            output_path = Path("artifacts/answers/test_answer.md")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(answer.markdown)
            print(f"✅ Saved answer to {output_path}")
            
    except Exception as e:
        print(f"❌ Error executing query: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Run all tests."""
    print("🚀 Starting database tests...")
    
    # Create artifacts directory
    Path("artifacts").mkdir(exist_ok=True)
    
    # Run tests
    test_database_connection()
    test_models()
    
    print("\n✨ All tests completed!")

if __name__ == "__main__":
    main()
