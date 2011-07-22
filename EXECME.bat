@echo off

python -c "print 'hello'" > _pythonCheck_.tmp 

for %%f in (_pythonCheck_.tmp) do if %%~zf==0 goto Zero

del _pythonCheck_.tmp 

python tools\execme.py
if errorlevel 1 exit /b
call .\tools\setup-readme.bat -q
echo.
echo Invoking Caty server ...
echo Please Access http://localhost:8000/readme/
pause
echo.
python .\stdcaty.py server

goto End

:Zero
del _pythonCheck_.tmp 

echo.
echo python command not found.
echo Please install the Python version 2.5 or 2.6
echo.

:End
