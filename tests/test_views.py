"""
Integration tests for Invoicing views.
"""

import json
import uuid
import pytest
from decimal import Decimal
from django.test import Client
from django.utils import timezone

from invoicing.models import InvoicingSettings, InvoiceSeries, Invoice, InvoiceLine


pytestmark = [pytest.mark.django_db, pytest.mark.unit]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _set_hub_config(db, settings):
    """Ensure HubConfig + StoreConfig exist so middleware won't redirect."""
    from apps.configuration.models import HubConfig, StoreConfig
    config = HubConfig.get_solo()
    config.save()
    store = StoreConfig.get_solo()
    store.business_name = 'Test Business'
    store.is_configured = True
    store.save()


@pytest.fixture
def hub_id(db):
    from apps.configuration.models import HubConfig
    return HubConfig.get_solo().hub_id


@pytest.fixture
def employee(db):
    """Create a local user (employee)."""
    from apps.accounts.models import LocalUser
    return LocalUser.objects.create(
        name='Test Employee',
        email='employee@test.com',
        role='admin',
        is_active=True,
    )


@pytest.fixture
def auth_client(employee):
    """Authenticated Django test client."""
    client = Client()
    session = client.session
    session['local_user_id'] = str(employee.id)
    session['user_name'] = employee.name
    session['user_email'] = employee.email
    session['user_role'] = employee.role
    session['store_config_checked'] = True
    session.save()
    return client


@pytest.fixture
def series(hub_id):
    """Create a default invoice series."""
    return InvoiceSeries.objects.create(
        hub_id=hub_id,
        prefix='F',
        name='Facturas',
        is_default=True,
        number_digits=6,
    )


@pytest.fixture
def sample_invoice(hub_id, series):
    """Create a sample issued invoice."""
    return Invoice.objects.create(
        hub_id=hub_id,
        series=series,
        number='F000001',
        customer_name='Maria Garcia',
        customer_tax_id='12345678Z',
        customer_address='Calle Mayor 1',
        subtotal=Decimal('100.00'),
        tax_rate=Decimal('21.00'),
        tax_amount=Decimal('21.00'),
        total=Decimal('121.00'),
        status=Invoice.Status.ISSUED,
    )


@pytest.fixture
def draft_invoice(hub_id, series):
    """Create a draft invoice."""
    return Invoice.objects.create(
        hub_id=hub_id,
        series=series,
        customer_name='Test Customer',
        customer_tax_id='87654321X',
        status=Invoice.Status.DRAFT,
    )


# ---------------------------------------------------------------------------
# Dashboard / Index
# ---------------------------------------------------------------------------

class TestDashboard:

    def test_requires_login(self):
        client = Client()
        response = client.get('/m/invoicing/')
        assert response.status_code == 302

    def test_index_loads(self, auth_client):
        response = auth_client.get('/m/invoicing/')
        assert response.status_code == 200

    def test_index_htmx(self, auth_client):
        response = auth_client.get('/m/invoicing/', HTTP_HX_REQUEST='true')
        assert response.status_code == 200

    def test_dashboard_loads(self, auth_client):
        response = auth_client.get('/m/invoicing/dashboard/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Invoices List
# ---------------------------------------------------------------------------

class TestInvoicesList:

    def test_invoices_list_loads(self, auth_client, series):
        response = auth_client.get('/m/invoicing/invoices/')
        assert response.status_code == 200

    def test_invoices_list_with_data(self, auth_client, sample_invoice):
        response = auth_client.get('/m/invoicing/invoices/')
        assert response.status_code == 200

    def test_invoices_list_htmx(self, auth_client, series):
        response = auth_client.get('/m/invoicing/invoices/', HTTP_HX_REQUEST='true')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Invoice Detail
# ---------------------------------------------------------------------------

class TestInvoiceDetail:

    def test_detail_loads(self, auth_client, sample_invoice):
        response = auth_client.get(f'/m/invoicing/invoices/{sample_invoice.pk}/')
        assert response.status_code == 200

    def test_detail_htmx(self, auth_client, sample_invoice):
        response = auth_client.get(
            f'/m/invoicing/invoices/{sample_invoice.pk}/',
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 200

    def test_detail_not_found(self, auth_client):
        fake_uuid = uuid.uuid4()
        response = auth_client.get(f'/m/invoicing/invoices/{fake_uuid}/')
        # View returns 200 with error context (rendered via @htmx_view)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Invoice Create
# ---------------------------------------------------------------------------

class TestInvoiceCreate:

    def test_create_form_loads(self, auth_client, series):
        response = auth_client.get('/m/invoicing/invoices/new/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Invoice Issue
# ---------------------------------------------------------------------------

class TestInvoiceIssue:

    def test_issue_draft(self, auth_client, draft_invoice):
        response = auth_client.post(f'/m/invoicing/invoices/{draft_invoice.pk}/issue/')
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        draft_invoice.refresh_from_db()
        assert draft_invoice.status == Invoice.Status.ISSUED
        assert draft_invoice.number != ''

    def test_issue_non_draft_fails(self, auth_client, sample_invoice):
        response = auth_client.post(f'/m/invoicing/invoices/{sample_invoice.pk}/issue/')
        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False


# ---------------------------------------------------------------------------
# Invoice Cancel
# ---------------------------------------------------------------------------

class TestInvoiceCancel:

    def test_cancel_invoice(self, auth_client, sample_invoice):
        response = auth_client.post(f'/m/invoicing/invoices/{sample_invoice.pk}/cancel/')
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        sample_invoice.refresh_from_db()
        assert sample_invoice.status == Invoice.Status.CANCELLED

    def test_cancel_already_cancelled(self, auth_client, hub_id, series):
        inv = Invoice.objects.create(
            hub_id=hub_id, series=series,
            customer_name='Test', status=Invoice.Status.CANCELLED,
        )
        response = auth_client.post(f'/m/invoicing/invoices/{inv.pk}/cancel/')
        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False


# ---------------------------------------------------------------------------
# Invoice Print
# ---------------------------------------------------------------------------

class TestInvoicePrint:

    def test_print_loads(self, auth_client, sample_invoice):
        response = auth_client.get(f'/m/invoicing/invoices/{sample_invoice.pk}/print/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Series List
# ---------------------------------------------------------------------------

class TestSeriesList:

    def test_series_list_loads(self, auth_client, series):
        response = auth_client.get('/m/invoicing/series/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Series CRUD
# ---------------------------------------------------------------------------

class TestSeriesCRUD:

    def test_add_form_loads(self, auth_client):
        response = auth_client.get('/m/invoicing/series/add/')
        assert response.status_code == 200

    def test_edit_form_loads(self, auth_client, series):
        response = auth_client.get(f'/m/invoicing/series/{series.pk}/edit/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class TestSettingsView:

    def test_settings_loads(self, auth_client, series):
        response = auth_client.get('/m/invoicing/settings/')
        assert response.status_code == 200
