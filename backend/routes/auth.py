from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy.exc import IntegrityError
from database_config import get_db
from services.auth_service import (
    authenticate_user, create_user, update_user, get_user_by_id, get_all_users,
    create_role, get_role_by_id, get_all_roles, create_access_token,
    log_login_attempt, update_last_login, decode_token, check_permission, get_user_by_username,
    verify_password as verify_password_bcrypt
)
from utils.password_utils import verify_password
from models import User, Role
from functools import wraps
from datetime import timedelta

auth_bp = Blueprint('auth', __name__)

# 中间件：验证JWT令牌
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # 从请求头中获取令牌
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        if not token:
            return jsonify({"message": "缺少认证令牌"}), 401
        
        # 解码令牌
        try:
            payload = decode_token(token)
            db = next(get_db())
            current_user = get_user_by_id(db, payload['sub'])
        except Exception as e:
            return jsonify({"message": "无效或过期的令牌"}), 401
        
        # 将用户信息存储在g对象中，以便在路由处理函数中使用
        g.user = current_user
        return f(*args, **kwargs)
    
    return decorated

# 中间件：检查权限
def permission_required(required_permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 检查请求参数中是否有username
            username = request.args.get('username')
            if not username:
                # 检查JSON数据中是否有username
                json_data = request.get_json(silent=True)
                if json_data and 'username' in json_data:
                    username = json_data.get('username')
                else:
                    print(f"权限检查失败：缺少用户名参数，要求权限: {required_permission}")
                    return jsonify({"message": "未提供用户名，无法验证权限"}), 403
            
            # 从数据库获取用户信息
            try:
                db = next(get_db())
                user = db.query(User).filter(User.username == username).first()
                
                if not user:
                    print(f"权限检查失败：用户 {username} 不存在，要求权限: {required_permission}")
                    return jsonify({"message": "用户不存在"}), 404
                
                # 检查用户角色权限
                if not user.role or not user.role.permissions:
                    print(f"权限检查失败：用户 {username} 没有角色或权限为空，要求权限: {required_permission}")
                    return jsonify({"message": "用户没有任何权限"}), 403
                
                # 检查权限格式并处理
                permissions = user.role.permissions
                print(f"用户 {username} 的权限: {permissions}, 类型: {type(permissions)}")
                
                # 处理权限可能是字典的情况
                if isinstance(permissions, dict) and 'permissions' in permissions:
                    permissions = permissions['permissions']
                
                if required_permission not in permissions:
                    print(f"权限检查失败：用户 {username} 没有权限 {required_permission}，拥有权限: {permissions}")
                    return jsonify({"message": f"权限不足，需要 {required_permission} 权限"}), 403
                
                print(f"权限检查成功：用户 {username} 具有所需的 {required_permission} 权限")
                return f(*args, **kwargs)
            except Exception as e:
                print(f"权限检查过程中发生异常: {e}")
                return jsonify({"message": "验证权限时出错"}), 500
                
        return decorated_function
    return decorator

# 登录路由
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"message": "缺少用户名或密码"}), 400
    
    try:
        # 获取数据库会话
        db = next(get_db())
        
        # 从数据库中查询用户
        user = db.query(User).filter(User.username == data['username']).first()
        
        # 如果用户不存在，返回错误
        if not user:
            return jsonify({"message": "用户名或密码错误"}), 401
        
        # 检查用户是否已被禁用
        if not user.is_active:
            return jsonify({"message": "账户已被禁用，请联系管理员"}), 403
        
        # 先尝试使用新的统一密码验证方法
        password_valid = verify_password(data['password'], user.password_hash)
        
        # 如果新的验证方法失败，尝试使用旧的bcrypt方法
        if not password_valid:
            print(f"统一密码验证失败，尝试使用bcrypt方法 - 用户: {user.username}")
            password_valid = verify_password_bcrypt(data['password'], user.password_hash)
        
        if not password_valid:
            # 记录更详细的日志，帮助调试
            print(f"两种密码验证方法均失败 - 用户: {user.username}, 哈希值: {user.password_hash[:20]}...")
            return jsonify({"message": "用户名或密码错误"}), 401
        
        # 更新最后登录时间
        update_last_login(db, user.id)
        
        # 获取权限数据
        permissions = user.role.permissions
        if isinstance(permissions, dict) and 'permissions' in permissions:
            permissions = permissions['permissions']
        
        # 返回登录成功响应
        return jsonify({
            "message": "登录成功",
            "user": {
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role.name if user.role else "未知角色",
                "permissions": permissions
            }
        })
    except Exception as e:
        print(f"登录异常: {e}")
        return jsonify({"message": "服务器内部错误"}), 500

# 获取当前用户信息
@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    # 从查询参数获取用户名
    username = request.args.get('username')
    if not username:
        return jsonify({"message": "缺少用户名参数"}), 400
    
    try:
        # 从数据库获取用户信息
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            return jsonify({"message": "用户不存在"}), 404
        
        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": {
                "id": user.role.id,
                "name": user.role.name,
                "permissions": user.role.permissions
            },
            "last_login": user.last_login,
            "is_active": user.is_active,
            "first_login": user.first_login
        })
    except Exception as e:
        print(f"获取用户信息异常: {e}")
        return jsonify({"message": "服务器内部错误"}), 500

