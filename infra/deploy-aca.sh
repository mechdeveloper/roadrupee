#!/usr/bin/env bash
# Deploy RoadRupee to Azure Container Apps (centralindia).
#
#   az login                       # once
#   ANTHROPIC_API_KEY=sk-ant-... ./infra/deploy-aca.sh
#
# The key may also live in ./.env (never committed). Safe to re-run: apps are updated in place.
#
# Topology: frontend = EXTERNAL ingress (public URL); backend = INTERNAL ingress (reachable only
# from other apps in the environment). The browser only ever calls the frontend's /api/*, which the
# Next.js route handler proxies to BACKEND_URL (set below, read at runtime).
set -euo pipefail

cd "$(dirname "$0")/.."

RG="${RG:-roadrupee-rg}"
LOCATION="${LOCATION:-centralindia}"
ENV_NAME="${ENV_NAME:-roadrupee-env}"
BACKEND_APP="${BACKEND_APP:-roadrupee-backend}"
FRONTEND_APP="${FRONTEND_APP:-roadrupee-frontend}"
CLAUDE_MODEL_LIVE="${CLAUDE_MODEL_LIVE:-claude-sonnet-5-5}"
CLAUDE_MODEL_EXTRACT="${CLAUDE_MODEL_EXTRACT:-claude-opus-5-5}"
TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"

log() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

# --- API key: from the environment, else .env. Never echoed. -----------------------------------
if [[ -z "${ANTHROPIC_API_KEY:-}" && -f .env ]]; then
  ANTHROPIC_API_KEY="$(grep -E '^ANTHROPIC_API_KEY=' .env | head -1 | cut -d= -f2- | tr -d '"'"'" || true)"
fi
# Workspace ID (not a secret). Needed when the API key is not scoped to a workspace; sent as the
# anthropic-workspace-id header by backend/app/ai/client.py.
if [[ -z "${ANTHROPIC_WORKSPACE_ID:-}" && -f .env ]]; then
  ANTHROPIC_WORKSPACE_ID="$(grep -E '^ANTHROPIC_WORKSPACE_ID=' .env | head -1 | cut -d= -f2- | tr -d '"'"'" || true)"
fi
WORKSPACE_ENV=()
[[ -n "${ANTHROPIC_WORKSPACE_ID:-}" ]] && WORKSPACE_ENV=("ANTHROPIC_WORKSPACE_ID=$ANTHROPIC_WORKSPACE_ID")
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ANTHROPIC_API_KEY is not set (export it or put it in .env). Aborting." >&2
  exit 1
fi

az account show >/dev/null 2>&1 || { echo "Not logged in. Run: az login" >&2; exit 1; }
az extension add --name containerapp --upgrade --only-show-errors >/dev/null

SUB_ID="$(az account show --query id -o tsv)"
# ACR names are global, 5-50 chars, alphanumeric only. Derive a stable one from the subscription.
ACR_NAME="${ACR_NAME:-roadrupee$(echo "$SUB_ID" | tr -d '-' | cut -c1-8)}"

# --- Resource providers (a fresh subscription has none of these registered) --------------------
log "Registering resource providers"
for ns in Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry; do
  az provider register --namespace "$ns" --wait
  echo "$ns: $(az provider show --namespace "$ns" --query registrationState -o tsv)"
done

log "Resource group $RG ($LOCATION)"
az group create --name "$RG" --location "$LOCATION" --output none

log "Container registry $ACR_NAME"
if ! az acr show --name "$ACR_NAME" --resource-group "$RG" >/dev/null 2>&1; then
  # Admin user keeps the hackathon deploy simple (no role-assignment propagation wait).
  az acr create --name "$ACR_NAME" --resource-group "$RG" --location "$LOCATION" \
    --sku Basic --admin-enabled true --output none
fi
ACR_SERVER="$(az acr show --name "$ACR_NAME" --resource-group "$RG" --query loginServer -o tsv)"
ACR_USER="$(az acr credential show --name "$ACR_NAME" --query username -o tsv)"
ACR_PASS="$(az acr credential show --name "$ACR_NAME" --query 'passwords[0].value' -o tsv)"

# --- Build in ACR (linux/amd64, regardless of the laptop's architecture) -----------------------
log "Building backend image (context: repo root, bundles data/)"
az acr build --registry "$ACR_NAME" --platform linux/amd64 \
  --image "roadrupee-backend:$TAG" --file backend/Dockerfile .

