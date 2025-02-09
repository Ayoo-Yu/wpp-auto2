from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from minio import Minio
from config import POSTGRES_CONFIG, MINIO_CONFIG
from base import Base


# 修改后（使用config中的配置）
SQLALCHEMY_DATABASE_URL = (
    f"postgresql+psycopg2://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}"
    f"@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 初始化MinIO客户端（使用config中的配置）
minio_client = Minio(
    MINIO_CONFIG["endpoint"],
    access_key=MINIO_CONFIG["access_key"],
    secret_key=MINIO_CONFIG["secret_key"],
    secure=MINIO_CONFIG["secure"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
