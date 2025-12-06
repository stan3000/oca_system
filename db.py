import sqlite3
import pandas as pd

DB_PATH = "attendance.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)

    # ---------------- MEMBERS TABLE ----------------
    conn.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    # ---------------- ATTENDANCE TABLE ----------------
    conn.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        member_id INTEGER,
        status TEXT,
        notes TEXT,
        FOREIGN KEY(member_id) REFERENCES members(id)
    )
    """)

    # ---------------- REQUIRED UNIQUE INDEX ----------------
    # This is CRITICAL for the upsert_attendance() ON CONFLICT() to work
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_date_member
        ON attendance(date, member_id)
    """)

    return conn

# ======================================================================
#                          MEMBERS FUNCTIONS
# ======================================================================

def add_member(name):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO members (name) VALUES (?)", (name,))
    conn.commit()

def get_members():
    conn = get_connection()
    return pd.read_sql_query("SELECT * FROM members ORDER BY name ASC", conn)

# ======================================================================
#                        ATTENDANCE FUNCTIONS
# ======================================================================

def save_attendance(date, member_id, status, notes=""):
    conn = get_connection()
    conn.execute("""
        INSERT INTO attendance (date, member_id, status, notes)
        VALUES (?, ?, ?, ?)
    """, (date, member_id, status, notes))
    conn.commit()

def upsert_attendance(date, member_id, status, notes=""):
    """
    Upsert pattern:
    - If (date, member_id) does NOT exist → INSERT
    - If it DOES exist → UPDATE status + notes
    """
    conn = get_connection()
    conn.execute("""
        INSERT INTO attendance (date, member_id, status, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(date, member_id)
        DO UPDATE SET 
            status = excluded.status,
            notes = excluded.notes
    """, (date, member_id, status, notes))
    conn.commit()

def get_attendance():
    conn = get_connection()
    return pd.read_sql_query("""
        SELECT a.date, m.name, a.status, a.notes
        FROM attendance a
        JOIN members m ON m.id = a.member_id
        ORDER BY a.date DESC, m.name ASC
    """, conn)


# ================================================================== ADDED


def update_member_name(member_id, new_name):
    """
    Rename a member. Returns True if success, False if name already exists.
    """
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE members SET name = ? WHERE id = ?",
            (new_name, member_id)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Violates UNIQUE(name)
        return False
