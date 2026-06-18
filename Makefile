ifneq (,$(wildcard ./.env))
    include .env
endif

.DEFAULT_GOAL := help

help:
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Delete?
#setup-project-prod: install-prod-packages-apt setup-certbot-with-autorenewal nginx-conf ## Before executing make sure to setup your .env and point your domain to this server (f.e. DNS A Record)! --- Setup the project for production. This includes setting up certbot with nginx plugin and auto-renewal for real SSL certificates, generating nginx config from template, and installing npm packages. The app needs to be started with "npm run docker:build" and "npm run docker:start". Afterwards the app is reachable at the DOMAIN and BASE_URL specified in .env.
setup-project-prod: nginx-conf

# Might be deleted because we dont install cerbot on the host anymore, nut rather in a docker container
#install-prod-packages-apt: ## Install necessary apt packages for production setup. This includes openssl and curl.
#	@sudo apt update
#	sudo apt install certbot python3-certbot-nginx

# Same as above.
#setup-certbot-with-autorenewal: ## Make sure to add a correct A record for your domain before you run this. This sets up certbot with nginx plugin and auto-renewal (for production, to get real certificates).
#	sudo certbot certonly --nginx -d ${DOMAIN} --agree-tos --no-eff-email -m ${CERTBOT_UPDATES_RECEIVER}
#	sudo certbot renew --dry-run

nginx-conf:
	@mkdir -p ./nginx/active
	@export DOMAIN=$$(grep '^DOMAIN=' .env | head -n1 | sed 's/#.*//' | cut -d '=' -f2- | tr -d '\"' | xargs) && \
	export TARGET=$$(grep '^TARGET=' .env | head -n1 | sed 's/#.*//' | cut -d '=' -f2- | tr -d '\"' | xargs) && \
	envsubst '$$DOMAIN $$TARGET' < ./nginx/default.conf.template > ./nginx/active/default.conf
	@cp ./nginx/http-connection-upgrade-map.conf ./nginx/active/ 2>/dev/null || true

# Might be deleted; not relevant
#react-router-typegen: ## Generate types for react-router routes.
#	npm run typegen

#mailer-start: ## MailPit for local development email testing. Access the dashboard at http://localhost:8025 after starting. SMTP Enpoint is localhost:1025
#	docker compose -f mailpit/compose.yml up -d

#mailer-stop: ## Stop MailPit
#	docker compose -f mailpit/compose.yml down

create-docker-network: 
	@docker network inspect dif-network >/dev/null 2>&1 || docker network create dif-network