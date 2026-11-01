import base64
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError


DEFAULT_CPU = "256"
DEFAULT_MEMORY = "512"
CONTAINER_PORT = 80

PROTECTED_SERVICE_NAME = "capstone-devops-service"


def clean_name(value):
    name = re.sub(r"[^a-z0-9_-]", "-", str(value).lower())
    name = re.sub(r"[-_]+", "-", name).strip("-")
    return name[:40].rstrip("-") or "website"


def run_command(command, cwd=None, input_text=None):
    print("\n> " + " ".join(str(part) for part in command))

    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        text=True,
        check=True,
    )


def load_deployment_config():
    path = Path.home() / ".deploy-tool" / "config.json"

    if not path.is_file():
        raise FileNotFoundError(
            f"Deployment configuration not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    if not isinstance(config, dict):
        raise RuntimeError(
            "Deployment configuration must be a JSON object."
        )

    return config


def find_execution_role(config, session):
    configured = (
        config.get("ecs_execution_role_arn") or ""
    ).strip()

    if not configured:
        raise RuntimeError(
            "Configure ecs_execution_role_arn with the existing "
            "ECS execution role ARN."
        )

    role_name = configured.rsplit("/", 1)[-1]
    iam = session.client("iam")

    try:
        role = iam.get_role(RoleName=role_name)["Role"]
    except ClientError as error:
        raise RuntimeError(
            "The configured ECS execution role could not be verified."
        ) from error

    if role["Arn"] != configured:
        raise RuntimeError(
            "Configured execution role ARN does not match the AWS role."
        )

    if role.get("AssumeRolePolicyDocument", {}).get("Statement") is None:
        raise RuntimeError(
            "ECS execution role has no valid trust policy."
        )

    return role["Arn"]


def get_route_table(ec2, subnet_id, vpc_id):
    tables = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    ).get("RouteTables", [])

    for table in tables:
        for association in table.get("Associations", []):
            if association.get("SubnetId") == subnet_id:
                return table

    for table in tables:
        for association in table.get("Associations", []):
            if association.get("Main", False):
                return table

    return None


def has_internet_gateway_route(table):
    if not table:
        return False

    return any(
        route.get("DestinationCidrBlock") == "0.0.0.0/0"
        and route.get("GatewayId", "").startswith("igw-")
        and route.get("State") == "active"
        for route in table.get("Routes", [])
    )


def ensure_http_ingress(ec2, security_group_id):
    groups = ec2.describe_security_groups(
        GroupIds=[security_group_id]
    ).get("SecurityGroups", [])

    if not groups:
        raise RuntimeError(
            f"Security group {security_group_id} was not found."
        )

    allowed = any(
        permission.get("IpProtocol") == "tcp"
        and permission.get("FromPort", 0) <= CONTAINER_PORT
        and permission.get("ToPort", 0) >= CONTAINER_PORT
        and any(
            item.get("CidrIp") == "0.0.0.0/0"
            for item in permission.get("IpRanges", [])
        )
        for permission in groups[0].get("IpPermissions", [])
    )

    if not allowed:
        raise RuntimeError(
            "The selected security group does not allow public HTTP "
            "access on port 80. No security rule was changed."
        )


