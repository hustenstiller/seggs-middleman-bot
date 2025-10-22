import mysql.connector
from mysql.connector import errorcode

MYSQL_CONFIG = {
    'user': 'u792117142_seggs',
    'password': 'co2eBih=wipL4OS',
    'host': 'srv480.hstgr.io',
    'database': 'u792117142_seggs_vouch'
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