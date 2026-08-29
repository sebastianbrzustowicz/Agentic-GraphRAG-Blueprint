LOCATION ?= swedencentral
RG_NAME ?= rg-tfstate-graphrag
CONTAINER_NAME ?= tfstate
SUB_SHORT = $(shell az account show --query id -o tsv 2>/dev/null | tr -d '-' | cut -c1-8)
SA_NAME ?= sttfstate$(SUB_SHORT)
APP_RG_NAME ?= rg-agentic-graphrag-dev
SP_NAME ?= sp-github-graphrag-infra

.PHONY: bootstrap apply ingest destroy clean-state destroy-all

bootstrap:
	chmod +x ./infrastructure/bootstrap/init-tf-state.sh
	LOCATION="$(LOCATION)" RG_NAME="$(RG_NAME)" CONTAINER_NAME="$(CONTAINER_NAME)" SA_NAME="$(SA_NAME)" ./infrastructure/bootstrap/init-tf-state.sh

plan:
	cd infrastructure/terraform && terraform init \
		-backend-config="resource_group_name=$(RG_NAME)" \
		-backend-config="storage_account_name=$(SA_NAME)" \
		-backend-config="container_name=$(CONTAINER_NAME)" \
		-backend-config="key=terraform.tfstate" && terraform plan

apply:
	cd infrastructure/terraform && terraform init \
		-backend-config="resource_group_name=$(RG_NAME)" \
		-backend-config="storage_account_name=$(SA_NAME)" \
		-backend-config="container_name=$(CONTAINER_NAME)" \
		-backend-config="key=terraform.tfstate" && terraform apply -auto-approve

ingest:
	curl -s -X POST http://localhost:8000/ingest

destroy:
	cd infrastructure/terraform && terraform init \
		-backend-config="resource_group_name=$(RG_NAME)" \
		-backend-config="storage_account_name=$(SA_NAME)" \
		-backend-config="container_name=$(CONTAINER_NAME)" \
		-backend-config="key=terraform.tfstate" && terraform destroy -auto-approve

clean-state:
	az group delete --name $(APP_RG_NAME) --yes
	az storage blob delete --container-name $(CONTAINER_NAME) --name terraform.tfstate --account-name $(SA_NAME) --auth-mode login 2>/dev/null || true

destroy-all:
	az group delete --name $(APP_RG_NAME) --yes
	az group delete --name $(RG_NAME) --yes
	@SP_ID=$$(az ad sp list --display-name "$(SP_NAME)" --query "[0].appId" -o tsv 2>/dev/null); \
	if [ -n "$$SP_ID" ]; then az ad sp delete --id $$SP_ID; fi
