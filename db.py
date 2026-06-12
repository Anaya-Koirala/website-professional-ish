import datetime
import sqlite3

tables: list[str] = ["messages", "writings"]


def create_conn():
    return sqlite3.connect("database.sqlite")


def create_table() -> None:
    conn = create_conn()
    cursor = conn.cursor()
    for table in tables:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(15) NOT NULL,
                date DATE NOT NULL,
                content TEXT NOT NULL
            )
            """
        )
    conn.commit()
    conn.close()


def get_all(table: str):
    conn = create_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table} ORDER BY id DESC")
    data = cursor.fetchall()
    conn.close()
    return data


def get_post(table: str, post_id: int):
    conn = create_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table} WHERE id=?", (post_id,))
    post = cursor.fetchone()
    conn.close()
    return post


def create_post(table: str, username: str, content: str) -> None:
    conn = create_conn()
    cursor = conn.cursor()
    today: str = datetime.datetime.now().strftime("%d-%b-%y")
    cursor.execute(
        f"INSERT INTO {table} (username, date, content) VALUES (?, ?, ?)",
        (username, today, content),
    )
    conn.commit()
    conn.close()


def delete_post(table: str, post_id: int) -> None:
    conn = create_conn()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table} WHERE id=?", (post_id,))
    conn.commit()
    conn.close()
