# Azure Deployment

This folder contains a Bicep deployment for Azure Container Apps plus the supporting Azure resources used by the MVP.

## What It Deploys
- Log Analytics workspace and Application Insights.
- Azure Container Apps managed environment.
- Backend and frontend Container Apps.
- Backend worker process for background jobs and durable outbox processing.
- Azure Database for PostgreSQL Flexible Server.
- Azure Cache for Redis.
- Azure AI Search service.
- Azure Storage account and private blob container.
- Azure Key Vault with application secrets.
- User-assigned managed identity and Key Vault Secrets User role assignment for the backend app.

Azure OpenAI, Azure AI Vision, and Azure Communication Services can be supplied as existing service endpoints/keys because those resources often require subscription-specific approvals, sender/domain setup, or regional choices.

## Image Build
Build and push images before deploying:

```powershell
docker build -t YOUR_REGISTRY.azurecr.io/airport-lost-found-backend:latest ./backend
docker build --build-arg VITE_API_URL=https://YOUR_BACKEND_FQDN -t YOUR_REGISTRY.azurecr.io/airport-lost-found-frontend:latest ./frontend
docker push YOUR_REGISTRY.azurecr.io/airport-lost-found-backend:latest
docker push YOUR_REGISTRY.azurecr.io/airport-lost-found-frontend:latest
```

The frontend is a static Vite build, so `VITE_API_URL` must be set at image build time. The Bicep template accepts optional registry server, username, and password parameters for private registries.

## Deploy
Copy `main.parameters.example.json`, fill real values, then run:

```powershell
./infra/deploy.ps1 -ResourceGroup airport-lost-found-rg -Location eastus -ParametersFile ./infra/main.parameters.json
```

After deployment, the backend starts with `RUN_MIGRATIONS_ON_STARTUP=true` so Alembic applies database migrations automatically. Keep `RUN_SEED_ON_STARTUP=false` outside local/dev environments.

## Pilot Gates
Before production promotion:
- Run the GitHub Actions test job.
- Deploy the image tag to staging.
- Verify `/health/ready/deep`.
- Confirm Key Vault secrets are current.
- Confirm the worker is processing jobs and no outbox entries are dead-lettered.
- Shift production traffic only after the staging smoke test passes.

## GitHub Actions
`.github/workflows/azure-container-apps.yml` provides a deployment workflow with backend tests, migration smoke tests, frontend build, Docker build checks, and deploy gates. Configure repository variables for names/endpoints such as `ACR_NAME`, `ACR_LOGIN_SERVER`, `AZURE_RESOURCE_GROUP`, `AZURE_LOCATION`, `AZURE_NAME_PREFIX`, `BACKEND_PUBLIC_URL`, and Azure service endpoints. Configure repository secrets for Azure federated login, `ACR_USERNAME`, `ACR_PASSWORD`, and sensitive service keys.