# 修改密码
@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    data = request.json
    if not data or not data.get('username') or not data.get('current_password') or not data.get('new_password'):
        return jsonify({"message": "缺少必要参数"}), 400
    
    try:
        db = next(get_db())
        user = authenticate_user(db, data['username'], data['current_password'])
        
        if not user:
            return jsonify({"message": "当前密码错误"}), 401
        
        # 确保使用服务层函数而不是本地函数
        from services.auth_service import update_user as update_user_service
        update_user_service(db, user.id, password=data['new_password'])
        
        return jsonify({"message": "密码修改成功"})
    except Exception as e:
        print(f"修改密码异常: {e}")
        return jsonify({"message": "服务器内部错误"}), 500

# 获取所有用户（仅管理员）
@auth_bp.route('/users', methods=['GET'])
@permission_required("manage_users")
def get_users():
    db = next(get_db())
    users = db.query(User).all()
    
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": {
                "id": user.role.id,
                "name": user.role.name,
                "permissions": user.role.permissions
            },
            "is_active": user.is_active,
            "last_login": user.last_login,
            "first_login": user.first_login
        })
    
    return jsonify(result)

# 通过ID获取用户
@auth_bp.route('/users/<int:user_id>', methods=['GET'])
@permission_required("manage_users")
def get_user(user_id):
    db = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return jsonify({"message": "用户不存在"}), 404
    
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": {
            "id": user.role.id,
            "name": user.role.name,
            "permissions": user.role.permissions
        },
        "is_active": user.is_active,
        "last_login": user.last_login,
        "first_login": user.first_login
    })

# 辅助函数：检查是否是超级管理员
def is_super_admin(username):
    # 通过用户名判断是否是超级管理员
    return username == 'admin'

# 辅助函数：检查是否是系统管理员角色
def is_admin_role(role):
    return role and (role.name == '系统管理员' or role.name == 'admin')

# 更新用户信息
@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@permission_required("manage_users")
def update_user_info(user_id):
    data = request.json
    if not data:
        return jsonify({"message": "没有提供数据"}), 400
    
    db = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return jsonify({"message": "用户不存在"}), 404
    
    # 获取当前请求的用户名
    current_username = request.args.get('username')
    
    # 检查是否试图更改系统管理员角色或状态
    if is_admin_role(user.role):
        # 不允许修改其他系统管理员的信息，除非是超级管理员
        if current_username != user.username and not is_super_admin(current_username):
            return jsonify({"message": "只有超级管理员才能修改其他系统管理员的信息"}), 403
        
        # 不允许系统管理员更改自己的角色或禁用自己
        if current_username == user.username and (
            ('role_id' in data and data['role_id'] != user.role_id) or 
            ('is_active' in data and data['is_active'] == False)
        ):
            return jsonify({"message": "系统管理员不能更改自己的角色或禁用自己的账户"}), 403
    
    # 更新用户信息
    try:
        from services.auth_service import update_user as update_user_service
        updated_user = update_user_service(db, user_id, **data)
        
        return jsonify({
            "message": "用户更新成功",
            "user": {
                "id": updated_user.id,
                "username": updated_user.username,
                "email": updated_user.email,
                "full_name": updated_user.full_name,
                "role_id": updated_user.role_id,
                "is_active": updated_user.is_active
            }
        })
    except IntegrityError:
        db.rollback()
        return jsonify({"message": "邮箱已被使用"}), 400

# 删除用户
@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@permission_required("manage_users")
def delete_user(user_id):
    db = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return jsonify({"message": "用户不存在"}), 404
    
    # 获取当前请求的用户名
    current_username = request.args.get('current_username')
    
    # 检查是否试图删除系统管理员
    if is_admin_role(user.role) and not is_super_admin(current_username):
        return jsonify({"message": "只有超级管理员才能删除系统管理员账户"}), 403
    
    # 防止删除自己
    try:
        if current_username and user.username == current_username:
            return jsonify({"message": "不能删除当前登录的用户"}), 400
        
        db.delete(user)
        db.commit()
        
        return jsonify({"message": "用户删除成功"})
    except Exception as e:
        db.rollback()
        print(f"删除用户异常: {e}")
        return jsonify({"message": "删除用户失败"}), 500

# 重置用户密码
@auth_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@permission_required("manage_users")
def reset_user_password(user_id):
    data = request.json
    if not data or 'new_password' not in data:
        return jsonify({"message": "缺少新密码"}), 400
    
    db = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return jsonify({"message": "用户不存在"}), 404
    
    # 获取当前请求的用户名
    current_username = request.args.get('username')
    
    # 检查是否试图重置系统管理员的密码
    if is_admin_role(user.role) and current_username != user.username and not is_super_admin(current_username):
        return jsonify({"message": "只有超级管理员才能重置其他系统管理员的密码"}), 403
    
    try:
        # 确保使用服务层函数更新密码
        from services.auth_service import update_user as update_user_service
        update_user_service(db, user_id, password=data['new_password'])
        
        return jsonify({"message": "密码重置成功"})
    except Exception as e:
        db.rollback()
        print(f"重置密码异常: {e}")
        return jsonify({"message": "重置密码失败"}), 500

