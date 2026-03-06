import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger("mcp_prototype.db")

MONGO_URI = os.getenv("AZURE_MONGODB_CONNECTION_STRING", "sua_string_de_conexao")
DB_NAME = os.getenv("AZURE_MONGODB_DATABASE_NAME", "seu_banco")

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_to_mongo():
    db_instance.client = AsyncIOMotorClient(MONGO_URI)
    db_instance.db = db_instance.client[DB_NAME]
    logger.info("🟢 Conectado ao MongoDB do MCP de Protótipos.")

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        logger.info("🔴 Conexão com MongoDB encerrada.")
