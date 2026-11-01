# Vercel-Like Deployment Tool

A reusable Python-based deployment platform that automates website deployment to **AWS ECS Fargate using Docker and Amazon ECR**, with additional static website deployment and release management through Amazon S3.

## 1. Project Overview

The Vercel-Like Deployment Tool simplifies the process of deploying web applications to AWS.

Instead of manually building Docker images, pushing them to ECR, registering ECS task definitions, and creating ECS services, users can perform these operations through a single CLI command.

The tool supports:

- Website validation before deployment.
- Docker image building and containerization.
- Pushing application images to Amazon ECR.
- Creating application-specific ECS task definitions and services.
- Deploying containers on AWS Fargate.
- Checking individual application deployment status.
- Destroying an individual application deployment.
- Preserving shared AWS infrastructure and other applications.
- Static website deployment and release management through Amazon S3.

## 2. Architecture

### Main Components

1. **React/Vite:** Frontend website applications.
2. **Python CLI:** Accepts commands and manages deployment operations.
3. **Docker:** Builds website applications into container images.
4. **Amazon ECR:** Stores application-specific Docker images.
5. **Amazon ECS:** Manages container deployments.
6. **AWS Fargate:** Runs containers without requiring EC2 instance management.
7. **Amazon S3:** Stores static website files and releases.
8. **Terraform:** Manages S3 infrastructure and references existing shared AWS resources.

### Container Deployment Flow

```text
Developer
    |
    v
Python Deployment CLI
    |
    v
Validate Website Project
    |
    v
Docker Build
    |
    v
Amazon ECR
    |
    v
Register ECS Task Definition
    |
    v
Amazon ECS Service
    |
    v
AWS Fargate
    |
    v
Deployed Website
```

### Deployment Workflow

1. Developer provides the website project path and application name.
2. CLI validates the website project and Dockerfile.
3. Docker builds the application image.
4. CLI authenticates with Amazon ECR.
5. Docker pushes the image to the application-specific ECR repository.
6. CLI registers an ECS task definition.
7. ECS creates the application-specific service.
8. AWS Fargate runs the container.
9. CLI waits for deployment completion and displays the website URL.

## 3. Technologies Used

| Technology | Purpose |
|---|---|
| Python | CLI development |
| React and Vite | Frontend application |
| Docker | Containerization |
| Amazon ECR | Container image storage |
| Amazon ECS | Container orchestration |
| AWS Fargate | Container execution |
| Amazon S3 | Static website and release storage |
| Terraform | Infrastructure management |
| AWS CLI | AWS command-line operations |
| Boto3 | AWS integration with Python |
| Git and GitHub | Version control |
| GitHub Actions | Retained workflow, currently disabled |

## 4. Project Structure

```text
capstone-devops/
|
|-- sample-react-app/
|   |-- src/
|   |-- public/
|   |-- package.json
|   |-- package-lock.json
|   |-- Dockerfile
|   `-- vite.config.js
|
|-- cli/
|   |-- deploy_tool/
|   |   |-- main.py
|   |   |-- config.py
|   |   |-- aws_deploy.py
|   |   |-- ecs_deploy.py
|   |   `-- __init__.py
|   `-- pyproject.toml
|
|-- infrastructure/
|   |-- main.tf
|   `-- variables.tf
|
|-- tests/
|   `-- test_deployment_records.py
|
|-- .github/
|   `-- workflows/
|       `-- deploy.yml.disabled
|
|-- screenshots/
|-- .gitignore
`-- README.md
```

## 5. AWS Infrastructure

The deployment tool uses shared AWS infrastructure:

- Amazon VPC
- Public subnets across two Availability Zones
- Internet Gateway and routing
- Security group
- IAM execution role
- Amazon ECS cluster
- Amazon S3 bucket

Terraform references existing shared infrastructure and manages the project's S3 resources.

The Python CLI manages application-specific container deployment resources.

### Infrastructure Responsibilities

| Component | Responsibility |
|---|---|
| Terraform | Manages S3 resources and references shared infrastructure |
| Python CLI | Manages application-specific deployment |
| Amazon ECR | Stores Docker images |
| Amazon ECS | Manages application services |
| AWS Fargate | Runs application containers |
| Amazon S3 | Stores website files and releases |

**Important:** Deploying or destroying one application must not remove shared infrastructure or other applications.

## 6. Prerequisites

Install the following software:

- Python 3.10 or later
- Docker Desktop
- AWS CLI
- Node.js and npm
- Terraform
- Git

Configure AWS credentials using an IAM identity with the permissions required for the deployment operations.

Docker Desktop must be running when building and deploying container images.

## 7. Installation

### Step 1: Clone the Repository

```cmd
git clone https://github.com/likithreddy114/capstone-devops.git
```

### Step 2: Navigate to the Project

```cmd
cd capstone-devops
```

### Step 3: Install the Python CLI

```cmd
python -m pip install -e cli
```

### Step 4: Verify Installation

```cmd
deploy-tool --help
```

Check the installed version:

```cmd
deploy-tool --version
```

## 8. Configure the Deployment Tool

View the current configuration:

```cmd
deploy-tool config list
```

