@echo off
title MercadoFacil Web
cd /d "%~dp0"
set MERCADOFACIL_DB_HOST=localhost
set MERCADOFACIL_DB_PORT=3306
set MERCADOFACIL_DB_USER=root
set MERCADOFACIL_DB_PASSWORD=123456
set MERCADOFACIL_DB_NAME=mercadofacil
set MERCADOFACIL_ADMIN_USER=mercadofacil
set MERCADOFACIL_ADMIN_PASSWORD=Mercado@2026
start "" http://localhost:5000
py app.py
pause