# 创建新用户（仅管理员）
@auth_bp.route('/users', methods=['POST'])
@permission_required("manage_users")
def create_new_user():
    data = request.json
    if not data:
        return jsonify({"message": "缺少用户数据"}), 400
    
    required_fields = ['username', 'password', 'full_name', 'email', 'role_id']
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"缺少必填字段: {field}"}), 400
    
    db = next(get_db())
    
    # 检查角色是否存在
    role = get_role_by_id(db, data['role_id'])
    if not role:
        return jsonify({"message": "指定的角色不存在"}), 400
    
    try:
        user = create_user(
            db,
            data['username'],
            data['password'],
            data['email'],
            data['full_name'],
            data['role_id']
        )
        
        return jsonify({
            "message": "用户创建成功",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role_id": user.role_id
            }
        }), 201
    
    except IntegrityError:
        db.rollback()
        return jsonify({"message": "用户名或邮箱已存在"}), 400

# 创建角色（仅管理员）
@auth_bp.route('/roles', methods=['POST'])
@permission_required("manage_roles")
def create_role():
    data = request.json
    if not data:
        return jsonify({"message": "缺少角色数据"}), 400
    
    required_fields = ['name', 'description', 'permissions']
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"缺少必填字段: {field}"}), 400
    
    db = next(get_db())
    
    try:
        role = create_role(
            db,
            data['name'],
            data['description'],
            data['permissions']
        )
        
        return jsonify({
            "message": "角色创建成功",
            "role": {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "permissions": role.permissions
            }
        }), 201
    
    except IntegrityError:
        db.rollback()
        return jsonify({"message": "角色名已存在"}), 400

# 获取所有角色
@auth_bp.route('/roles', methods=['GET'])
def get_roles():
    db = next(get_db())
    roles = get_all_roles(db)
    
    result = []
    for role in roles:
        result.append({
            "id": role.id,
            "name": role.name,
            "permissions": role.permissions,
            "description": role.description
        })
    
    return jsonify(result)

# 获取角色详情
@auth_bp.route('/roles/<int:role_id>', methods=['GET'])
@permission_required("manage_roles")
def get_role(role_id):
    db = next(get_db())
    role = get_role_by_id(db, role_id)
    
    if not role:
        return jsonify({"message": "角色不存在"}), 404
    
    return jsonify({
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "permissions": role.permissions,
        "created_at": role.created_at,
        "updated_at": role.updated_at
    })

# 更新角色
@auth_bp.route('/roles/<int:role_id>', methods=['PUT'])
@permission_required("manage_roles")
def update_role_info(role_id):
    data = request.json
    if not data:
        return jsonify({"message": "没有提供数据"}), 400
    
    db = next(get_db())
    role = db.query(Role).filter(Role.id == role_id).first()
    
    if not role:
        return jsonify({"message": "角色不存在"}), 404
    
    # 更新角色信息
    try:
        updated_role = update_role(db, role_id, **data)
        
        return jsonify({
            "message": "角色更新成功",
            "role": {
                "id": updated_role.id,
                "name": updated_role.name,
                "description": updated_role.description,
                "permissions": updated_role.permissions
            }
        })
    except IntegrityError:
        db.rollback()
        return jsonify({"message": "角色名已存在"}), 400

# 删除角色
@auth_bp.route('/roles/<int:role_id>', methods=['DELETE'])
@permission_required("manage_roles")
def delete_role(role_id):
    db = next(get_db())
    role = db.query(Role).filter(Role.id == role_id).first()
    
    if not role:
        return jsonify({"message": "角色不存在"}), 404
    
    try:
        db.delete(role)
        db.commit()
        
        return jsonify({"message": "角色删除成功"})
    except Exception as e:
        db.rollback()
        print(f"删除角色异常: {e}")
        return jsonify({"message": "删除角色失败"}), 500

# 添加诊断端点
@auth_bp.route('/debug/permissions', methods=['GET'])
def debug_permissions():
    username = request.args.get('username')
    if not username:
        return jsonify({"message": "缺少用户名参数"}), 400
    
    try:
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            return jsonify({"message": "用户不存在"}), 404
        
        # 返回详细的权限结构
        permissions_info = {
            "username": user.username,
            "role_name": user.role.name if user.role else None,
            "raw_permissions": user.role.permissions if user.role else None,
            "permissions_type": str(type(user.role.permissions)) if user.role and user.role.permissions else None,
            "is_dict": isinstance(user.role.permissions, dict) if user.role and user.role.permissions else False,
            "has_permissions_key": "permissions" in user.role.permissions if user.role and user.role.permissions and isinstance(user.role.permissions, dict) else False
        }
        
        return jsonify(permissions_info)
    except Exception as e:
        print(f"诊断权限失败: {e}")
        return jsonify({"message": "服务器内部错误", "error": str(e)}), 500 