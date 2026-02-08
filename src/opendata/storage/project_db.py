import sqlite3
from pathlib import Path
from typing import List, Dict, Optional


class ProjectInventoryDB:
    """Manages project file inventory in a SQLite database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Performance PRAGMAs for fast bulk operations
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_inventory (
                    path TEXT PRIMARY KEY,
                    size INTEGER,
                    mtime REAL
                )
            """)
            conn.commit()

    def update_inventory(self, files: List[dict]):
        """Replaces the entire inventory with new data using an optimized transaction."""
        with sqlite3.connect(self.db_path) as conn:
            # Optimize transaction
            conn.execute("PRAGMA synchronous = OFF")
            conn.execute("BEGIN TRANSACTION")
            try:
                conn.execute("DELETE FROM file_inventory")
                conn.executemany(
                    "INSERT INTO file_inventory (path, size, mtime) VALUES (:path, :size, :mtime)",
                    files,
                )
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e

    def get_inventory(self) -> List[dict]:
        """Returns the complete cached inventory."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT path, size, mtime FROM file_inventory ORDER BY path"
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_file_count(self) -> int:
        """Returns the number of files in the inventory."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM file_inventory").fetchone()[0]
