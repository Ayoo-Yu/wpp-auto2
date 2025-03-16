from database_config import Base, engine
from scripts.init_users import init_users_and_roles

# 创建所有表
Base.metadata.create_all(bind=engine)

# 初始化用户和角色
init_users_and_roles()

print("数据库初始化完成") 