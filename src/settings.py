from dotenv import load_dotenv, find_dotenv
import os
from pathlib import Path
# localiza o arquivo de .env
dotenv_file = find_dotenv()

# Carrega o arquivo .env
load_dotenv(dotenv_file)

BASE_DIR = Path(__file__).resolve().parent

# Configurações da API
HOST = os.getenv("HOST", "0.0.0.0")
PORT = os.getenv("PORT", "8000")
RELOAD = os.getenv("RELOAD", True)

# Configurações banco de dados
DB_SGDB = os.getenv("DB_SGDB")
DB_NAME = os.getenv("DB_NAME")

# Caso seja diferente de sqlite
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# Ajusta STR_DATABASE conforme gerenciador escolhido
if DB_SGDB == "sqlite":
    DB_PATH = BASE_DIR / f"{DB_NAME}.db"
    STR_DATABASE = f"sqlite:///{DB_PATH}"

# Configurações de database assíncrono
# Converte string de conexão para async se necessário
if STR_DATABASE.startswith("sqlite:///"):
    ASYNC_STR_DATABASE = STR_DATABASE.replace("sqlite:///", "sqlite+aiosqlite:///")
elif STR_DATABASE.startswith("sqlite://"):
    ASYNC_STR_DATABASE = STR_DATABASE.replace("sqlite://", "sqlite+aiosqlite:///")

# Configurações JWT
SECRET_KEY = os.getenv("SECRET_KEY", "d6cf05df57c5fe76a488f84827a35851c0b718e465b478937fc97a95a0fd7a01")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
