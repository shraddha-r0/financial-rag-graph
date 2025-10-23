"""
Expense Data Cleaning Script

This script cleans and processes expense data from Toshl exports.
It handles date parsing, currency conversion, and adds useful derived fields.

Usage:
    python clean_expense_data.py --input data/raw/your_export_file.csv --output data/clean/toshl_cleaned.csv
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import numpy as np


def clean_expense_data(input_file, output_file=None):
    """
    Clean and process expense data from a Toshl export.
    
    Args:
        input_file (str): Path to the input CSV file
        output_file (str, optional): Path to save the cleaned data. If None, will save to 
                                   'data/clean/toshl_<month><year>_clean.csv'.
    
    Returns:
        pd.DataFrame: The cleaned DataFrame
    """
    # Read the input file
    df = pd.read_csv(input_file, parse_dates=['Date'])
    print(f"✅ Loaded {len(df)} rows from {input_file}")
    
    # Convert Date column to datetime with specific format
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    
    # Remove unnecessary columns
    df.drop(columns=['Account', 'Main currency', 'Currency'], inplace=True, errors='ignore')
    
    # Rename columns for consistency
    df.rename(columns={
        'Category': 'category',
        'Date': 'date',
        'Description': 'description',
        'Tags': 'tags',
        'Expense amount': 'expense',
        'Income amount': 'income',
        'In main currency': 'amount_clp'
    }, inplace=True)
    
    # Extract day name
    df['day'] = df['date'].dt.day_name()
    
    # Convert amount columns to float, handling thousands separators
    for col in ['expense', 'income', 'amount_clp']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '').astype(float)
    
    # Fill missing values
    for col in ['expense', 'income']:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    
    df['tags'] = df['tags'].fillna('none')
    df['description'] = df['description'].fillna('none')
    
    # Generate output filename if not provided
    if output_file is None:
        # Extract month and year from input filename (e.g., 'Toshl_export_June_2025.csv' -> 'june2025')
        input_path = Path(input_file)
        filename_parts = input_path.stem.split('_')
        
        if len(filename_parts) >= 4:
            month = filename_parts[-2].lower()  # june
            year = filename_parts[-1]           # 2025
            month_year = f"{month}{year}"
        else:
            # Fallback to current date if pattern not matched
            from datetime import datetime
            month_year = datetime.now().strftime("%B%Y").lower()
        
        # Create clean directory if it doesn't exist
        clean_dir = input_path.parent.parent / 'clean'
        clean_dir.mkdir(exist_ok=True)
        
        output_file = clean_dir / f"toshl_{month_year}_clean.csv"
    
    # Save the cleaned data
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"✅ Cleaned data saved to {output_file}")
    
    return df


def main():
    parser = argparse.ArgumentParser(description='Clean and process expense data from Toshl exports.')
    parser.add_argument('--input', required=True, help='Path to the input CSV file')
    parser.add_argument('--output', help='Path to save the cleaned CSV file')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"❌ Error: Input file '{args.input}' not found.")
        sys.exit(1)
    
    try:
        clean_expense_data(args.input, args.output)
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()