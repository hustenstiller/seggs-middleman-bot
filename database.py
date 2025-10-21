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

    conn.commit()
    conn.close()


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
    """Deletes a vouch from the local SQLite database based on its text."""
    conn = sqlite3.connect("vouches.db")
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM vouches WHERE message = ? LIMIT 1", (message_text,))
        if cur.rowcount > 0:
            conn.commit()
            print(f"Successfully deleted vouch from local SQLite DB.")
            return True
        else:
            print(f"No vouch found in local SQLite DB to delete.")
            return False
    except sqlite3.Error as e:
        print(f"SQLite Error on delete: {e}")
        return False
    finally:
        conn.close()