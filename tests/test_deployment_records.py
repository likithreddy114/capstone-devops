
import tempfile
import unittest
from pathlib import Path

from cli.deploy_tool import ecs_deploy


class DeploymentRecordTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_dir = ecs_deploy.DEPLOYMENTS_DIR
        ecs_deploy.DEPLOYMENTS_DIR = Path(self.temp_dir.name)

        self.record = {
            "app_name": "test-website",
            "cluster": "test-cluster",
            "service": "custom-test-service",
            "repository": "custom-test-repository",
            "region": "ap-south-1",
            "task_family": "test-website-task",
            "account_id": "123456789012",
        }

    def tearDown(self):
        ecs_deploy.DEPLOYMENTS_DIR = self.original_dir
        self.temp_dir.cleanup()

    def test_save_and_load_record(self):
        ecs_deploy._save_deployment_record(self.record)

        loaded = ecs_deploy._load_deployment_record(
            "test-website"
        )

        self.assertEqual(loaded, self.record)

    def test_remove_record(self):
        ecs_deploy._save_deployment_record(self.record)

        ecs_deploy._remove_deployment_record(
            "test-website"
        )

        loaded = ecs_deploy._load_deployment_record(
            "test-website"
        )

        self.assertEqual(loaded, {})

    def test_missing_record_returns_empty_dictionary(self):
        loaded = ecs_deploy._load_deployment_record(
            "missing-website"
        )

        self.assertEqual(loaded, {})

    def test_incorrect_ownership_is_rejected(self):
        incorrect_tags = {
            "ManagedBy": "another-tool",
            "Application": "test-website",
        }

        with self.assertRaises(RuntimeError):
            ecs_deploy._require_owned(
                incorrect_tags,
                "test-website",
                "test ECR repository",
            )

    def test_correct_ownership_is_accepted(self):
        correct_tags = {
            "ManagedBy": "deploy-tool",
            "Application": "test-website",
        }

        result = ecs_deploy._require_owned(
            correct_tags,
            "test-website",
            "test ECR repository",
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
