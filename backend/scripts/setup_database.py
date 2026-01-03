#!/usr/bin/env python3
"""
Set up the complete database schema using the single schema file.
This script applies the complete schema and can be run safely multiple times.
"""

import os
import sys
import psycopg2

def setup_database(database_url: str):
    """Set up the complete database schema"""
    
    # Get the schema file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema_file = os.path.join(script_dir, '..', 'migrations', 'complete_schema.sql')
    
    if not os.path.exists(schema_file):
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    
    # Read the schema file
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    print(f"📋 Reading schema from: {schema_file}")
    
    # Connect to database
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    try:
        print("🚀 Applying complete database schema...")
        cur.execute(schema_sql)
        conn.commit()
        print("✅ Database schema applied successfully!")
        
        # Show created tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        print(f"\n📚 Tables created/verified ({len(tables)}):")
        for table in tables:
            print(f"  ✓ {table[0]}")
        
        # Show created views
        cur.execute("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        views = cur.fetchall()
        if views:
            print(f"\n👁️  Views created/verified ({len(views)}):")
            for view in views:
                print(f"  ✓ {view[0]}")
    
    finally:
        cur.close()
        conn.close()

def main():
    """Main function"""
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    try:
        print("🗄️  Setting up Pick6 database schema...")
        setup_database(database_url)
        print("🎉 Database setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
