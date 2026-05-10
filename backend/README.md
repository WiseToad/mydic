# Backend

## DEVELOPMENT

### Prerequisites

Setup and start DB.

### Project setup

Set current directory to where this README is.

#### Python Virtual Environment (venv)

```sh
python3 -m venv .venv

source .venv/bin/activate && \
pip install -r requirements.txt
```

#### App Environment (.env)

```sh
cp .env.dev-sample .env
```

Edit all TODOs in `.env` file.

#### Alembic

```sh
source .venv/bin/activate && \
alembic revision --autogenerate -m "init" && \
alembic upgrade head
```

### Startup and Usage

Start backend (hot-reload will be activated as well):
```
./start-dev.sh
```

API available at http://localhost:8000/docs.

In order to apply DB schema changes:
```sh
source .venv/bin/activate && \
alembic upgrade head
```
