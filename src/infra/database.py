from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from settings import ASYNC_STR_DATABASE

# Motor assíncrono - Otimizado
# Certifique-se que ASYNC_STR_DATABASE comece com "mysql+aiomysql://"
async_engine = create_async_engine(
    ASYNC_STR_DATABASE,
    echo=True,
    pool_pre_ping=True,  # Ajuda a manter a conexão com o MySQL estável no Docker
)

# Base para os modelos ORM
Base = declarative_base()

# Fábrica de sessões assíncronas
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


# Cria as tabelas no banco de dados (usado na inicialização)
async def cria_tabelas():
    async with async_engine.begin() as conn:
        # Importe seus modelos aqui antes de criar, se necessário
        await conn.run_sync(Base.metadata.create_all)


# Dependência para as rotas do FastAPI (Dependency Injection)
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
