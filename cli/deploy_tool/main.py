
import argparse
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
from deploy_tool.ecs_deploy import deploy_container


def get_project_root():
    """Find the Capstone project root."""
    current = Path.cwd().resolve()

    for directory in [current, *current.parents]:
        if (directory / "sample-react-app").is_dir():
            return directory

    raise FileNotFoundError(
        "Project root not found. Ensure sample-react-app exists."
    )


def initialize_project():
    """Verify that the required project directories exist."""
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
        print(f"Verified directory: {path}")

    print("\nProject initialization completed successfully.")


def show_status():
    """Check whether the configured S3 bucket is accessible."""
    print("Checking S3 deployment status...")

    if check_bucket():
        print("S3 status check completed.")
    else:
        raise RuntimeError(
            "Cannot access the configured S3 bucket. "
            "Check your AWS credentials and bucket configuration."
        )


def deploy_application():
    """Upload the existing Capstone React build to S3."""
    project_dir = get_project_root()
    build_dir = project_dir / "sample-react-app" / "dist"

    if not build_dir.is_dir() or not (build_dir / "index.html").is_file():
        raise FileNotFoundError(
            "React build not found. Run these commands first:\n"
            "cd sample-react-app\n"
            "npm run build"
        )

    print("React build found.")
    print("Starting S3 deployment...")
    deploy_to_s3()


def create_release():
    """Upload the current React build as a separate release."""
    print("Starting release creation...")
    deploy_release()


def show_releases():
    """List releases stored in S3."""
    print("Checking stored deployment releases...")
    list_releases()


def rollback_application(release_id):
    """Restore a selected release from S3."""
    if not release_id:
        print("Please provide a release ID.")
        print("Run: deploy-tool releases")
        print("Then use: deploy-tool rollback RELEASE_ID")
        return

    print(f"Preparing to roll back to release: {release_id}")
    rollback_release(release_id)


def deploy_container_application(args):
    """Deploy a Dockerized website using explicit or saved settings."""
    config = load_config()

    project_path_value = args.project_path
    repository = args.repository or config.get("ecr_repository", "")
    cluster = args.cluster or config.get("ecs_cluster", "")
    service = args.service or config.get("ecs_service", "")
    region = args.region or config.get("region", "ap-south-1")

    if not project_path_value:
        raise ValueError(
            "Project path is required. Use --project-path PATH."
        )

    missing = []
    if not repository:
        missing.append("ECR repository")
    if not cluster:
        missing.append("ECS cluster")
    if not service:
        missing.append("ECS service")

    if missing:
        raise ValueError(
            "Missing deployment settings: "
            + ", ".join(missing)
            + ". Set them with 'deploy-tool config set KEY VALUE'."
        )

    project_path = Path(project_path_value).expanduser().resolve()

    if not project_path.is_dir():
        raise FileNotFoundError(
            f"Project folder does not exist: {project_path}"
        )

    if not (project_path / "Dockerfile").is_file():
        raise FileNotFoundError(
            f"No Dockerfile found in {project_path}. "
            "Provide a website folder containing a Dockerfile."
        )

    print("Starting container deployment...")
    print(f"Project path: {project_path}")
    print(f"ECR repository: {repository}")
    print(f"ECS cluster: {cluster}")
    print(f"ECS service: {service}")
    print(f"AWS region: {region}")

    deploy_container(
        project_path=str(project_path),
        repository=repository,
        cluster=cluster,
        service=service,
        region=region,
    )


def main():
    parser = argparse.ArgumentParser(
        prog="deploy-tool",
        description=(
            "Deploy React websites to S3 or Dockerized websites "
            "to AWS ECS Fargate."
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version="deploy-tool 0.1.0",
    )

    commands = parser.add_subparsers(dest="command")

    commands.add_parser(
        "init",
        help="Initialize the Capstone deployment project",
    )

    commands.add_parser(
        "deploy",
        help="Deploy the Capstone React application to S3",
    )

    container_parser = commands.add_parser(
        "deploy-container",
        help="Build and deploy a Dockerized website to ECS Fargate",
    )

    container_parser.add_argument(
        "--project-path",
        required=True,
        help="Website folder containing a Dockerfile",
    )

    container_parser.add_argument(
        "--repository",
        default=None,
        help="Existing ECR repository (defaults to saved config)",
    )

    container_parser.add_argument(
        "--cluster",
        default=None,
        help="Existing ECS cluster (defaults to saved config)",
    )

    container_parser.add_argument(
        "--service",
        default=None,
        help="Existing ECS service (defaults to saved config)",
    )

    container_parser.add_argument(
        "--region",
        default=None,
        help="AWS region (defaults to saved config)",
    )

    commands.add_parser(
        "status",
        help="Check S3 bucket accessibility",
    )

    commands.add_parser(
        "release",
        help="Create a versioned release in S3",
    )

    commands.add_parser(
        "releases",
        help="List stored releases in S3",
    )

    rollback_parser = commands.add_parser(
        "rollback",
        help="Restore a stored release to S3",
    )

    rollback_parser.add_argument(
        "release_id",
        nargs="?",
        default=None,
        help="Release ID to restore",
    )

    config_parser = commands.add_parser(
        "config",
        help="Manage deployment configuration",
    )

    config_parser.add_argument(
        "action",
        choices=["list", "set"],
        help="List or update configuration",
    )

    config_parser.add_argument(
        "key",
        nargs="?",
        help="Configuration key",
    )

    config_parser.add_argument(
        "value",
        nargs="?",
        help="New configuration value",
    )

    args = parser.parse_args()

    try:
        if args.command == "init":
            initialize_project()

        elif args.command == "deploy":
            deploy_application()

        elif args.command == "deploy-container":
            deploy_container_application(args)

        elif args.command == "status":
            show_status()

        elif args.command == "release":
            create_release()

        elif args.command == "releases":
            show_releases()

        elif args.command == "rollback":
            rollback_application(args.release_id)

        elif args.command == "config":
            if args.action == "list":
                if args.key or args.value:
                    parser.error("Usage: deploy-tool config list")
                show_config()

            elif args.action == "set":
                if not args.key or args.value is None:
                    parser.error(
                        "Usage: deploy-tool config set KEY VALUE"
                    )

                if args.key not in DEFAULT_CONFIG:
                    allowed = ", ".join(DEFAULT_CONFIG.keys())
                    parser.error(f"KEY must be one of: {allowed}")

                if not args.value.strip():
                    parser.error("VALUE cannot be empty")

                set_config(args.key, args.value)
                print(f"Configuration updated: {args.key}")

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