def find_network(config, session):
    ec2 = session.client("ec2")

    vpc_id = (config.get("vpc_id") or "").strip()

    if not vpc_id:
        raise RuntimeError("Configure the existing vpc_id.")

    vpcs = ec2.describe_vpcs(
        VpcIds=[vpc_id]
    ).get("Vpcs", [])

    if not vpcs:
        raise RuntimeError(f"VPC {vpc_id} was not found.")

    subnet_ids = config.get("subnet_ids") or []

    if isinstance(subnet_ids, str):
        subnet_ids = [
            item.strip()
            for item in subnet_ids.split(",")
            if item.strip()
        ]

    if not subnet_ids:
        raise RuntimeError(
            "Configure the existing public subnet_ids."
        )

    if len(subnet_ids) != len(set(subnet_ids)):
        raise RuntimeError("Duplicate subnet IDs were provided.")

    subnets = ec2.describe_subnets(
        SubnetIds=subnet_ids
    ).get("Subnets", [])

    if len(subnets) != len(set(subnet_ids)):
        raise RuntimeError(
            "One or more configured subnet IDs were not found."
        )

    for subnet in subnets:
        subnet_id = subnet["SubnetId"]

        if subnet.get("VpcId") != vpc_id:
            raise RuntimeError(
                f"Subnet {subnet_id} does not belong to {vpc_id}."
            )

        if not subnet.get("MapPublicIpOnLaunch", False):
            raise RuntimeError(
                f"Subnet {subnet_id} does not assign public IPs on launch."
            )

        route_table = get_route_table(
            ec2, subnet_id, vpc_id
        )

        if not has_internet_gateway_route(route_table):
            raise RuntimeError(
                f"Subnet {subnet_id} has no active Internet Gateway route."
            )

    security_group_id = (
        config.get("security_group_id") or ""
    ).strip()

    if not security_group_id:
        raise RuntimeError(
            "Configure an existing security_group_id."
        )

    groups = ec2.describe_security_groups(
        GroupIds=[security_group_id]
    ).get("SecurityGroups", [])

    if not groups or groups[0].get("VpcId") != vpc_id:
        raise RuntimeError(
            "Configured security group does not belong to the selected VPC."
        )

    ensure_http_ingress(ec2, security_group_id)

    return subnet_ids, security_group_id


def ensure_repository(ecr, repository, app_name):
    """
    Find the application's ECR repository.
    Create it automatically if it does not exist.
    """

    repository = clean_name(repository or app_name)

    try:
        result = ecr.describe_repositories(
            repositoryNames=[repository]
        )

        repositories = result.get("repositories", [])

        if repositories:
            print(f"Using existing ECR repository: {repository}")
            return repositories[0]["repositoryUri"]

    except ClientError as error:
        error_code = error.response.get(
            "Error", {}
        ).get("Code")

        if error_code != "RepositoryNotFoundException":
            raise

    print(f"Creating ECR repository: {repository}")

    try:
        result = ecr.create_repository(
            repositoryName=repository,
            imageTagMutability="MUTABLE",
            imageScanningConfiguration={
                "scanOnPush": True
            },
            tags=[
                {"Key": "ManagedBy", "Value": "deploy-tool"},
                {"Key": "Application", "Value": app_name},
            ],
        )

        repository_uri = result["repository"]["repositoryUri"]

        print(f"Created ECR repository: {repository}")

        return repository_uri

    except ClientError as error:
        error_code = error.response.get(
            "Error", {}
        ).get("Code")

        if error_code == "RepositoryAlreadyExistsException":
            result = ecr.describe_repositories(
                repositoryNames=[repository]
            )
            return result["repositories"][0]["repositoryUri"]

        raise


def verify_existing_cluster(ecs, cluster):
    result = ecs.describe_clusters(
        clusters=[cluster]
    )

    clusters = result.get("clusters", [])

    if not clusters or clusters[0].get("status") != "ACTIVE":
        raise RuntimeError(
            f"Existing ECS cluster '{cluster}' is not ACTIVE."
        )

    print(f"Using existing ECS cluster: {cluster}")


def register_application_task(
    ecs,
    app_name,
    image_uri,
    execution_role_arn,
    task_role_arn=None,
):
    container = {
        "name": app_name,
        "image": image_uri,
        "essential": True,
        "portMappings": [
            {
                "containerPort": CONTAINER_PORT,
                "hostPort": CONTAINER_PORT,
                "protocol": "tcp",
            }
        ],
    }

    arguments = {
        "family": f"{app_name}-task",
        "networkMode": "awsvpc",
        "requiresCompatibilities": ["FARGATE"],
        "cpu": DEFAULT_CPU,
        "memory": DEFAULT_MEMORY,
        "executionRoleArn": execution_role_arn,
        "containerDefinitions": [container],
        "tags": [
            {"key": "ManagedBy", "value": "deploy-tool"},
            {"key": "Application", "value": app_name},
        ],
    }

    if task_role_arn:
        arguments["taskRoleArn"] = task_role_arn

    result = ecs.register_task_definition(**arguments)

    task = result["taskDefinition"]

    print(
        f"Registered task definition: {task['taskDefinitionArn']}"
    )

    return task["taskDefinitionArn"]


