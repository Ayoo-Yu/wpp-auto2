import os
from minio import Minio
from minio.commonconfig import ENABLED
import json

KINGBASE_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "54321"),  # 金仓数据库默认端口
    "user": "system",                           # 金仓默认用户
    "password": "12345678ab",                   # 金仓默认密码
    "database": "test",                         # 使用test作为初始数据库
    "default_db": "test"                        # 默认数据库名称
}

MINIO_CONFIG = {
    "endpoint": os.environ.get("MINIO_ENDPOINT", "localhost") + ":" + os.environ.get("MINIO_PORT", "9000"),
    "access_key": "minioadmin",
    "secret_key": "minioadmin",
    "secure": False,
    "buckets": {
        "datasets": "wind-datasets",
        "models": "wind-models",
        "predictions": "wind-predictions",
        "scalers": "wind-scalers",
        "metrics": "wind-metrics",
        "logs": "wind-logs"
    },
    "access_control": {
        "wind-datasets": "private",
        "wind-models": "public-read",
        "wind-predictions": "private",
        "wind-scalers": "private",
        "wind-metrics": "public-read",
        "wind-logs": "public-read"
    }
}

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'forecasts')
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB
    ALLOWED_EXTENSIONS = {'csv','joblib'}

    KINGBASE_CONFIG = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "54321"),  # 金仓数据库默认端口
        "user": "system",                           # 金仓用户
        "password": "12345678ab",                   # 金仓密码
        "database": "test",                             # 使用test作为初始数据库
        "default_db": "test"                              # 默认数据库名称
    }
    
    MINIO_CONFIG = {
        "endpoint": os.environ.get("MINIO_ENDPOINT", "localhost") + ":" + os.environ.get("MINIO_PORT", "9000"),
        "access_key": "minioadmin",
        "secret_key": "minioadmin",
        "secure": False,
        "buckets": {
            "datasets": "wind-datasets",
            "models": "wind-models",
            "predictions": "wind-predictions",
            "scalers": "wind-scalers",
            "metrics": "wind-metrics",
            "logs": "wind-logs"
        },
        "access_control": {
            "wind-datasets": "private",
            "wind-models": "public-read",
            "wind-predictions": "private",
            "wind-scalers": "private",
            "wind-metrics": "public-read",
            "wind-logs": "public-read"
        }
    }

    MODEL_STORAGE = {
        'model_dir': os.path.join(BASE_DIR, 'saved_models'),
        'scaler_dir': os.path.join(BASE_DIR, 'saved_scalers'),
        'metrics_dir': os.path.join(BASE_DIR, 'saved_metrics')
    }

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{KINGBASE_CONFIG['user']}:{KINGBASE_CONFIG['password']}@{KINGBASE_CONFIG['host']}:{KINGBASE_CONFIG['port']}/windpower"
    PRESERVE_CONTEXT_ON_EXCEPTION = False

def set_bucket_policy(client, bucket_name, policy):
    """更精确的策略配置"""
    if policy == "private":
        policy_json = json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": [
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:PutObjectAcl",
                        "s3:GetObjectAcl"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}",
                        f"arn:aws:s3:::{bucket_name}/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                    "Condition": {
                        "StringEquals": {
                            "aws:UserAgent": "WindPowerForecast/1.0"
                        }
                    }
                }
            ]
        })
    elif policy == "public-read":
        policy_json = json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }]
        })
    client.set_bucket_policy(bucket_name, policy_json)
