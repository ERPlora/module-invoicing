"""
Unit tests for Invoicing models.
"""

import pytest
from decimal import Decimal
from django.utils import timezone

from invoicing.models import InvoicingConfig, InvoiceSeries, Invoice, InvoiceLine


@pytest.mark.django_db
class TestInvoicingConfig:
    """Tests for InvoicingConfig singleton model."""

    def test_get_config_creates_singleton(self):
        """Test get_config creates singleton if not exists."""
        config = InvoicingConfig.get_config()

        assert config is not None
        assert config.pk == 1

    def test_get_config_returns_existing(self):
        """Test get_config returns existing config."""
        config1 = InvoicingConfig.get_config()
        config2 = InvoicingConfig.get_config()

        assert config1.pk == config2.pk

    def test_default_values(self):
        """Test default configuration values."""
        config = InvoicingConfig.get_config()

        assert config.default_series == 'F'
        assert config.auto_generate_invoice is False
        assert config.require_customer is True

    def test_str_representation(self):
        """Test string representation."""
        config = InvoicingConfig.get_config()

        assert str(config) == 'Invoicing Configuration'

    def test_save_forces_singleton(self):
        """Test saving always uses pk=1."""
        config = InvoicingConfig(pk=999, company_name="Test")
        config.save()

        assert config.pk == 1


@pytest.mark.django_db
class TestInvoiceSeries:
    """Tests for InvoiceSeries model."""

    def test_create_series(self):
        """Test creating an invoice series."""
        series = InvoiceSeries.objects.create(
            prefix='F',
            name='Facturas',
            number_digits=6
        )

        assert series.id is not None
        assert series.prefix == 'F'
        assert series.next_number == 1

    def test_get_next_number(self):
        """Test generating sequential invoice numbers."""
        series = InvoiceSeries.objects.create(
            prefix='F',
            name='Facturas',
            number_digits=6
        )

        num1 = series.get_next_number()
        num2 = series.get_next_number()
        num3 = series.get_next_number()

        assert num1 == 'F000001'
        assert num2 == 'F000002'
        assert num3 == 'F000003'

    def test_number_digits_format(self):
        """Test different number digit formats."""
        series = InvoiceSeries.objects.create(
            prefix='R',
            name='Rectificativas',
            number_digits=4
        )

        num = series.get_next_number()

        assert num == 'R0001'

    def test_str_representation(self):
        """Test string representation."""
        series = InvoiceSeries.objects.create(
            prefix='T',
            name='Tickets'
        )

        assert str(series) == 'T - Tickets'

    def test_default_is_active(self):
        """Test series is active by default."""
        series = InvoiceSeries.objects.create(
            prefix='F',
            name='Facturas'
        )

        assert series.is_active is True

    def test_only_one_default_series(self):
        """Test only one series can be default."""
        series1 = InvoiceSeries.objects.create(
            prefix='F',
            name='Facturas',
            is_default=True
        )
        series2 = InvoiceSeries.objects.create(
            prefix='R',
            name='Rectificativas',
            is_default=True
        )

        series1.refresh_from_db()

        assert series1.is_default is False
        assert series2.is_default is True

    def test_ordering_by_prefix(self):
        """Test series are ordered by prefix."""
        InvoiceSeries.objects.create(prefix='Z', name='Z Series')
        InvoiceSeries.objects.create(prefix='A', name='A Series')
        InvoiceSeries.objects.create(prefix='M', name='M Series')

        series = list(InvoiceSeries.objects.all())

        assert series[0].prefix == 'A'
        assert series[1].prefix == 'M'
        assert series[2].prefix == 'Z'


