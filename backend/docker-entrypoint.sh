#!/bin/bash
set -e

# 检查PM2安装状态
python check_pm2.py

# 创建utils目录（如果不存在）
mkdir -p /app/backend/utils

# 确保子目录中的__init__.py文件存在
touch /app/backend/utils/__init__.py

# 创建用于检查数据库连接的临时Python脚本
cat > check_db.py << EOL
import psycopg2
import os
import sys
import time

# 从环境变量获取数据库连接信息
host = os.environ.get('DB_HOST', 'kingbase')
port = os.environ.get('DB_PORT', '54321')
user = os.environ.get('DB_USER', 'system')
password = os.environ.get('DB_PASSWORD', '12345678ab')
dbname = os.environ.get('DB_NAME', 'windpower')

try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        connect_timeout=3
    )
    conn.close()
    print("数据库连接成功")
    sys.exit(0)
except Exception as e:
    print(f"数据库连接失败: {e}")
    sys.exit(1)
EOL

# 等待PostgreSQL和MinIO服务可用
echo "等待数据库服务就绪..."
for i in {1..30}; do
  if python check_db.py; then
    echo "数据库服务已就绪"
    break
  fi
  echo "等待数据库服务启动... $i/30"
  sleep 2
done

# 初始化数据库和用户
echo "初始化数据库和用户..."
python -m init_users

# 修复管理员权限
echo "检查并修复管理员权限..."
python -m fix_admin_permissions

# 修复所有角色权限
echo "检查并修复所有角色权限..."
python -m fix_user_permissions

# 使用标记文件判断是否为首次部署
# 确保工作目录存在
mkdir -p /app/backend/data

# 使用相对于应用的稳定路径
INIT_FLAG_FILE="/app/backend/data/admin_initialized.flag"
if [ ! -f "$INIT_FLAG_FILE" ]; then
    echo "首次部署：重置管理员密码为默认值(admin123)..."
    python -m reset_admin
    # 创建标记文件，表示已完成初始化
    touch "$INIT_FLAG_FILE"
    echo "已完成管理员密码初始化"
else
    echo "检测到已初始化标记，跳过管理员密码重置"
fi

# 启动应用
echo "启动应用..."
pm2-runtime start ecosystem.config.js 