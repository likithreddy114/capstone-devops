
# DevOps Capstone Project — Automated Cloud Deployment

## 1. Project Overview

This project demonstrates automated deployment of React websites using Docker, Amazon ECR, Amazon ECS Fargate, Terraform, GitHub Actions, and a Python-based deployment CLI.

The project supports two deployment workflows:

- **CI/CD workflow:** GitHub Actions can build and deploy the application according to the configured workflow.
- **Reusable CLI workflow:** A Python command-line tool builds a Docker image, pushes it to Amazon ECR, registers a new ECS task-definition revision, and updates a selected ECS service.

The goal is to simplify website deployment and reduce repetitive manual steps.

## 2. Architecture

### Main CI/CD Architecture

Developer → GitHub → GitHub Actions → Docker Build → Amazon ECR → Amazon ECS Fargate → Live Website

Terraform provisions and manages the AWS infrastructure.

### CLI Deployment Architecture

Developer → Deploy CLI → Docker Build → Amazon ECR → ECS Task Definition → ECS Service → Live Website

The CLI deployment workflow was tested successfully using the Recipe Finder React application.

## 3. Technologies Used

- **Frontend:** React, Vite
- **Programming Language:** Python
- **Containerization:** Docker
- **Container Registry:** Amazon Elastic Container Registry (ECR)
- **Container Deployment:** Amazon ECS Fargate
- **Infrastructure as Code:** Terraform
- **CI/CD:** GitHub Actions
- **Cloud Platform:** Amazon Web Services (AWS)
- **AWS SDK:** Boto3
- **Version Control:** Git and GitHub

## 4. Project Components

### React Application

The React application provides the website that is packaged into a Docker image and deployed to ECS.

### Python Deployment CLI

The CLI automates the container deployment process. It supports:

- Reading saved deployment configuration.
- Validating the selected project directory and Dockerfile.
- Building a Docker image.
- Authenticating with Amazon ECR.
- Pushing the image to ECR.
- Registering a new ECS task-definition revision.
- Updating the selected ECS service.
- Waiting for the ECS service deployment to stabilize.

### Amazon ECR

Amazon ECR stores the Docker images used by ECS.

### Amazon ECS Fargate

Amazon ECS manages the containerized application. Fargate runs the tasks without requiring the user to manage EC2 container hosts.

### Terraform

Terraform defines the AWS infrastructure, including the VPC, public subnets, routing, security group, ECS cluster, task definition, ECS service, and task execution role.

### GitHub Actions

The repository contains a GitHub Actions workflow intended to automate the application deployment process. The exact automated steps depend on the workflow configuration in `.github/workflows/deploy.yml`.

## 5. AWS Infrastructure

The current Terraform configuration defines:

- Amazon VPC
- Two public subnets
- Internet Gateway
- Public route table and subnet associations
- Security group allowing HTTP traffic on port 80
- Amazon ECS cluster
- Amazon ECS Fargate task definition
- Amazon ECS Fargate service
- IAM task execution role
- Amazon ECR image reference

The running website is accessed directly through the public IP assigned to its ECS task.

An Application Load Balancer, CloudFront, and cloud monitoring are not included in the current project scope.

## 6. Repository Structure

```text
capstone-devops/
├── .github/
│   └── workflows/
│       └── deploy.yml
├── cli/
│   ├── pyproject.toml
│   └── deploy_tool/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── aws_deploy.py
│       └── ecs_deploy.py
├── infrastructure/
│   ├── main.tf
│   └── variables.tf
├── sample-react-app/
├── docs/
├── tests/
└── README.md
```

Some directories may contain additional files as the project evolves.

## 7. CLI Configuration

The deployment CLI stores local configuration in:

```text
~/.deploy-tool/config.json
```

On Windows, this is typically located under the current user's home directory.

The configuration includes:

- `region`
- `bucket`
- `environment`
- `ecr_repository`
- `ecs_cluster`
- `ecs_service`

### Display Configuration

```cmd
deploy-tool config list
```

### Configure the ECR Repository

```cmd
deploy-tool config set ecr_repository recipe-finder
```

### Configure the ECS Cluster

```cmd
deploy-tool config set ecs_cluster capstone-devops-cluster
```

### Configure the ECS Service

```cmd
deploy-tool config set ecs_service recipe-finder-service
```

These are local CLI settings. They do not create AWS resources.

