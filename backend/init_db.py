from database_config import engine
from base import Base
from models import *

def init_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("数据库已重新初始化")

if __name__ == "__main__":
    init_db() 