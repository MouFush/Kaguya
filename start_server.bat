@echo off
echo ================================================
echo   MiniMind CS336 Learning Platform Launcher
echo ================================================
echo.

where python >nul 2>&1
if %errorlevel% equ 0 (
    echo Starting server with Python...
    echo.
    echo Server URL: http://localhost:8080/code_runner.html
    echo Press Ctrl+C to stop
    echo.
    start http://localhost:8080/code_runner.html
    python -m http.server 8080
    goto :end
)

where node >nul 2>&1
if %errorlevel% equ 0 (
    echo Starting server with Node.js...
    echo.
    echo Server URL: http://localhost:8080/code_runner.html
    echo Press Ctrl+C to stop
    echo.
    start http://localhost:8080/code_runner.html
    node -e "require('http').createServer((q,s)=>{const f=require('fs');const p=q.url.split('?')[0];const file=p==='/'?'code_runner.html':p.slice(1);f.readFile(file,(e,d)=>{if(e){s.writeHead(404);s.end('Not Found')}else{const t=file.endsWith('.html')?'text/html':file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/plain';s.writeHead(200,{'Content-Type':t,'Access-Control-Allow-Origin':'*'});s.end(d)}})}).listen(8080,()=>console.log('Server running at http://localhost:8080/'))"
    goto :end
)

echo.
echo ERROR: No server software found
echo.
echo Please install one of:
echo   - Python 3.x (recommended)
echo   - Node.js
echo.
echo Or use VS Code Live Server extension
echo.
pause

:end