def create_or_update_service(
    ecs,
    cluster,
    service,
    task_definition,
    subnet_ids,
    security_group_id,
    assign_public_ip,
    desired_count=1,
    app_name=None,
):
    owner_app = clean_name(app_name or service.removesuffix('-service'))
    if service == PROTECTED_SERVICE_NAME:
        raise RuntimeError(
            "The original Capstone ECS service is protected. "
            "Use a separate service name for reusable deployments."
        )

    result = ecs.describe_services(
        cluster=cluster,
        services=[service],
    )

    existing = result.get("services", [])

    if existing and existing[0].get("status") == "ACTIVE":
        current_task = ecs.describe_task_definition(
            taskDefinition=existing[0]["taskDefinition"]
        )["taskDefinition"]
        expected_family = f"{owner_app}-task"
        if current_task.get("family") != expected_family:
            raise RuntimeError(
                f"Refusing to update service '{service}': its current task "
                f"family is '{current_task.get('family')}', not '{expected_family}'."
            )

        # Adopt only a service whose name and current task family match this app.
        ecs.tag_resource(
            resourceArn=existing[0]["serviceArn"],
            tags=[
                {"key": "ManagedBy", "value": "deploy-tool"},
                {"key": "Application", "value": owner_app},
            ],
        )
        print(f"Updating reusable website service: {service}")

        ecs.update_service(
            cluster=cluster,
            service=service,
            taskDefinition=task_definition,
            desiredCount=desired_count,
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": subnet_ids,
                    "securityGroups": [security_group_id],
                    "assignPublicIp": assign_public_ip,
                }
            },
            forceNewDeployment=True,
        )
        return

    if existing:
        raise RuntimeError(
            f"Service {service} exists but is not ACTIVE."
        )

    print(f"Creating separate website service: {service}")

    ecs.create_service(
        cluster=cluster,
        serviceName=service,
        taskDefinition=task_definition,
        desiredCount=desired_count,
        launchType="FARGATE",
        platformVersion="LATEST",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": subnet_ids,
                "securityGroups": [security_group_id],
                "assignPublicIp": assign_public_ip,
            }
        },
        deploymentConfiguration={
            "maximumPercent": 200,
            "minimumHealthyPercent": 100,
        },
        tags=[
            {"key": "ManagedBy", "value": "deploy-tool"},
            {"key": "Application", "value": owner_app},
        ],
    )


def get_public_ip(
    ecs,
    ec2,
    cluster,
    service,
    attempts=6,
    delay=5,
):
    for attempt in range(attempts):
        task_arns = ecs.list_tasks(
            cluster=cluster,
            serviceName=service,
            desiredStatus="RUNNING",
        ).get("taskArns", [])

        if task_arns:
            tasks = ecs.describe_tasks(
                cluster=cluster,
                tasks=task_arns,
            ).get("tasks", [])

            for task in tasks:
                for attachment in task.get("attachments", []):
                    if attachment.get("type") != "ElasticNetworkInterface":
                        continue

                    eni_id = next(
                        (
                            detail["value"]
                            for detail in attachment.get("details", [])
                            if detail.get("name") == "networkInterfaceId"
                        ),
                        None,
                    )

                    if eni_id:
                        interfaces = ec2.describe_network_interfaces(
                            NetworkInterfaceIds=[eni_id]
                        ).get("NetworkInterfaces", [])

                        if interfaces:
                            public_ip = interfaces[0].get(
                                "Association", {}
                            ).get("PublicIp")

                            if public_ip:
                                return public_ip

        if attempt < attempts - 1:
            time.sleep(delay)

    return None


