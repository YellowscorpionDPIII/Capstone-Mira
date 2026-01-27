"""
Tests for deployment scripts and configurations.
"""
import os
import json
import subprocess
import unittest
from pathlib import Path


class TestDeploymentConfiguration(unittest.TestCase):
    """Test deployment scripts and configuration files."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent
        self.deploy_script = self.project_root / "deploy_gcp.sh"
        self.k8s_config = self.project_root / "k8s-hpa-config.yaml"
        self.cloudrun_config = self.project_root / "cloudrun-config.yaml"
        self.locustfile = self.project_root / "locustfile.py"
        self.workflows_dir = self.project_root / "workflows"
    
    def test_deploy_script_exists(self):
        """Test that deployment script exists and is executable."""
        self.assertTrue(self.deploy_script.exists(), "deploy_gcp.sh should exist")
        self.assertTrue(os.access(self.deploy_script, os.X_OK), "deploy_gcp.sh should be executable")
    
    def test_deploy_script_syntax(self):
        """Test that deployment script has valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", str(self.deploy_script)],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, f"Bash syntax error: {result.stderr}")
    
    def test_deploy_script_contains_secret_rotation(self):
        """Test that deployment script includes secret rotation functionality."""
        with open(self.deploy_script, 'r') as f:
            content = f.read()
        
        self.assertIn("gcloud secrets versions access", content, 
                     "Script should use gcloud secrets versions access")
        self.assertIn("rotate_secret", content,
                     "Script should have rotate_secret function")
    
    def test_deploy_script_contains_rollback(self):
        """Test that deployment script includes rollback functionality."""
        with open(self.deploy_script, 'r') as f:
            content = f.read()
        
        self.assertIn("rollback", content,
                     "Script should include rollback functionality")
        self.assertIn("gcloud run services update", content,
                     "Script should use gcloud run services update for rollback")
        self.assertIn("--image", content,
                     "Script should support image updates")
    
    def test_deploy_script_contains_compliance_scan(self):
        """Test that deployment script includes compliance scanning."""
        with open(self.deploy_script, 'r') as f:
            content = f.read()
        
        self.assertIn("run_compliance_scan", content,
                     "Script should have compliance scanning function")
        self.assertIn("governance/risk_assessor.py", content,
                     "Script should reference Risk Assessor")
    
    def test_k8s_hpa_config_exists(self):
        """Test that Kubernetes HPA configuration exists."""
        self.assertTrue(self.k8s_config.exists(), "k8s-hpa-config.yaml should exist")
    
    def test_k8s_hpa_config_structure(self):
        """Test that Kubernetes HPA configuration has correct structure."""
        with open(self.k8s_config, 'r') as f:
            content = f.read()
        
        # Check for required HPA parameters
        self.assertIn("minReplicas: 2", content,
                     "HPA should have minReplicas: 2")
        self.assertIn("maxReplicas: 10", content,
                     "HPA should have maxReplicas: 10")
        self.assertIn("HorizontalPodAutoscaler", content,
                     "Should define HorizontalPodAutoscaler")
    
    def test_cloudrun_config_exists(self):
        """Test that Cloud Run configuration exists."""
        self.assertTrue(self.cloudrun_config.exists(), "cloudrun-config.yaml should exist")
    
    def test_cloudrun_config_structure(self):
        """Test that Cloud Run configuration has correct parameters."""
        with open(self.cloudrun_config, 'r') as f:
            content = f.read()
        
        self.assertIn('minScale: "2"', content,
                     "Cloud Run should have minScale: 2")
        self.assertIn('maxScale: "10"', content,
                     "Cloud Run should have maxScale: 10")
        self.assertIn("containerConcurrency: 80", content,
                     "Cloud Run should have concurrency: 80")
    
    def test_locustfile_exists(self):
        """Test that Locust performance testing file exists."""
        self.assertTrue(self.locustfile.exists(), "locustfile.py should exist")
    
    def test_locustfile_syntax(self):
        """Test that Locust file has valid Python syntax."""
        try:
            with open(self.locustfile, 'r') as f:
                compile(f.read(), str(self.locustfile), 'exec')
        except SyntaxError as e:
            self.fail(f"Locustfile has syntax error: {e}")
    
    def test_locustfile_contains_required_classes(self):
        """Test that Locust file contains required user classes."""
        with open(self.locustfile, 'r') as f:
            content = f.read()
        
        self.assertIn("class MiraUser", content,
                     "Locustfile should define MiraUser class")
        self.assertIn("class HighVolumeUser", content,
                     "Locustfile should define HighVolumeUser class")
        self.assertIn("class RevenueTargetShape", content,
                     "Locustfile should define RevenueTargetShape class")
    
    def test_locustfile_targets_correct_throughput(self):
        """Test that Locust file targets 1000+ requests/min."""
        with open(self.locustfile, 'r') as f:
            content = f.read()
        
        # Check for throughput target documentation
        self.assertIn("1,000+ requests/min", content,
                     "Locustfile should document 1000+ req/min target")
    
    def test_locustfile_revenue_simulation(self):
        """Test that Locust file includes revenue range simulation."""
        with open(self.locustfile, 'r') as f:
            content = f.read()
        
        self.assertIn("$50k", content,
                     "Locustfile should include $50k revenue simulation")
        self.assertIn("$5M", content,
                     "Locustfile should include $5M revenue simulation")
    
    def test_workflows_directory_exists(self):
        """Test that workflows directory exists."""
        self.assertTrue(self.workflows_dir.exists(), "workflows directory should exist")
        self.assertTrue(self.workflows_dir.is_dir(), "workflows should be a directory")
    
    def test_sample_workflow_exists(self):
        """Test that at least one sample workflow exists."""
        workflow_files = list(self.workflows_dir.glob("*.json"))
        self.assertGreater(len(workflow_files), 0, 
                          "workflows directory should contain at least one JSON workflow")
    
    def test_workflow_json_valid(self):
        """Test that workflow JSON files are valid."""
        workflow_files = list(self.workflows_dir.glob("*.json"))
        
        for workflow_file in workflow_files:
            with open(workflow_file, 'r') as f:
                try:
                    workflow_data = json.load(f)
                    self.assertIn("name", workflow_data,
                                f"{workflow_file.name} should have 'name' field")
                    self.assertIn("nodes", workflow_data,
                                f"{workflow_file.name} should have 'nodes' field")
                    self.assertIn("connections", workflow_data,
                                f"{workflow_file.name} should have 'connections' field")
                except json.JSONDecodeError as e:
                    self.fail(f"{workflow_file.name} has invalid JSON: {e}")


