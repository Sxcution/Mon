@echo off
REM ============================================================================
REM Script tạo file AP.tar.md5 chuẩn cho Odin
REM Sử dụng: create_tar_md5.bat [input_file] [output_name]
REM Default: input=system.img.lz4, output=AP
REM ============================================================================

setlocal enabledelayedexpansion

REM Parse arguments
set INPUT_FILE=%1
if "%INPUT_FILE%"=="" set INPUT_FILE=system.img.lz4

set OUTPUT_NAME=%2
if "%OUTPUT_NAME%"=="" set OUTPUT_NAME=AP

set OUTPUT_TAR=%OUTPUT_NAME%.tar
set OUTPUT_TAR_MD5=%OUTPUT_NAME%.tar.md5

REM ============================================================================
REM Kiểm tra file input
REM ============================================================================
echo [*] Checking input file: %INPUT_FILE%
if not exist "%INPUT_FILE%" (
    echo [!] ERROR: File %INPUT_FILE% not found!
    pause
    exit /b 1
)
echo [+] Input file found: %INPUT_FILE%

REM ============================================================================
REM Tạo file tar với format ustar
REM ============================================================================
echo [*] Creating tar file: %OUTPUT_TAR%
tar -H ustar -c -f %OUTPUT_TAR% %INPUT_FILE%

if not exist "%OUTPUT_TAR%" (
    echo [!] ERROR: Failed to create %OUTPUT_TAR%!
    pause
    exit /b 1
)
echo [+] Tar file created: %OUTPUT_TAR%

REM ============================================================================
REM Tính MD5 hash
REM ============================================================================
echo [*] Calculating MD5 hash...
for /f "usebackq tokens=*" %%a in (`powershell -NoProfile -Command "(Get-FileHash %OUTPUT_TAR% -Algorithm MD5).Hash.ToLower()"`) do set MD5_HASH=%%a

echo [+] MD5: %MD5_HASH%

REM ============================================================================
REM Tạo file AP.tar.md5
REM ============================================================================
echo [*] Creating %OUTPUT_TAR_MD5%...
echo %MD5_HASH%  %OUTPUT_TAR%> %OUTPUT_TAR_MD5%

if not exist "%OUTPUT_TAR_MD5%" (
    echo [!] ERROR: Failed to create %OUTPUT_TAR_MD5%!
    pause
    exit /b 1
)

REM ============================================================================
REM Hoàn tất
REM ============================================================================
echo.
echo [=] SUCCESS!
echo [=] Created: %OUTPUT_TAR%
echo [=] Created: %OUTPUT_TAR_MD5%
echo [=] MD5: %MD5_HASH%
echo.

pause















