import mysql.connector
from mysql.connector import errorcode
import os
from dotenv import load_dotenv

# Load environment variables from your .env file
load_dotenv()

# Database configuration is read from environment variables
MYSQL_CONFIG = {
    'user': os.getenv("user"),
    'password': os.getenv("password"),
    'host': os.getenv("host"),
    'database': os.getenv("database")
}

def permanently_delete_marked_vouches():
    """
    Connects to the MySQL database and permanently deletes all vouches
    that have their status marked as 'deleted'.
    """
    conn = None  # Initialize connection to None
    try:
        # Establish the database connection
        print("Connecting to the database...")
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        print("Connection successful.")

        # The SQL query to delete the rows
        delete_query = "DELETE FROM vouches WHERE status = 'deleted'"

        # Execute the query
        print("Executing delete command...")
        cursor.execute(delete_query)

        # Get the number of rows that were deleted
        deleted_count = cursor.rowcount

        # Commit the changes to the database to make them permanent
        conn.commit()

        if deleted_count > 0:
            print(f"Success! Permanently deleted {deleted_count} vouches.")
        else:
            print("No vouches marked as 'deleted' were found to delete.")

    except mysql.connector.Error as err:
        # Handle potential errors, such as connection issues or SQL syntax errors
        print(f"Error: Failed to delete vouches. Reason: {err}")
        if conn:
            # Rollback any changes if an error occurred
            conn.rollback()
            print("Transaction has been rolled back.")
            
    finally:
        # Ensure the connection is always closed, whether it succeeded or failed
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("MySQL connection has been closed.")

if __name__ == "__main__":
    # This block runs when the script is executed directly
    print("Starting the cleanup process for deleted vouches...")
    permanently_delete_marked_vouches()
    print("Cleanup process finished.")