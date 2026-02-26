"""
PostgreSQL Database Client
Replaces SQLite for production use
"""

import asyncpg
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from src.config import settings


class PostgresClient:
    """Async PostgreSQL client"""
    
    def __init__(self):
        self.host = settings.postgres_host if hasattr(settings, 'postgres_host') else 'localhost'
        self.port = settings.postgres_port if hasattr(settings, 'postgres_port') else 5432
        self.database = settings.postgres_db if hasattr(settings, 'postgres_db') else 'voixai'
        self.user = settings.postgres_user if hasattr(settings, 'postgres_user') else 'postgres'
        self.password = settings.postgres_password if hasattr(settings, 'postgres_password') else 'postgres'
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=5,
                max_size=20
            )
            print(f"[Postgres] Connected to {self.database}")
            return True
        except Exception as e:
            print(f"[Postgres] Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            print("[Postgres] Disconnected")
    
    async def init_tables(self):
        """Initialize database tables"""
        async with self.pool.acquire() as conn:
            # Customers table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    phone_number VARCHAR(20) UNIQUE,
                    email VARCHAR(255),
                    name VARCHAR(100),
                    preferences JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Conversations table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    customer_id UUID REFERENCES customers(id),
                    session_id VARCHAR(100) UNIQUE NOT NULL,
                    channel VARCHAR(20) DEFAULT 'web',
                    started_at TIMESTAMP DEFAULT NOW(),
                    ended_at TIMESTAMP,
                    duration_seconds INTEGER,
                    status VARCHAR(20) DEFAULT 'active',
                    sentiment_start FLOAT,
                    sentiment_end FLOAT,
                    metadata JSONB DEFAULT '{}'
                )
            """)
            
            # Messages table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id UUID REFERENCES conversations(id),
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    audio_url VARCHAR(500),
                    latency_ms INTEGER,
                    tokens_input INTEGER,
                    tokens_output INTEGER,
                    timestamp TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Orders table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id UUID REFERENCES conversations(id),
                    customer_id UUID REFERENCES customers(id),
                    items JSONB NOT NULL,
                    total_amount DECIMAL(10,2) NOT NULL,
                    tax_amount DECIMAL(10,2),
                    status VARCHAR(20) DEFAULT 'pending',
                    order_type VARCHAR(20) DEFAULT 'pickup',
                    estimated_ready_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Tickets table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    ticket_type VARCHAR(50) NOT NULL,
                    description TEXT NOT NULL,
                    priority VARCHAR(20) DEFAULT 'medium',
                    status VARCHAR(20) DEFAULT 'open',
                    customer_info JSONB,
                    order_id UUID,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    resolved_at TIMESTAMP,
                    resolution_notes TEXT
                )
            """)
            
            print("[Postgres] Tables initialized")
    
    async def create_customer(self, name: str, phone: str = None, email: str = None) -> Dict:
        """Create a new customer"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO customers (name, phone_number, email)
                VALUES ($1, $2, $3)
                ON CONFLICT (phone_number) DO UPDATE SET
                    name = EXCLUDED.name,
                    updated_at = NOW()
                RETURNING id, name, phone_number, email, preferences
                """,
                name, phone, email
            )
            return dict(row)
    
    async def get_customer(self, customer_id: str = None, phone: str = None) -> Optional[Dict]:
        """Get customer by ID or phone"""
        async with self.pool.acquire() as conn:
            if customer_id:
                row = await conn.fetchrow(
                    "SELECT * FROM customers WHERE id = $1",
                    customer_id
                )
            elif phone:
                row = await conn.fetchrow(
                    "SELECT * FROM customers WHERE phone_number = $1",
                    phone
                )
            else:
                return None
            
            return dict(row) if row else None
    
    async def create_conversation(self, session_id: str, customer_id: str = None, channel: str = 'web') -> Dict:
        """Create a new conversation"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO conversations (session_id, customer_id, channel, status)
                VALUES ($1, $2, $3, 'active')
                RETURNING id, session_id, customer_id, channel, started_at, status
                """,
                session_id, customer_id, channel
            )
            return dict(row)
    
    async def save_message(self, conversation_id: str, role: str, content: str, 
                          latency_ms: int = None, tokens_in: int = None, tokens_out: int = None):
        """Save a message to the conversation"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, latency_ms, tokens_input, tokens_output)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                conversation_id, role, content, latency_ms, tokens_in, tokens_out
            )
    
    async def create_order(self, conversation_id: str, customer_id: str, items: List[Dict],
                          total: float, tax: float, order_type: str = 'pickup') -> Dict:
        """Create a new order"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO orders (conversation_id, customer_id, items, total_amount, tax_amount, order_type, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'pending')
                RETURNING id, items, total_amount, status, created_at
                """,
                conversation_id, customer_id, json.dumps(items), total, tax, order_type
            )
            return dict(row)
    
    async def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[Dict]:
        """Get conversation messages"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM messages 
                WHERE conversation_id = $1 
                ORDER BY timestamp DESC 
                LIMIT $2
                """,
                conversation_id, limit
            )
            return [dict(row) for row in rows]


class HybridMemoryManager:
    """
    Three-tier memory using PostgreSQL for persistent storage
    """
    
    def __init__(self):
        self.postgres = PostgresClient()
        self.working_memory = {}  # In-memory for current session
    
    async def init(self):
        """Initialize connections"""
        return await self.postgres.connect()
    
    async def start_conversation(self, session_id: str, customer_name: str) -> Dict:
        """Start a new conversation"""
        # Create/get customer
        customer = await self.postgres.create_customer(name=customer_name)
        
        # Create conversation
        conversation = await self.postgres.create_conversation(
            session_id=session_id,
            customer_id=customer['id']
        )
        
        # Initialize working memory
        self.working_memory[session_id] = {
            'customer': customer,
            'conversation': conversation,
            'messages': [],
            'order': {'items': []}
        }
        
        return {
            'customer_id': customer['id'],
            'conversation_id': conversation['id'],
            'session_id': session_id
        }
    
    async def add_message(self, session_id: str, role: str, content: str, **kwargs):
        """Add message to memory"""
        if session_id not in self.working_memory:
            return
        
        memory = self.working_memory[session_id]
        
        # Add to working memory
        memory['messages'].append({
            'role': role,
            'content': content,
            'timestamp': datetime.now()
        })
        
        # Persist to PostgreSQL
        conversation_id = memory['conversation']['id']
        await self.postgres.save_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            latency_ms=kwargs.get('latency_ms'),
            tokens_in=kwargs.get('tokens_in'),
            tokens_out=kwargs.get('tokens_out')
        )
    
    async def save_order(self, session_id: str, order_data: Dict):
        """Save order to database"""
        if session_id not in self.working_memory:
            return
        
        memory = self.working_memory[session_id]
        
        order = await self.postgres.create_order(
            conversation_id=memory['conversation']['id'],
            customer_id=memory['customer']['id'],
            items=order_data.get('items', []),
            total=order_data.get('total', 0),
            tax=order_data.get('tax', 0),
            order_type=order_data.get('order_type', 'pickup')
        )
        
        memory['order_db'] = order
        return order
    
    def get_context(self, session_id: str, limit: int = 10) -> str:
        """Get recent conversation context"""
        if session_id not in self.working_memory:
            return ""
        
        messages = self.working_memory[session_id]['messages'][-limit:]
        context = []
        for msg in messages:
            role = "Customer" if msg['role'] == 'user' else "Tasha"
            context.append(f"{role}: {msg['content']}")
        
        return "\n".join(context)
