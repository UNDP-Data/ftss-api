#!/usr/bin/env python3
"""
Export signals and trends data for LLM processing.
Exports all public signals and trends to CSV format, excluding certain fields.
"""

import os
import sys
import asyncio
import csv
from datetime import datetime
import psycopg
from psycopg.rows import dict_row

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# No need to import get_connection_string - we'll use DB_CONNECTION directly

# Fields to exclude from the export
EXCLUDE_FIELDS = [
    'is_draft', 'private', 'favourite', 
    'can_edit', 'modified_at', 'url', 'favorite'
]
file_path = ".exports"

async def export_table_to_csv(conn, table_name, query, filename_prefix):
    """Export data from a table to CSV, excluding certain fields."""
    print(f"Exporting {table_name}...")

    async with conn.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(query)
        records = await cursor.fetchall()

    if not records:
        print(f"No records found in {table_name}.")
        return

    # Get all field names from the first record
    all_fields = list(records[0].keys())
    # Filter out excluded fields
    export_fields = [field for field in all_fields if field not in EXCLUDE_FIELDS]
    # Add app_link as the last column
    export_fields.append('app_link')

    # Compose filename
    filename = f'{file_path}/{table_name}.csv'

    # Ensure export directory exists
    os.makedirs(file_path, exist_ok=True)

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=export_fields)
        writer.writeheader()
        for record in records:
            row = {field: record[field] for field in export_fields if field != 'app_link'}
            for field, value in row.items():
                if isinstance(value, list):
                    row[field] = ', '.join(str(v) for v in value) if value else ''
            # Add app_link
            if table_name == 'signals':
                row['app_link'] = f'https://signals.data.undp.org/signals/{record["id"]}'
            elif table_name == 'trends':
                row['app_link'] = f'https://signals.data.undp.org/trends/{record["id"]}'
            else:
                row['app_link'] = ''
            writer.writerow(row)

    print(f"Exported {len(records)} {table_name} to {filename}")
    return filename

async def main():
    """Main function to export signals and trends."""
    # Get database connection string from environment
    connection_string = os.environ.get("DB_CONNECTION")
    
    if not connection_string:
        print("Error: DB_CONNECTION environment variable not set")
        sys.exit(1)
    
    try:
        # Connect to the database
        async with await psycopg.AsyncConnection.connect(
            connection_string,
            row_factory=dict_row
        ) as conn:
            print("Connected to database successfully")
            
            # Export signals
            signals_query = """
                SELECT * FROM signals 
                WHERE private = FALSE OR private IS NULL
                ORDER BY id
            """
            signals_file = await export_table_to_csv(conn, "signals", signals_query, "signals")

            # Export trends
            trends_query = """
                SELECT * FROM trends 
                ORDER BY id
            """
            trends_file = await export_table_to_csv(conn, "trends", trends_query, "trends")
            
            print("\nExport completed successfully!")
            if signals_file:
                print(f"Signals: {signals_file}")
            if trends_file:
                print(f"Trends: {trends_file}")
                
    except Exception as e:
        print(f"Error during export: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())