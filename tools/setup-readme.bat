@echo off

setlocal

set files=RELEASE.txt CONTRIBUTORS.txt EXCUSE.txt INSTALL.txt LICENSE.ja-utf8.txt LICENSE.txt README.txt HISTORY.txt

if "%1" == "-q" goto Quiet
:else
 for %%f in (%files%) do xcopy /F /D /Y %%f examples\readme\pub\
 goto :End

:Quiet
 for %%f in (%files%) do xcopy /F /D /Y /Q %%f examples\readme\pub\ > nul
 goto End

:End
 endlocal
