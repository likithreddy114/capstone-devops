\# DevOps Capstone Project — Automated Cloud Deployment



\## Project Overview



This project demonstrates automated deployment of a React website using Docker, Amazon ECR, Amazon ECS Fargate, Terraform, and GitHub Actions.



The CI/CD pipeline builds a Docker image, pushes it to Amazon ECR, and deploys the updated application to ECS Fargate.



\## Architecture



Developer → GitHub → GitHub Actions → Docker Build → Amazon ECR → Amazon ECS Fargate → Live React Website



Terraform provisions and manages the AWS infrastructure.



\## Technologies Used



\- \*\*Frontend:\*\* React, Vite

\- \*\*Containerization:\*\* Docker

\- \*\*Container Registry:\*\* Amazon ECR

\- \*\*Container Deployment:\*\* Amazon ECS Fargate

\- \*\*Infrastructure as Code:\*\* Terraform

\- \*\*CI/CD:\*\* GitHub Actions

\- \*\*Cloud Platform:\*\* AWS

\- \*\*Version Control:\*\* Git and GitHub



\## CI/CD Workflow



1\. Developer pushes code to the `main` branch.

2\. GitHub Actions checks out the repository.

3\. AWS credentials are configured using GitHub Secrets.

4\. GitHub Actions authenticates with Amazon ECR.

5\. Docker builds the React application image.

6\. The image is tagged and pushed to Amazon ECR.

7\. The ECS deployment workflow updates the application.

8\. ECS runs the container and serves the website.



\## AWS Infrastructure



\- Amazon VPC

\- Public subnets

\- Internet Gateway and public route table

\- Security group allowing HTTP traffic on port 80

\- Amazon ECR repository

\- Amazon ECS cluster and Fargate service

\- IAM task execution role



The website is accessed directly through the public IP assigned to the running ECS task. An Application Load Balancer and CloudFront are not used in the current configuration.



\## Terraform Commands



Format configuration:



```bash

terraform -chdir=infrastructure fmt

```



Validate configuration:



```bash

terraform -chdir=infrastructure validate

```



Preview infrastructure changes:



```bash

terraform -chdir=infrastructure plan

```



\## Deployment Verification



\- Confirm that the GitHub Actions workflow succeeds.

\- Confirm that the Docker image exists in Amazon ECR.

\- Confirm that the ECS service has a running task.

\- Open the task's current public IP using HTTP to verify the website.



\## Security Notes



\- Store AWS credentials in GitHub Actions Secrets; never commit credentials to the repository.

\- Restrict SSH access and AWS permissions where applicable.

\- The public IP of an ECS task can change when the task is replaced.

\- Direct public-IP access is suitable for this learning project but is less robust than a production deployment with a stable endpoint.



\## Learning Outcomes



\- Built and containerized a React application.

\- Automated image builds and pushes using GitHub Actions.

\- Deployed a containerized application to Amazon ECS Fargate.

\- Provisioned cloud infrastructure using Terraform.

\- Verified deployment through AWS CLI and a web browser.



