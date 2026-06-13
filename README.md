# AWS E-Commerce Backend

A production-grade e-commerce backend built with a real-world Cloud and DevOps stack. This project demonstrates how Cloud and DevOps engineers design, provision, containerise, deploy and monitor a backend system on AWS using industry-standard tools and practices.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        GitHub Actions                        │
│         push to main → build → push ECR → helm deploy        │
└────────────────────────┬────────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │     Amazon ECR       │
              │  Docker image store  │
              └──────────┬──────────┘
                         │ helm upgrade --install
              ┌──────────▼──────────────────────────┐
              │           Amazon EKS                  │
              │       Kubernetes 1.32                 │
              │   2 nodes · private subnets · HA      │
              │                                       │
              │   ┌───────────────────────────────┐  │
              │   │    FastAPI + Gunicorn           │  │
              │   │    2–6 pods · HPA              │  │
              │   │    IRSA — no hardcoded keys    │  │
              │   └──────────┬────────────────────┘  │
              └─────────────┼─────────────────────────┘
                            │
           ┌────────────────┼──────────────────┐
           │                │                   │
  ┌────────▼──────┐ ┌───────▼──────┐ ┌────────▼──────────┐
  │   DynamoDB    │ │     S3        │ │  Secrets Manager   │
  │  - products   │ │ product imgs  │ │  jwt_secret        │
  │  - orders     │ │ presigned URLs│ │  stripe_api_key    │
  │  - users      │ └───────────────┘ └────────────────────┘
  └────────┬──────┘
           │ DynamoDB Stream (INSERT only)
  ┌────────▼──────────────┐
  │      AWS Lambda        │
  │   order_processor      │
  │  · decrement stock     │
  │  · confirm order       │
  └────────┬──────────────┘
           │
  ┌────────▼──────────────┐
  │      CloudWatch        │
  │  · Container Insights  │
  │  · Fluent Bit logs     │
  │  · Lambda alarms       │
  └───────────────────────┘
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
| Observability | CloudWatch | Container Insights, logs, alarms |
| Infrastructure as Code | Terraform (modular) | Provisions all AWS resources |
| CI/CD | GitHub Actions | Build, push, deploy pipeline on every push |
| AWS Authentication | IRSA | Pods assume IAM roles — no hardcoded keys |
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
            ├── service.yaml    # ClusterIP service + HPA + ConfigMap
            └── _helpers.tpl    # Helm helper functions
```

---

## Prerequisites

- AWS CLI configured with sufficient IAM permissions
- Terraform >= 1.6
- kubectl
- Helm >= 3.14
- Docker

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

Takes approximately 15 minutes. EKS provisioning is the longest step.

### Step 3 — Configure kubectl

```bash
aws eks update-kubeconfig \
  --region eu-west-1 \
  --name dev-ecommerce-eks

kubectl get nodes
```

### Step 4 — Add GitHub Actions secrets

Go to your GitHub repo → Settings → Secrets and variables → Actions and add:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | Your IAM user secret key |

### Step 5 — Push to trigger the pipeline

```bash
git push origin main
```

GitHub Actions will build the Docker image, push to ECR and deploy to EKS via Helm automatically.

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
| `GET` | `/products/category/{cat}` | List products by category |
| `POST` | `/products/{id}/image` | Upload a product image to S3 |
| `GET` | `/products/{id}/image-url` | Get a presigned URL for the product image |
| `POST` | `/users` | Register a new user |
| `GET` | `/users/{id}` | Get a user by ID |
| `POST` | `/orders` | Place a new order |
| `GET` | `/orders/{id}` | Get an order by ID |
| `GET` | `/orders/user/{user_id}` | Get all orders for a user |
| `PATCH` | `/orders/{id}/status` | Update order status |

### Example — Place an order

```bash
curl -X POST https://<your-eks-endpoint>/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "abc123",
    "items": [
      { "product_id": "prod-001", "quantity": 2 }
    ]
  }'
```

Response:

```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "abc123",
  "items": [...],
  "total_amount": 199.98,
  "status": "PENDING",
  "created_at": "2026-06-07T10:00:00Z"
}
```

The API responds immediately. The DynamoDB Stream then triggers Lambda asynchronously to process the order.

---

## CI/CD Pipeline

```
Push to main
      │
      ▼
┌─────────────────┐
│   Build job      │
│  · ECR login     │
│  · docker build  │
│  · docker push   │
└────────┬────────┘
         │ on success
         ▼
┌─────────────────┐
│   Deploy job     │
│  · kubeconfig   │
│  · helm upgrade  │
└─────────────────┘
```

Every push to `main` triggers a full build and deploy. The Docker image is tagged with the short Git SHA for full traceability.

---

## Key Design Decisions

### IRSA — No hardcoded AWS credentials
EKS pods assume an IAM role via OIDC federation. No AWS keys are stored in the application, Kubernetes secrets or environment variables. The role is annotated on the Kubernetes ServiceAccount and scoped to only the DynamoDB tables, S3 bucket and Secrets Manager entries the app needs.

### DynamoDB Streams + Lambda
Order processing is fully asynchronous. The API writes the order and responds immediately. A DynamoDB Stream triggers Lambda which decrements stock using a conditional update — preventing overselling — and confirms the order. This decouples the API from processing logic and keeps response times fast.

### Multi-stage Dockerfile
The builder stage installs dependencies. The runtime stage copies only the installed packages. The final image has no build tools, reducing size and attack surface. The container runs as a non-root user.

### Terraform modules + remote state
Each concern (networking, EKS, Lambda, storage) is an isolated reusable module. State is stored in S3 with DynamoDB locking, preventing concurrent applies from corrupting state.

### Helm over raw manifests
Helm provides templating, environment-specific values and rollback capability. The chart includes HPA, topology spread constraints across AZs, liveness and readiness probes and graceful shutdown hooks.

### Horizontal Pod Autoscaler
The API scales between 2 and 6 pods based on CPU utilisation. Pods are spread across availability zones using topology spread constraints so a single AZ failure does not take down the service.

---

## Observability

| Tool | Purpose |
|---|---|
| CloudWatch Container Insights | CPU, memory and network metrics for all EKS pods |
| Fluent Bit | Ships pod logs to CloudWatch Logs automatically |
| Structured JSON logging | All app and Lambda logs are JSON-formatted for easy querying |
| CloudWatch Alarms | Alerts on Lambda error rate and p95 duration |
| Log retention | 7-day retention in dev to control costs |

---

## Author

**Abraham Fayemi** — Cloud & DevOps Engineer
Bologna, Italy
[linkedin.com/in/abraham-fayemi-0032382a0](https://linkedin.com/in/abraham-fayemi-0032382a0) · [github.com/seed111](https://github.com/seed111)
