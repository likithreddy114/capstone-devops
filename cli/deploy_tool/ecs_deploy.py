
import base64
import subprocess
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError


def run_command(command, cwd=None, input_text=None):
    """Run a command and stop if it fails."""
    print("\n> " + " ".join(str(part) for part in command))

    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        text=True,
        check=True,
    )
    return result


def deploy_container(
    project_path,
    repository,
    cluster,
    service,
    region="ap-south-1",
):
    """Build and deploy a Dockerized website to a specified ECS service."""
    project = Path(project_path).expanduser().resolve()

    if not project.is_dir():
        raise FileNotFoundError(f"Project folder not found: {project}")

    if not (project / "Dockerfile").is_file():
        raise FileNotFoundError(
            f"No Dockerfile found in {project}. "
            "The selected website must contain a Dockerfile."
        )

    if not all([repository, cluster, service, region]):
        raise ValueError(
            "Repository, cluster, service, and region are required."
        )

    session = boto3.Session(region_name=region)
    sts = session.client("sts")
    ecr = session.client("ecr")
    ecs = session.client("ecs")

    try:
        account_id = sts.get_caller_identity()["Account"]

        # Verify the requested ECR repository exists.
        response = ecr.describe_repositories(
            repositoryNames=[repository]
        )
        repository_uri = response["repositories"][0]["repositoryUri"]

        # Verify the requested ECS service exists.
        response = ecs.describe_services(
            cluster=cluster,
            services=[service],
        )
        services = response.get("services", [])

        if response.get("failures") or not services:
            raise RuntimeError(
                f"ECS service '{service}' was not found in cluster '{cluster}'."
            )

        current_service = services[0]

        if current_service["status"] != "ACTIVE":
            raise RuntimeError(
                f"ECS service '{service}' is not ACTIVE."
            )

        current_task = ecs.describe_task_definition(
            taskDefinition=current_service["taskDefinition"]
        )["taskDefinition"]

        containers = current_task["containerDefinitions"]

        if len(containers) != 1:
            raise RuntimeError(
                "This version supports ECS task definitions with exactly "
                "one container. No ECS update was made."
            )

        container_name = containers[0]["name"]
        image_uri = f"{repository_uri}:latest"

        print(f"AWS account: {account_id}")
        print(f"Project: {project}")
        print(f"ECR image: {image_uri}")
        print(f"ECS cluster: {cluster}")
        print(f"ECS service: {service}")
        print(f"Container name: {container_name}")

        # Build the selected website's Docker image.
        run_command(
            ["docker", "build", "-t", image_uri, "."],
            cwd=project,
        )

        # Authenticate Docker to the selected ECR registry.
        auth = ecr.get_authorization_token()["authorizationData"][0]
        registry = auth["proxyEndpoint"].replace("https://", "").rstrip("/")
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

        # Push the image to the specified ECR repository.
        run_command(["docker", "push", image_uri])

        # Prepare a new revision of the selected service's task definition.
        updated_containers = []

        for container in containers:
            updated = dict(container)

            if updated["name"] == container_name:
                updated["image"] = image_uri

            updated_containers.append(updated)

        register_args = {
            "family": current_task["family"],
            "containerDefinitions": updated_containers,
            "networkMode": current_task["networkMode"],
            "requiresCompatibilities": current_task.get(
                "requiresCompatibilities", ["FARGATE"]
            ),
            "cpu": current_task["cpu"],
            "memory": current_task["memory"],
        }

        optional_fields = [
            "executionRoleArn",
            "taskRoleArn",
            "volumes",
            "runtimePlatform",
            "ephemeralStorage",
            "pidMode",
            "ipcMode",
            "proxyConfiguration",
        ]

        for field in optional_fields:
            if field in current_task:
                register_args[field] = current_task[field]

        new_task = ecs.register_task_definition(
            **register_args
        )["taskDefinition"]

        task_arn = new_task["taskDefinitionArn"]
        print(f"Registered task definition: {task_arn}")

        # Update only the explicitly selected ECS service.
        ecs.update_service(
            cluster=cluster,
            service=service,
            taskDefinition=task_arn,
        )

        print("Waiting for ECS service deployment to stabilize...")

        ecs.get_waiter("services_stable").wait(
            cluster=cluster,
            services=[service],
            WaiterConfig={
                "Delay": 15,
                "MaxAttempts": 40,
            },
        )

        final_service = ecs.describe_services(
            cluster=cluster,
            services=[service],
        )["services"][0]

        if final_service["runningCount"] < 1:
            raise RuntimeError(
                "The service stabilized without a running task."
            )

        print("\nDeployment completed successfully.")
        print(f"Service: {service}")
        print(f"Task definition: {task_arn}")
        print(f"Running tasks: {final_service['runningCount']}")
        print(
            "Retrieve the task's public IP from ECS to access the website."
        )

    except (ClientError, BotoCoreError) as error:
        raise RuntimeError(
            f"AWS deployment failed: {error}"
        ) from error