def deploy_container(
    project_path,
    repository=None,
    cluster=None,
    service=None,
    region=None,
    app_name=None,
):
    """Deploy a separate website to an existing ECS Fargate cluster."""

    project = Path(project_path).expanduser().resolve()

    if not project.is_dir():
        raise FileNotFoundError(
            f"Project folder not found: {project}"
        )

    if not (project / "Dockerfile").is_file():
        raise FileNotFoundError(
            f"No Dockerfile found in {project}."
        )

    config = load_deployment_config()

    region = region or config.get("region", "ap-south-1")

    app_name = clean_name(app_name or project.name)

    # Each application gets its own repository by default.
    # An explicitly supplied repository still takes priority.
    # Each application gets its own ECR repository by default.
    # A global config value must never make unrelated apps share a repository.
    repository = clean_name(repository or app_name)

    cluster = cluster or config.get("ecs_cluster")

    if not cluster:
        raise RuntimeError(
            "Configure an existing ecs_cluster."
        )

    # Never default to the Terraform-managed Capstone service.
    service = clean_name(service or f"{app_name}-service")

    if service == PROTECTED_SERVICE_NAME:
        raise RuntimeError(
            "The original Capstone ECS service cannot be modified "
            "by the reusable deployment tool."
        )

    assign_public_ip = (
        config.get("assign_public_ip", "ENABLED") or "ENABLED"
    ).upper()

    if assign_public_ip not in ("ENABLED", "DISABLED"):
        raise RuntimeError(
            "assign_public_ip must be ENABLED or DISABLED."
        )

    desired_count = int(config.get("desired_count", 1))

    if desired_count < 1:
        raise RuntimeError("desired_count must be at least 1.")

    session = boto3.Session(region_name=region)

    try:
        print("\n======================================")
        print("   DEPLOY TOOL - WEBSITE DEPLOYMENT")
        print("======================================")

        print(f"Application: {app_name}")
        print(f"Project: {project}")
        print(f"Region: {region}")
        print(f"ECR repository: {repository}")
        print(f"ECS cluster: {cluster}")
        print(f"ECS service: {service}")

        print("\nPREFLIGHT: Checking AWS identity and resources")

        account_id = session.client(
            "sts"
        ).get_caller_identity()["Account"]

        print(f"AWS account: {account_id}")

        execution_role_arn = find_execution_role(
            config, session
        )

        print(f"ECS execution role: {execution_role_arn}")

        subnet_ids, security_group_id = find_network(
            config, session
        )

        print(f"Validated public subnets: {subnet_ids}")
        print(f"HTTP security group: {security_group_id}")

        ecr = session.client("ecr")
        ecs = session.client("ecs")
        ec2 = session.client("ec2")

        repository_uri = ensure_repository(
            ecr, repository, app_name
        )

        verify_existing_cluster(ecs, cluster)

        tag = datetime.now(
            timezone.utc
        ).strftime("%Y%m%d%H%M%S")

        image_uri = f"{repository_uri}:{tag}"

        print("\nSTEP 1: Building Docker image")

        run_command(
            ["docker", "build", "-t", image_uri, "."],
            cwd=project,
        )

        print("\nSTEP 2: Authenticating with ECR")

        auth = ecr.get_authorization_token()[
            "authorizationData"
        ][0]

        registry = (
            auth["proxyEndpoint"]
            .replace("https://", "")
            .rstrip("/")
        )

        password = base64.b64decode(
            auth["authorizationToken"]
        ).decode("utf-8").split(":", 1)[1]

        run_command(
            [
                "docker",
                "login",
                "--username",
                "AWS",
                "--password-stdin",
                registry,
            ],
            input_text=password,
        )

        print("\nSTEP 3: Pushing image to ECR")

        run_command(
            ["docker", "push", image_uri]
        )

        print("\nSTEP 4: Registering application task")

        task_definition = register_application_task(
            ecs,
            app_name,
            image_uri,
            execution_role_arn,
            config.get("ecs_task_role_arn") or None,
        )

        print("\nSTEP 5: Creating or updating separate ECS service")

        create_or_update_service(
            ecs,
            cluster,
            service,
            task_definition,
            subnet_ids,
            security_group_id,
            assign_public_ip,
            desired_count,
            app_name=app_name,
        )

        print("\nSTEP 6: Waiting for ECS service stability")

        ecs.get_waiter("services_stable").wait(
            cluster=cluster,
            services=[service],
            WaiterConfig={
                "Delay": 15,
                "MaxAttempts": 40,
            },
        )

        services = ecs.describe_services(
            cluster=cluster,
            services=[service],
        ).get("services", [])

        if (
            not services
            or services[0].get("runningCount", 0) < 1
        ):
            raise RuntimeError(
                "Deployment finished without a running task."
            )

        public_ip = None

        if assign_public_ip == "ENABLED":
            public_ip = get_public_ip(
                ecs, ec2, cluster, service
            )

        print("\n======================================")
        print("       DEPLOYMENT SUCCESSFUL")
        print("======================================")

        print(f"Application: {app_name}")
        print(f"AWS account: {account_id}")
        print(f"ECR image: {image_uri}")
        print(f"ECS service: {service}")
        print(
            f"Running tasks: {services[0].get('runningCount', 0)}"
        )

        if public_ip:
            print(f"Website URL: http://{public_ip}")
        elif assign_public_ip == "ENABLED":
            print(
                "Task is running, but its public IP is not available yet."
            )
        else:
            print(
                "Public IP assignment is disabled; no public URL is available."
            )

    except (ClientError, BotoCoreError) as error:
        raise RuntimeError(
            f"AWS deployment failed: {error}"
        ) from error


