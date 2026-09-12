@echo off
rem One-step Minimal Home install for Windows.
rem Usage (from the repository root): tools\install.cmd [TV_HOST]
rem Finds a POSIX shell (Git Bash or WSL) and forwards everything to tools/install.sh.
setlocal
where sh.exe >NUL 2>NUL
if %ERRORLEVEL%==0 goto :use_path_sh
if exist "%ProgramFiles%\Git\bin\sh.exe" goto :use_git_sh
if exist "%ProgramFiles(x86)%\Git\bin\sh.exe" goto :use_git_x86_sh
where wsl.exe >NUL 2>NUL
if %ERRORLEVEL%==0 goto :use_wsl
echo error: no POSIX shell found. Install Git for Windows (Git Bash) or WSL, then retry. 1>&2
exit /b 1
:use_path_sh
sh.exe tools/install.sh %*
exit /b %ERRORLEVEL%
:use_git_sh
"%ProgramFiles%\Git\bin\sh.exe" tools/install.sh %*
exit /b %ERRORLEVEL%
:use_git_x86_sh
"%ProgramFiles(x86)%\Git\bin\sh.exe" tools/install.sh %*
exit /b %ERRORLEVEL%
:use_wsl
wsl sh tools/install.sh %*
exit /b %ERRORLEVEL%