class TestDeploymentScriptFunctions(unittest.TestCase):
    """Test deployment script function signatures."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent
        self.deploy_script = self.project_root / "deploy_gcp.sh"
        
        with open(self.deploy_script, 'r') as f:
            self.script_content = f.read()
    
    def test_has_log_function(self):
        """Test that script has logging functions."""
        self.assertIn("log()", self.script_content)
        self.assertIn("log_error()", self.script_content)
        self.assertIn("log_warning()", self.script_content)
    
    def test_has_rotate_secret_function(self):
        """Test that script has rotate_secret function."""
        self.assertIn("rotate_secret()", self.script_content)
    
    def test_has_rollback_function(self):
        """Test that script has rollback_service function."""
        self.assertIn("rollback_service()", self.script_content)
    
    def test_has_deploy_function(self):
        """Test that script has deploy_to_cloud_run function."""
        self.assertIn("deploy_to_cloud_run()", self.script_content)
    
    def test_has_compliance_scan_function(self):
        """Test that script has run_compliance_scan function."""
        self.assertIn("run_compliance_scan()", self.script_content)
    
    def test_has_error_handling(self):
        """Test that script includes error handling."""
        self.assertIn("set -e", self.script_content,
                     "Script should exit on error")
        self.assertIn("if [ $? -eq 0 ]", self.script_content,
                     "Script should check command exit codes")
    
    def test_has_usage_documentation(self):
        """Test that script has usage documentation."""
        self.assertIn("Usage:", self.script_content,
                     "Script should document usage")


if __name__ == '__main__':
    unittest.main()
