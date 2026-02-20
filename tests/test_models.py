"""
Unit tests for Invoicing models.
"""

import pytest
from decimal import Decimal
from django.utils import timezone

from invoicing.models import InvoicingSettings, InvoiceSeries, Invoice, InvoiceLine


pytestmark = [pytest.mark.django_db, pytest.mark.unit]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def hub_id(hub_config):
    """Hub ID from HubConfig singleton."""
    return hub_config.hub_id


@pytest.fixture
def series(hub_id):
    """Create an invoice series."""
    return InvoiceSeries.objects.create(
        hub_id=hub_id,
        prefix='F',
        name='Facturas',
        number_digits=6,
        is_default=True,
    )


@pytest.fixture
def draft_invoice(hub_id, series):
    """Create a draft invoice."""
    return Invoice.objects.create(
        hub_id=hub_id,
        series=series,
        customer_name='Test Customer',
        customer_tax_id='12345678Z',
        customer_address='Calle Mayor 1',
        status=Invoice.Status.DRAFT,
    )


@pytest.fixture
def issued_invoice(hub_id, series):
    """Create an issued invoice with a number."""
    inv = Invoice.objects.create(
        hub_id=hub_id,
        series=series,
        customer_name='Maria Garcia',
        customer_tax_id='87654321X',
        customer_address='Calle Sol 5',
        status=Invoice.Status.DRAFT,
    )
    inv.issue()
    return inv


# ---------------------------------------------------------------------------
# InvoicingSettings
# ---------------------------------------------------------------------------

class TestInvoicingSettings:
    """Tests for InvoicingSettings model."""

    def test_get_settings_creates(self, hub_id):
        s = InvoicingSettings.get_settings(hub_id)
        assert s is not None
        assert s.hub_id == hub_id

    def test_get_settings_returns_existing(self, hub_id):
        s1 = InvoicingSettings.get_settings(hub_id)
        s2 = InvoicingSettings.get_settings(hub_id)
        assert s1.pk == s2.pk

    def test_default_values(self, hub_id):
        s = InvoicingSettings.get_settings(hub_id)
        assert s.default_series_prefix == 'F'
        assert s.auto_generate_invoice is False
        assert s.require_customer is True
        assert s.company_name == ''
        assert s.company_tax_id == ''
        assert s.invoice_footer == ''

    def test_str(self, hub_id):
        s = InvoicingSettings.get_settings(hub_id)
        assert 'Invoicing Settings' in str(s)

    def test_update_company_data(self, hub_id):
        s = InvoicingSettings.get_settings(hub_id)
        s.company_name = 'Test Company SL'
        s.company_tax_id = 'B12345678'
        s.company_address = 'Business St 42'
        s.company_phone = '+34600123456'
        s.company_email = 'admin@test.com'
        s.save()

        refreshed = InvoicingSettings.get_settings(hub_id)
        assert refreshed.company_name == 'Test Company SL'
        assert refreshed.company_tax_id == 'B12345678'


# ---------------------------------------------------------------------------
# InvoiceSeries
# ---------------------------------------------------------------------------

class TestInvoiceSeries:
    """Tests for InvoiceSeries model."""

    def test_create(self, series):
        assert series.prefix == 'F'
        assert series.name == 'Facturas'
        assert series.next_number == 1
        assert series.is_active is True
        assert series.is_default is True
        assert series.number_digits == 6

    def test_get_next_number(self, series):
        num1 = series.get_next_number()
        num2 = series.get_next_number()
        num3 = series.get_next_number()
        assert num1 == 'F000001'
        assert num2 == 'F000002'
        assert num3 == 'F000003'

    def test_number_digits_format(self, hub_id):
        s = InvoiceSeries.objects.create(
            hub_id=hub_id, prefix='R',
            name='Rectificativas', number_digits=4,
        )
        num = s.get_next_number()
        assert num == 'R0001'

    def test_str(self, series):
        assert str(series) == 'F - Facturas'

    def test_only_one_default_per_hub(self, hub_id, series):
        """Saving a new series as default should un-default the old one."""
        s2 = InvoiceSeries.objects.create(
            hub_id=hub_id, prefix='R',
            name='Rectificativas', is_default=True,
        )
        series.refresh_from_db()
        assert series.is_default is False
        assert s2.is_default is True

    def test_ordering_by_prefix(self, hub_id):
        InvoiceSeries.objects.create(hub_id=hub_id, prefix='Z', name='Z Series')
        InvoiceSeries.objects.create(hub_id=hub_id, prefix='A', name='A Series')
        InvoiceSeries.objects.create(hub_id=hub_id, prefix='M', name='M Series')
        series_list = list(InvoiceSeries.objects.filter(hub_id=hub_id))
        prefixes = [s.prefix for s in series_list]
        assert prefixes == sorted(prefixes)

    def test_unique_prefix_per_hub(self, hub_id, series):
        """Cannot create two series with same prefix for same hub (constraint in Meta)."""
        # Verify unique_together constraint is declared in Meta
        unique = InvoiceSeries._meta.unique_together
        assert ('hub_id', 'prefix') in unique

    def test_soft_delete(self, hub_id):
        s = InvoiceSeries.objects.create(
            hub_id=hub_id, prefix='T', name='Tickets',
        )
        s.delete()
        assert s.is_deleted is True
        assert InvoiceSeries.objects.filter(pk=s.pk).count() == 0
        assert InvoiceSeries.all_objects.filter(pk=s.pk).count() == 1


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

