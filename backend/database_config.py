from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from minio import Minio
from config import POSTGRES_CONFIG, MINIO_CONFIG
from base import Base
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy.orm import Session
from models import Model
from sqlalchemy import inspect


# 修改后（使用config中的配置）
SQLALCHEMY_DATABASE_URL = (
    f"postgresql+psycopg2://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}"
    f"@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"
)

# 在engine创建之前添加数据库自动创建逻辑
def create_database_if_not_exists():
    # 使用默认数据库连接
    conn = psycopg2.connect(
        dbname="postgres",
        user=POSTGRES_CONFIG['user'],
        password=POSTGRES_CONFIG['password'],
        host=POSTGRES_CONFIG['host'],
        port=POSTGRES_CONFIG['port']
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    try:
        with conn.cursor() as cursor:
            # 检查数据库是否存在
            cursor.execute(
                sql.SQL("SELECT 1 FROM pg_database WHERE datname = {}")
                .format(sql.Literal(POSTGRES_CONFIG['database']))
            )
            exists = cursor.fetchone()
            
            if not exists:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}")
                    .format(sql.Identifier(POSTGRES_CONFIG['database']))
                )
                print(f"✅ 成功创建数据库: {POSTGRES_CONFIG['database']}")
            else:
                print(f"✅ 数据库已存在: {POSTGRES_CONFIG['database']}")
    finally:
        conn.close()

# 执行数据库创建
create_database_if_not_exists()

# 原有engine创建保持不变
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 在engine创建之后检查迁移
def check_migrations():
    inspector = inspect(engine)
    
    if not inspector.has_table("models"):
        Base.metadata.create_all(engine)
        print("✅ 已自动创建缺失的数据库表")

check_migrations()  # 现在engine已经定义

# 初始化MinIO客户端（使用config中的配置）
minio_client = Minio(
    MINIO_CONFIG["endpoint"],
    access_key=MINIO_CONFIG["access_key"],
    secret_key=MINIO_CONFIG["secret_key"],
    secure=MINIO_CONFIG["secure"]
)

# 修改后的初始化部分
required_buckets = list(MINIO_CONFIG["buckets"].values())
existing_buckets = [b.name for b in minio_client.list_buckets()]

for bucket in required_buckets:
    if bucket not in existing_buckets:
        minio_client.make_bucket(bucket)
        print(f"✅ 成功创建存储桶: {bucket}")
    else:
        print(f"✅ 存储桶已存在: {bucket}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def cleanup_old_models(db: Session, keep_last=5):
    """保留最近5个模型版本"""
    try:
        # 获取所有模型按时间倒序
        models = db.query(Model).order_by(Model.train_time.desc()).all()
        
        # 删除旧版本
        for model in models[keep_last:]:
            # 删除MinIO中的文件
            try:
                minio_client.remove_object("wind-models", model.model_path)
                if model.scaler_path:
                    minio_client.remove_object("wind-scalers", model.scaler_path)
            except Exception as e:
                print(f"删除MinIO文件失败: {e}")
            
            # 删除数据库记录
            db.delete(model)
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
