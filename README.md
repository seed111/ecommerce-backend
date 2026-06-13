# AWS E-Commerce Backend

A production-grade e-commerce backend built with a real-world Cloud and DevOps stack. This project demonstrates how Cloud and DevOps engineers design, provision, containerise, deploy and monitor a backend system on AWS using industry-standard tools and practices.

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Deployment Guide](#deployment-guide)
- [API Endpoints](#api-endpoints)
- [CI/CD Pipeline](#cicd-pipeline)
- [Observability](#observability)
- [Key Design Decisions](#key-design-decisions)
- [Author](#author)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        GitHub Actions                        │
│         push to main → build → push ECR → helm deploy       │
└────────────────────────────┬────────────────────────────────┘
                             │ docker push
                    ┌────────▼────────┐
                    │   Amazon ECR    │
                    │  Image registry │
                    └────────┬────────┘
                             │ helm upgrade
              ┌──────────────▼──────────────────┐
              │          Amazon EKS              │
              │      Kubernetes 1.32             │
              │   Private subnets across 3 AZs  │
              │                                  │
              │  ┌──────────────────────────┐   │
              │  │   FastAPI + Gunicorn      │   │
              │  │   2–6 pods · HPA         │   │
              │  │   IRSA — no AWS keys     │   │
              │  └──────┬───────────────────┘   │
              └─────────┼────────────────────────┘
                        │
          ┌─────────────┼──────────────┬──────────────────┐
          │             │              │                    │
   ┌──────▼──────┐  ┌───▼──────┐  ┌───▼──────┐  ┌────────▼───────┐
   │  DynamoDB   │  │    S3    │  │ Secrets  │  │  CloudWatch    │
   │  products   │  │ product  │  │ Manager  │  │  Logs · Alarms │
   │  orders ────┤  │ images   │  │ jwt key  │  │  Container     │
   │  users      │  │ presigned│  │ stripe   │  │  Insights      │
   └──────┬──────┘  │ URLs     │  └──────────┘  └────────────────┘
          │         └──────────┘
          │ DynamoDB Stream (INSERT only)
   ┌──────▼──────────────┐
   │     AWS Lambda      │
   │   order_processor   │
   │  · decrement stock  │
   │  · confirm order    │
   └─────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Container Orchestration | Amazon EKS 1.32 | Runs the FastAPI application |
| Application | FastAPI + Gunicorn + Uvicorn | REST API with async support |
| Containerisation | Docker (multi-stage build) | Lightweight production image |
| Kubernetes Packaging | Helm 3 | Manages K8s manifests and deployments |
| Event Processing | AWS Lambda (Python 3.12) | Async order processing via DynamoDB Streams |
| Database | Amazon DynamoDB | Serverless NoSQL for products, orders, users |
| Object Storage | Amazon S3 | Product image uploads with presigned URLs |
| Container Registry | Amazon ECR | Stores Docker images with lifecycle policies |
| Secrets | AWS Secrets Manager | Stores JWT and Stripe secrets securely |
| Observability | CloudWatch | Container Insights, logs, alarms, dashboards |
| Infrastructure as Code | Terraform (modular) | Provisions all AWS resources |
| CI/CD | GitHub Actions | Build, push, deploy pipeline on every push |
| AWS Authentication | IRSA | Pods assume IAM roles without hardcoded keys |
| Networking | VPC, private subnets, NAT Gateway | Secure isolated network across 3 AZs |

---

## Project Structure

```
ecommerce-backend/
├── .github/
│   └── workflows/
│       ├── ci.yml              # PR: lint + terraform validate
│       └── deploy.yml          # main: build → push ECR → helm deploy
│
├── terraform/
│   ├── environments/
│   │   └── dev/
│   │       ├── main.tf         # Wires all modules together
│   │       ├── backend.tf      # S3 remote state + DynamoDB locking
│   │       ├── variables.tf    # Environment-level variables
│   │       └── outputs.tf      # Cluster endpoint, ECR URL, table names
│   └── modules/
│       ├── networking/         # VPC, subnets, NAT Gateway, route tables
│       ├── eks/                # EKS cluster, node group, IRSA
│       ├── ecr/                # Container registry + lifecycle policy
│       ├── dynamodb/           # Products, orders, users tables + Streams
│       ├── s3/                 # Product images bucket
│       ├── lambda/             # Order processor + event source mapping
│       ├── secrets/            # Secrets Manager entries
│       └── cloudwatch/         # Log groups, alarms, Container Insights
│
├── app/
│   ├── Dockerfile              # Multi-stage build, non-root user
│   ├── main.py                 # FastAPI app, JSON logging, health probes
│   ├── requirements.txt
│   ├── routers/
│   │   ├── products.py         # CRUD + S3 image upload
│   │   ├── orders.py           # Place orders, query by user
│   │   └── users.py            # Register users, prevent duplicates
│   ├── services/
│   │   ├── dynamo.py           # DynamoDB client wrapper
│   │   └── s3.py               # S3 upload + presigned URL generation
│   └── tests/
│       └── test_routers.py     # pytest + moto (no real AWS needed)
│
├── lambda/
│   └── order_processor/
│       └── handler.py          # DynamoDB Stream handler
│
└── helm/
    └── ecommerce/
        ├── Chart.yaml
        ├── values.yaml         # Image, resources, HPA, probes, env vars
        └── templates/
            ├── deployment.yaml # Topology spread, lifecycle hooks
            ├── service.yaml    # ClusterIP + HPA + ConfigMap + ServiceAccount
            └── _helpers.tpl    # Helm helper functions
```

---

## Prerequisites

- AWS CLI configured with sufficient IAM permissions
- Terraform >= 1.6
- kubectl
- Helm >= 3.14
- Docker
- A GitHub account with Actions enabled

---

## Deployment Guide

### Step 1 — Bootstrap Terraform remote state

Run once before the first `terraform apply`:

```bash
# Create S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket ecommerce-terraform-state-dev-seed111 \
  --region eu-west-1 \
  --create-bucket-configuration LocationConstraint=eu-west-1

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name ecommerce-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-1
```

### Step 2 — Provision infrastructure

```bash
cd terraform/environments/dev
terraform init
terraform plan
terraform apply
```

> Takes approximately 15 minutes. EKS provisioning is the longest step.

### Step 3 — Configure kubectl

```bash
aws eks update-kubeconfig \
  --region eu-west-1 \
  --name dev-ecommerce-eks

# Verify nodes are ready
kubectl get nodes
```

### Step 4 — Add GitHub Actions secrets

Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions** and add:

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |

### Step 5 — Push to trigger CI/CD

```bash
git push origin main
```

GitHub Actions will build the Docker image, push to ECR, and deploy to EKS via Helm automatically.

### Step 6 — Verify deployment

```bash
kubectl get pods -n ecommerce
kubectl get svc -n ecommerce
kubectl get hpa -n ecommerce
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/healthz` | Liveness probe |
| `GET` | `/readyz` | Readiness probe — checks DynamoDB connectivity |
| `GET` | `/products` | List all products |
| `POST` | `/products` | Create a product |
| `GET` | `/products/{id}` | Get a product by ID |
| `GET` | `/products/category/{category}` | List products by category |
| `POST` | `/products/{id}/image` | Upload a product image to S3 |
| `GET` | `/products/{id}/image-url` | Get a presigned URL for a product image |
| `POST` | `/users` | Register a new user |
| `GET` | `/users/{id}` | Get a user by ID |
| `POST` | `/orders` | Place a new order |
| `GET` | `/orders/{id}` | Get an order by ID |
| `GET` | `/orders/user/{user_id}` | Get all orders for a user |
| `PATCH` | `/orders/{id}/status` | Update order status |

### Example — Place an order

**Request:**
```bash
curl -X POST https://<your-endpoint>/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "abc123",
    "items": [
      { "product_id": "prod-001", "quantity": 2 }
    ]
  }'
```

**Response:**
```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "abc123",
  "items": [
    {
      "product_id": "prod-001",
      "name": "Test Sneaker",
      "quantity": 2,
      "unit_price": 99.99,
      "line_total": 199.98
    }
  ],
  "total_amount": 199.98,
  "status": "PENDING",
  "created_at": "2026-06-07T10:00:00Z"
}
```

After the order is written to DynamoDB, the Stream triggers Lambda which confirms the order asynchronously.

---

## CI/CD Pipeline

```
Push to main
     │
     ▼
┌─────────────────────┐
│     Build job        │
│  1. ECR login        │
│  2. docker build     │
│  3. docker push ECR  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│     Deploy job       │
│  1. kubeconfig       │
│  2. helm upgrade     │
│     --install        │
└─────────────────────┘
```

Every push to `main` triggers a full build and deploy. The Docker image is tagged with the short Git SHA for full traceability across ECR and Kubernetes.

---

## Observability

| Component | What it monitors |
|---|---|
| CloudWatch Container Insights | CPU, memory, network for all EKS pods |
| Fluent Bit | Ships pod logs to CloudWatch Logs automatically |
| Structured JSON logging | All app and Lambda logs are JSON-formatted for querying |
| Lambda error alarm | Fires when Lambda errors exceed 5 in 60 seconds |
| Lambda duration alarm | Fires when p95 duration exceeds 25 seconds |
| Log retention | All log groups set to 7-day retention in dev |

---

## Key Design Decisions

### IRSA — No hardcoded AWS credentials

EKS pods assume an IAM role via OIDC federation. No AWS keys are stored in the application, environment variables or Kubernetes secrets. The IAM role is annotated on the Kubernetes ServiceAccount and scoped to only the DynamoDB tables, S3 bucket and Secrets Manager entries it needs.

### DynamoDB Streams + Lambda

Order processing is fully asynchronous. The API writes the order to DynamoDB and responds immediately with `PENDING` status. A DynamoDB Stream fires on INSERT and triggers the Lambda function, which atomically decrements stock using a conditional update — preventing overselling — and updates the order status to `CONFIRMED`. This decouples the API from processing logic and keeps response times fast.

### Multi-stage Dockerfile

The builder stage installs all dependencies. The runtime stage copies only the installed packages into a clean image. No build tools reach production. The final image runs as a non-root user for security.

### Terraform modules + remote state

Each concern — networking, EKS, Lambda, storage, observability — is an isolated reusable module. State is stored in S3 with DynamoDB locking, preventing concurrent applies from corrupting state. The `dev` and `prod` environments are separate folders calling the same modules with different variable values.

### Helm over raw manifests

Helm provides templating, environment-specific values files, and rollback on failure. The chart includes HPA, topology spread constraints across availability zones, liveness and readiness probes, resource requests and limits, and graceful shutdown hooks via `preStop`.

### Horizontal Pod Autoscaler

The FastAPI application scales between 2 and 6 pods based on CPU utilisation. Topology spread constraints ensure pods are distributed across all 3 availability zones so a single AZ failure does not take down the service.

---

## Author

**Abraham Fayemi** — Cloud & DevOps Engineer
Bologna, Italy

- GitHub: [github.com/seed111](https://github.com/seed111)
- LinkedIn: [linkedin.com/in/abraham-fayemi-0032382a0](https://linkedin.com/in/abraham-fayemi-0032382a0)
- Email: abrahamsheye1@gmail.com
