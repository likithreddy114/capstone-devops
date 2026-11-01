terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# Verify the AWS account
data "aws_caller_identity" "current" {}

# Reference existing VPC
data "aws_vpc" "existing" {
  id = var.vpc_id
}

# Reference existing public subnets
data "aws_subnet" "public_a" {
  id = var.subnet_ids[0]
}

data "aws_subnet" "public_b" {
  id = var.subnet_ids[1]
}

# Reference existing ECS security group
data "aws_security_group" "existing" {
  id = var.security_group_id
}

# Reference existing ECS cluster
data "aws_ecs_cluster" "existing" {
  cluster_name = var.ecs_cluster_name
}

# Reference existing ECS execution role
data "aws_iam_role" "existing" {
  name = var.ecs_execution_role_name
}

# Manage the existing private S3 deployment bucket
resource "aws_s3_bucket" "website" {
  bucket = var.bucket_name

  lifecycle {
    prevent_destroy = true
  }
}

# Manage existing S3 versioning
resource "aws_s3_bucket_versioning" "website" {
  bucket = aws_s3_bucket.website.id

  versioning_configuration {
    status = "Enabled"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# Manage existing S3 public access protection
resource "aws_s3_bucket_public_access_block" "website" {
  bucket = aws_s3_bucket.website.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true

  lifecycle {
    prevent_destroy = true
  }
}

# Outputs
output "aws_account_id" {
  description = "AWS account used by Terraform"
  value       = data.aws_caller_identity.current.account_id
}

output "s3_bucket_name" {
  description = "S3 deployment bucket"
  value       = aws_s3_bucket.website.bucket
}

output "vpc_id" {
  description = "Existing VPC ID"
  value       = data.aws_vpc.existing.id
}

output "public_subnet_ids" {
  description = "Existing public subnet IDs"
  value = [
    data.aws_subnet.public_a.id,
    data.aws_subnet.public_b.id
  ]
}

output "security_group_id" {
  description = "Existing ECS security group"
  value       = data.aws_security_group.existing.id
}

output "ecs_cluster_name" {
  description = "Existing ECS cluster"
  value       = data.aws_ecs_cluster.existing.cluster_name
}

output "ecs_execution_role_arn" {
  description = "Existing ECS execution role"
  value       = data.aws_iam_role.existing.arn
}