log "Building frontend image"
# az acr build resolves --file relative to the current working directory (not the build context),
# so the path must include frontend/ even though the context is ./frontend. Same rule as the backend
# build above (--file backend/Dockerfile .). "--file Dockerfile" fails with "Unable to find 'Dockerfile'".
az acr build --registry "$ACR_NAME" --platform linux/amd64 \
  --image "roadrupee-frontend:$TAG" --file frontend/Dockerfile frontend

# --- Container Apps environment (also creates the Log Analytics workspace) ---------------------
log "Container Apps environment $ENV_NAME"
if ! az containerapp env show --name "$ENV_NAME" --resource-group "$RG" >/dev/null 2>&1; then
  az containerapp env create --name "$ENV_NAME" --resource-group "$RG" --location "$LOCATION" --output none
fi

# --- Backend: INTERNAL ingress, API key as an ACA secret ---------------------------------------
log "Backend app $BACKEND_APP (internal ingress)"
if az containerapp show --name "$BACKEND_APP" --resource-group "$RG" >/dev/null 2>&1; then
  az containerapp secret set --name "$BACKEND_APP" --resource-group "$RG" \
    --secrets "anthropic-api-key=$ANTHROPIC_API_KEY" --output none
  az containerapp update --name "$BACKEND_APP" --resource-group "$RG" \
    --image "$ACR_SERVER/roadrupee-backend:$TAG" \
    --set-env-vars "ANTHROPIC_API_KEY=secretref:anthropic-api-key" \
      "CLAUDE_MODEL_LIVE=$CLAUDE_MODEL_LIVE" "CLAUDE_MODEL_EXTRACT=$CLAUDE_MODEL_EXTRACT" \
      ${WORKSPACE_ENV[@]+"${WORKSPACE_ENV[@]}"} \
    --output none
else
  az containerapp create --name "$BACKEND_APP" --resource-group "$RG" --environment "$ENV_NAME" \
    --image "$ACR_SERVER/roadrupee-backend:$TAG" \
    --registry-server "$ACR_SERVER" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --ingress internal --target-port 8000 --allow-insecure true \
    --cpu 0.5 --memory 1.0Gi --min-replicas 1 --max-replicas 2 \
    --secrets "anthropic-api-key=$ANTHROPIC_API_KEY" \
    --env-vars "ANTHROPIC_API_KEY=secretref:anthropic-api-key" \
      "CLAUDE_MODEL_LIVE=$CLAUDE_MODEL_LIVE" "CLAUDE_MODEL_EXTRACT=$CLAUDE_MODEL_EXTRACT" \
      ${WORKSPACE_ENV[@]+"${WORKSPACE_ENV[@]}"} \
    --output none
fi

# Apps in the same environment reach each other at http://<app-name> (internal ingress).
BACKEND_URL="http://$BACKEND_APP"

# --- Frontend: EXTERNAL ingress ----------------------------------------------------------------
log "Frontend app $FRONTEND_APP (external ingress)"
if az containerapp show --name "$FRONTEND_APP" --resource-group "$RG" >/dev/null 2>&1; then
  az containerapp update --name "$FRONTEND_APP" --resource-group "$RG" \
    --image "$ACR_SERVER/roadrupee-frontend:$TAG" \
    --set-env-vars "BACKEND_URL=$BACKEND_URL" --output none
else
  az containerapp create --name "$FRONTEND_APP" --resource-group "$RG" --environment "$ENV_NAME" \
    --image "$ACR_SERVER/roadrupee-frontend:$TAG" \
    --registry-server "$ACR_SERVER" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --ingress external --target-port 3000 \
    --cpu 0.5 --memory 1.0Gi --min-replicas 1 --max-replicas 3 \
    --env-vars "BACKEND_URL=$BACKEND_URL" \
    --output none
fi

FQDN="$(az containerapp show --name "$FRONTEND_APP" --resource-group "$RG" \
  --query properties.configuration.ingress.fqdn -o tsv)"

log "Smoke test https://$FQDN/api/health"
for i in 1 2 3 4 5 6; do
  if curl -fsS -m 10 "https://$FQDN/api/health"; then echo; break; fi
  echo "not ready yet ($i/6), retrying in 10s..." >&2; sleep 10
done

cat <<EOF

Deployed.
  App:       https://$FQDN
  Flags CSV: https://$FQDN/api/flags.csv
  Image tag: $TAG

Logs:     az containerapp logs show -n $BACKEND_APP -g $RG --follow
Tear down: az group delete -n $RG --yes --no-wait
EOF
