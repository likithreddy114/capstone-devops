# Vercel-Like Deployment Tool

A reusable website deployment platform that automates the deployment of web applications to **AWS ECS Fargate using Docker and Amazon ECR**, with additional static website deployment and release management through Amazon S3.

## 1. Project Overview

The Vercel-Like Deployment Tool is a Python-based command-line application designed to simplify website deployment.

Users can deploy different web applications without manually repeating the Docker build, image push, and ECS service deployment steps.

The tool supports:

- Deploying websites to AWS ECS Fargate.
- Building Docker images and pushing them to Amazon ECR.
- Creating and managing application-specific ECS services.
- Checking individual application deployment status.
- Removing an individual application deployment without deleting shared infrastructure.
- Deploying static website releases to Amazon S3.
- Managing S3 releases and rollbacks.

## 2. Architecture

The deployment workflow uses the following components:

1. **React/Vite:** Frontend website application.
2. **Python CLI:** Accepts deployment commands and manages the deployment process.
3. **Docker:** Builds the website into a container image.
4. **Amazon ECR:** Stores application-specific Docker images.
5. **Amazon ECS:** Manages container deployments.
6. **AWS Fargate:** Runs containers without requiring users to manage EC2 instances.
7. **Amazon S3:** Stores static website files and versioned releases.
8. **Terraform:** Manages S3 infrastructure and references existing shared AWS resources.

### Deployment Flow

```text
Developer
    |
    v
Python Deployment CLI
    |
    v
Validate Website
    |
    v
Docker Build
    |
    v
Amazon ECR
    |
    v
Amazon ECS
    |
    v
AWS Fargate
    |
    v
Deployed Website
```

### Deployment Workflow

1. Developer provides a website project path.
2. Python CLI validates the project.
3. Docker builds the application image.
4. CLI authenticates with Amazon ECR.
5. Docker image is pushed to the application-specific ECR repository.
6. CLI registers an ECS task definition.
7. ECS creates or updates the application service.
8. AWS Fargate runs the container.
9. CLI provides the deployed website endpoint.

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
| Git and GitHub | Version control |
| GitHub Actions | Workflow automation configuration |

## 4. Project Structure

