@echo off
chcp 65001 >nul
title Easy Dataset

echo ========================================
echo   Easy Dataset 启动器
echo ========================================
echo.

cd /d D:\easy-dataset-main

echo [1/2] 初始化数据库...
call npx prisma db push --skip-generate

echo [2/2] 启动服务...
echo.
echo ========================================
echo   服务地址: http://localhost:1717
echo   按 Ctrl+C 可停止服务
echo ========================================
echo.

start "" http://localhost:1717

call pnpm dev
