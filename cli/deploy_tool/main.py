import argparse
import json
import re
import socket
import subprocess
import sys
from pathlib import Path

from deploy_tool.config import (
    DEFAULT_CONFIG,
    load_config,
    set_config,
    show_config,
)

from deploy_tool.aws_deploy import (
    check_bucket,
    deploy_to_s3,
    deploy_release,
    list_releases,
    rollback_release,
)

from deploy_tool.ecs_deploy import (
    deploy_container,
    show_ecs_status,
    destroy_application,
)


def get_project_root():
    """Find the Capstone project root."""
    current = Path.cwd().resolve()

    for directory in [current, *current.parents]:
        if (directory / "sample-react-app").is_dir():
            return directory

    raise FileNotFoundError("Capstone project root not found.")


def initialize_project():
    """Verify required Capstone directories."""
    project_dir = get_project_root()

    required_dirs = [
        "sample-react-app",
        "infrastructure",
        "docs",
        "tests",
    ]

    for directory in required_dirs:
        path = project_dir / directory
        path.mkdir(parents=True, exist_ok=True)
        print(f"Verified: {path}")

    print("\nProject initialization completed.")


def validate_website(project_path, app_name=None):
    """Validate a Node.js website without contacting AWS."""
    project = Path(project_path).expanduser().resolve()

    if not project.is_dir():
        raise FileNotFoundError(
            f"Website directory not found: {project}"
        )

    package_file = project / "package.json"
    dockerfile = project / "Dockerfile"

    if not package_file.is_file():
        raise ValueError("package.json not found.")

    if not dockerfile.is_file():
        raise ValueError("Dockerfile not found.")

    with package_file.open("r", encoding="utf-8") as file:
        package = json.load(file)

    scripts = package.get("scripts", {})

    if "build" not in scripts:
        raise ValueError("No build script found in package.json.")

    name = app_name or project.name

    print("\nWebsite validation successful")
    print("--------------------------------")
    print(f"Application: {name}")
    print(f"Project: {project}")
    print(f"Package: {package.get('name', project.name)}")
    print(f"Dockerfile: {dockerfile}")
    print(f"Build script: {scripts['build']}")
    print("AWS connection: Not required")
    print("--------------------------------")

    return True


def run_local_website(project_path, app_name=None):
    """Build and run a website locally using Docker."""
    project = Path(project_path).expanduser().resolve()

    validate_website(project, app_name)

    name = re.sub(
        r"[^a-zA-Z0-9_-]",
        "-",
        (app_name or project.name).lower(),
    ).strip("-")

    if not name:
        name = "website"

    container_name = f"{name}-local"
    image_name = f"{name}-local:latest"

    existing = subprocess.run(
        [
            "docker",
            "ps",
            "--filter",
            f"name=^{container_name}$",
            "--format",
            "{{.Names}}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    if existing.stdout.strip() == container_name:
        result = subprocess.run(
            ["docker", "port", container_name, "80"],
            capture_output=True,
            text=True,
            check=True,
        )

        mapping = result.stdout.strip().splitlines()

        if mapping:
            address = mapping[0]
            port = address.rsplit(":", 1)[-1]

            print("\nWebsite is already running.")
            print(f"Website URL: http://localhost:{port}")
            return

    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True,
        text=True,
    )

    print("\nBuilding Docker image...")

    subprocess.run(
        ["docker", "build", "-t", image_name, "."],
        cwd=project,
        check=True,
    )

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    print("\nStarting local website container...")

    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{port}:80",
            image_name,
        ],
        check=True,
    )

    print("\n================================")
    print(" LOCAL DEPLOYMENT SUCCESSFUL")
    print("================================")
    print(f"Application: {name}")
    print(f"Container: {container_name}")
    print(f"Website URL: http://localhost:{port}")
    print("================================")


def show_status():
    """Check S3 bucket accessibility."""
    print("Checking S3 deployment status...")

    if check_bucket():
        print("S3 status check completed.")
    else:
        raise RuntimeError("Cannot access configured S3 bucket.")


def deploy_application():
    """Deploy the original Capstone website to S3."""
    project_dir = get_project_root()
    build_dir = project_dir / "sample-react-app" / "dist"

    if not build_dir.is_dir() or not (
        build_dir / "index.html"
    ).is_file():
        raise FileNotFoundError(
            "React build not found. Run npm run build "
            "inside sample-react-app."
        )

    print("Starting Capstone S3 deployment...")
    deploy_to_s3()


def create_release():
    """Create a versioned S3 release."""
    print("Starting release creation...")
    deploy_release()


def show_releases():
    """List releases stored in S3."""
    print("Checking stored releases...")
    list_releases()


def rollback_application(release_id):
    """Restore a selected S3 release."""
    if not release_id:
        print("Run: deploy-tool releases")
        print("Then: deploy-tool rollback RELEASE_ID")
        return

    rollback_release(release_id)


def deploy_container_application(args):
    """Deploy an independent website to ECS Fargate."""
    config = load_config()

    project = Path(args.project_path).expanduser().resolve()

    validate_website(project, args.name)

    repository = args.repository
    cluster = args.cluster or config.get("ecs_cluster")
    region = args.region or config.get("region", "ap-south-1")

    service = args.service or (
        f"{args.name or project.name}-service"
    )

    missing = []

    if not cluster:
        missing.append("ECS cluster")

    if not service:
        missing.append("Application-specific ECS service")

    if missing:
        raise ValueError(
            "Missing deployment settings: "
            + ", ".join(missing)
            + ". Configure the required settings before deployment."
        )

    print("\nStarting ECS Fargate deployment...")
    print(f"Project: {project}")
    print(
        f"ECR repository: {repository or 'Automatic per application'}"
    )
    print(f"ECS cluster: {cluster}")
    print(f"ECS service: {service}")
    print(f"AWS region: {region}")

    deploy_container(
        project_path=str(project),
        repository=repository,
        cluster=cluster,
        service=service,
        region=region,
        app_name=args.name,
    )


