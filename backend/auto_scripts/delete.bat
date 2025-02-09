@echo off
rem 设置命令提示符使用 UTF-8 编码，防止中文乱码
chcp 65001

rem 删除文件夹中的所有文件（不删除文件夹本身）
setlocal enabledelayedexpansion

rem 指定要删除文件的文件夹路径（可以多次指定多个文件夹路径）
set FOLDER1="D:\my-vue-project\wind-power-forecast\backend\auto_scripts\train_predictions"
set FOLDER2="D:\my-vue-project\wind-power-forecast\backend\auto_scripts\results"
set FOLDER3="D:\my-vue-project\wind-power-forecast\backend\auto_scripts\models"


rem 删除文件夹1中的所有文件
if exist %FOLDER1% (
    echo 正在删除 %FOLDER1% 中的文件...
    del /q /f %FOLDER1%\*.*
    rem 删除文件夹1中的空子文件夹
    for /d %%D in (%FOLDER1%\*) do rd /s /q "%%D"
)

rem 删除文件夹2中的所有文件
if exist %FOLDER2% (
    echo 正在删除 %FOLDER2% 中的文件...
    del /q /f %FOLDER2%\*.*
    rem 删除文件夹2中的空子文件夹
    for /d %%D in (%FOLDER2%\*) do rd /s /q "%%D"
)

rem 删除文件夹3中的所有文件
if exist %FOLDER3% (
    echo 正在删除 %FOLDER3% 中的文件...
    del /q /f %FOLDER3%\*.*
    rem 删除文件夹3中的空子文件夹
    for /d %%D in (%FOLDER3%\*) do rd /s /q "%%D"
)

echo 所有文件删除完毕！
pause