@pytest.mark.django_db
class TestInvoice:
    """Tests for Invoice model."""

    @pytest.fixture
    def series(self):
        """Create a series for testing."""
        return InvoiceSeries.objects.create(
            prefix='F',
            name='Facturas',
            number_digits=6
        )

    def test_create_draft_invoice(self, series):
        """Test creating a draft invoice."""
        invoice = Invoice.objects.create(
            series=series,
            customer_name='Test Customer',
            customer_tax_id='12345678Z'
        )

        assert invoice.id is not None
        assert invoice.status == Invoice.Status.DRAFT
        assert invoice.number == ''  # No number for drafts

    def test_invoice_number_generated_on_issue(self, series):
        """Test invoice number is generated when status changes from draft."""
        invoice = Invoice.objects.create(
            series=series,
            customer_name='Test Customer',
            status=Invoice.Status.ISSUED
        )

        assert invoice.number.startswith('F')
        assert len(invoice.number) == 7  # F + 6 digits

    def test_default_values(self, series):
        """Test default invoice values."""
        invoice = Invoice.objects.create(
            series=series,
            customer_name='Test'
        )

        assert invoice.status == Invoice.Status.DRAFT
        assert invoice.invoice_type == Invoice.InvoiceType.INVOICE
        assert invoice.subtotal == Decimal('0.00')
        assert invoice.tax_rate == Decimal('21.00')
        assert invoice.tax_amount == Decimal('0.00')
        assert invoice.total == Decimal('0.00')

    def test_str_representation(self, series):
        """Test string representation."""
        invoice = Invoice.objects.create(
            series=series,
            customer_name='Test Customer',
            status=Invoice.Status.ISSUED
        )

        assert 'Test Customer' in str(invoice)

    def test_status_choices(self, series):
        """Test all status choices are valid."""
        for status, label in Invoice.Status.choices:
            invoice = Invoice.objects.create(
                series=series,
                customer_name='Test',
                status=status
            )
            assert invoice.status == status

    def test_invoice_type_choices(self, series):
        """Test all invoice type choices are valid."""
        for inv_type, label in Invoice.InvoiceType.choices:
            invoice = Invoice.objects.create(
                series=series,
                customer_name='Test',
                invoice_type=inv_type
            )
            assert invoice.invoice_type == inv_type

    def test_ordering(self, series):
        """Test invoices are ordered by issue_date descending."""
        inv1 = Invoice.objects.create(
            series=series,
            customer_name='First',
            issue_date=timezone.now().date()
        )
        inv2 = Invoice.objects.create(
            series=series,
            customer_name='Second',
            issue_date=timezone.now().date()
        )

        invoices = list(Invoice.objects.all())

        # Both have same issue_date, so ordered by created_at desc
        assert invoices[0] == inv2
        assert invoices[1] == inv1


@pytest.mark.django_db
class TestInvoiceLine:
    """Tests for InvoiceLine model."""

    @pytest.fixture
    def invoice(self):
        """Create an invoice for testing lines."""
        series = InvoiceSeries.objects.create(prefix='F', name='Facturas')
        return Invoice.objects.create(
            series=series,
            customer_name='Test Customer'
        )

    def test_create_invoice_line(self, invoice):
        """Test creating an invoice line."""
        line = InvoiceLine.objects.create(
            invoice=invoice,
            description='Test Product',
            quantity=Decimal('2'),
            unit_price=Decimal('10.00')
        )

        assert line.id is not None
        assert line.description == 'Test Product'

    def test_line_total_calculation(self, invoice):
        """Test line total is calculated on save."""
        line = InvoiceLine.objects.create(
            invoice=invoice,
            description='Product',
            quantity=Decimal('3'),
            unit_price=Decimal('10.00')
        )

        assert line.total == Decimal('30.00')

    def test_line_total_with_discount(self, invoice):
        """Test line total with discount."""
        line = InvoiceLine.objects.create(
            invoice=invoice,
            description='Product',
            quantity=Decimal('2'),
            unit_price=Decimal('100.00'),
            discount_percent=Decimal('10')  # 10% discount
        )

        # 2 * 100 = 200, 10% discount = 20, total = 180
        assert line.total == Decimal('180.00')

    def test_str_representation(self, invoice):
        """Test string representation."""
        line = InvoiceLine.objects.create(
            invoice=invoice,
            description='Test Product',
            quantity=Decimal('5'),
            unit_price=Decimal('10.00')
        )

        assert 'Test Product' in str(line)
        assert '5' in str(line)

    def test_default_values(self, invoice):
        """Test default line values."""
        line = InvoiceLine.objects.create(
            invoice=invoice,
            description='Product',
            unit_price=Decimal('10.00')
        )

        assert line.quantity == Decimal('1')
        assert line.discount_percent == Decimal('0')
        assert line.tax_rate == Decimal('21.00')

    def test_ordering(self, invoice):
        """Test lines are ordered by order field."""
        line3 = InvoiceLine.objects.create(
            invoice=invoice,
            description='Third',
            unit_price=10,
            order=3
        )
        line1 = InvoiceLine.objects.create(
            invoice=invoice,
            description='First',
            unit_price=10,
            order=1
        )
        line2 = InvoiceLine.objects.create(
            invoice=invoice,
            description='Second',
            unit_price=10,
            order=2
        )

        lines = list(invoice.lines.all())

        assert lines[0] == line1
        assert lines[1] == line2
        assert lines[2] == line3