def _get_tags(client, resource_arn):
    """Return ECS or ECR resource tags as a simple key/value dictionary."""
    result = client.list_tags_for_resource(resourceArn=resource_arn)
    return {
        item.get("key", item.get("Key")): item.get("value", item.get("Value"))
        for item in result.get("tags", [])
    }


def _require_owned(tags, app_name, resource_description):
    if tags.get("ManagedBy") != "deploy-tool" or tags.get("Application") != app_name:
        raise RuntimeError(
            f"Refusing to delete {resource_description}: ownership tags do not "
            f"confirm that deploy-tool owns it for application '{app_name}'. "
            "No resources have been deleted."
        )


def show_ecs_status(app_name, cluster=None, service=None, region=None):
    """Display the status of one application-specific ECS service."""
    config = load_deployment_config()
    app_name = clean_name(app_name)
    cluster = cluster or config.get("ecs_cluster")
    service = clean_name(service or f"{app_name}-service")
    region = region or config.get("region", "ap-south-1")
    if not cluster:
        raise RuntimeError("Configure an existing ecs_cluster.")

    session = boto3.Session(region_name=region)
    ecs = session.client("ecs")
    ec2 = session.client("ec2")
    verify_existing_cluster(ecs, cluster)
    result = ecs.describe_services(cluster=cluster, services=[service])
    services = result.get("services", [])
    failures = result.get("failures", [])
    if not services:
        detail = failures[0].get("reason", "service was not found") if failures else "service was not found"
        raise RuntimeError(f"ECS service '{service}' not found in cluster '{cluster}': {detail}.")

    item = services[0]
    print("\n======================================")
    print("          WEBSITE ECS STATUS")
    print("======================================")
    print(f"Application: {app_name}")
    print(f"Cluster: {cluster}")
    print(f"Service: {service}")
    print(f"Status: {item.get('status', 'UNKNOWN')}")
    print(f"Desired tasks: {item.get('desiredCount', 0)}")
    print(f"Running tasks: {item.get('runningCount', 0)}")
    print(f"Pending tasks: {item.get('pendingCount', 0)}")
    print(f"Task definition: {item.get('taskDefinition', 'N/A')}")
    for deployment in item.get("deployments", []):
        print(
            "Deployment: "
            f"{deployment.get('status', 'UNKNOWN')} | "
            f"running={deployment.get('runningCount', 0)} | "
            f"desired={deployment.get('desiredCount', 0)}"
        )
    if item.get("runningCount", 0) > 0:
        public_ip = get_public_ip(ecs, ec2, cluster, service, attempts=2, delay=2)
        if public_ip:
            print(f"Website URL: http://{public_ip}")
    print("======================================")


