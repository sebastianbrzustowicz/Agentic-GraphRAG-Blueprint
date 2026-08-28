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

echo ""
echo "=== ENTER THE FOLLOWING VALUES INTO GITHUB SECRETS ==="
echo "ARM_CLIENT_ID       : $(echo "$SP_OUTPUT" | awk '{print $1}')"
echo "ARM_CLIENT_SECRET   : $(echo "$SP_OUTPUT" | awk '{print $2}')"
echo "ARM_TENANT_ID       : $(az account show --query tenantId -o tsv)"
echo "ARM_SUBSCRIPTION_ID : $(az account show --query id -o tsv)"
echo "TF_STATE_RG         : $RG_NAME"
echo "TF_STATE_SA         : $SA_NAME"