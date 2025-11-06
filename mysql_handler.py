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

def get_mysql_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def add_vouch_to_mysql(vouch_by, vouch_text):
    """Adds a vouch to the MySQL database, ignoring duplicates."""
    conn = get_mysql_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    query = ("INSERT INTO vouches (vouch_by, vouch_text) "
             "VALUES (%s, %s)")
    try:
        cursor.execute(query, (vouch_by, vouch_text))
        conn.commit()
        print(f"Successfully added vouch to MySQL from: {vouch_by}")
        return True
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_DUP_ENTRY:
            print(f"Duplicate vouch detected, not adding to MySQL.")
        else:
            print(f"MySQL Error: {err}")
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
    
def save_invoice_to_mysql(invoice_id, amount, url_key, currency_id=None):
    """Saves the new invoice with its unique URL key to the database."""
    conn = get_mysql_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    query = ("INSERT INTO invoices (invoice_id, amount, url_key, currency_id, status, notified) "
             "VALUES (%s, %s, %s, %s, 'pending', FALSE)")
    try:
        cursor.execute(query, (invoice_id, amount, url_key, currency_id))
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
    query = "SELECT invoice_id, amount FROM invoices WHERE status = 'paid' AND notified = FALSE"
    
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

def get_mysql_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def add_vouch_to_mysql(vouch_by, vouch_text):
    """Adds a vouch to the MySQL database, ignoring duplicates."""
    conn = get_mysql_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    query = ("INSERT INTO vouches (vouch_by, vouch_text) "
             "VALUES (%s, %s)")
    try:
        cursor.execute(query, (vouch_by, vouch_text))
        conn.commit()
        print(f"Successfully added vouch to MySQL from: {vouch_by}")
        return True
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_DUP_ENTRY:
            print(f"Duplicate vouch detected, not adding to MySQL.")
        else:
            print(f"MySQL Error: {err}")
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
    query = "SELECT invoice_id, amount FROM invoices WHERE status = 'paid' AND notified = FALSE"
    
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

# --- NEW FUNCTIONS ---

def is_new_user(user_id: int) -> bool:
    """Checks if a user_id exists in the users table."""
    conn = get_mysql_connection()
    if not conn: return False # Assume not new if DB fails
    
    cursor = conn.cursor()
    query = "SELECT user_id FROM users WHERE user_id = %s"
    try:
        cursor.execute(query, (user_id,))
        # If fetchone() finds a row, it returns a tuple. If not, it returns None.
        is_existing = cursor.fetchone() is not None
        return not is_existing
    except mysql.connector.Error as err:
        print(f"MySQL Error checking user: {err}")
        return False # Fail safe
    finally:
        cursor.close()
        conn.close()

def add_user(user_id: int):
    """Adds a new user's ID to the users table."""
    conn = get_mysql_connection()
    if not conn: return False
    
    cursor = conn.cursor()
    # INSERT IGNORE will prevent errors if the user already exists (e.g., in a race condition)
    query = "INSERT IGNORE INTO users (user_id) VALUES (%s)"
    try:
        cursor.execute(query, (user_id,))
        conn.commit()
        print(f"New user added to database: {user_id}")
        return True
    except mysql.connector.Error as err:
        print(f"MySQL Error adding user: {err}")
        return False
    finally:
        cursor.close()
        conn.close()