```text
capstone-devops/
|
|-- sample-react-app/
|   |-- src/
|   |-- public/
|   |-- package.json
|   |-- Dockerfile
|   `-- vite.config.js
|
|-- cli/
|   |-- deploy_tool/
|   |   |-- main.py
|   |   |-- config.py
|   |   |-- aws_deploy.py
|   |   `-- ecs_deploy.py
|   `-- pyproject.toml
|
|-- infrastructure/
|   |-- main.tf
|   `-- variables.tf
|
|-- .github/
|   `-- workflows/
|       `-- deploy.yml
|
|-- .gitignore
`-- README.md
```

## 5. AWS Infrastructure

The project uses shared AWS infrastructure:

- Amazon VPC
- Public subnets across two Availability Zones
- Internet Gateway and routing
- Security group
- IAM execution role
- Amazon ECS cluster
- Amazon S3 bucket

Terraform references the existing shared VPC, subnets, security group, ECS cluster, and IAM execution role. It manages the project's S3 bucket and its configuration.

The Python CLI manages application-specific deployment resources.

### Infrastructure Responsibilities

| Component | Responsibility |
|---|---|
| Terraform | Manages S3 resources and references shared infrastructure |
| Python CLI | Manages application-specific deployment |
| Amazon ECR | Stores application Docker images |
| Amazon ECS | Manages application services |
| AWS Fargate | Runs application containers |
| Amazon S3 | Stores website files and releases |

**Important:** Deploying or destroying an individual website must not remove shared infrastructure or other applications.

## 6. Prerequisites

Install the following software before using the deployment tool:

- Python 3.10 or later
- Docker Desktop
- AWS CLI
- Node.js and npm
- Terraform
- Git

Configure AWS credentials with an IAM identity that has the required ECR, ECS, S3, and IAM permissions.

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

The CLI uses Python and Boto3 to communicate with AWS services.

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

The CLI uses configuration for:

- AWS region
- S3 bucket
- ECS cluster
- VPC
- Subnets
- Security group
- ECS execution role
- Public IP assignment

The configuration is stored locally in the user's deployment-tool configuration directory.

## 9. Deploy a Website to ECS Fargate

Use the following command:

```cmd
deploy-tool deploy --project-path "sample-react-app" --name "my-website" --repository "my-website" --cluster "deploy-tool-cluster" --service "my-website-service" --region "ap-south-1"
```

### Deployment Process

1. Validate the website project.
2. Build the Docker image.
3. Authenticate with Amazon ECR.
4. Create or use the application's ECR repository.
5. Push the Docker image to ECR.
6. Register the ECS task definition.
7. Create or update the ECS service.
8. Wait for the application deployment.
9. Retrieve the website's public endpoint.

## 10. Check Deployment Status

Check an individual website:

```cmd
deploy-tool ecs-status --name "my-website" --cluster "deploy-tool-cluster" --service "my-website-service" --region "ap-south-1"
```

The command checks the ECS service and reports:

- ECS service status
- Desired task count
- Running task count
- Pending task count
- Deployment information

## 11. Destroy an Individual Website

To remove one application deployment:

```cmd
deploy-tool destroy --name "my-website" --cluster "deploy-tool-cluster" --service "my-website-service" --repository "my-website" --region "ap-south-1"
```

The destroy operation is designed to remove only the selected application's owned ECS service and ECR repository/images after ownership checks.

### Resources Preserved

- VPC and subnets
- Internet Gateway
- Security group
- IAM roles
- Shared ECS cluster
- Shared S3 resources

**Important:**

- Review the pre-flight summary before confirming a destroy operation.
- The tool checks resource ownership before deleting application resources.
- AWS task-definition revisions are deregistered rather than permanently deleted.
- Shared infrastructure and other application deployments must remain unaffected.

## 12. S3 Deployment and Release Management

The CLI also supports static website deployment and release management.

Available commands:

```cmd
deploy-tool deploy-s3 --help
```

```cmd
deploy-tool status --help
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

These commands support the original Capstone website's S3 deployment, release storage, and rollback workflow.

## 13. Deployment Verification

The React/Vite application in `sample-react-app` was successfully deployed to AWS ECS Fargate.

### Verified Deployment

| Detail | Result |
|---|---|
| Application | capstone-frontend-v2 |
| ECS Cluster | deploy-tool-cluster |
| ECS Service | capstone-frontend-v2-service |
| Desired Tasks | 1 |
| Running Tasks | 1 |
| Pending Tasks | 0 |
| Deployment Status | ACTIVE |
| Website Access | Verified successfully |

### Status Verification Command

```cmd
deploy-tool ecs-status --name capstone-frontend-v2 --cluster deploy-tool-cluster --service capstone-frontend-v2-service --region ap-south-1
```

The deployment was tested using the CLI's `deploy` and `ecs-status` commands. The deployed website was also opened successfully in a browser.

## 14. Security Considerations

- AWS credentials should not be committed to GitHub.
- Use IAM permissions appropriate for deployment operations.
- Keep `.env` files and private keys out of version control.
- Do not commit Terraform state files.
- Exclude local backup files and generated files from Git.
- Use application-specific ownership checks before deleting resources.
- Preserve shared infrastructure when removing an individual deployment.

## 15. Project Scope

This project focuses on automated container-based website deployment using:

- Docker
- Amazon ECR
- Amazon ECS
- AWS Fargate
- Amazon S3
- Terraform
- Python CLI

CloudFront and cloud monitoring are not included in this project scope.

## 16. Future Improvements

- Align and validate the GitHub Actions workflow with the current AWS account and per-application ECS deployment design.
- Improve deployment error handling.
- Expand deployment validation and testing.
- Improve CLI documentation and user experience.

**Note:** The current GitHub Actions workflow requires updating and validation before it can be considered aligned with the latest per-application ECS deployment implementation.

## 17. Author

**Project:** Vercel-Like Deployment Tool

**GitHub Repository:**
https://github.com/likithreddy114/capstone-devops