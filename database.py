import sqlite3


def initialize_db():
    conn = sqlite3.connect("vouches.db")
    conn.execute("""
                CREATE TABLE IF NOT EXISTS vouches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vouch_by TEXT,
                    vouch_for TEXT,
                    message TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)

    conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_id TEXT,
                    chain TEXT,
                    chat_id TEXT,
                    message_id TEXT,
                    business_connection_id TEXT,
                    status TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)

    conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
    conn.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    invoice_id TEXT PRIMARY KEY,
                    amount REAL NOT NULL,
                    currency_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)

    conn.commit()
    conn.close()


def is_new_user(user_id: int) -> bool:
    """Check if a user is new by seeing if they are in the users table."""
    with sqlite3.connect("vouches.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is None

def add_user(user_id: int):
    """Add a new user to the users table."""
    with sqlite3.connect("vouches.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()


def save_vouch(vouch_by, vouch_for, message):
    conn = sqlite3.connect("vouches.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO vouches (vouch_by, vouch_for, message) VALUES (?, ?, ?)",
                (vouch_by, vouch_for, message))
    conn.commit()
    conn.close()


def save_transaction(tx_id, chain, chat_id, message_id, business_connection_id = '', status = "pending"):
    conn = sqlite3.connect("vouches.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO transactions (tx_id, chain, chat_id, message_id, business_connection_id, status) VALUES (?, ?, ?, ?, ?, ?)",
                (tx_id, chain, chat_id, message_id, business_connection_id, status))
    conn.commit()
    conn.close()

def delete_vouch_from_local_db(message_text):
    try:
        with sqlite3.connect("vouches.db") as conn:
            cursor = conn.cursor()
            query = "DELETE FROM vouches WHERE rowid = (SELECT rowid FROM vouches WHERE message = ? LIMIT 1)"
            
            cursor.execute(query, (message_text,))
            
            if cursor.rowcount > 0:
                conn.commit()
                print("Successfully deleted vouch from local SQLite DB.")
                return True
            else:
                print("No vouch found in local SQLite DB to delete.")
                return False
    except sqlite3.Error as e:
        print(f"SQLite Error on delete: {e}")
        return False
    
def save_invoice(invoice_id, amount, currency_id=None):
    with sqlite3.connect("vouches.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO invoices (invoice_id, amount, currency_id) VALUES (?, ?, ?)",
            (invoice_id, amount, currency_id)
        )
        conn.commit()