The configuration includes:

- AWS region
- S3 bucket
- ECS cluster
- VPC
- Subnets
- Security group
- ECS execution role
- Public IP assignment

AWS credentials should be configured separately and must not be committed to GitHub.

## 9. Deploy a Website to ECS Fargate

The deployment command accepts the website project path and application name.

### Deployment Command

```cmd
deploy-tool deploy --project-path "C:\path\to\website" --name my-website
```

### Example: Deploy the Sample React Application

```cmd
deploy-tool deploy --project-path "C:\Users\likit\capstone-devops\sample-react-app" --name sample-react-app
```

### Deployment Process

1. Validate the website project.
2. Build the Docker image.
3. Authenticate with Amazon ECR.
4. Create or use the application's ECR repository.
5. Push the Docker image to ECR.
6. Register the ECS task definition.
7. Create the application-specific ECS service.
8. Wait for the ECS service deployment.
9. Display the deployed website endpoint.

Each application gets its own ECR repository, task definition family, ECS service, and local deployment record.

## 10. Check Deployment Status

Check an individual application's ECS status:

```cmd
deploy-tool ecs-status --name sample-react-app
```

The command reports:

- ECS service status
- Desired task count
- Running task count
- Pending task count
- Task definition
- Deployment information
- Website URL, when available

## 11. Destroy an Individual Website

The tool supports application-specific cleanup using only the application name.

### Destroy Command

```cmd
deploy-tool destroy --name sample-react-app
```

### Destroy Process

1. Identify the selected application's deployment resources.
2. Perform ownership and protection checks.
3. Delete the selected ECS service.
4. Deregister its owned task definition revisions.
5. Delete its application-specific ECR repository and images.
6. Remove its local deployment record.

### Resources Preserved

- Shared VPC
- Public subnets
- Internet Gateway and routing
- Security group
- IAM roles
- Shared ECS cluster
- Shared S3 resources
- Other application deployments

**Important:**

- The destroy operation performs pre-flight ownership checks.
- Only resources belonging to the selected application should be deleted.
- AWS task-definition revisions are deregistered rather than permanently erased.
- Shared infrastructure must remain available for other applications.

## 12. Multiple Application Support

The deployment tool is designed to reuse the same deployment workflow for compatible website projects.

For example, after cloning another compatible React application, it can be deployed separately:

```cmd
deploy-tool deploy --project-path "C:\path\to\recipe-finder-react" --name recipe-finder
```

Check its status:

```cmd
deploy-tool ecs-status --name recipe-finder
```

Destroy only that application:

```cmd
deploy-tool destroy --name recipe-finder
```

The same CLI can manage multiple application deployments without replacing the original sample React application.

Each application has its own deployment resources and local deployment record.

## 13. S3 Deployment and Release Management

The CLI also retains static website deployment and release management functionality through Amazon S3.

Check the available commands:

```cmd
deploy-tool deploy-s3 --help
```

```cmd
deploy-tool release --help
```

```cmd
deploy-tool releases --help
```

```cmd
deploy-tool rollback --help
```

These commands support the original S3 deployment and release-management workflow.

## 14. Deployment Verification

The sample React application was successfully deployed to AWS ECS Fargate.

### Verified Deployment

| Detail | Result |
|---|---|
| Application | sample-react-app |
| AWS Region | ap-south-1 |
| ECS Cluster | deploy-tool-cluster |
| ECS Service | sample-react-app-service |
| ECR Repository | sample-react-app |
| Task Definition | sample-react-app-task:1 |
| Desired Tasks | 1 |
| Running Tasks | 1 |
| Pending Tasks | 0 |
| ECS Service Status | ACTIVE |
| Website Access | Successfully verified |

### Deployment Verification Command

```cmd
deploy-tool ecs-status --name sample-react-app
```

The website was successfully opened in a browser using its public endpoint.

### Destroy Verification

The application-specific destroy command was also executed successfully.

The ECS service became inactive, with zero desired and running tasks. The local deployment record was removed, while the other application's deployment record remained.

This demonstrated the deployment and cleanup workflow for an individual application.

## 15. Security Considerations

- Never commit AWS credentials to GitHub.
- Use IAM permissions appropriate for deployment operations.
- Keep `.env` files and private keys out of version control.
- Do not commit Terraform state files.
- Exclude local backup and generated files from Git.
- Perform ownership checks before deleting application resources.
- Preserve shared infrastructure when removing an individual deployment.

## 16. Project Scope

This project focuses on automated website deployment using:

- Python CLI
- Docker
- Amazon ECR
- Amazon ECS
- AWS Fargate
- Amazon S3
- Terraform

CloudFront and cloud monitoring are not included in this project scope.

The GitHub Actions deployment workflow is currently disabled; the verified container deployment workflow is executed through the Python CLI.

## 17. Future Improvements

- Test deployment with additional compatible React applications.
- Expand deployment validation and automated tests.
- Improve CLI error handling.
- Improve deployment documentation and user experience.

## 18. Author and Repository

**Project:** Vercel-Like Deployment Tool

**GitHub Repository:**

https://github.com/likithreddy114/capstone-devops
