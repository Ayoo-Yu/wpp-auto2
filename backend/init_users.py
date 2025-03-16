from database_config import get_db, Base, engine
from models import User, UserRole
from werkzeug.security import generate_password_hash
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def init_users_and_roles():
    """初始化默认角色和管理员用户"""
    try:
        # 创建数据库表
        Base.metadata.create_all(bind=engine)
        
        db = next(get_db())
        
        # 检查是否已经有角色
        roles_count = db.query(UserRole).count()
        if roles_count > 0:
            logger.info("已经存在角色数据，跳过初始化")
            return
        
        logger.info("开始初始化默认角色和管理员用户")
        
        # 创建默认角色
        admin_role = UserRole(
            name="系统管理员",
            description="系统管理员，拥有所有权限",
            permissions={
                "homepage": {"view": True, "edit": True},
                "modeltrain": {"view": True, "edit": True},
                "powerpredict": {"view": True, "edit": True},
                "autopredict": {"view": True, "edit": True},
                "powercompare": {"view": True, "edit": True},
                "users": {"view": True, "edit": True}
            }
        )
        
        operator_role = UserRole(
            name="运行操作人员",
            description="运行操作人员，可以操作大部分功能",
            permissions={
                "homepage": {"view": True, "edit": True},
                "modeltrain": {"view": True, "edit": True},
                "powerpredict": {"view": True, "edit": True},
                "autopredict": {"view": True, "edit": True},
                "powercompare": {"view": True, "edit": True},
                "users": {"view": False, "edit": False}
            }
        )
        
        viewer_role = UserRole(
            name="普通人员",
            description="普通人员，只能查看",
            permissions={
                "homepage": {"view": True, "edit": False},
                "modeltrain": {"view": True, "edit": False},
                "powerpredict": {"view": True, "edit": False},
                "autopredict": {"view": True, "edit": False},
                "powercompare": {"view": True, "edit": False},
                "users": {"view": False, "edit": False}
            }
        )
        
        db.add_all([admin_role, operator_role, viewer_role])
        db.commit()
        
        # 创建默认管理员用户
        admin_user = User(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            email="admin@example.com",
            full_name="系统管理员",
            is_active=True,
            role_id=admin_role.id,
            created_at=datetime.now()
        )
        
        db.add(admin_user)
        db.commit()
        
        logger.info(f"初始化完成，创建了管理员用户: {admin_user.username}")
        
    except Exception as e:
        logger.error(f"初始化用户和角色失败: {str(e)}")
        raise

if __name__ == "__main__":
    init_users_and_roles() 