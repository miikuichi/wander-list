"""
Test suite for expense validation and CRUD operations.
Run with: python manage.py test expenses.tests
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages import get_messages
from unittest.mock import patch, MagicMock
from expenses.views import CATEGORIES


class ExpenseValidationTestCase(TestCase):
    """Test expense form validation."""
    
    def setUp(self):
        """Set up test client and mock user session."""
        self.client = Client()
        # Create a session with user_id
        session = self.client.session
        session['user_id'] = 1
        session['username'] = 'testuser'
        session['email'] = 'test@example.com'
        session.save()
    
    @patch('expenses.views.get_service_client')
    def test_valid_expense_submission(self, mock_supabase):
        """Test that valid expense data is accepted."""
        # Mock Supabase response
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client
        
        response = self.client.post(reverse('expenses'), {
            'amount': '50.75',
            'category': 'Food',
            'date': '2025-10-15',
            'notes': 'Lunch at restaurant'
        })
        
        # Should redirect after successful submission
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('expenses'))
    
    def test_negative_amount_rejected(self):
        """Test that negative amounts are rejected."""
        response = self.client.post(reverse('expenses'), {
            'amount': '-50',
            'category': 'Food',
            'date': '2025-10-15',
            'notes': ''
        })
        
        # Should redirect back with error message
        self.assertEqual(response.status_code, 302)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('greater than zero' in str(m) for m in messages))
    
    def test_zero_amount_rejected(self):
        """Test that zero amount is rejected."""
        response = self.client.post(reverse('expenses'), {
            'amount': '0',
            'category': 'Food',
            'date': '2025-10-15',
            'notes': ''
        })
        
        self.assertEqual(response.status_code, 302)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('greater than zero' in str(m) for m in messages))
    
    def test_invalid_amount_format_rejected(self):
        """Test that non-numeric amounts are rejected."""
        response = self.client.post(reverse('expenses'), {
            'amount': 'abc',
            'category': 'Food',
            'date': '2025-10-15',
            'notes': ''
        })
        
        self.assertEqual(response.status_code, 302)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('valid number' in str(m) for m in messages))
    
    def test_amount_too_large_rejected(self):
        """Test that amounts exceeding maximum are rejected."""
        response = self.client.post(reverse('expenses'), {
            'amount': '9999999999',
            'category': 'Food',
            'date': '2025-10-15',
            'notes': ''
        })
        
        self.assertEqual(response.status_code, 302)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('too large' in str(m) for m in messages))
    
    def test_invalid_category_rejected(self):
        """Test that invalid categories are rejected."""
        response = self.client.post(reverse('expenses'), {
            'amount': '50',
            'category': 'InvalidCategory',
            'date': '2025-10-15',
            'notes': ''
        })
        
        self.assertEqual(response.status_code, 302)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('Invalid category' in str(m) for m in messages))
    
    def test_missing_required_fields(self):
        """Test that missing required fields are rejected."""
        # Missing amount
        response = self.client.post(reverse('expenses'), {
            'category': 'Food',
            'date': '2025-10-15',
            'notes': ''
        })
        
        self.assertEqual(response.status_code, 302)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('required' in str(m) for m in messages))
    
    def test_invalid_date_format_rejected(self):
        """Test that invalid date formats are rejected."""
        response = self.client.post(reverse('expenses'), {
            'amount': '50',
            'category': 'Food',
            'date': '15-10-2025',  # Wrong format
            'notes': ''
        })
        
        self.assertEqual(response.status_code, 302)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('Invalid date' in str(m) for m in messages))
    
    def test_unauthenticated_user_redirected(self):
        """Test that unauthenticated users are redirected to login."""
        # Clear session
        self.client.session.flush()
        
        response = self.client.get(reverse('expenses'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))
    
    @patch('expenses.views.get_service_client')
    def test_all_valid_categories_accepted(self, mock_supabase):
        """Test that all predefined categories are valid."""
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client
        
        for category in CATEGORIES:
            response = self.client.post(reverse('expenses'), {
                'amount': '25.50',
                'category': category,
                'date': '2025-10-15',
                'notes': f'Test for {category}'
            })
            
            # Should succeed for all valid categories
            self.assertEqual(response.status_code, 302)


class ExpenseFetchTestCase(TestCase):
    """Test expense fetching and display."""
    
    def setUp(self):
        """Set up test client and mock user session."""
        self.client = Client()
        session = self.client.session
        session['user_id'] = 1
        session['username'] = 'testuser'
        session['email'] = 'test@example.com'
        session.save()
    
    @patch('expenses.views.get_service_client')
    def test_expense_list_fetched(self, mock_supabase):
        """Test that expenses are fetched from Supabase."""
        # Mock Supabase response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                'id': 1,
                'user_id': 1,
                'amount': 50.00,
                'category': 'Food',
                'date': '2025-10-15',
                'notes': 'Lunch'
            }
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client
        
        response = self.client.get(reverse('expenses'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('recent_expenses', response.context)
        self.assertEqual(len(response.context['recent_expenses']), 1)
    
    @patch('expenses.views.get_service_client')
    def test_categories_passed_to_template(self, mock_supabase):
        """Test that categories are available in template context."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client
        
        response = self.client.get(reverse('expenses'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('categories', response.context)
        self.assertEqual(response.context['categories'], CATEGORIES)
    
    @patch('expenses.views.get_service_client')
    def test_edit_expense_get(self, mock_supabase):
        """Test fetching expense data for editing (GET request)."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = {
            'id': 1,
            'user_id': 1,
            'amount': 500.00,
            'category': 'Food',
            'date': '2024-01-15',
            'notes': 'Test expense'
        }
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_response
        mock_supabase.return_value = mock_client
        
        response = self.client.get(reverse('edit_expense', args=[1]))
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['amount'], 500.00)
        self.assertEqual(response_data['category'], 'Food')
    
    @patch('expenses.views.get_service_client')
    def test_edit_expense_post_valid(self, mock_supabase):
        """Test updating an expense with valid data."""
        mock_client = MagicMock()
        
        # Mock verification query
        mock_verify = MagicMock()
        mock_verify.data = [{'id': 1}]
        
        # Mock update query
        mock_update = MagicMock()
        
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_verify
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_update
        mock_supabase.return_value = mock_client
        
        response = self.client.post(reverse('edit_expense', args=[1]), {
            'amount': '750.50',
            'category': 'Transport',
            'date': '2024-01-20',
            'notes': 'Updated expense'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('expenses'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('updated successfully' in str(m) for m in messages))
    
    @patch('expenses.views.get_service_client')
    def test_edit_expense_unauthorized(self, mock_supabase):
        """Test that users cannot edit expenses they don't own."""
        mock_client = MagicMock()
        mock_verify = MagicMock()
        mock_verify.data = []  # No expense found
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_verify
        mock_supabase.return_value = mock_client
        
        response = self.client.post(reverse('edit_expense', args=[999]), {
            'amount': '100.00',
            'category': 'Food',
            'date': '2024-01-20',
            'notes': ''
        })
        
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("don't have permission" in str(m) for m in messages))
    
    def test_edit_expense_validation_negative(self):
        """Test that edit expense validates negative amounts."""
        response = self.client.post(reverse('edit_expense', args=[1]), {
            'amount': '-50.00',
            'category': 'Food',
            'date': '2024-01-20',
            'notes': ''
        })
        
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('greater than zero' in str(m) for m in messages))
    
    def test_edit_expense_validation_invalid_category(self):
        """Test that edit expense validates category."""
        response = self.client.post(reverse('edit_expense', args=[1]), {
            'amount': '50.00',
            'category': 'InvalidCategory',
            'date': '2024-01-20',
            'notes': ''
        })
        
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid category' in str(m) for m in messages))
    
    @patch('expenses.views.get_service_client')
    def test_delete_expense_valid(self, mock_supabase):
        """Test deleting an expense successfully."""
        mock_client = MagicMock()
        
        # Mock verification query
        mock_verify = MagicMock()
        mock_verify.data = [{
            'id': 1,
            'amount': 500.00,
            'category': 'Food'
        }]
        
        # Mock delete query
        mock_delete = MagicMock()
        
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_verify
        mock_client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = mock_delete
        mock_supabase.return_value = mock_client
        
        response = self.client.post(reverse('delete_expense', args=[1]))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('expenses'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('deleted successfully' in str(m) for m in messages))
    
    @patch('expenses.views.get_service_client')
    def test_delete_expense_unauthorized(self, mock_supabase):
        """Test that users cannot delete expenses they don't own."""
        mock_client = MagicMock()
        mock_verify = MagicMock()
        mock_verify.data = []  # No expense found
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_verify
        mock_supabase.return_value = mock_client
        
        response = self.client.post(reverse('delete_expense', args=[999]))
        
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("don't have permission" in str(m) for m in messages))
    
    def test_delete_expense_get_request_rejected(self):
        """Test that GET requests to delete are rejected."""
        response = self.client.get(reverse('delete_expense', args=[1]))
        
        # Should redirect without deleting
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('expenses'))
