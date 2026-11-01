variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "aws_profile" {
  description = "AWS CLI profile"
  type        = string
  default     = "capstone-deploy"
}

variable "bucket_name" {
  description = "S3 deployment bucket"
  type        = string
  default     = "deploy-tool-assets-278031908362-ap-south-1"
}

variable "vpc_id" {
  description = "Existing VPC ID"
  type        = string
  default     = "vpc-060db9e74285b787b"
}

variable "subnet_ids" {
  description = "Existing public subnet IDs"
  type        = list(string)

  default = [
    "subnet-027551c64394eb306",
    "subnet-0125f24561b77f57a"
  ]
}

variable "security_group_id" {
  description = "Existing ECS security group ID"
  type        = string
  default     = "sg-0c2f2fd43849d98fd"
}

variable "ecs_cluster_name" {
  description = "Existing ECS cluster name"
  type        = string
  default     = "deploy-tool-cluster"
}

variable "ecs_execution_role_name" {
  description = "Existing ECS execution role name"
  type        = string
  default     = "deploy-tool-ecs-execution-role"
}