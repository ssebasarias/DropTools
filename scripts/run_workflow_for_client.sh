#!/bin/bash
# Script para ejecutar el workflow_orchestrator con un usuario cliente por email
# Uso: ./scripts/run_workflow_for_client.sh <email_del_cliente> [--headless]

set -e

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar que se proporcionó el email
if [ -z "$1" ]; then
    echo -e "${RED}Error: Debes proporcionar el email del usuario cliente${NC}"
    echo ""
    echo "Uso: $0 <email_del_cliente> [--headless]"
    echo ""
    echo "Ejemplos:"
    echo "  $0 tier.bronze@local.test"
    echo "  $0 cliente@ejemplo.com --headless"
    echo ""
    exit 1
fi

CLIENT_EMAIL="$1"
HEADLESS_FLAG="${2:-}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Ejecutando Workflow Orchestrator${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Usuario cliente:${NC} ${CLIENT_EMAIL}"
echo -e "${GREEN}Modo headless:${NC} ${HEADLESS_FLAG:-No (visible)}"
echo ""

# Cambiar al directorio backend
cd "$(dirname "$0")/../backend" || exit 1

# Activar entorno virtual si existe
if [ -f "../activate_env.bat" ]; then
    echo -e "${YELLOW}Nota: En Windows, ejecuta desde PowerShell:${NC}"
    echo "  cd backend"
    echo "  ..\\activate_env.bat"
    echo "  python manage.py workflow_orchestrator --user-email \"${CLIENT_EMAIL}\" ${HEADLESS_FLAG}"
    echo ""
fi

# Ejecutar el orquestador
echo -e "${GREEN}Ejecutando workflow_orchestrator...${NC}"
python manage.py workflow_orchestrator \
    --user-email "${CLIENT_EMAIL}" \
    ${HEADLESS_FLAG}

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Workflow completado${NC}"
echo -e "${GREEN}========================================${NC}"