class TestInvoice:
    """Tests for Invoice model."""

    def test_create_draft(self, draft_invoice):
        assert draft_invoice.status == Invoice.Status.DRAFT
        assert draft_invoice.number == ''
        assert draft_invoice.customer_name == 'Test Customer'

    def test_default_values(self, hub_id, series):
        inv = Invoice.objects.create(
            hub_id=hub_id, series=series, customer_name='Test',
        )
        assert inv.status == Invoice.Status.DRAFT
        assert inv.invoice_type == Invoice.InvoiceType.INVOICE
        assert inv.subtotal == Decimal('0.00')
        assert inv.tax_rate == Decimal('21.00')
        assert inv.tax_amount == Decimal('0.00')
        assert inv.total == Decimal('0.00')
        assert inv.paid_amount == Decimal('0.00')

    def test_str_draft(self, draft_invoice):
        result = str(draft_invoice)
        assert 'DRAFT' in result
        assert 'Test Customer' in result

    def test_str_issued(self, issued_invoice):
        result = str(issued_invoice)
        assert 'F' in result
        assert 'Maria Garcia' in result

    def test_issue_draft_to_issued(self, draft_invoice):
        """Test draft -> issued transition assigns number."""
        result = draft_invoice.issue()
        assert result is True
        draft_invoice.refresh_from_db()
        assert draft_invoice.status == Invoice.Status.ISSUED
        assert draft_invoice.number.startswith('F')
        assert len(draft_invoice.number) == 7  # F + 6 digits

    def test_issue_non_draft_fails(self, issued_invoice):
        """Cannot issue an already-issued invoice."""
        result = issued_invoice.issue()
        assert result is False

    def test_issue_cancelled_fails(self, hub_id, series):
        """Cannot issue a cancelled invoice."""
        inv = Invoice.objects.create(
            hub_id=hub_id, series=series, customer_name='Test',
            status=Invoice.Status.CANCELLED,
        )
        result = inv.issue()
        assert result is False

    def test_all_status_choices(self, hub_id, series):
        for status, _ in Invoice.Status.choices:
            inv = Invoice.objects.create(
                hub_id=hub_id, series=series,
                customer_name='Test', status=status,
            )
            assert inv.status == status

    def test_all_invoice_type_choices(self, hub_id, series):
        for inv_type, _ in Invoice.InvoiceType.choices:
            inv = Invoice.objects.create(
                hub_id=hub_id, series=series,
                customer_name='Test', invoice_type=inv_type,
            )
            assert inv.invoice_type == inv_type

    def test_ordering_newest_first(self, hub_id, series):
        inv1 = Invoice.objects.create(
            hub_id=hub_id, series=series, customer_name='First',
        )
        inv2 = Invoice.objects.create(
            hub_id=hub_id, series=series, customer_name='Second',
        )
        invoices = list(Invoice.objects.filter(hub_id=hub_id))
        assert invoices[0].pk == inv2.pk

    def test_calculate_totals(self, hub_id, series):
        """Test calculate_totals sums lines correctly."""
        inv = Invoice.objects.create(
            hub_id=hub_id, series=series, customer_name='Test',
            tax_rate=Decimal('21.00'),
        )
        InvoiceLine.objects.create(
            hub_id=hub_id, invoice=inv,
            description='Product 1',
            quantity=Decimal('2'), unit_price=Decimal('50.00'),
        )
        InvoiceLine.objects.create(
            hub_id=hub_id, invoice=inv,
            description='Product 2',
            quantity=Decimal('1'), unit_price=Decimal('100.00'),
        )
        inv.calculate_totals()
        # Line 1: 2*50 = 100, Line 2: 1*100 = 100 -> subtotal 200
        assert inv.subtotal == Decimal('200.00')
        # tax: 200 * 21% = 42
        assert inv.tax_amount == Decimal('42.00')
        # total: 200 + 42 = 242
        assert inv.total == Decimal('242.00')

    def test_indexes(self):
        index_fields = [idx.fields for idx in Invoice._meta.indexes]
        assert ['hub_id', 'number'] in index_fields
        assert ['hub_id', 'status'] in index_fields
        assert ['hub_id', 'issue_date'] in index_fields
        assert ['hub_id', 'customer_tax_id'] in index_fields

    def test_soft_delete(self, draft_invoice):
        draft_invoice.delete()
        assert draft_invoice.is_deleted is True
        assert Invoice.objects.filter(pk=draft_invoice.pk).count() == 0
        assert Invoice.all_objects.filter(pk=draft_invoice.pk).count() == 1


