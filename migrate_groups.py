import sqlite3
import os

DB_PATH = "/Users/rafaelmotalima/Desktop/Projetos/Balizamento Automatico/swimming.db"

def migrate():
    print(f"Migrating {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Create groups table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL UNIQUE,
                created_at DATETIME
            )
        """)
        print("Created 'groups' table.")

        # Add group_id to students
        try:
            cursor.execute("ALTER TABLE students ADD COLUMN group_id INTEGER REFERENCES groups(id)")
            print("Added 'group_id' to 'students'.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("'group_id' already exists in 'students'.")
            else:
                raise e

        # Add group_id to events
        try:
            cursor.execute("ALTER TABLE events ADD COLUMN group_id INTEGER REFERENCES groups(id)")
            print("Added 'group_id' to 'events'.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("'group_id' already exists in 'events'.")
            else:
                raise e

        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        migrate()
    else:
        print(f"Database {DB_PATH} not found.")
