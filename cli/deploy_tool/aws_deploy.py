import json
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, BotoCoreError


def get_config():
    """Load deployment settings."""
    config_path = Path.home() / ".deploy-tool" / "config.json"

    if not config_path.exists():
        raise FileNotFoundError(
            "Configuration not found. Run deploy-tool config first."
        )

    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_s3_client():
    """Create an S3 client using the configured AWS region."""
    config = get_config()
    return boto3.client("s3", region_name=config["region"])


def get_project_root():
    """Find the project root from the current directory or its parents."""
    current = Path.cwd().resolve()

    for directory in [current, *current.parents]:
        if (directory / "sample-react-app").is_dir():
            return directory

    raise FileNotFoundError(
        "Project root not found. Make sure sample-react-app exists."
    )


def get_build_dir():
    """Return the React production build directory."""
    return get_project_root() / "sample-react-app" / "dist"


def check_bucket():
    """Check whether the configured S3 bucket is accessible."""
    config = get_config()
    s3 = get_s3_client()

    try:
        s3.head_bucket(Bucket=config["bucket"])
        print(f"Success: S3 bucket '{config['bucket']}' exists.")
        return True

    except (ClientError, BotoCoreError) as error:
        print(f"Unable to access the bucket: {error}")
        return False


def deploy_to_s3():
    """Upload the React production build to the S3 bucket root."""
    config = get_config()
    s3 = get_s3_client()
    build_dir = get_build_dir()

    if not build_dir.is_dir() or not (build_dir / "index.html").is_file():
        raise FileNotFoundError(
            "React build not found. Run npm run build inside "
            "sample-react-app first."
        )

    print("Starting S3 deployment...")
    uploaded = 0

    for file_path in build_dir.rglob("*"):
        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(build_dir).as_posix()
        content_type, _ = mimetypes.guess_type(str(file_path))
        extra_args = {}

        if content_type:
            extra_args["ContentType"] = content_type

        s3.upload_file(
            str(file_path),
            config["bucket"],
            relative_path,
            ExtraArgs=extra_args,
        )

        print(f"Uploaded: {relative_path}")
        uploaded += 1

    print(f"Deployment successful! Uploaded {uploaded} files.")
    print("Note: CloudFront caching may delay visible changes.")


def deploy_release():
    """Upload the React build to a uniquely named S3 release folder."""
    config = get_config()
    s3 = get_s3_client()
    build_dir = get_build_dir()

    if not build_dir.is_dir() or not (build_dir / "index.html").is_file():
        raise FileNotFoundError(
            "React build not found. Run npm run build first."
        )

    release_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    prefix = f"releases/{release_id}/"

    print(f"Creating release: {release_id}")
    uploaded = 0

    for file_path in build_dir.rglob("*"):
        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(build_dir).as_posix()
        s3_key = prefix + relative_path
        content_type, _ = mimetypes.guess_type(str(file_path))
        extra_args = {}

        if content_type:
            extra_args["ContentType"] = content_type

        s3.upload_file(
            str(file_path),
            config["bucket"],
            s3_key,
            ExtraArgs=extra_args,
        )

        print(f"Uploaded: {s3_key}")
        uploaded += 1

    print(f"Release {release_id} uploaded successfully.")
    print(f"Files uploaded: {uploaded}")
    print("This stores a release; it does not switch the live website.")


def check_deployment_status():
    """Show the number of objects in the S3 bucket."""
    config = get_config()
    s3 = get_s3_client()

    try:
        paginator = s3.get_paginator("list_objects_v2")
        count = 0

        for page in paginator.paginate(Bucket=config["bucket"]):
            count += len(page.get("Contents", []))

        print(f"Bucket: {config['bucket']}")
        print(f"Total objects in bucket: {count}")

    except (ClientError, BotoCoreError) as error:
        raise RuntimeError(
            f"Unable to check deployment status: {error}"
        ) from error


def check_website_health():
    """Check whether index.html exists at the bucket root."""
    config = get_config()
    s3 = get_s3_client()

    try:
        s3.head_object(
            Bucket=config["bucket"],
            Key="index.html",
        )
        print("Health check passed: index.html exists in S3.")
        return True

    except (ClientError, BotoCoreError) as error:
        print(f"Health check failed: {error}")
        return False


def list_releases():
    """List release IDs stored under releases/ in S3."""
    config = get_config()
    s3 = get_s3_client()
    releases = set()

    try:
        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(
            Bucket=config["bucket"],
            Prefix="releases/",
        ):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                parts = key.split("/")

                if len(parts) >= 3 and parts[1]:
                    releases.add(parts[1])

    except (ClientError, BotoCoreError) as error:
        raise RuntimeError(
            f"Could not list releases from S3: {error}"
        ) from error

    release_list = sorted(releases, reverse=True)

    if release_list:
        print("Stored deployment releases:")
        for release in release_list:
            print(f"- {release}")
    else:
        print("No releases found under the S3 releases/ prefix.")
        print("Create a release before listing releases.")

    return release_list


def rollback_release(release_id):
    """Restore a selected release to the S3 bucket root."""

    # Validate the release ID before using it in an S3 path.
    if not re.fullmatch(r"\d{8}-\d{6}", release_id or ""):
        print("Error: Invalid release ID format.")
        print("Expected format: YYYYMMDD-HHMMSS")
        return False

    config = get_config()
    s3 = get_s3_client()
    bucket = config["bucket"]

    # Verify that the requested release exists.
    available_releases = list_releases()

    if release_id not in available_releases:
        print(f"Error: Release '{release_id}' was not found.")
        return False

    prefix = f"releases/{release_id}/"
    release_objects = []

    try:
        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(
            Bucket=bucket,
            Prefix=prefix,
        ):
            for obj in page.get("Contents", []):
                source_key = obj["Key"]
                relative_key = source_key[len(prefix):]

                if relative_key:
                    release_objects.append((source_key, relative_key))

        # Refuse to restore a release without its entry point.
        if not any(
            destination_key == "index.html"
            for _, destination_key in release_objects
        ):
            print("Error: This release does not contain index.html.")
            return False

        print(f"Selected release: {release_id}")
        print(f"Files to restore: {len(release_objects)}")
        print("WARNING: Matching live S3 files will be overwritten.")
        print("Files absent from this release will NOT be deleted.")
        print("CloudFront caching may delay visible changes.")

        confirmation = input(
            "Type YES to confirm rollback: "
        )

        if confirmation != "YES":
            print("Rollback cancelled. No files were changed.")
            return False

        # Copy each release object to the live bucket root.
        for source_key, destination_key in release_objects:
            s3.copy_object(
                Bucket=bucket,
                Key=destination_key,
                CopySource={
                    "Bucket": bucket,
                    "Key": source_key,
                },
                MetadataDirective="COPY",
            )

            print(f"Restored: {destination_key}")

        print(f"Rollback copy completed for release {release_id}.")
        print("Check the website to verify the restored version.")
        print("CloudFront invalidation is not performed automatically.")

        return True

    except (ClientError, BotoCoreError) as error:
        raise RuntimeError(
            f"Rollback failed: {error}"
        ) from error