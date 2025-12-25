"""
Integration tests for Invoicing views.
"""

import pytest
import json
from decimal import Decimal
from django.test import Client
from django.utils import timezone

from invoicing.models import Invoice, InvoiceLine, InvoiceSeries, InvoicingConfig


@pytest.fixture
def client():
    """Create test client."""
    return Client()


@pytest.fixture
def series():
    """Create a default invoice series."""
    return InvoiceSeries.objects.create(
        prefix='F',
        name='Facturas',
        is_default=True,
        number_digits=6
    )


@pytest.fixture
def sample_invoice(series):
    """Create a sample invoice."""
    return Invoice.objects.create(
        series=series,
        customer_name='Test Customer',
        customer_tax_id='12345678Z',
        customer_address='Test Address',
        subtotal=Decimal('100.00'),
        tax_rate=Decimal('21.00'),
        tax_amount=Decimal('21.00'),
        total=Decimal('121.00'),
        status=Invoice.Status.ISSUED,
        number='F000001'
    )


@pytest.mark.django_db
class TestDashboardView:
    """Tests for invoicing dashboard."""

    def test_dashboard_get(self, client):
        """Test GET dashboard page."""
        response = client.get('/modules/invoicing/')

        assert response.status_code == 200

    def test_dashboard_htmx(self, client):
        """Test HTMX dashboard request."""
        response = client.get(
            '/modules/invoicing/',
            HTTP_HX_REQUEST='true'
        )

        assert response.status_code == 200


@pytest.mark.django_db
class TestInvoicesListView:
    """Tests for invoices list view."""

    def test_invoices_list_get(self, client):
        """Test GET invoices list."""
        response = client.get('/modules/invoicing/invoices/')

        assert response.status_code == 200

    def test_invoices_list_htmx(self, client):
        """Test HTMX invoices list request."""
        response = client.get(
            '/modules/invoicing/invoices/',
            HTTP_HX_REQUEST='true'
        )

        assert response.status_code == 200

    def test_invoices_list_with_invoices(self, client, sample_invoice):
        """Test list with existing invoices."""
        response = client.get('/modules/invoicing/invoices/')

        assert response.status_code == 200


