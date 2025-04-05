#!/usr/bin/env python3
"""
用户权限修复工具 - 确保所有角色的权限正确设置
"""
import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import get_db
from db_models import User, Role
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_all_roles_permissions():
    """检查并修复所有角色权限"""
    try:
        db = next(get_db())
        
        # 查找所有角色
        roles = db.query(Role).all()
        logger.info(f"找到 {len(roles)} 个角色")
        
        for role in roles:
            logger.info(f"检查角色: {role.name}")
            logger.info(f"当前权限: {role.permissions}")
            
            if role.name == "系统管理员":
                # 确保系统管理员有所有权限
                role.permissions = {
                    "permissions": [
                        "manage_users",
                        "manage_roles",
                        "view_all_data",
                        "upload_files",
                        "download_files",
                        "train_models",
                        "run_predictions",
                        "configure_system",
                        "view_dashboard",
                        "manage_tasks"
                    ]
                }
                logger.info("已更新系统管理员权限")
            
            elif role.name == "运行操作人员":
                # 确保运行操作人员有正确的权限
                role.permissions = {
                    "permissions": [
                        "view_all_data",
                        "upload_files",
                        "download_files",
                        "train_models",
                        "run_predictions",
                        "view_dashboard"
                    ]
                }
                logger.info("已更新运行操作人员权限")
            
            elif role.name == "普通人员":
                # 确保普通人员只有查看权限
                role.permissions = {
                    "permissions": [
                        "view_dashboard"
                    ]
                }
                logger.info("已更新普通人员权限")
            
            # 检查权限格式
            if not isinstance(role.permissions, dict) or "permissions" not in role.permissions:
                logger.error(f"角色 {role.name} 权限格式不正确，正在修复")
                if isinstance(role.permissions, list):
                    role.permissions = {"permissions": role.permissions}
                elif isinstance(role.permissions, str):
                    try:
                        perm_obj = json.loads(role.permissions)
                        if isinstance(perm_obj, list):
                            role.permissions = {"permissions": perm_obj}
                        else:
                            role.permissions = perm_obj
                    except:
                        logger.error(f"无法解析字符串权限: {role.permissions}")
                        role.permissions = {"permissions": []}
            
            logger.info(f"更新后的权限: {role.permissions}")
        
        # 提交更改
        db.commit()
        logger.info("所有角色权限已更新")
        
        # 列出所有用户及其角色
        users = db.query(User).all()
        for user in users:
            logger.info(f"用户: {user.username}, 角色: {user.role.name if user.role else '无角色'}")
        
        return True
    
    except Exception as e:
        logger.error(f"修复角色权限失败: {str(e)}")
        return False

if __name__ == "__main__":
    if fix_all_roles_permissions():
        logger.info("角色权限修复成功")
    else:
        logger.error("角色权限修复失败") 