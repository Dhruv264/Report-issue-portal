"""
Migration Script: Add rejection and rejection_reason columns to issues table
Run this script to add these columns if they don't exist
"""

import psycopg2
from config import Config

def add_rejection_columns():
    """Add rejection and rejection_reason columns to issues table"""
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            port=Config.DB_PORT
        )
        cur = conn.cursor()

        # Check if rejection column exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'issues' 
                AND column_name = 'rejection'
            )
        """)
        rejection_exists = cur.fetchone()[0]

        # Check if rejection_reason column exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'issues' 
                AND column_name = 'rejection_reason'
            )
        """)
        reason_exists = cur.fetchone()[0]

        # Add rejection column if it doesn't exist
        if not rejection_exists:
            cur.execute("""
                ALTER TABLE issues
                ADD COLUMN rejection BOOLEAN DEFAULT FALSE
            """)
            print("✅ Successfully added 'rejection' column to issues table!")
        else:
            print("ℹ️  'rejection' column already exists in issues table.")

        # Add rejection_reason column if it doesn't exist
        if not reason_exists:
            cur.execute("""
                ALTER TABLE issues
                ADD COLUMN rejection_reason TEXT DEFAULT NULL
            """)
            print("✅ Successfully added 'rejection_reason' column to issues table!")
        else:
            print("ℹ️  'rejection_reason' column already exists in issues table.")

        conn.commit()
        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error adding columns: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  Adding rejection columns to issues table")
    print("="*50 + "\n")

    if add_rejection_columns():
        print("\n" + "="*50)
        print("  ✅ Migration complete!")
        print("="*50 + "\n")
    else:
        print("\n❌ Migration failed.")
        print("Please ensure:")
        print("1. PostgreSQL is running")
        print("2. Credentials in config.py are correct")
        print("3. The issues table exists")
