import mysql.connector
from mysql.connector import errorcode
import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_CONFIG = {
    'user': os.getenv("user"),
    'password': os.getenv("password"),
    'host': os.getenv("host"),
    'database': os.getenv("database")
}

try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="bot_pool",
        pool_size=12,
        user=os.getenv("user"),
        password=os.getenv("password"),
        host=os.getenv("host"),
        database=os.getenv("database"),
        pool_reset_session=True
    )
    print("MySQL Connection Pool created successfully.")
except mysql.connector.Error as err:
    print(f"Error creating MySQL connection pool: {err}")
    db_pool = None

def get_mysql_connection():
    """
    CORRECT: Gets a reusable connection from the established pool.
    """
    if db_pool is None:
        print("Error: Connection pool is not available.")
        return None
    try:
        # This borrows a connection from the pool. It does NOT create a new one.
        return db_pool.get_connection()
    except mysql.connector.Error as err:
        print(f"Error getting connection from pool: {err}")
        return None

def permanently_delete_vouches():
    """Permanently deletes vouches marked as 'deleted' from the database."""
    conn = get_mysql_connection()
    if not conn:
        print("Error: Could not get a database connection for vouch cleanup.")
        return

    cursor = None
    try:
        cursor = conn.cursor()
        query = "DELETE FROM vouches WHERE status = 'deleted'"
        cursor.execute(query)
        deleted_count = cursor.rowcount
        conn.commit()
        if deleted_count > 0:
            print(f"Successfully purged {deleted_count} deleted vouches from the database.")
    except mysql.connector.Error as err:
        print(f"MySQL Error on purging vouches: {err}")
        if conn:
            conn.rollback()
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

# NEW: Checks if the user has permission to vouch
def has_permission_to_vouch(user_id: int) -> bool:
    """Checks the `users` table to see if a user has the `can_vouch` flag set to true."""
    conn = get_mysql_connection()
    if not conn:
        return False  # Fail safe: prevent vouches if DB is down

    can_vouch = False
    cursor = None
    try:
        cursor = conn.cursor()
        query = "SELECT can_vouch FROM users WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        if result and result[0] == 1:
            can_vouch = True
    except mysql.connector.Error as err:
        print(f"MySQL Error checking vouch permission: {err}")
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()
    return can_vouch

# NEW: Revokes a user's permission after they vouch
def revoke_vouch_permission(user_id: int):
    """Sets the `can_vouch` flag to 0 (false) for a user."""
    conn = get_mysql_connection()
    if not conn: return

    cursor = None
    try:
        cursor = conn.cursor()
        query = "UPDATE users SET can_vouch = 0 WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"MySQL Error revoking vouch permission: {err}")
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

# NEW: Grants permission for the .reset command
def grant_vouch_permission(user_id: int) -> bool:
    """Sets the `can_vouch` flag to 1 (true) for a user, allowing them to vouch again."""
    conn = get_mysql_connection()
    if not conn: return False

    success = False
    cursor = None
    try:
        cursor = conn.cursor()
        query = "UPDATE users SET can_vouch = 1 WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Successfully granted vouch permission to user_id: {user_id}")
            success = True
        else:
            print(f"Could not find user_id {user_id} to grant vouch permission.")
    except mysql.connector.Error as err:
        print(f"MySQL Error granting vouch permission: {err}")
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()
    return success

