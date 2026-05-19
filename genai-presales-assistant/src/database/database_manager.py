"""
Database Manager for CRM System

Handles SQLite database creation, schema management, and data loading operations.
Provides a clean interface for database operations used by the SQL agent.
"""

import sqlite3
import os
import re
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from loguru import logger


class DatabaseManager:
    """Manages SQLite database operations for the CRM system"""
    
    def __init__(self, db_path: str = "data/crm_database.db"):
        """Initialize database manager"""
        self.db_path = db_path
        self.connection = None
        self._ensure_database_directory()
        
    def _ensure_database_directory(self):
        """Ensure the database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
    
    def connect(self) -> sqlite3.Connection:
        """Establish database connection"""
        if not self.connection:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access
            logger.info(f"Connected to database: {self.db_path}")
        return self.connection
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def create_schema(self) -> None:
        """Create database schema for CRM tables"""
        logger.info("Creating database schema")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # Drop existing tables if they exist
        cursor.execute("DROP TABLE IF EXISTS activities")
        cursor.execute("DROP TABLE IF EXISTS deals")
        cursor.execute("DROP TABLE IF EXISTS products")
        cursor.execute("DROP TABLE IF EXISTS customers")
        
        # Create customers table
        cursor.execute("""
            CREATE TABLE customers (
                customer_id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                industry TEXT,
                company_size TEXT,
                website TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                created_date DATE,
                last_contact_date DATE,
                account_owner TEXT,
                annual_revenue REAL
            )
        """)
        
        # Create products table
        cursor.execute("""
            CREATE TABLE products (
                product_id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                category TEXT,
                description TEXT,
                unit_price REAL,
                cost REAL,
                margin_percent REAL,
                created_date DATE,
                is_active BOOLEAN
            )
        """)
        
        # Create deals table
        cursor.execute("""
            CREATE TABLE deals (
                deal_id TEXT PRIMARY KEY,
                customer_id TEXT,
                deal_name TEXT NOT NULL,
                stage TEXT,
                value REAL,
                currency TEXT,
                probability REAL,
                expected_close_date DATE,
                created_date DATE,
                last_modified_date DATE,
                deal_owner TEXT,
                description TEXT,
                actual_close_date DATE,
                FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
            )
        """)
        
        # Create activities table
        cursor.execute("""
            CREATE TABLE activities (
                activity_id TEXT PRIMARY KEY,
                customer_id TEXT,
                deal_id TEXT,
                activity_type TEXT,
                subject TEXT,
                description TEXT,
                activity_date DATE,
                duration_minutes INTEGER,
                owner TEXT,
                outcome TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
                FOREIGN KEY (deal_id) REFERENCES deals (deal_id)
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("CREATE INDEX idx_customers_industry ON customers (industry)")
        cursor.execute("CREATE INDEX idx_customers_account_owner ON customers (account_owner)")
        cursor.execute("CREATE INDEX idx_products_category ON products (category)")
        cursor.execute("CREATE INDEX idx_deals_customer_id ON deals (customer_id)")
        cursor.execute("CREATE INDEX idx_deals_stage ON deals (stage)")
        cursor.execute("CREATE INDEX idx_deals_deal_owner ON deals (deal_owner)")
        cursor.execute("CREATE INDEX idx_activities_customer_id ON activities (customer_id)")
        cursor.execute("CREATE INDEX idx_activities_deal_id ON activities (deal_id)")
        cursor.execute("CREATE INDEX idx_activities_activity_type ON activities (activity_type)")
        
        conn.commit()
        logger.info("Database schema created successfully")
    
    def load_data_from_csv(self, csv_file: str, table_name: str) -> int:
        """Load data from CSV file into specified table"""
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        
        logger.info(f"Loading data from {csv_file} into {table_name}")
        
        # Read CSV file
        df = pd.read_csv(csv_file)
        
        # Handle NaN values
        df = df.where(pd.notnull(df), None)
        
        conn = self.connect()
        
        # Load data into database
        rows_affected = df.to_sql(
            table_name, 
            conn, 
            if_exists='append', 
            index=False,
            method='multi'
        )
        
        conn.commit()
        logger.info(f"Loaded {rows_affected} rows into {table_name}")
        
        return rows_affected
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute SQL query and return results"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # For SELECT queries, return results
            if query.strip().upper().startswith('SELECT'):
                results = [dict(row) for row in cursor.fetchall()]
                logger.info(f"Query returned {len(results)} results")
                return results
            else:
                # For INSERT, UPDATE, DELETE queries
                conn.commit()
                rows_affected = cursor.rowcount
                logger.info(f"Query affected {rows_affected} rows")
                return [{"affected_rows": rows_affected}]
                
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            conn.rollback()
            raise e
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a specific table"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        return {
            "table_name": table_name,
            "columns": [dict(col) for col in columns],
            "row_count": row_count
        }
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get complete database schema information"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_info = {}
        for table in tables:
            schema_info[table] = self.get_table_info(table)
        
        return schema_info
    
    def validate_query_safety(self, query: str) -> Tuple[bool, str]:
        """Validate SQL query for safety (prevent destructive operations)"""
        query_upper = query.upper().strip()
        
        # Allow SELECT queries and common data query patterns
        allowed_patterns = ['SELECT', 'WITH', 'COUNT(', 'SUM(', 'AVG(', 'MIN(', 'MAX(']
        
        if not any(query_upper.startswith(pattern) for pattern in allowed_patterns):
            return False, f"Query must start with allowed pattern: {', '.join(allowed_patterns)}"
        
        # List of forbidden operations (check as whole words to avoid false positives)
        forbidden_patterns = [
            r'\bDROP\b', r'\bDELETE\b', r'\bTRUNCATE\b', r'\bALTER\b', r'\bCREATE\b', 
            r'\bINSERT\b', r'\bUPDATE\b', r'\bGRANT\b', r'\bREVOKE\b', r'\bEXEC\b'
        ]
        
        import re
        for pattern in forbidden_patterns:
            if re.search(pattern, query_upper):
                friendly = pattern.replace(r"\b", "")
                return False, f"Query contains forbidden operation: {friendly}"
        
        # Validate aggregation consistency
        aggregation_validation = self._validate_aggregation_consistency(query)
        if not aggregation_validation[0]:
            return aggregation_validation
        
        # Additional check: Allow simple GROUP BY queries for data retrieval
        query_upper = query.upper().strip()
        if ('GROUP BY' in query_upper and 
            ('ORDER BY' in query_upper or 'LIMIT' in query_upper or
             any(keyword in query_upper for keyword in ['SELECT', 'FROM', 'WHERE']))):
            return True, "Query is safe for data retrieval"
        
        return True, "Query is safe"
    
    def _validate_aggregation_consistency(self, query: str) -> Tuple[bool, str]:
        """Validate aggregation consistency in SQL queries"""
        query_upper = query.upper().strip()
        
        # Check for aggregation functions
        agg_patterns = [r'\bSUM\(', r'\bCOUNT\(', r'\bAVG\(', r'\bMIN\(', r'\bMAX\(']
        has_aggregation = any(re.search(pattern, query_upper) for pattern in agg_patterns)
        
        # Check for GROUP BY
        has_group_by = 'GROUP BY' in query_upper
        
        # Validation rules
        if has_aggregation and not has_group_by:
            # Check if SELECT contains non-aggregated columns with aggregation
            select_part = query_upper.split('FROM')[0].replace('SELECT', '').strip()
            
            # Count aggregation functions
            agg_count = sum(len(re.findall(pattern, select_part)) for pattern in agg_patterns)
            
            # Count columns (simplified check)
            columns = [col.strip() for col in select_part.split(',') if col.strip()]
            
            # If we have aggregations but multiple columns, likely missing GROUP BY
            if agg_count > 0 and len(columns) > agg_count:
                return False, "Query uses aggregation with multiple columns but missing GROUP BY clause"
        
        if has_group_by and not has_aggregation:
            return False, "Query has GROUP BY but no aggregation functions"
        
        # Check for LIMIT without ORDER BY in aggregated queries
        if 'LIMIT' in query_upper and 'ORDER BY' not in query_upper and has_aggregation:
            return False, "Aggregated query with LIMIT should have ORDER BY for meaningful results"
        
        return True, "Aggregation is consistent"
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample data from a table for context"""
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        return self.execute_query(query)
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Get table info
        schema_info = self.get_schema_info()
        
        # Calculate total records
        total_records = sum(table["row_count"] for table in schema_info.values())
        
        return {
            "database_path": self.db_path,
            "total_tables": len(schema_info),
            "total_records": total_records,
            "tables": schema_info
        }


if __name__ == "__main__":
    # Example usage
    db_manager = DatabaseManager()
    
    # Create schema
    db_manager.create_schema()
    
    # Load data (assuming CSV files exist)
    csv_files = {
        "customers": "data/raw/customers.csv",
        "products": "data/raw/products.csv", 
        "deals": "data/raw/deals.csv",
        "activities": "data/raw/activities.csv"
    }
    
    for table, csv_file in csv_files.items():
        if os.path.exists(csv_file):
            db_manager.load_data_from_csv(csv_file, table)
    
    # Print database stats
    stats = db_manager.get_database_stats()
    print("Database Statistics:", stats)
    
    db_manager.disconnect()