def add_deployment_arguments(deploy_parser):
    """Add common arguments for website deployments."""
    deploy_parser.add_argument(
        "--project-path",
        required=True,
        help="Path to the React website project",
    )
    deploy_parser.add_argument(
        "--name",
        default=None,
        help="Unique application name",
    )
    deploy_parser.add_argument(
        "--repository",
        default=None,
        help="Optional ECR repository name",
    )
    deploy_parser.add_argument(
        "--cluster",
        default=None,
        help="ECS cluster name",
    )
    deploy_parser.add_argument(
        "--service",
        default=None,
        help="ECS service name",
    )
    deploy_parser.add_argument(
        "--region",
        default=None,
        help="AWS region",
    )


def main():
    parser = argparse.ArgumentParser(
        prog="deploy-tool",
        description=(
            "Reusable website deployment platform "
            "using Docker, AWS S3 and ECS Fargate."
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version="deploy-tool 0.4.0",
    )

    commands = parser.add_subparsers(dest="command")

    commands.add_parser(
        "init",
        help="Initialize the Capstone project",
    )

    # Main command: deploy to ECS.
    deploy_parser = commands.add_parser(
        "deploy",
        help="Deploy any website to AWS ECS Fargate",
    )
    add_deployment_arguments(deploy_parser)

    # Preserve the existing S3 deployment.
    commands.add_parser(
        "deploy-s3",
        help="Deploy the original Capstone website to S3",
    )

    validate_parser = commands.add_parser(
        "validate",
        help="Validate a website locally",
    )
    validate_parser.add_argument("--project-path", required=True)
    validate_parser.add_argument("--name", default=None)

    local_parser = commands.add_parser(
        "run-local",
        help="Build and run a website locally using Docker",
    )
    local_parser.add_argument("--project-path", required=True)
    local_parser.add_argument("--name", default=None)

    # Keep the old ECS command for backward compatibility.
    container_parser = commands.add_parser(
        "deploy-container",
        help="Deploy a website to AWS ECS Fargate (legacy command)",
    )
    add_deployment_arguments(container_parser)

    commands.add_parser(
        "status",
        help="Check S3 bucket accessibility",
    )

    commands.add_parser(
        "release",
        help="Create a versioned S3 release",
    )

    commands.add_parser(
        "releases",
        help="List stored S3 releases",
    )

    rollback_parser = commands.add_parser(
        "rollback",
        help="Restore an S3 release",
    )
    rollback_parser.add_argument(
        "release_id",
        nargs="?",
        default=None,
    )

    ecs_status_parser = commands.add_parser(
        "ecs-status",
        help="Check one deployed website's ECS status",
    )
    ecs_status_parser.add_argument("--name", required=True)
    ecs_status_parser.add_argument("--cluster", default=None)
    ecs_status_parser.add_argument("--service", default=None)
    ecs_status_parser.add_argument("--region", default=None)

    destroy_parser = commands.add_parser(
        "destroy",
        help="Destroy one website deployment without deleting shared infrastructure",
    )
    destroy_parser.add_argument("--name", required=True)
    destroy_parser.add_argument("--cluster", default=None)
    destroy_parser.add_argument("--service", default=None)
    destroy_parser.add_argument("--repository", default=None)
    destroy_parser.add_argument("--region", default=None)

    config_parser = commands.add_parser(
        "config",
        help="Manage deployment configuration",
    )
    config_parser.add_argument(
        "action",
        choices=["list", "set"],
    )
    config_parser.add_argument("key", nargs="?")
    config_parser.add_argument("value", nargs="?")

    args = parser.parse_args()

    try:
        if args.command == "init":
            initialize_project()

        elif args.command == "validate":
            validate_website(
                args.project_path,
                args.name,
            )

        elif args.command == "run-local":
            run_local_website(
                args.project_path,
                args.name,
            )

        elif args.command == "deploy":
            deploy_container_application(args)

        elif args.command == "deploy-container":
            deploy_container_application(args)

        elif args.command == "deploy-s3":
            deploy_application()

        elif args.command == "status":
            show_status()

        elif args.command == "release":
            create_release()

        elif args.command == "releases":
            show_releases()

        elif args.command == "rollback":
            rollback_application(args.release_id)

        elif args.command == "ecs-status":
            show_ecs_status(
                app_name=args.name,
                cluster=args.cluster,
                service=args.service,
                region=args.region,
            )

        elif args.command == "destroy":
            destroy_application(
                app_name=args.name,
                cluster=args.cluster,
                service=args.service,
                repository=args.repository,
                region=args.region,
            )

        elif args.command == "config":
            if args.action == "list":
                if args.key or args.value:
                    parser.error(
                        "Usage: deploy-tool config list"
                    )

                show_config()

            elif args.action == "set":
                if not args.key or not args.value:
                    parser.error(
                        "Usage: deploy-tool config set KEY VALUE"
                    )

                if args.key not in DEFAULT_CONFIG:
                    parser.error("Unknown configuration key.")

                set_config(args.key, args.value)
                print(f"Updated configuration: {args.key}")

        else:
            parser.print_help()

    except (
        ValueError,
        OSError,
        RuntimeError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