@pytest.mark.django_db
class TestInvoiceCalculateTotals:
    """Tests for Invoice.calculate_totals method."""

    @pytest.fixture
    def invoice_with_lines(self):
        """Create an invoice with lines for testing."""
        series = InvoiceSeries.objects.create(prefix='F', name='Facturas')
        invoice = Invoice.objects.create(
            series=series,
            customer_name='Test Customer',
            tax_rate=Decimal('21.00')
        )

        # Add lines
        InvoiceLine.objects.create(
            invoice=invoice,
            description='Product 1',
            quantity=Decimal('2'),
            unit_price=Decimal('50.00')
        )
        InvoiceLine.objects.create(
            invoice=invoice,
            description='Product 2',
            quantity=Decimal('1'),
            unit_price=Decimal('100.00')
        )

        return invoice

    def test_calculate_totals(self, invoice_with_lines):
        """Test calculate_totals sums lines correctly."""
        invoice_with_lines.calculate_totals()

        # Line 1: 2 * 50 = 100
        # Line 2: 1 * 100 = 100
        # Subtotal: 200
        assert invoice_with_lines.subtotal == Decimal('200.00')

    def test_calculate_tax_amount(self, invoice_with_lines):
        """Test tax amount calculation."""
        invoice_with_lines.calculate_totals()

        # Subtotal 200 * 21% = 42
        assert invoice_with_lines.tax_amount == Decimal('42.00')

    def test_calculate_total(self, invoice_with_lines):
        """Test total calculation."""
        invoice_with_lines.calculate_totals()

        # Subtotal 200 + Tax 42 = 242
        assert invoice_with_lines.total == Decimal('242.00')


@pytest.mark.django_db
class TestInvoiceIndexes:
    """Tests for Invoice model indexes."""

    def test_number_index_exists(self):
        """Test number field has index."""
        indexes = Invoice._meta.indexes
        index_fields = [idx.fields for idx in indexes]

        assert ['number'] in index_fields

    def test_status_index_exists(self):
        """Test status field has index."""
        indexes = Invoice._meta.indexes
        index_fields = [idx.fields for idx in indexes]

        assert ['status'] in index_fields

    def test_issue_date_index_exists(self):
        """Test issue_date field has index."""
        indexes = Invoice._meta.indexes
        index_fields = [idx.fields for idx in indexes]

        assert ['issue_date'] in index_fields

    def test_customer_tax_id_index_exists(self):
        """Test customer_tax_id field has index."""
        indexes = Invoice._meta.indexes
        index_fields = [idx.fields for idx in indexes]

        assert ['customer_tax_id'] in index_fields
