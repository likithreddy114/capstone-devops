
import argparse
import sys
from pathlib import Path

from deploy_tool.config import set_config, show_config
from deploy_tool.aws_deploy import (
    check_bucket,
    deploy_to_s3,
    deploy_release,
    list_releases,
    rollback_release,
)


def get_project_root():
    """Find the folder containing the project directories."""
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
    """Upload the built React application to S3."""
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
    """Restore the selected stored release to the S3 bucket."""
    if not release_id:
        print("Please provide a release ID.")
        print("Run: deploy-tool releases")
        print("Then use: deploy-tool rollback RELEASE_ID")
        return

    print(f"Preparing to roll back to release: {release_id}")
    rollback_release(release_id)


def main():
    parser = argparse.ArgumentParser(
        prog="deploy-tool",
        description=(
            "CLI tool for deploying React applications to AWS S3."
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
        help="Initialize the deployment project",
    )

    commands.add_parser(
        "deploy",
        help="Deploy the built React application to S3",
    )

    commands.add_parser(
        "status",
        help="Check S3 bucket accessibility",
    )

    commands.add_parser(
        "release",
        help="Create a new versioned release in S3",
    )

    commands.add_parser(
        "releases",
        help="List stored deployment releases in S3",
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
        help="Configuration key: region, bucket, or environment",
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

                allowed_keys = {
                    "region",
                    "bucket",
                    "environment",
                }

                if args.key not in allowed_keys:
                    parser.error(
                        "KEY must be region, bucket, or environment"
                    )

                if not args.value.strip():
                    parser.error("VALUE cannot be empty")

                set_config(args.key, args.value)
                print(f"Configuration updated: {args.key}")

        else:
            parser.print_help()

    except (ValueError, OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
