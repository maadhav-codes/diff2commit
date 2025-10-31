"""Track token usage and costs."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class UsageRecord:
    """Record of API usage."""

    timestamp: str
    provider: str
    model: str
    tokens: int
    cost: float
    success: bool


class UsageTracker:
    """Track and report on API usage and costs."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize usage tracker.

        Args:
            db_path: Path to SQLite database
        """
        if db_path is None:
            home = Path.home()
            data_dir = home / ".local" / "share" / "d2c"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "usage.db"

        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                tokens INTEGER NOT NULL,
                cost REAL NOT NULL,
                success INTEGER NOT NULL
            )
        """
        )

        conn.commit()
        conn.close()

    def record_usage(
        self, provider: str, model: str, tokens: int, cost: float, success: bool = True
    ) -> None:
        """Record a usage event.

        Args:
            provider: AI provider name
            model: Model name
            tokens: Token count
            cost: Cost in USD
            success: Whether the request succeeded
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO usage (timestamp, provider, model, tokens, cost, success)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (datetime.now().isoformat(), provider, model, tokens, cost, 1 if success else 0),
        )

        conn.commit()
        conn.close()

    def get_total_usage(self) -> Dict[str, Any]:
        """Get total usage statistics.

        Returns:
            Dictionary with total stats
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) as total_requests,
                SUM(tokens) as total_tokens,
                SUM(cost) as total_cost,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_requests
            FROM usage
        """
        )

        row = cursor.fetchone()
        conn.close()

        return {
            "total_requests": row[0] or 0,
            "total_tokens": row[1] or 0,
            "total_cost": round(row[2] or 0, 4),
            "successful_requests": row[3] or 0,
        }

    def get_monthly_usage(self) -> Dict[str, Any]:
        """Get current month usage statistics.

        Returns:
            Dictionary with monthly stats
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get first day of current month
        now = datetime.now()
        first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        cursor.execute(
            """
            SELECT
                COUNT(*) as total_requests,
                SUM(tokens) as total_tokens,
                SUM(cost) as total_cost
            FROM usage
            WHERE timestamp >= ?
        """,
            (first_day.isoformat(),),
        )

        row = cursor.fetchone()
        conn.close()

        return {
            "month": now.strftime("%B %Y"),
            "requests": row[0] or 0,
            "tokens": row[1] or 0,
            "cost": round(row[2] or 0, 4),
        }

    def get_usage_by_provider(self) -> List[Dict[str, Any]]:
        """Get usage statistics by provider.

        Returns:
            List of provider statistics
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                provider,
                model,
                COUNT(*) as requests,
                SUM(tokens) as tokens,
                SUM(cost) as cost
            FROM usage
            GROUP BY provider, model
            ORDER BY cost DESC
        """
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "provider": row[0],
                "model": row[1],
                "requests": row[2],
                "tokens": row[3],
                "cost": round(row[4], 4),
            }
            for row in rows
        ]

    def get_recent_usage(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent usage records.

        Args:
            days: Number of days to look back

        Returns:
            List of recent usage records
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(days=days)

        cursor.execute(
            """
            SELECT timestamp, provider, model, tokens, cost, success
            FROM usage
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 50
        """,
            (cutoff.isoformat(),),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "timestamp": row[0],
                "provider": row[1],
                "model": row[2],
                "tokens": row[3],
                "cost": round(row[4], 4),
                "success": bool(row[5]),
            }
            for row in rows
        ]

    def check_monthly_limit(self, limit: float) -> tuple[bool, float]:
        """Check if monthly cost limit is exceeded.

        Args:
            limit: Monthly limit in USD

        Returns:
            Tuple of (exceeded, current_cost)
        """
        monthly = self.get_monthly_usage()
        current_cost = monthly["cost"]
        return current_cost >= limit, current_cost
