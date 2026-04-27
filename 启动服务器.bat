@echo off
chcp 65001 >nul
echo ================================================
echo   MiniMind CS336 学习平台启动器
echo ================================================
echo.

REM 尝试使用Python启动服务器
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo 正在使用Python启动服务器...
    echo.
    echo 服务地址: http://localhost:8080/code_runner.html
    echo 按 Ctrl+C 停止服务器
    echo.
    start http://localhost:8080/code_runner.html
    python -m http.server 8080
    goto :end
)

REM 尝试使用Node.js启动服务器
where node >nul 2>&1
if %errorlevel% equ 0 (
    echo 正在使用Node.js启动服务器...
    echo.
    echo 服务地址: http://localhost:8080/code_runner.html
    echo 按 Ctrl+C 停止服务器
    echo.
    start http://localhost:8080/code_runner.html
    node -e "require('http').createServer((q,s)=>{const f=require('fs');const p=q.url.split('?')[0];const file=p==='/'?'code_runner.html':p.slice(1);f.readFile(file,(e,d)=>{if(e){s.writeHead(404);s.end('Not Found')}else{const t=file.endsWith('.html')?'text/html':file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/plain';s.writeHead(200,{'Content-Type':t,'Access-Control-Allow-Origin':'*'});s.end(d)}})}).listen(8080,()=>console.log('Server running at http://localhost:8080/'))"
    goto :end
)

REM 尝试使用PHP启动服务器
where php >nul 2>&1
if %errorlevel% equ 0 (
    echo 正在使用PHP启动服务器...
    echo.
    echo 服务地址: http://localhost:8080/code_runner.html
    echo 按 Ctrl+C 停止服务器
    echo.
    start http://localhost:8080/code_runner.html
    php -S localhost:8080
    goto :end
)

echo.
echo 错误: 未找到可用的服务器软件
echo.
echo 请安装以下任一软件:
echo   - Python 3.x (推荐)
echo   - Node.js
echo   - PHP
echo.
echo 或者直接在VS Code中使用Live Server插件
echo.
pause

:end
