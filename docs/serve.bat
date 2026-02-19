@echo off
echo Serving ERIS Dashboard at http://localhost:8080
echo Open http://localhost:8080 in your browser
cd /d "%~dp0"
python -m http.server 8080