@pytest.mark.django_db
class TestInvoicesListAjax:
    """Tests for invoices list AJAX API."""

    def test_list_ajax_empty(self, client):
        """Test AJAX list when empty."""
        response = client.get('/modules/invoicing/api/invoices/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['invoices'] == []

    def test_list_ajax_with_invoices(self, client, sample_invoice):
        """Test AJAX list with invoices."""
        response = client.get('/modules/invoicing/api/invoices/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert len(data['invoices']) == 1

    def test_list_ajax_search(self, client, sample_invoice):
        """Test AJAX list with search."""
        response = client.get('/modules/invoicing/api/invoices/?search=Test')

        data = json.loads(response.content)
        assert len(data['invoices']) == 1

        response = client.get('/modules/invoicing/api/invoices/?search=NotFound')
        data = json.loads(response.content)
        assert len(data['invoices']) == 0

    def test_list_ajax_filter_status(self, client, sample_invoice):
        """Test AJAX list filter by status."""
        response = client.get('/modules/invoicing/api/invoices/?status=issued')

        data = json.loads(response.content)
        assert len(data['invoices']) == 1

        response = client.get('/modules/invoicing/api/invoices/?status=draft')
        data = json.loads(response.content)
        assert len(data['invoices']) == 0


@pytest.mark.django_db
class TestInvoiceDetailView:
    """Tests for invoice detail view."""

    def test_detail_view(self, client, sample_invoice):
        """Test GET invoice detail."""
        response = client.get(f'/modules/invoicing/invoices/{sample_invoice.id}/')

        assert response.status_code == 200

    def test_detail_view_not_found(self, client):
        """Test GET invoice not found."""
        response = client.get('/modules/invoicing/invoices/99999/')

        assert response.status_code == 404

    def test_detail_view_htmx(self, client, sample_invoice):
        """Test HTMX detail request."""
        response = client.get(
            f'/modules/invoicing/invoices/{sample_invoice.id}/',
            HTTP_HX_REQUEST='true'
        )

        assert response.status_code == 200


@pytest.mark.django_db
class TestInvoiceCreateView:
    """Tests for invoice create view."""

    def test_create_get_form(self, client, series):
        """Test GET create form."""
        response = client.get('/modules/invoicing/invoices/create/')

        assert response.status_code == 200

    def test_create_invoice_success(self, client, series):
        """Test POST create invoice."""
        response = client.post(
            '/modules/invoicing/invoices/create/',
            data=json.dumps({
                'customer_name': 'New Customer',
                'customer_tax_id': '87654321X',
                'lines': [
                    {
                        'description': 'Product 1',
                        'quantity': 2,
                        'unit_price': 50.00
                    }
                ]
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'invoice_id' in data


@pytest.mark.django_db
class TestInvoiceIssueView:
    """Tests for invoice issue view."""

    def test_issue_draft_invoice(self, client, series):
        """Test issuing a draft invoice."""
        invoice = Invoice.objects.create(
            series=series,
            customer_name='Test',
            status=Invoice.Status.DRAFT
        )

        response = client.post(f'/modules/invoicing/invoices/{invoice.id}/issue/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

        invoice.refresh_from_db()
        assert invoice.status == Invoice.Status.ISSUED
        assert invoice.number != ''

    def test_issue_non_draft_fails(self, client, sample_invoice):
        """Test issuing non-draft invoice fails."""
        response = client.post(f'/modules/invoicing/invoices/{sample_invoice.id}/issue/')

        data = json.loads(response.content)
        assert data['success'] is False


@pytest.mark.django_db
class TestInvoiceCancelView:
    """Tests for invoice cancel view."""

    def test_cancel_invoice(self, client, sample_invoice):
        """Test cancelling an invoice."""
        response = client.post(f'/modules/invoicing/invoices/{sample_invoice.id}/cancel/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

        sample_invoice.refresh_from_db()
        assert sample_invoice.status == Invoice.Status.CANCELLED

    def test_cancel_already_cancelled(self, client, series):
        """Test cancelling already cancelled invoice fails."""
        invoice = Invoice.objects.create(
            series=series,
            customer_name='Test',
            status=Invoice.Status.CANCELLED
        )

        response = client.post(f'/modules/invoicing/invoices/{invoice.id}/cancel/')

        data = json.loads(response.content)
        assert data['success'] is False


@pytest.mark.django_db
class TestInvoicePrintView:
    """Tests for invoice print view."""

    def test_print_view(self, client, sample_invoice):
        """Test GET printable invoice."""
        response = client.get(f'/modules/invoicing/invoices/{sample_invoice.id}/print/')

        assert response.status_code == 200


@pytest.mark.django_db
class TestSeriesListView:
    """Tests for series list view."""

    def test_series_list_get(self, client, series):
        """Test GET series list."""
        response = client.get('/modules/invoicing/series/')

        assert response.status_code == 200


@pytest.mark.django_db
class TestSeriesCreateView:
    """Tests for series create view."""

    def test_create_get_form(self, client):
        """Test GET create form."""
        response = client.get('/modules/invoicing/series/create/')

        assert response.status_code == 200

    def test_create_series_success(self, client):
        """Test POST create series."""
        response = client.post('/modules/invoicing/series/create/', {
            'prefix': 'R',
            'name': 'Rectificativas',
            'description': 'Facturas rectificativas',
            'number_digits': 6
        })

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

        assert InvoiceSeries.objects.filter(prefix='R').exists()

    def test_create_series_no_prefix(self, client):
        """Test POST create series without prefix fails."""
        response = client.post('/modules/invoicing/series/create/', {
            'name': 'Test'
        })

        data = json.loads(response.content)
        assert data['success'] is False

    def test_create_series_duplicate_prefix(self, client, series):
        """Test POST create series with duplicate prefix fails."""
        response = client.post('/modules/invoicing/series/create/', {
            'prefix': 'F',
            'name': 'Duplicate'
        })

        data = json.loads(response.content)
        assert data['success'] is False


@pytest.mark.django_db
class TestSeriesEditView:
    """Tests for series edit view."""

    def test_edit_get_form(self, client, series):
        """Test GET edit form."""
        response = client.get(f'/modules/invoicing/series/{series.id}/edit/')

        assert response.status_code == 200

    def test_edit_series_success(self, client, series):
        """Test POST edit series."""
        response = client.post(f'/modules/invoicing/series/{series.id}/edit/', {
            'name': 'Updated Name',
            'description': 'Updated description',
            'number_digits': 8,
            'is_active': 'on'
        })

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

        series.refresh_from_db()
        assert series.name == 'Updated Name'


@pytest.mark.django_db
class TestSeriesDeleteView:
    """Tests for series delete view."""

    def test_delete_series_no_invoices(self, client):
        """Test deleting series with no invoices."""
        series = InvoiceSeries.objects.create(
            prefix='T',
            name='To Delete'
        )

        response = client.post(f'/modules/invoicing/series/{series.id}/delete/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

        assert not InvoiceSeries.objects.filter(id=series.id).exists()

    def test_delete_series_with_invoices(self, client, sample_invoice):
        """Test deleting series with invoices fails."""
        series_id = sample_invoice.series.id

        response = client.post(f'/modules/invoicing/series/{series_id}/delete/')

        data = json.loads(response.content)
        assert data['success'] is False


@pytest.mark.django_db
class TestSettingsView:
    """Tests for invoicing settings."""

    def test_settings_get(self, client, series):
        """Test GET settings page."""
        response = client.get('/modules/invoicing/settings/')

        assert response.status_code == 200

    def test_settings_save(self, client, series):
        """Test POST save settings."""
        response = client.post('/modules/invoicing/settings/', {
            'company_name': 'Test Company',
            'company_tax_id': 'B12345678',
            'company_address': 'Test Address',
            'company_phone': '+34600123456',
            'company_email': 'test@company.com',
            'default_series': 'F',
            'invoice_footer': 'Thanks for your business'
        })

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

        config = InvoicingConfig.get_config()
        assert config.company_name == 'Test Company'
