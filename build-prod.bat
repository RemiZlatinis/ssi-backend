@echo off
REM Build script for production Podman image

REM Get version from pyproject.toml
for /f "tokens=2 delims== " %%a in ('findstr /r "^version = " pyproject.toml') do set VERSION=%%a
if not defined VERSION (
    for /f %%i in ('git rev-parse --short HEAD') do set VERSION=%%i
)

REM Remove quotes from version if present
set VERSION=%VERSION:"=%

REM Build the production image with version tag
echo Building ssi-backend:prod-%VERSION%
podman build -f Dockerfile.prod -t ssi-backend:prod-%VERSION% .

REM Also tag as latest
podman tag ssi-backend:prod-%VERSION% ssi-backend:prod

echo Production image built successfully!
echo Tags: ssi-backend:prod-%VERSION% and ssi-backend:prod
echo To run the containers, use: podman compose -f docker-compose.prod.yml up
