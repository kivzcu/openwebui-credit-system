# OpenWebUI Credit Admin

This package provides the admin API and interface for the OpenWebUI credit management system.

See the repository-level README for full documentation.

## Install & Run (developer)

Install and sync the project environment with `uv` and run the app using the resolved environment:

```bash
# From the repository root (or inside `credit_admin`)
uv --project credit_admin lock    # create/update lockfile
uv --project credit_admin sync    # create .venv and install dependencies
uv --project credit_admin run -- python app/main.py
```

Interactive shell:

```bash
uv --project credit_admin run -- bash
```

## Docker (build)

The Docker build in `credit_admin/Dockerfile` builds a wheel and installs it into the image. To build the Docker image:

```bash
docker build -t openwebui-credit-admin:latest credit_admin/
```

