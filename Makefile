LOCATION ?= swedencentral
RG_NAME ?= rg-tfstate-graphrag
CONTAINER_NAME ?= tfstate
SUB_SHORT = $(shell az account show --query id -o tsv 2>/dev/null | tr -d '-' | cut -c1-8)
SA_NAME ?= sttfstate$(SUB_SHORT)
APP_RG_NAME ?= rg-agentic-graphrag-dev
SP_NAME ?= sp-github-graphrag-infra

-include infrastructure/terraform/.env
export

.PHONY: bootstrap plan apply ingest destroy clean-state destroy-all version lint test quality

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

quality: lint test

lint:
	cd backend && python -m ruff check .
	cd frontend && npm run lint

test:
	cd backend && python -m pytest -q

version:
	@test -n "$(VERSION)" || (echo "Usage: make version VERSION=1.0.0" && exit 1)
	@sed -i 's/"version": ".*"/"version": "$(VERSION)"/' frontend/package.json
	@sed -i 's/(Version [0-9][^)]*)/(Version $(VERSION))/' README.md
	@sed -i 's/version = {[^}]*}/version = {$(VERSION)}/' README.md
	@sed -i 's|badge/version-[^-]*-blue|badge/version-$(VERSION)-blue|' README.md
	@echo "Version $(VERSION) applied to frontend/package.json and README.md"

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
