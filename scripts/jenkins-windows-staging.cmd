@echo off
setlocal
if "%STAGING_NAME%"=="" set STAGING_NAME=aceest-staging-jenkins
if "%STAGING_HOST_PORT%"=="" set STAGING_HOST_PORT=5099

docker rm -f %STAGING_NAME% 2>nul
docker run -d --name %STAGING_NAME% -p %STAGING_HOST_PORT%:5000 aceest-fitness-api:staging
if errorlevel 1 exit /b 1

powershell -NoProfile -Command ^
  "$u='http://127.0.0.1:%STAGING_HOST_PORT%/health'; $ok=$false; ^
   for($i=0;$i -lt 20;$i++){ ^
     try { $r=Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 3; ^
           if($r.StatusCode -eq 200 -and $r.Content -match 'ok'){ $ok=$true; Write-Host $r.Content; break } } catch {} ^
     Start-Sleep -Seconds 2 }; ^
   if(-not $ok){ Write-Error 'Staging /health failed or timed out'; exit 1 }"

set PSERR=%ERRORLEVEL%
docker rm -f %STAGING_NAME% 2>nul
exit /b %PSERR%