## 8. Deploy a Website Using One Command

The CLI supports deployment to an existing ECS service.

Example using the Recipe Finder project:

```cmd
deploy-tool deploy-container --project-path "C:\Users\likit\recipe-finder-react"
```

The command uses the saved ECR repository, ECS cluster, ECS service, and AWS region.

### Deployment Process

1. Validate the project directory.
2. Check that the project contains a Dockerfile.
3. Build the Docker image.
4. Authenticate Docker with Amazon ECR.
5. Push the image to the configured ECR repository.
6. Register a new ECS task-definition revision.
7. Update the selected ECS service.
8. Wait for the service deployment to stabilize.
9. Report the deployment result.

The project must contain a compatible Dockerfile, and the selected ECS service must have appropriate container ports and networking.

## 9. Dockerfile Example

The following multi-stage Dockerfile illustrates how a React/Vite application can be built and served using Nginx.

```dockerfile
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

Use this example only for a compatible React/Vite project. Check the project's dependencies and build configuration before adopting it.

## 10. Terraform Commands

Run these commands from the repository root.

### Format Terraform Files

```cmd
terraform -chdir=infrastructure fmt
```

### Validate Terraform Configuration

```cmd
terraform -chdir=infrastructure validate
```

### Preview Infrastructure Changes

```cmd
terraform -chdir=infrastructure plan
```

Review the plan before applying any infrastructure changes.

**Important:** Never apply a Terraform plan without checking whether it proposes replacing or destroying existing resources. Keep the Terraform state file private and out of GitHub.

## 11. Deployment Verification

After deployment, verify the ECS service:

```cmd
aws ecs describe-services --cluster capstone-devops-cluster --services recipe-finder-service --region ap-south-1 --query "services[0].{Status:status,Running:runningCount,Desired:desiredCount,TaskDefinition:taskDefinition}" --output table
```

Check that:

- The ECS service status is `ACTIVE`.
- The running task count matches the desired count.
- The task definition references the intended container image.
- The website opens in a browser through the current task's public IP.

A successful ECS status check should be followed by a browser test to verify website accessibility.

## 12. Deployment Test Results

The Recipe Finder deployment was tested successfully using the reusable CLI.

Verified results:

- Docker image built successfully.
- Image pushed to Amazon ECR.
- ECS task-definition revision 4 registered.
- ECS service deployment completed successfully.
- ECS service status reported `ACTIVE`.
- One running task and one desired task were confirmed.
- The website opened successfully in a browser.

The test demonstrated that the CLI can automate the deployment of a compatible Dockerized website to an existing ECS service.

## 13. Security Considerations

- Never commit AWS access keys, passwords, tokens, or other secrets to GitHub.
- Store CI/CD credentials in GitHub Secrets or use an appropriate role-based authentication mechanism.
- Follow least-privilege IAM permissions.
- Restrict inbound traffic to only the ports and sources required by the application.
- Do not commit `terraform.tfstate`, saved plan files, or sensitive local configuration.
- A task's public IP may change when ECS replaces the task.
- Direct public-IP access is suitable for a learning project but is less robust than a production deployment with a stable endpoint.

## 14. Project Scope and Limitations

- The CLI deploys to existing ECR repositories and ECS services.
- It does not automatically provision every AWS resource required for a brand-new website.
- The selected project must contain a compatible Dockerfile.
- The target ECS service must have compatible container port and network settings.
- The CI/CD capabilities depend on the actual configuration of the GitHub Actions workflow.
- CloudFront and cloud monitoring are excluded from this project.

## 15. Learning Outcomes

Through this project, the following skills were practiced:

- Containerizing a React application using Docker.
- Building and pushing Docker images to Amazon ECR.
- Deploying containerized websites to Amazon ECS Fargate.
- Automating deployments using Python and Boto3.
- Managing AWS infrastructure using Terraform.
- Using Git and GitHub for version control.
- Verifying ECS deployments using AWS CLI.
- Understanding the relationship between CI/CD pipelines, container registries, and container orchestration.

## 16. Future Improvements

Potential future enhancements include:

- Automated unit and integration tests.
- More robust deployment error handling.
- Support for configurable Docker image tags.
- Automated provisioning of deployment infrastructure.
- Improved rollback support for container deployments.
- CI/CD integration for invoking the reusable CLI.

These improvements are future work and should not be considered implemented until they have been developed and tested.