# ---------------------------------------------------------------------------
# InvoiceLine
# ---------------------------------------------------------------------------

class TestInvoiceLine:
    """Tests for InvoiceLine model."""

    def test_create(self, hub_id, draft_invoice):
        line = InvoiceLine.objects.create(
            hub_id=hub_id, invoice=draft_invoice,
            description='Test Product',
            quantity=Decimal('2'), unit_price=Decimal('10.00'),
        )
        assert line.description == 'Test Product'
        assert line.quantity == Decimal('2')

    def test_line_total_calculation(self, hub_id, draft_invoice):
        """Total is auto-calculated on save."""
        line = InvoiceLine.objects.create(
            hub_id=hub_id, invoice=draft_invoice,
            description='Product',
            quantity=Decimal('3'), unit_price=Decimal('10.00'),
        )
        assert line.total == Decimal('30.00')

    def test_line_total_with_discount(self, hub_id, draft_invoice):
        """Test line total with discount percent."""
        line = InvoiceLine.objects.create(
            hub_id=hub_id, invoice=draft_invoice,
            description='Product',
            quantity=Decimal('2'), unit_price=Decimal('100.00'),
            discount_percent=Decimal('10'),
        )
        # 2 * 100 = 200, 10% discount = 20, total = 180
        assert line.total == Decimal('180.00')

    def test_default_values(self, hub_id, draft_invoice):
        line = InvoiceLine.objects.create(
            hub_id=hub_id, invoice=draft_invoice,
            description='Product', unit_price=Decimal('10.00'),
        )
        assert line.quantity == Decimal('1')
        assert line.discount_percent == Decimal('0')
        assert line.tax_rate == Decimal('21.00')
        assert line.order == 0

    def test_str(self, hub_id, draft_invoice):
        line = InvoiceLine.objects.create(
            hub_id=hub_id, invoice=draft_invoice,
            description='Test Product',
            quantity=Decimal('5'), unit_price=Decimal('10.00'),
        )
        result = str(line)
        assert 'Test Product' in result
        assert '5' in result

    def test_ordering_by_order_field(self, hub_id, draft_invoice):
        line3 = InvoiceLine.objects.create(
            hub_id=hub_id, invoice=draft_invoice,
            description='Third', unit_price=Decimal('10.00'), order=3,
        )
        line1 = InvoiceLine.objects.create(
            hub_id=hub_id, invoice=draft_invoice,
            description='First', unit_price=Decimal('10.00'), order=1,
        )
        line2 = InvoiceLine.objects.create(
            hub_id=hub_id, invoice=draft_invoice,
            description='Second', unit_price=Decimal('10.00'), order=2,
        )
        lines = list(draft_invoice.lines.all())
        assert lines[0].pk == line1.pk
        assert lines[1].pk == line2.pk
        assert lines[2].pk == line3.pk

    def test_calculate_total_method(self, hub_id, draft_invoice):
        """Test the calculate_total method returns and sets total."""
        line = InvoiceLine(
            hub_id=hub_id, invoice=draft_invoice,
            description='Manual',
            quantity=Decimal('4'), unit_price=Decimal('25.00'),
            discount_percent=Decimal('5'),
        )
        result = line.calculate_total()
        # 4 * 25 = 100, 5% discount = 5, total = 95
        assert result == Decimal('95.00')
        assert line.total == Decimal('95.00')


# ---------------------------------------------------------------------------
# Invoice State Transitions
# ---------------------------------------------------------------------------

class TestInvoiceStateTransitions:
    """Tests for invoice state machine: draft -> issued -> cancelled."""

    def test_draft_to_issued(self, draft_invoice):
        assert draft_invoice.status == Invoice.Status.DRAFT
        success = draft_invoice.issue()
        assert success is True
        draft_invoice.refresh_from_db()
        assert draft_invoice.status == Invoice.Status.ISSUED
        assert draft_invoice.number != ''

    def test_issued_cannot_be_re_issued(self, issued_invoice):
        success = issued_invoice.issue()
        assert success is False
        # Status remains ISSUED
        assert issued_invoice.status == Invoice.Status.ISSUED

    def test_cancelled_cannot_be_issued(self, hub_id, series):
        inv = Invoice.objects.create(
            hub_id=hub_id, series=series, customer_name='Test',
            status=Invoice.Status.CANCELLED,
        )
        success = inv.issue()
        assert success is False

    def test_sequential_invoice_numbers(self, hub_id, series):
        """Multiple issues from same series produce sequential numbers."""
        inv1 = Invoice.objects.create(
            hub_id=hub_id, series=series, customer_name='A',
        )
        inv2 = Invoice.objects.create(
            hub_id=hub_id, series=series, customer_name='B',
        )
        inv1.issue()
        inv2.issue()
        inv1.refresh_from_db()
        inv2.refresh_from_db()
        assert inv1.number == 'F000001'
        assert inv2.number == 'F000002'
