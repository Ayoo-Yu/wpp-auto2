@echo off
setlocal enabledelayedexpansion

rem 设置命令提示符使用 UTF-8 编码，防止中文乱码
chcp 65001

echo 正在切换到项目目录...
cd /d D:\my-vue-project\wind-power-forecast\backend\auto_scripts\scripts\short
if %errorlevel% neq 0 (
    echo 错误: 无法切换到 D:\my-vue-project\wind-power-forecast\backend\auto_scripts\scripts\short
    pause
    exit /b 1
)
echo 成功切换到项目目录。

echo 启动后端服务...
rem 调用 Conda 初始化脚本并激活环境
call "D:\Anaconda3\Scripts\activate.bat" D:\my-vue-project\wind-power-forecast\backend\env
if %errorlevel% neq 0 (
    echo 错误: 无法激活 Conda 环境。
    pause
    exit /b 1
)
rem 启动后端服务（请根据实际情况修改启动命令）
start cmd /k "cd /d D:\my-vue-project\wind-power-forecast\backend\auto_scripts\scripts\short "
if %errorlevel% neq 0 (
    echo 错误: 无法启动后端服务。
    pause
    exit /b 1
)
echo 后端服务已启动。

:check_time
rem 获取当前时间（去掉前导 0）
for /F "tokens=1-2 delims=:." %%a in ("%time%") do (
    set /A hour=%%a
    set /A minute=%%b
)

rem 补齐前导零
if !hour! LSS 10 set hour=0!hour!
if !minute! LSS 10 set minute=0!minute!

set currentTime=!hour!!minute!

echo 当前时间: !hour!:!minute!

if !currentTime! GEQ 0830 (
    echo 到达指定时间，运行 auto_pre_train.py
    call "D:\Anaconda3\Scripts\activate.bat" D:\my-vue-project\wind-power-forecast\backend\env
    python auto_pre_train.py
    if %errorlevel% neq 0 (
        echo 错误: 运行 auto_pre_train.py 失败。
        pause
        exit /b 1
    )
    goto :end
) else (
    echo 尚未到达指定时间，等待 10 秒后重新检查...
    timeout /t 10 /nobreak >nul
    goto check_time
)

:end
echo 脚本已完成。
pause
