"""Database management with aiosqlite."""
import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import config


class Database:
    """Async SQLite database manager."""
    
    def __init__(self):
        self.db_path = config.DB_PATH
    
    async def init_db(self):
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Gmail accounts table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS gmail_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    credentials_enc BLOB NOT NULL,
                    token_enc BLOB,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_sync TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, email)
                )
            """)
            
            # User sessions table (for OAuth flow)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Notification settings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS notification_settings (
                    user_id INTEGER PRIMARY KEY,
                    enabled BOOLEAN DEFAULT 1,
                    keywords TEXT,
                    exclude_spam BOOLEAN DEFAULT 1,
                    exclude_promotions BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Rate limiting table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id INTEGER,
                    endpoint TEXT,
                    request_count INTEGER DEFAULT 0,
                    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, endpoint)
                )
            """)
            
            await db.commit()
    
    async def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """Add or update user."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (user_id, username, first_name, last_active)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_active = excluded.last_active
            """, (user_id, username, first_name, datetime.now()))
            await db.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def add_gmail_account(self, user_id: int, email: str, 
                               credentials_enc: bytes, token_enc: bytes = None):
        """Add Gmail account for user."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO gmail_accounts (user_id, email, credentials_enc, token_enc)
                VALUES (?, ?, ?, ?)
            """, (user_id, email, credentials_enc, token_enc))
            await db.commit()
    
    async def get_gmail_accounts(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all Gmail accounts for user."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT id, email, last_sync, is_active
                FROM gmail_accounts
                WHERE user_id = ? AND is_active = 1
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_gmail_account(self, account_id: int) -> Optional[Dict[str, Any]]:
        """Get specific Gmail account with credentials."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM gmail_accounts WHERE id = ?
            """, (account_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def update_token(self, account_id: int, token_enc: bytes):
        """Update Gmail account token."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE gmail_accounts
                SET token_enc = ?, last_sync = ?
                WHERE id = ?
            """, (token_enc, datetime.now(), account_id))
            await db.commit()
    
    async def delete_gmail_account(self, account_id: int):
        """Delete Gmail account."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE gmail_accounts SET is_active = 0 WHERE id = ?",
                (account_id,)
            )
            await db.commit()
    
    async def create_session(self, session_id: str, user_id: int, 
                            state: str, data: Dict = None):
        """Create user session."""
        async with aiosqlite.connect(self.db_path) as db:
            expires_at = datetime.now().timestamp() + config.SESSION_TIMEOUT
            await db.execute("""
                INSERT INTO sessions (session_id, user_id, state, data, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, user_id, state, 
                  json.dumps(data) if data else None,
                  datetime.fromtimestamp(expires_at)))
            await db.commit()
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM sessions 
                WHERE session_id = ? AND expires_at > ?
            """, (session_id, datetime.now())) as cursor:
                row = await cursor.fetchone()
                if row:
                    result = dict(row)
                    if result.get('data'):
                        result['data'] = json.loads(result['data'])
                    return result
                return None
    
    async def delete_session(self, session_id: str):
        """Delete session."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            await db.commit()
    
    async def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sessions WHERE expires_at < ?", (datetime.now(),))
            await db.commit()
    
    async def get_notification_settings(self, user_id: int) -> Dict[str, Any]:
        """Get notification settings for user."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM notification_settings WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                # Return defaults
                return {
                    'enabled': True,
                    'keywords': None,
                    'exclude_spam': True,
                    'exclude_promotions': True
                }
    
    async def update_notification_settings(self, user_id: int, **settings):
        """Update notification settings."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO notification_settings (user_id, enabled, keywords, 
                                                   exclude_spam, exclude_promotions)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    enabled = excluded.enabled,
                    keywords = excluded.keywords,
                    exclude_spam = excluded.exclude_spam,
                    exclude_promotions = excluded.exclude_promotions
            """, (
                user_id,
                settings.get('enabled', True),
                settings.get('keywords'),
                settings.get('exclude_spam', True),
                settings.get('exclude_promotions', True)
            ))
            await db.commit()
    
    async def check_rate_limit(self, user_id: int, endpoint: str) -> bool:
        """Check if user exceeded rate limit."""
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now()
            window_start = datetime.fromtimestamp(
                now.timestamp() - config.RATE_LIMIT_WINDOW
            )
            
            async with db.execute("""
                SELECT request_count, window_start FROM rate_limits
                WHERE user_id = ? AND endpoint = ?
            """, (user_id, endpoint)) as cursor:
                row = await cursor.fetchone()
                
                if not row:
                    # First request
                    await db.execute("""
                        INSERT INTO rate_limits (user_id, endpoint, request_count)
                        VALUES (?, ?, 1)
                    """, (user_id, endpoint))
                    await db.commit()
                    return True
                
                count, start = row
                start_dt = datetime.fromisoformat(start)
                
                if start_dt < window_start:
                    # Reset window
                    await db.execute("""
                        UPDATE rate_limits
                        SET request_count = 1, window_start = ?
                        WHERE user_id = ? AND endpoint = ?
                    """, (now, user_id, endpoint))
                    await db.commit()
                    return True
                
                if count >= config.RATE_LIMIT_REQUESTS:
                    return False
                
                # Increment
                await db.execute("""
                    UPDATE rate_limits
                    SET request_count = request_count + 1
                    WHERE user_id = ? AND endpoint = ?
                """, (user_id, endpoint))
                await db.commit()
                return True


# Global database instance
db = Database()
