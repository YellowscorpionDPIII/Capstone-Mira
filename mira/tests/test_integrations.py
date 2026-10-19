"""Tests for integration adapters."""
import unittest
from mira.integrations.trello_integration import TrelloIntegration
from mira.integrations.jira_integration import JiraIntegration
from mira.integrations.github_integration import GitHubIntegration
from mira.integrations.airtable_integration import AirtableIntegration
from mira.integrations.google_docs_integration import GoogleDocsIntegration
from mira.integrations.pdf_integration import PDFIntegration


class TestTrelloIntegration(unittest.TestCase):
    """Test cases for Trello integration."""
    
    def test_connect_with_valid_config(self):
        """Test connection with valid configuration."""
        integration = TrelloIntegration({
            'api_key': 'test_key',
            'api_token': 'test_token',
            'board_id': 'test_board'
        })
        
        self.assertTrue(integration.connect())
        self.assertTrue(integration.connected)
        
    def test_connect_without_config(self):
        """Test connection fails without configuration."""
        integration = TrelloIntegration()
        self.assertFalse(integration.connect())
        
    def test_sync_tasks(self):
        """Test syncing tasks."""
        integration = TrelloIntegration({
            'api_key': 'test_key',
            'api_token': 'test_token',
            'board_id': 'test_board'
        })
        integration.connect()
        
        tasks = [
            {'id': 'T1', 'name': 'Task 1'},
            {'id': 'T2', 'name': 'Task 2'}
        ]
        
        result = integration.sync_data('tasks', tasks)
        self.assertTrue(result['success'])
        self.assertEqual(result['synced_count'], 2)


class TestJiraIntegration(unittest.TestCase):
    """Test cases for Jira integration."""
    
    def test_connect_with_valid_config(self):
        """Test connection with valid configuration."""
        integration = JiraIntegration({
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'api_token': 'test_token',
            'project_key': 'TEST'
        })
        
        self.assertTrue(integration.connect())
        
    def test_sync_issues(self):
        """Test syncing issues."""
        integration = JiraIntegration({
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'api_token': 'test_token',
            'project_key': 'TEST'
        })
        integration.connect()
        
        issues = [
            {'id': 'I1', 'title': 'Issue 1'},
            {'id': 'I2', 'title': 'Issue 2'}
        ]
        
        result = integration.sync_data('issues', issues)
        self.assertTrue(result['success'])


class TestGitHubIntegration(unittest.TestCase):
    """Test cases for GitHub integration."""
    
    def test_connect_with_valid_config(self):
        """Test connection with valid configuration."""
        integration = GitHubIntegration({
            'token': 'test_token',
            'repository': 'user/repo'
        })
        
        self.assertTrue(integration.connect())
        
    def test_sync_milestones(self):
        """Test syncing milestones."""
        integration = GitHubIntegration({
            'token': 'test_token',
            'repository': 'user/repo'
        })
        integration.connect()
        
        milestones = [
            {'id': 'M1', 'name': 'Milestone 1'},
            {'id': 'M2', 'name': 'Milestone 2'}
        ]
        
        result = integration.sync_data('milestones', milestones)
        self.assertTrue(result['success'])


class TestAirtableIntegration(unittest.TestCase):
    """Test cases for Airtable integration."""
    
    def test_connect_with_valid_config(self):
        """Test connection with valid configuration."""
        integration = AirtableIntegration({
            'api_key': 'test_key',
            'base_id': 'test_base'
        })
        
        self.assertTrue(integration.connect())
        
    def test_sync_records(self):
        """Test syncing records."""
        integration = AirtableIntegration({
            'api_key': 'test_key',
            'base_id': 'test_base'
        })
        integration.connect()
        
        records = [
            {'id': 'R1', 'data': 'Record 1'},
            {'id': 'R2', 'data': 'Record 2'}
        ]
        
        result = integration.sync_data('records', records)
        self.assertTrue(result['success'])
    
    def test_get_kpis(self):
        """Test getting KPI data for an initiative."""
        integration = AirtableIntegration({
            'api_key': 'test_key',
            'base_id': 'test_base'
        })
        integration.connect()
        
        result = integration.get_kpis('INIT-001')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['initiative_id'], 'INIT-001')
        self.assertIn('ebit_pct', result)
        self.assertIn('revenue_change', result)
        self.assertIn('cost_reduction', result)
        
    def test_get_kpis_not_connected(self):
        """Test getting KPI data when not connected."""
        integration = AirtableIntegration({
            'api_key': 'test_key',
            'base_id': 'test_base'
        })
        
        result = integration.get_kpis('INIT-001')
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)


class TestGoogleDocsIntegration(unittest.TestCase):
    """Test cases for Google Docs integration."""
    
    def test_connect_with_valid_config(self):
        """Test connection with valid configuration."""
        integration = GoogleDocsIntegration({
            'credentials_path': '/path/to/credentials.json'
        })
        
        self.assertTrue(integration.connect())
        
    def test_create_document(self):
        """Test document creation."""
        integration = GoogleDocsIntegration({
            'credentials_path': '/path/to/credentials.json'
        })
        integration.connect()
        
        doc_data = {
            'title': 'Test Document',
            'content': 'This is test content'
        }
        
        result = integration.sync_data('document', doc_data)
        self.assertTrue(result['success'])
        self.assertIn('document_id', result)


class TestPDFIntegration(unittest.TestCase):
    """Test cases for PDF integration."""
    
    def test_connect(self):
        """Test connection."""
        integration = PDFIntegration()
        self.assertTrue(integration.connect())
        
    def test_read_pdf_missing_file(self):
        """Test reading non-existent PDF."""
        integration = PDFIntegration()
        integration.connect()
        
        result = integration.sync_data('read', {
            'file_path': '/nonexistent/file.pdf'
        })
        
        self.assertFalse(result['success'])


if __name__ == '__main__':
    unittest.main()
