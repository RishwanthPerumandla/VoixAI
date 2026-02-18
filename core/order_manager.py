"""Order persistence with SQLite"""
import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager


class OrderManager:
    """Manages order persistence and conversation logging"""
    
    def __init__(self, db_path: str = "orders.db"):
        self.db_path = db_path
        self._init_tables()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_tables(self):
        """Initialize SQLite tables"""
        with self._get_connection() as conn:
            # Orders table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    items_json TEXT NOT NULL DEFAULT '[]',
                    total_items INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    special_instructions TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            
            # Conversation logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    audio_ms INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id)
                )
            """)
            
            # Create index for faster lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_session ON orders(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_order ON conversation_logs(order_id)")
    
    def create_order(self, session_id: str) -> int:
        """Create a new order and return its ID"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO orders (session_id, items_json, total_items) VALUES (?, ?, ?)",
                (session_id, '[]', 0)
            )
            return cursor.lastrowid
    
    def update_order_items(self, order_id: int, items: list):
        """Update order items"""
        total = sum(item.get("qty", 1) for item in items)
        items_json = json.dumps(items)
        
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE orders SET items_json = ?, total_items = ? WHERE id = ?",
                (items_json, total, order_id)
            )
    
    def log_turn(self, order_id: int, role: str, content: str, audio_ms: int = 0):
        """Log a conversation turn"""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO conversation_logs (order_id, role, content, audio_ms) VALUES (?, ?, ?, ?)",
                (order_id, role, content, audio_ms)
            )
    
    def complete_order(self, order_id: int, instructions: str = ""):
        """Mark order as completed"""
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE orders 
                   SET status = 'completed', 
                       completed_at = CURRENT_TIMESTAMP,
                       special_instructions = ?
                   WHERE id = ?""",
                (instructions, order_id)
            )
    
    def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
            
            if row:
                return {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "items": json.loads(row["items_json"]),
                    "total_items": row["total_items"],
                    "status": row["status"],
                    "special_instructions": row["special_instructions"],
                    "created_at": row["created_at"],
                    "completed_at": row["completed_at"]
                }
            return None
    
    def get_conversation_history(self, order_id: int) -> list:
        """Get conversation logs for an order"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM conversation_logs WHERE order_id = ? ORDER BY timestamp",
                (order_id,)
            ).fetchall()
            
            return [
                {
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "audio_ms": row["audio_ms"],
                    "timestamp": row["timestamp"]
                }
                for row in rows
            ]
