# Future Trends and Signals System (FTSS) API

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License](https://img.shields.io/github/license/undp-data/ftss-api)](https://github.com/undp-data/ftss-api/blob/main/LICENSE)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)
[![Build and deploy Python app to Azure Web App](https://github.com/UNDP-Data/ftss-api/actions/workflows/azure-webapps-python.yml/badge.svg)](https://github.com/UNDP-Data/ftss-api/actions/workflows/azure-webapps-python.yml)

This repository hosts the API that powers the [UNDP Future Trends and Signals System](https://signals.data.undp.org) (FTSS).
The API is written using [FastAPI](https://fastapi.tiangolo.com) in Python and deployed on Azure App Services.
It serves as an intermediary between the front-end application and back-end database. The codebase is an open-source
of the original project transferred from Azure DevOps.

## Table of Contents

- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Build and Test](#build-and-test)
- [Contribute](#contribute)
- [License](#license)
- [Contact](#contact)

## Introduction 

The FTSS is an internal system built for the staff of the United Nations Development Programme, designed to capture
signals of change, and identify emerging trends within and outside the organisation. This repository hosts the back-end
API that powers the platform and is accompanied by the [front-end repository](https://github.com/undp-data/fe-signals-and-trends).

The API is written and tested in Python `3.11` using [FastAPI](https://fastapi.tiangolo.com) framework. Database and 
storage routines are implemented in an asynchronous manner, making the application fast and responsive. The API is
deployed on Azure App Services to development and production environments from `dev` and `main` branches
respectively. The API interacts with a PostgreSQL database deployed as an Azure Database for PostgreSQL instance. The
instance comprises `staging` and `production` databases. An Azure Blob Storage container stores images used as
illustrations for signals and trends. The simplified architecture of the whole application is shown in the image below.

Commits to `staging` branch in the front-end repository and `dev` branch in this repository trigger CI/CD pipelines for
the staging environment. While there is a single database instance, the data in the staging environment is isolated in
the `staging` database/schema separate from `production` database/schema within the same database instance. The same
logic applies to the blob storage – images uploaded in the staging environment are managed separately from those in the
production environment.

![Preview](images/architecture.drawio.svg)

Authentication in the API happens via tokens (JWT) issued by Microsoft Entra upon user log-in in the front-end
application. Some endpoints to retrieve approved signals/trends are accessible with a static API key 
for integration with other applications. 

## Getting Started

For running the application locally, you can use either your local environment or a Docker container. Either way,
clone the repository and navigate to the project directory first:

```shell
# Clone the repository
git clone https://github.com/undp-data/ftss-api

# Navigate to the project folder
cd ftss-api
```

You must also ensure that the following environment variables are set up:

```text
# Authentication
TENANT_ID="<microsoft-entra-tenant-id>"
CLIENT_ID="<app-id>"
API_KEY="<strong-password>" # for accessing "public" endpoints

# Database and Storage
DB_CONNECTION="postgresql://<user>:<password>@<host>:5432/<staging|production>"
SAS_URL=""https://<account-name>.blob.core.windows.net/<container-name>?<sas-token>"

# Azure OpenAI, only required for `/signals/generation`
AZURE_OPENAI_ENDPOINT="https://<subdomain>.openai.azure.com/"
AZURE_OPENAI_API_KEY="<api-key>"

# Testing, only required to run tests, must be a valid token of a regular user
API_JWT="<json-token>"
```

### Local Environment

For this scenario, you will need a connection string to the staging database.

```bash
# Create and activate a virtual environment.
python3 -m venv venv
source venv/bin/activate

# Install core dependencies.
pip install -r requirements.txt

# Launch the application.
uvicorn main:app --reload
```

Once launched, the application will be running at http://127.0.0.1:8000.

### Docker Environment

For this scenario, you do not need a connection string as a fresh PostgreSQL instance will be
set up for you in the container. Ensure that Docker engine is running on you machine, then execute:

```shell
# Start the containers
docker compose up --build -d
```

Once launched, the application will be running at http://127.0.0.1:8000.

# Build and Test

The codebase provides some basic tests written in `pytest`. To run them, ensure you have specified a valid token in your
`API_JWT` environment variable. Then run:

```shell
# run all tests
 python -m pytest tests/
 
 # or alternatively
 make test
```

Note that some tests for search endpoints might fail as the tests are run against dynamically changing databases.

# Contribute

All contributions must follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
The codebase is formatted with `black` and `isort`. Use the provided [Makefile](Makefile) for these
routine operations. Make sure to run the linter against your code.

1. Clone or fork the repository
2. Create a new branch (`git checkout -b feature-branch`)
3. Make your changes
4. Ensure your code is properly formatted (`make format`)
5. Run the linter and check for any issues (`make lint`)
6. Execute the tests (`make test`)
7. Commit your changes (`git commit -m 'Add some feature'`)
8. Push to the branch (`git push origin feature-branch`)
9. Open a pull request to `dev` branch
10. Once tested in the staging environment, open a pull requests to `main` branch

## Contact

This project has been originally developed and maintained by [Data Futures Exchange (DFx)](https://data.undp.org) at UNDP.
If you are facing any issues or would like to make some suggestions, feel free to
[open an issue](https://github.com/undp-data/ftss-api/issues/new/choose).
For enquiries about DFx, visit [Contact Us](https://data.undp.org/contact-us).
