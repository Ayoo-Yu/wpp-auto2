@echo off
setlocal

echo 金仓数据库方言测试脚本 
echo ====================================

REM 设置环境变量
set DB_HOST=localhost
set DB_PORT=54321
set DB_USER=system
set DB_PASSWORD=12345678ab
set DB_NAME=windpower
set PYTHONPATH=%CD%

echo 环境变量设置:
echo   DB_HOST=%DB_HOST%
echo   DB_PORT=%DB_PORT%
echo   DB_USER=%DB_USER%
echo   DB_PASSWORD=******
echo   DB_NAME=%DB_NAME%
echo   PYTHONPATH=%PYTHONPATH%

:menu
echo.
echo 请选择测试选项:
echo 1. 运行基本方言测试 (test_dialect.py)
echo 2. 运行Alembic兼容性测试 (test_alembic.py)
echo 3. 直接运行Alembic current命令
echo 4. 直接运行Alembic revision --autogenerate命令
echo 5. 查看帮助信息
echo 0. 退出
echo.

set /p choice=请输入选项编号:

if "%choice%"=="1" goto run_dialect_test
if "%choice%"=="2" goto run_alembic_test
if "%choice%"=="3" goto run_alembic_current
if "%choice%"=="4" goto run_alembic_revision
if "%choice%"=="5" goto show_help
if "%choice%"=="0" goto end

echo 无效选项，请重新选择...
goto menu

:run_dialect_test
echo.
echo 运行基本方言测试...
python test_dialect.py
echo.
echo 测试完成!
pause
goto menu

:run_alembic_test
echo.
echo 运行Alembic兼容性测试...
python test_alembic.py
echo.
echo 测试完成!
pause
goto menu

:run_alembic_current
echo.
echo 运行Alembic current命令...
echo.
alembic current
echo.
echo 命令执行完毕!
pause
goto menu

:run_alembic_revision
echo.
echo 运行Alembic revision --autogenerate命令...
set /p message=请输入迁移说明消息:
echo.
alembic revision --autogenerate -m "%message%"
echo.
echo 命令执行完毕!
pause
goto menu

:show_help
echo.
echo 帮助信息:
echo ---------------------------------------------------------------------------
echo 此脚本用于测试金仓数据库方言与Alembic的兼容性。
echo.
echo 测试前准备:
echo 1. 确保金仓数据库服务已启动
echo 2. 确保已配置正确的连接参数 (主机、端口、用户名、密码)
echo 3. 确保已安装Python和所需依赖包 (SQLAlchemy, Alembic等)
echo.
echo 常见问题:
echo - 如果遇到模块导入错误，请检查PYTHONPATH是否正确设置
echo - 如果遇到连接错误，请检查数据库连接参数是否正确
echo - 如果遇到类型转换错误，请检查kingbase_dialect.py是否正确加载
echo.
echo 更多详细信息请查看KINGBASE_README.md文件
echo ---------------------------------------------------------------------------
pause
goto menu

:end
echo 感谢使用金仓数据库方言测试脚本!
endlocal 