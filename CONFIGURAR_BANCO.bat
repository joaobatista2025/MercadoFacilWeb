@echo off
title Configurar banco MercadoFacil
cd /d "%~dp0"
set MERCADOFACIL_DB_HOST=localhost
set MERCADOFACIL_DB_PORT=3306
set MERCADOFACIL_DB_USER=root
set MERCADOFACIL_DB_PASSWORD=123456
set MERCADOFACIL_DB_NAME=mercadofacil
py scripts\configurar_banco.py
pause
