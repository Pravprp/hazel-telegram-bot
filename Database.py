# Database.py
import os
import psycopg2
from datetime import datetime, timedelta
from Errors import logger

DATABASE_URL = os.getenv("DATABASE_URL")

DEFAULT_SETTINGS = {
    "language": "English",
    "translation": False,
    "voice_chat": False,
    "tone": "Friendly"
}

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    """Initializes the multi-tenant layout inside PostgreSQL."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_configs (
            group_id BIGINT PRIMARY KEY,
            language VARCHAR(50) DEFAULT 'English',
            translation BOOLEAN DEFAULT FALSE,
            voice_chat BOOLEAN DEFAULT FALSE,
            tone VARCHAR(30) DEFAULT 'Friendly',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_reset_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()
    logger.info("PostgreSQL database schemas successfully validated.")

def check_and_apply_quarterly_reset(group_id):
    """Resets records back to factory defaults if the 3-month lifespan expires."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_reset_at FROM group_configs WHERE group_id = %s;", (group_id,))
    row = cursor.fetchone()
    
    if row:
        last_reset = row[0]
        if datetime.utcnow() - last_reset >= timedelta(days=90):
            cursor.execute("""
                UPDATE group_configs 
                SET language = 'English', translation = FALSE, voice_chat = FALSE, 
                    tone = 'Friendly', last_reset_at = CURRENT_TIMESTAMP
                WHERE group_id = %s;
            """, (group_id,))
            conn.commit()
            logger.info(f"Quarterly configuration cycle automatically reset for group {group_id}")
    cursor.close()
    conn.close()

def get_group_config(group_id):
    """Fetches or registers a group context securely."""
    check_and_apply_quarterly_reset(group_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT language, translation, voice_chat, tone FROM group_configs WHERE group_id = %s;", 
        (group_id,)
    )
    row = cursor.fetchone()
    
    if not row:
        cursor.execute(
            "INSERT INTO group_configs (group_id) VALUES (%s) ON CONFLICT DO NOTHING;", 
            (group_id,)
        )
        conn.commit()
        config = DEFAULT_SETTINGS
    else:
        config = {
            "language": row[0],
            "translation": row[1],
            "voice_chat": row[2],
            "tone": row[3]
        }
        
    cursor.close()
    conn.close()
    return config

def update_group_config(group_id, column, value):
    """Updates group properties directly inside the row."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"UPDATE group_configs SET {column} = %s WHERE group_id = %s;"
    cursor.execute(query, (value, group_id))
    conn.commit()
    cursor.close()
    conn.close()
