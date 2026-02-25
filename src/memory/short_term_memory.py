"""
Short-Term Memory - Redis-based session storage
Persists conversation state for session duration
"""

import json
from typing import Dict, Optional
import redis.asyncio as redis
from src.config import settings


class ShortTermMemory:
    """Redis-based short-term memory for session persistence"""
    
    def __init__(self, host: str = None, port: int = None, db: int = None):
        self.host = host or settings.redis_host
        self.port = port or settings.redis_port
        self.db = db or settings.redis_db
        self._redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        if self._redis is None:
            self._redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True
            )
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    def _key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"session:{session_id}"
    
    async def save_session(
        self, 
        session_id: str, 
        data: Dict,
        ttl: int = 3600  # 1 hour default
    ):
        """Save session data to Redis"""
        await self.connect()
        key = self._key(session_id)
        
        await self._redis.hset(key, mapping={
            "data": json.dumps(data),
            "last_activity": json.dumps({"timestamp": "now"})
        })
        await self._redis.expire(key, ttl)
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data from Redis"""
        await self.connect()
        key = self._key(session_id)
        
        data = await self._redis.hget(key, "data")
        if data:
            return json.loads(data)
        return None
    
    async def update_session(
        self, 
        session_id: str, 
        updates: Dict,
        ttl: int = 3600
    ):
        """Update session data"""
        existing = await self.get_session(session_id) or {}
        existing.update(updates)
        await self.save_session(session_id, existing, ttl)
    
    async def delete_session(self, session_id: str):
        """Delete session"""
        await self.connect()
        key = self._key(session_id)
        await self._redis.delete(key)
    
    async def exists(self, session_id: str) -> bool:
        """Check if session exists"""
        await self.connect()
        key = self._key(session_id)
        return await self._redis.exists(key) > 0
