# Keliu AI Customer Retention Platform

Keliu is a full-stack AI-powered customer retention and marketing management platform for store operators and small businesses.

It brings customer profiles, AI scoring, marketing campaigns, analytics, subscription billing, Alipay sandbox payment, and a platform admin console into one practical SaaS-style application.

## Overview

This project uses a modern frontend-backend architecture:

- Frontend: Vue 3, TypeScript, Vite, Element Plus, Pinia, and Vue Router.
- Backend: FastAPI, SQLAlchemy, Alembic, and Pydantic.
- Data services: MySQL, Redis, and Elasticsearch.
- Background jobs: Celery and Celery Beat.
- Payment: Alipay sandbox integration for subscription upgrades.
- DevOps support: Docker Compose, GitHub Actions, and Dify workflow files.

## Features

| Module | Description |
| --- | --- |
| Authentication | User registration, login, role-based access, merchant/admin routing |
| Store onboarding | Merchant store creation after signup |
| Dashboard | Business overview, customer activity, and retention indicators |
| Customer management | Customer profiles, tags, consumption records, visit history, and detail pages |
| AI scoring | Retention, churn-risk, and customer-value analysis support |
| Campaigns | Marketing campaign creation and management |
| Analytics | Charts, trend analysis, and business insights |
| Subscription billing | Free, Basic, and Professional plan logic |
| Alipay payment | Sandbox checkout, return verification, and plan upgrade synchronization |
| Admin console | Store management, user management, payment order tracking |
| Real-time updates | WebSocket-based notification support |

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Vue 3, TypeScript, Vite |
| State and routing | Pinia, Vue Router |
| UI and charts | Element Plus, ECharts, vue-echarts |
| Backend | FastAPI, Pydantic |
| ORM and migration | SQLAlchemy 2, Alembic |
| Database | MySQL 8 |
| Cache and queue | Redis, Celery, Celery Beat |
| Search and analytics support | Elasticsearch |
| Payment | Alipay sandbox |
| Automation | Dify workflows, GitHub Actions |
| Deployment | Docker, Docker Compose |

## Project Structure

```text
.
├── backend/              # FastAPI backend service
│   ├── app/
│   │   ├── routers/      # API routes
│   │   ├── services/     # Business services
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── tasks/        # Celery tasks
│   └── alembic/          # Database migrations
├── frontend/             # Vue 3 frontend application
│   └── src/
│       ├── views/        # Page views
│       ├── api/          # API clients
│       ├── stores/       # Pinia stores
│       └── router/       # Frontend routes
├── dify-workflows/       # Dify workflow examples
├── scripts/              # Helper and smoke-test scripts
├── docker-compose.yml    # Local Docker orchestration
└── docker-compose.prod.yml
```

## Application Pages

### Merchant App

- `/dashboard`: Store dashboard
- `/customers`: Customer list
- `/customers/:id`: Customer detail
- `/campaigns`: Campaign list
- `/campaigns/new`: Campaign editor
- `/analytics`: Analytics dashboard
- `/billing`: Subscription and payment
- `/settings`: Account and store settings

### Admin Console

- `/admin`: Admin overview
- `/admin/stores`: Store management
- `/admin/stores/:id`: Store detail
- `/admin/payment-orders`: Payment order management

## Payment Upgrade Flow

The project includes an Alipay sandbox payment flow for subscription upgrades:

```text
Select a plan
  -> Create a payment order
  -> Redirect to Alipay sandbox checkout
  -> Buyer completes payment
  -> Return to the frontend payment result page
  -> Backend verifies and synchronizes the order status
  -> Merchant subscription is upgraded automatically
```

Related environment variables are configured in `backend/.env`:

```env
ALIPAY_APP_ID=
ALIPAY_APP_PRIVATE_KEY=
ALIPAY_ALIPAY_PUBLIC_KEY=
ALIPAY_GATEWAY=https://openapi-sandbox.dl.alipaydev.com/gateway.do
ALIPAY_RETURN_URL=http://localhost:5173/billing
```

Do not commit real `.env` files, private keys, payment secrets, or production credentials.

## Local Development

### 1. Start the Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Default backend URL:

```text
http://127.0.0.1:8009
```

### 2. Start the Frontend

```powershell
cd frontend
npm install
npm run dev
```

Default frontend URL:

```text
http://localhost:5173
```

### 3. Start Services with Docker

```powershell
docker compose up -d
```

Docker Compose starts MySQL, Redis, Elasticsearch, the backend service, Celery Worker, and Celery Beat.

## Common Commands

### Frontend

```powershell
cd frontend
npm run dev
npm run build
npm run preview
```

### Backend

```powershell
cd backend
python run.py
alembic upgrade head
```

### Git Workflow

```powershell
git status
git add .
git commit -m "Update project"
git push
```

## Deployment Notes

For production deployment, prepare these parts separately:

- Frontend: run `npm run build` and deploy `frontend/dist`.
- Backend: deploy the FastAPI service with production environment variables.
- Data services: prepare MySQL, Redis, and Elasticsearch.
- Payment: update Alipay callback URLs to match the production domains.
- Security: use HTTPS and manage secrets through secure environment variables.

The project can be deployed with GitHub-based workflows, Docker, cloud servers, Vercel, Cloudflare, or another platform depending on the backend and database strategy.

## Learning Value

This repository is useful for studying:

- Vue 3 admin-style frontend development
- FastAPI backend API design
- SQLAlchemy ORM and Alembic migrations
- SaaS subscription and payment order modeling
- Alipay sandbox payment integration
- Merchant/admin permission separation
- Docker Compose multi-service local development

## Repository

[https://github.com/hejie0373-cloud/my-project](https://github.com/hejie0373-cloud/my-project)

