COMPOSE=docker-compose $(COMPOSE_OPTS)
DJANGO=$(COMPOSE) run --rm app poetry run python manage.py

run:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

# target: logs - Shows logs for api
logs:
	$(COMPOSE) logs -f app

# target: bash - Runs /bin/bash in App container for development
bash:
	$(COMPOSE) exec app /bin/bash

# target: makemigrations - create missing migrations from source code
makemigrations:
	$(DJANGO) makemigrations

# target: migrate - Migrate database
migrate:
	$(DJANGO) migrate