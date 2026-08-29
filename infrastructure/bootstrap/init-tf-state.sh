#!/usr/bin/env bash
set -e

az group create \
  --name "$RG_NAME" \
  --location "$LOCATION" \
  --output none

az storage account create \
  --name "$SA_NAME" \
  --resource-group "$RG_NAME" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --allow-blob-public-access false \
  --output none

az storage container create \
  --name "$CONTAINER_NAME" \
  --account-name "$SA_NAME" \
  --auth-mode login \
  --output none

SP_OUTPUT=$(az ad sp create-for-rbac \
  --name "sp-github-graphrag-infra" \
  --role "Contributor" \
  --scopes "/subscriptions/$(az account show --query id -o tsv)" \
  --query "{clientId: appId, clientSecret: password}" \
  -o tsv)

SP_CLIENT_ID=$(echo "$SP_OUTPUT" | awk '{print $1}')

az ad app update \
  --id "$SP_CLIENT_ID" \
  --required-resource-accesses \
  '[{"resourceAppId":"00000003-0000-0000-c000-000000000000","resourceAccess":[{"id":"1bfefb4e-e0b5-418b-a88f-73c46d2cc8e9","type":"Role"}]}]'

az ad app permission admin-consent --id "$SP_CLIENT_ID"

echo ""
echo "=== ENTER THE FOLLOWING VALUES INTO GITHUB SECRETS ==="
echo "ARM_CLIENT_ID       : $SP_CLIENT_ID"
echo "ARM_CLIENT_SECRET   : $(echo "$SP_OUTPUT" | awk '{print $2}')"
echo "ARM_TENANT_ID       : $(az account show --query tenantId -o tsv)"
echo "ARM_SUBSCRIPTION_ID : $(az account show --query id -o tsv)"
echo "TF_STATE_RG         : $RG_NAME"
echo "TF_STATE_SA         : $SA_NAME"
echo ""
echo "NOTE: Application.ReadWrite.All was granted and admin-consented for the service principal, so Terraform can create the Entra ID app registration for the frontend."

TF_ENV_FILE="$(cd "$(dirname "$0")" && pwd)/../terraform/.env"
cat > "$TF_ENV_FILE" <<EOF
ARM_CLIENT_ID=$SP_CLIENT_ID
ARM_CLIENT_SECRET=$(echo "$SP_OUTPUT" | awk '{print $2}')
ARM_TENANT_ID=$(az account show --query tenantId -o tsv)
ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TF_STATE_RG=$RG_NAME
TF_STATE_SA=$SA_NAME
EOF
chmod 600 "$TF_ENV_FILE"

echo ""
echo "Local deployment variables written to $TF_ENV_FILE"
echo "Run 'make plan' / 'make apply' to deploy without GitHub."