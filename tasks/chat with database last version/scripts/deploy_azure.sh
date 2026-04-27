#!/bin/bash
# =============================================================================
# Chinook SQL Chatbot — Azure Deployment Script
# =============================================================================
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - Docker installed
#   - .env file with AZURE_OPENAI_* values and optional LangSmith settings
#
# Usage:
#   chmod +x scripts/deploy_azure.sh
#   ./scripts/deploy_azure.sh
# =============================================================================

set -euo pipefail

# --- Configuration (edit these) ---
RESOURCE_GROUP="chinook-chatbot-rg"
LOCATION="eastus"
PG_SERVER_NAME="chinook-pg-server"
PG_ADMIN_USER="chinookadmin"
PG_ADMIN_PASSWORD="${PG_ADMIN_PASSWORD:-}"  # SET THIS before running, or pass as env var
PG_DB_NAME="chinookdb"
ACR_NAME="chinookchatbotacr"
APP_SERVICE_PLAN="chinook-plan"
APP_NAME="chinook-chatbot-app"
IMAGE_NAME="chinook-chatbot"

# Load secrets from .env if available
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$PG_ADMIN_PASSWORD" ]; then
    echo "ERROR: Set PG_ADMIN_PASSWORD before running."
    echo "  export PG_ADMIN_PASSWORD='YourSecurePassword123!'"
    exit 1
fi

: "${AZURE_OPENAI_API_KEY:?ERROR: Set AZURE_OPENAI_API_KEY in .env or the environment.}"
: "${AZURE_OPENAI_ENDPOINT:?ERROR: Set AZURE_OPENAI_ENDPOINT in .env or the environment.}"
AZURE_OPENAI_API_VERSION="${AZURE_OPENAI_API_VERSION:-2024-12-01-preview}"
AZURE_OPENAI_DEPLOYMENT="${AZURE_OPENAI_DEPLOYMENT:-gpt-4o-mini}"

echo "=== Step 1: Create Resource Group ==="
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION"

echo "=== Step 2: Create Azure PostgreSQL Flexible Server ==="
az postgres flexible-server create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$PG_SERVER_NAME" \
    --location "$LOCATION" \
    --admin-user "$PG_ADMIN_USER" \
    --admin-password "$PG_ADMIN_PASSWORD" \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --storage-size 32 \
    --version 15 \
    --public-access 0.0.0.0 \
    --yes

echo "=== Step 3: Create Database ==="
az postgres flexible-server db create \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$PG_SERVER_NAME" \
    --database-name "$PG_DB_NAME"

echo "=== Step 4: Configure Firewall (allow Azure services) ==="
az postgres flexible-server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$PG_SERVER_NAME" \
    --rule-name AllowAzureServices \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0

# Allow current machine (for data loading)
MY_IP=$(curl -s https://api.ipify.org)
az postgres flexible-server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$PG_SERVER_NAME" \
    --rule-name AllowMyIP \
    --start-ip-address "$MY_IP" \
    --end-ip-address "$MY_IP"

echo "=== Step 5: Load Data into PostgreSQL ==="
PG_HOST="${PG_SERVER_NAME}.postgres.database.azure.com"
AZURE_DB_URL="postgresql://${PG_ADMIN_USER}:${PG_ADMIN_PASSWORD}@${PG_HOST}:5432/${PG_DB_NAME}?sslmode=require"

DATABASE_URL="$AZURE_DB_URL" python scripts/deploy_db.py

echo "=== Step 6: Create Azure Container Registry ==="
az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic \
    --admin-enabled true

echo "=== Step 7: Build and Push Docker Image ==="
az acr build \
    --registry "$ACR_NAME" \
    --image "${IMAGE_NAME}:latest" \
    .

echo "=== Step 8: Create App Service Plan ==="
az appservice plan create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_SERVICE_PLAN" \
    --sku B1 \
    --is-linux

echo "=== Step 9: Create Web App ==="
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

az webapp create \
    --resource-group "$RESOURCE_GROUP" \
    --plan "$APP_SERVICE_PLAN" \
    --name "$APP_NAME" \
    --container-image-name "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest" \
    --container-registry-url "https://${ACR_LOGIN_SERVER}" \
    --container-registry-user "$ACR_NAME" \
    --container-registry-password "$ACR_PASSWORD"

echo "=== Step 10: Configure Environment Variables ==="
az webapp config appsettings set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --settings \
        AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY}" \
        AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT}" \
        AZURE_OPENAI_API_VERSION="${AZURE_OPENAI_API_VERSION}" \
        AZURE_OPENAI_DEPLOYMENT="${AZURE_OPENAI_DEPLOYMENT}" \
        DATABASE_URL="${AZURE_DB_URL}" \
        LANGSMITH_TRACING="${LANGSMITH_TRACING:-true}" \
        LANGSMITH_API_KEY="${LANGSMITH_API_KEY:-}" \
        LANGSMITH_PROJECT="${LANGSMITH_PROJECT:-chinook-chatbot}" \
        WEBSITES_PORT=8501

echo "=== Step 11: Configure Startup ==="
az webapp config set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --startup-file "streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true"

APP_URL="https://${APP_NAME}.azurewebsites.net"
echo ""
echo "============================================"
echo "  Deployment complete!"
echo "  App URL: ${APP_URL}"
echo "============================================"