def destroy_application(app_name, cluster=None, service=None, repository=None, region=None):
    """Destroy only the selected application's owned ECS/ECR resources."""
    config = load_deployment_config()
    app_name = clean_name(app_name)
    cluster = cluster or config.get("ecs_cluster")
    service = clean_name(service or f"{app_name}-service")
    repository = clean_name(repository or app_name)
    region = region or config.get("region", "ap-south-1")
    task_family = f"{app_name}-task"

    if not cluster:
        raise RuntimeError("Configure an existing ecs_cluster.")
    if service == PROTECTED_SERVICE_NAME:
        raise RuntimeError("The original Capstone ECS service is protected. It cannot be destroyed by this command.")

    session = boto3.Session(region_name=region)
    ecs = session.client("ecs")
    ecr = session.client("ecr")
    verify_existing_cluster(ecs, cluster)

    # PRE-FLIGHT: verify every resource before deleting anything.
    repo_arn = None
    try:
        repos = ecr.describe_repositories(repositoryNames=[repository]).get("repositories", [])
        if repos:
            repo_arn = repos[0]["repositoryArn"]
            _require_owned(_get_tags(ecr, repo_arn), app_name, f"ECR repository '{repository}'")
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        if code != "RepositoryNotFoundException":
            raise

    service_item = None
    result = ecs.describe_services(cluster=cluster, services=[service])
    services = result.get("services", [])
    if services:
        service_item = services[0]
        _require_owned(_get_tags(ecs, service_item["serviceArn"]), app_name, f"ECS service '{service}'")
        task = ecs.describe_task_definition(taskDefinition=service_item["taskDefinition"])["taskDefinition"]
        if task.get("family") != task_family:
            raise RuntimeError(
                f"Refusing to destroy service '{service}': it uses task family "
                f"'{task.get('family')}', expected '{task_family}'. No resources have been deleted."
            )

    # Collect only task-definition revisions with exact ownership tags.
    owned_task_arns = []
    paginator = ecs.get_paginator("list_task_definitions")
    for page in paginator.paginate(familyPrefix=task_family, status="ACTIVE", sort="DESC"):
        for arn in page.get("taskDefinitionArns", []):
            detail = ecs.describe_task_definition(taskDefinition=arn, include=["TAGS"])
            task = detail["taskDefinition"]
            tags = {t.get("key"): t.get("value") for t in detail.get("tags", [])}
            if task.get("family") == task_family and tags.get("ManagedBy") == "deploy-tool" and tags.get("Application") == app_name:
                owned_task_arns.append(arn)

    print("\nDESTROY PRE-FLIGHT PASSED")
    print(f"Application: {app_name}")
    print(f"ECS service: {service_item.get('serviceName') if service_item else 'not found'}")
    print(f"Owned task definitions to deregister: {len(owned_task_arns)}")
    print(f"Owned ECR repository: {repository if repo_arn else 'not found'}")
    print("Shared ECS cluster, VPC, subnets, security group and IAM roles will be preserved.")

    if not service_item and not repo_arn and not owned_task_arns:
        print("Nothing owned by deploy-tool was found for this application.")
        return

    if service_item:
        print(f"\nDeleting ECS service: {service}")
        ecs.delete_service(cluster=cluster, service=service, force=True)
        ecs.get_waiter("services_inactive").wait(
            cluster=cluster,
            services=[service],
            WaiterConfig={"Delay": 10, "MaxAttempts": 30},
        )

    for arn in owned_task_arns:
        print(f"Deregistering task definition: {arn}")
        ecs.deregister_task_definition(taskDefinition=arn)

    if repo_arn:
        print(f"Deleting ECR repository and its images: {repository}")
        ecr.delete_repository(repositoryName=repository, force=True)

    print("\n======================================")
    print("       DESTROY COMPLETED")
    print("======================================")
    print(f"Application: {app_name}")
    print("The selected website deployment resources were removed.")
    print("Shared infrastructure was not deleted.")
    print("Note: ECS task definitions are deregistered, not permanently erased by AWS.")