def add_vouch_to_mysql(vouch_by, vouch_text, user_id):
    """Adds a vouch to the MySQL database. Does NOT change permission here."""
    conn = get_mysql_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    query = ("INSERT INTO vouches (vouch_by, user_id, vouch_text) "
             "VALUES (%s, %s, %s)")
    try:
        cursor.execute(query, (vouch_by, user_id, vouch_text))
        conn.commit()
        print(f"Successfully added vouch to MySQL from: {vouch_by} (User ID: {user_id})")
        return True
    except mysql.connector.Error as err:
        print(f"MySQL Error adding vouch: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

def has_user_vouched(user_id: int) -> bool:
    """Checks if a user already has a visible vouch in the database."""
    conn = get_mysql_connection()
    if not conn:
        return True # Fail safe: prevent duplicate vouches if DB is down

    cursor = conn.cursor()
    query = "SELECT 1 FROM vouches WHERE user_id = %s AND status = 'visible' LIMIT 1"
    try:
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        return result is not None # Returns True if a vouch exists, False otherwise
    except mysql.connector.Error as err:
        print(f"MySQL Error checking vouch status: {err}")
        return True # Fail safe
    finally:
        cursor.close()
        conn.close()

def reset_vouch_for_user(user_id: int) -> bool:
    """Resets a user's vouch by marking their existing vouch as 'deleted'."""
    conn = get_mysql_connection()
    if not conn:
        return False

    cursor = conn.cursor()
    query = "UPDATE vouches SET status = 'deleted' WHERE user_id = %s AND status = 'visible' LIMIT 1"
    try:
        cursor.execute(query, (user_id,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Successfully reset vouch for user_id: {user_id}")
            return True
        else:
            print(f"No active vouch found to reset for user_id: {user_id}")
            return True # Not an error if no vouch existed
    except mysql.connector.Error as err:
        print(f"MySQL Error on resetting vouch: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

def delete_vouch_from_mysql(vouch_text):
    """Deletes a vouch from the MySQL database based on its text content."""
    conn = get_mysql_connection()
    if not conn:
        return False

    cursor = conn.cursor()
    query = "UPDATE vouches SET status = 'deleted' WHERE vouch_text = %s LIMIT 1"
    try:
        cursor.execute(query, (vouch_text,))
        if cursor.rowcount > 0:
            conn.commit()
            print(f"Successfully marked vouch as deleted in MySQL with text: {vouch_text[:30]}...")
            return True
        else:
            print(f"No vouch found in MySQL to delete with text: {vouch_text[:30]}...")
            return False
    except mysql.connector.Error as err:
        print(f"MySQL Error on delete: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_vouch_text_from_message(message_text: str) -> str | None:
    """
    Parses the full text of a vouch message and returns only the comment part.
    This is needed for the /del_vouch command to find the correct database entry.
    """
    if not message_text:
        return None

    parts = message_text.strip().split()
    if len(parts) > 2 and parts[1].startswith('@'):
        return " ".join(parts[2:])

    elif len(parts) > 1 and parts[0].lower() == 'vouch':
        return " ".join(parts[1:])

    else:
        return None
    
def save_invoice_to_mysql(invoice_id, amount, url_key, currency_id=None, chat_id=None, message_id=None):
    """Saves the new invoice with its unique URL key and message location."""
    conn = get_mysql_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    query = ("INSERT INTO invoices (invoice_id, amount, url_key, currency_id, customer_chat_id, customer_message_id, status, notified) "
             "VALUES (%s, %s, %s, %s, %s, %s, 'pending', FALSE)")
    try:
        cursor.execute(query, (invoice_id, amount, url_key, currency_id, chat_id, message_id))
        conn.commit()
        print(f"Successfully added invoice {invoice_id} to MySQL.")
        return True
    except mysql.connector.Error as err:
        print(f"MySQL Error on saving invoice: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_paid_unnotified_invoices_from_mysql():
    """Fetches invoices that are paid but not yet notified from MySQL."""
    conn = get_mysql_connection()
    if not conn:
        return []
        
    cursor = conn.cursor(dictionary=True)
    query = "SELECT invoice_id, amount, customer_chat_id, customer_message_id FROM invoices WHERE status = 'paid' AND notified = FALSE"
    
    invoices = []
    try:
        cursor.execute(query)
        invoices = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"MySQL Error fetching paid invoices: {err}")
    finally:
        cursor.close()
        conn.close()
    
    return invoices

def update_invoice_notified_status_mysql(invoice_id):
    conn = get_mysql_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    query = "UPDATE invoices SET notified = TRUE WHERE invoice_id = %s"
    try:
        cursor.execute(query, (invoice_id,))
        conn.commit()
        print(f"Successfully marked invoice {invoice_id} as notified in MySQL.")
        return True
    except mysql.connector.Error as err:
        print(f"MySQL Error on updating notified status: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

def save_transaction_to_mysql(tx_id, chain, chat_id, message_id, business_connection_id = '', status = "pending"):
    """Saves a new transaction to the MySQL database."""
    conn = get_mysql_connection()
    if not conn: return False
    
    cursor = conn.cursor()
    query = ("INSERT INTO transactions (tx_id, chain, chat_id, message_id, business_connection_id, status) "
             "VALUES (%s, %s, %s, %s, %s, %s)")
    try:
        cursor.execute(query, (tx_id, chain, chat_id, message_id, business_connection_id, status))
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"MySQL Error on saving transaction: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_pending_transactions_from_mysql():
    """Fetches all pending transactions from MySQL."""
    conn = get_mysql_connection()
    if not conn: return []

    cursor = conn.cursor(dictionary=True)
    query = "SELECT id, tx_id, chain, message_id, chat_id, business_connection_id, date FROM transactions WHERE status = 'pending'"
    
    transactions = []
    try:
        cursor.execute(query)
        transactions = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"MySQL Error fetching pending transactions: {err}")
    finally:
        cursor.close()
        conn.close()
    
    return transactions

def update_transaction_status_in_mysql(transaction_id, status, chain=None):
    """Updates the status and optionally the chain of a transaction in MySQL."""
    conn = get_mysql_connection()
    if not conn: return False

    cursor = conn.cursor()
    if chain:
        query = "UPDATE transactions SET status = %s, chain = %s WHERE id = %s"
        params = (status, chain, transaction_id)
    else:
        query = "UPDATE transactions SET status = %s WHERE id = %s"
        params = (status, transaction_id)

    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"MySQL Error on updating transaction status: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

def is_new_user(user_id: int) -> bool:
    """Checks if a user_id exists in the users table."""
    conn = get_mysql_connection()
    if not conn: return False 
    
    cursor = conn.cursor()
    query = "SELECT user_id FROM users WHERE user_id = %s"
    try:
        cursor.execute(query, (user_id,))
        is_existing = cursor.fetchone() is not None
        return not is_existing
    except mysql.connector.Error as err:
        print(f"MySQL Error checking user: {err}")
        return False 
    finally:
        cursor.close()
        conn.close()

# MODIFIED: Ensure new users can vouch by default
def add_user(user_id: int):
    """Adds a new user with vouching permission enabled by default."""
    conn = get_mysql_connection()
    if not conn: return False
    
    cursor = None
    try:
        cursor = conn.cursor()
        # Inserts a new user with can_vouch set to 1. IGNORE does nothing if user exists.
        query = "INSERT IGNORE INTO users (user_id, can_vouch) VALUES (%s, 1)"
        cursor.execute(query, (user_id,))
        conn.commit()
        print(f"User added or already exists: {user_id}")
        return True
    except mysql.connector.Error as err:
        print(f"MySQL Error adding user: {err}")
        return False
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

def update_invoice_message_id(invoice_id, message_id):
    """Updates an existing invoice with the message_id after it has been sent."""
    conn = get_mysql_connection()
    if not conn: return False
    
    cursor = conn.cursor()
    query = "UPDATE invoices SET customer_message_id = %s WHERE invoice_id = %s"
    try:
        cursor.execute(query, (message_id, invoice_id))
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"MySQL Error on updating message_id: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

def save_reminder_to_mysql(remind_at, reminder_text, chat_id, business_connection_id=None):
    """Saves a new reminder to the MySQL database."""
    conn = get_mysql_connection()
    if not conn:
        return False

    cursor = conn.cursor()
    query = ("INSERT INTO reminders (remind_at, reminder_text, chat_id, business_connection_id, status) "
             "VALUES (%s, %s, %s, %s, 'pending')")
    try:
        cursor.execute(query, (remind_at, reminder_text, chat_id, business_connection_id))
        conn.commit()
        print(f"Successfully saved reminder for chat_id {chat_id} at {remind_at}.")
        return True
    except mysql.connector.Error as err:
        print(f"MySQL Error on saving reminder: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_due_reminders_from_mysql():
    """Fetches all pending reminders that are due."""
    conn = get_mysql_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)
    query = "SELECT id, reminder_text, chat_id, business_connection_id FROM reminders WHERE remind_at <= NOW() AND status = 'pending'"

    reminders = []
    try:
        cursor.execute(query)
        reminders = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"MySQL Error fetching due reminders: {err}")
    finally:
        cursor.close()
        conn.close()
    return reminders

def update_reminder_status_mysql(reminder_id, status):
    """Updates the status of a reminder in MySQL."""
    conn = get_mysql_connection()
    if not conn:
        return False

    cursor = conn.cursor()
    query = "UPDATE reminders SET status = %s WHERE id = %s"
    try:
        cursor.execute(query, (status, reminder_id))
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"MySQL Error on updating reminder status: {err}")
        return False
    finally:
        cursor.close()
        conn.close()