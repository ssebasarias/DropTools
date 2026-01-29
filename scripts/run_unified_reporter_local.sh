#!/bin/bash
# Script para ejecutar el flujo unificado en modo visible (local)
# Permite ver todos los pasos que realiza el bot

# Colores
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Verificar argumentos
if [ -z "$1" ]; then
    echo "Uso: $0 <user_id> [browser] [download_dir]"
    echo "  browser: chrome, edge, brave, firefox (default: edge)"
    exit 1
fi

USER_ID=$1
BROWSER=${2:-edge}
DOWNLOAD_DIR=$3

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  EJECUTANDO FLUJO UNIFICADO (LOCAL)${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}Usuario ID: $USER_ID${NC}"
echo -e "${YELLOW}Navegador: $BROWSER${NC}"
echo -e "${GREEN}Modo: VISIBLE (podrás ver el navegador)${NC}"
echo ""

# Cambiar al directorio del backend
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/../backend"
cd "$BACKEND_DIR"

# Ejecutar el comando
CMD="python manage.py unified_reporter --user-id $USER_ID --browser $BROWSER"

if [ -n "$DOWNLOAD_DIR" ]; then
    CMD="$CMD --download-dir \"$DOWNLOAD_DIR\""
fi

echo -e "${GRAY}Ejecutando: $CMD${NC}"
echo ""

eval $CMD

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  PROCESO FINALIZADO${NC}"
echo -e "${CYAN}========================================${NC}"
