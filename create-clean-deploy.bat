@echo off
echo Creating clean deployment folder...

:: Create clean folder
mkdir vcp-dashboard-clean 2>nul
cd vcp-dashboard-clean

:: Copy only necessary files
echo Copying frontend...
mkdir frontend
xcopy ..\frontend\src frontend\src /E /I /Q
xcopy ..\frontend\public frontend\public /E /I /Q
copy ..\frontend\package.json frontend\
copy ..\frontend\vite.config.ts frontend\
copy ..\frontend\tailwind.config.js frontend\
copy ..\frontend\tsconfig.json frontend\
copy ..\frontend\index.html frontend\

echo Copying backend...
mkdir backend
copy ..\backend\*.py backend\
copy ..\backend\requirements.txt backend\

echo Copying config files...
copy ..\.gitignore .
copy ..\railway.toml .
copy ..\DEPLOY_TO_RAILWAY.md .

echo Done! Clean version ready in vcp-dashboard-clean
echo Size should be ~50MB instead of 1.5GB
pause
