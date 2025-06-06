import sqlite3

def execute_schema(db_file, schema_file):
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Read the schema.sql file
    with open(schema_file, 'r') as file:
        schema_sql = file.read()

    # Execute the SQL commands
    cursor.executescript(schema_sql)

    # Commit changes and close connection
    conn.commit()
    conn.close()
    print(f"Schema from {schema_file} executed successfully in {db_file}")

if __name__ == "__main__":
    # Replace with your database file and schema file paths
    database = "helpdesk.db"
    schema_file = "schema.sql"
    execute_schema(database, schema_file)