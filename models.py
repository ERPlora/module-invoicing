"""Invoicing models."""

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.core.models import HubBaseModel


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class InvoicingSettings(HubBaseModel):
    """Per-hub invoicing configuration."""

    # Company data for invoices
    company_name = models.CharField(
        _('Company Name'), max_length=255, blank=True,
    )
    company_tax_id = models.CharField(
        _('Tax ID (NIF/CIF)'), max_length=50, blank=True,
    )
    company_address = models.TextField(_('Address'), blank=True)
    company_phone = models.CharField(
        _('Phone'), max_length=50, blank=True,
    )
    company_email = models.EmailField(_('Email'), blank=True)

    # Invoice settings
    default_series_prefix = models.CharField(
        _('Default Series Prefix'), max_length=10, default='F',
    )
    auto_generate_invoice = models.BooleanField(
        _('Auto-generate on Sale'), default=False,
    )
    require_customer = models.BooleanField(
        _('Require Customer'), default=True,
    )

    # Invoice footer
    invoice_footer = models.TextField(
        _('Invoice Footer'), blank=True,
        help_text=_('Text shown at the bottom of invoices'),
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'invoicing_settings'
        verbose_name = _('Invoicing Settings')
        verbose_name_plural = _('Invoicing Settings')
        unique_together = [('hub_id',)]

    def __str__(self):
        return f'Invoicing Settings (hub={self.hub_id})'

    @classmethod
    def get_settings(cls, hub_id):
        obj, _ = cls.all_objects.get_or_create(hub_id=hub_id)
        return obj


# ---------------------------------------------------------------------------
# Invoice Series
# ---------------------------------------------------------------------------

class InvoiceSeries(HubBaseModel):
    """
    Invoice numbering series.
    Examples: F (facturas), R (rectificativas), T (tickets).
    """

    prefix = models.CharField(_('Prefix'), max_length=10)
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)

    # Counter
    next_number = models.PositiveIntegerField(
        _('Next Number'), default=1,
    )

    # Settings
    is_active = models.BooleanField(_('Active'), default=True)
    is_default = models.BooleanField(_('Default Series'), default=False)

    # Format: how many digits for the number (e.g. 6 → F000001)
    number_digits = models.PositiveSmallIntegerField(
        _('Number Digits'), default=6,
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'invoicing_series'
        verbose_name = _('Invoice Series')
        verbose_name_plural = _('Invoice Series')
        ordering = ['prefix']
        unique_together = [('hub_id', 'prefix')]

    def __str__(self):
        return f'{self.prefix} - {self.name}'

    def get_next_number(self):
        """Get and increment the next invoice number."""
        number = self.next_number
        self.next_number += 1
        self.save(update_fields=['next_number', 'updated_at'])
        return f'{self.prefix}{str(number).zfill(self.number_digits)}'

    def save(self, *args, **kwargs):
        # Ensure only one default series per hub
        if self.is_default:
            InvoiceSeries.objects.filter(
                hub_id=self.hub_id, is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

class Invoice(HubBaseModel):
    """Fiscal invoice document."""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        ISSUED = 'issued', _('Issued')
        PAID = 'paid', _('Paid')
        CANCELLED = 'cancelled', _('Cancelled')

    class InvoiceType(models.TextChoices):
        INVOICE = 'invoice', _('Invoice')
        SIMPLIFIED = 'simplified', _('Simplified Invoice')
        RECTIFYING = 'rectifying', _('Rectifying Invoice')

    # Identification
    series = models.ForeignKey(
        InvoiceSeries, on_delete=models.PROTECT,
        verbose_name=_('Series'),
    )
    number = models.CharField(
        _('Invoice Number'), max_length=50, blank=True,
    )
    invoice_type = models.CharField(
        _('Type'), max_length=20,
        choices=InvoiceType.choices, default=InvoiceType.INVOICE,
    )
    status = models.CharField(
        _('Status'), max_length=20,
        choices=Status.choices, default=Status.DRAFT,
    )

    # Dates
    issue_date = models.DateField(_('Issue Date'), default=timezone.now)
    due_date = models.DateField(_('Due Date'), null=True, blank=True)

    # Customer data (snapshot at invoice time — immutable)
    customer_name = models.CharField(
        _('Customer Name'), max_length=255,
    )
    customer_tax_id = models.CharField(
        _('Customer Tax ID'), max_length=50, blank=True,
    )
    customer_address = models.TextField(
        _('Customer Address'), blank=True,
    )
    customer_email = models.EmailField(
        _('Customer Email'), blank=True,
    )
    customer_phone = models.CharField(
        _('Customer Phone'), max_length=50, blank=True,
    )

    # FK to original customer (optional reference)
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='invoices',
        verbose_name=_('Customer'),
    )

    # FK to sale (optional)
    sale = models.ForeignKey(
        'sales.Sale', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='invoices',
        verbose_name=_('Sale'),
    )

    # Amounts
    subtotal = models.DecimalField(
        _('Subtotal'), max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
    )
    tax_rate = models.DecimalField(
        _('Tax Rate %'), max_digits=5, decimal_places=2,
        default=Decimal('21.00'),
    )
    tax_amount = models.DecimalField(
        _('Tax Amount'), max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
    )
    total = models.DecimalField(
        _('Total'), max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
    )

    # Payment
    payment_method = models.CharField(
        _('Payment Method'), max_length=50, blank=True,
    )
    paid_amount = models.DecimalField(
        _('Paid Amount'), max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
    )
    paid_at = models.DateTimeField(_('Paid At'), null=True, blank=True)

    # Notes
    notes = models.TextField(_('Notes'), blank=True)

    # Rectifying invoice reference
    rectified_invoice = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rectifying_invoices',
        verbose_name=_('Rectified Invoice'),
    )

    # Employee who created/issued
    employee = models.ForeignKey(
        'accounts.LocalUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
        verbose_name=_('Employee'),
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'invoicing_invoice'
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['hub_id', 'number']),
            models.Index(fields=['hub_id', 'status']),
            models.Index(fields=['hub_id', 'issue_date']),
            models.Index(fields=['hub_id', 'customer_tax_id']),
        ]

    def __str__(self):
        return f'{self.number or "DRAFT"} - {self.customer_name}'

    def calculate_totals(self):
        """Recalculate totals from lines."""
        lines = self.lines.all()
        self.subtotal = sum(l.total for l in lines)
        self.tax_amount = self.subtotal * (self.tax_rate / Decimal('100'))
        self.total = self.subtotal + self.tax_amount

    def issue(self):
        """Issue the invoice: assign number and mark as issued."""
        if self.status != self.Status.DRAFT:
            return False
        self.number = self.series.get_next_number()
        self.status = self.Status.ISSUED
        self.issue_date = timezone.now().date()
        self.save(update_fields=[
            'number', 'status', 'issue_date', 'updated_at',
        ])
        return True


# ---------------------------------------------------------------------------
# Invoice Line
# ---------------------------------------------------------------------------

class InvoiceLine(HubBaseModel):
    """Individual line item in an invoice."""

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE,
        related_name='lines', verbose_name=_('Invoice'),
    )

    # Product reference (optional, for traceability)
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
        verbose_name=_('Product'),
    )
    product_sku = models.CharField(_('SKU'), max_length=50, blank=True)

    # Line data (snapshot at invoice time — immutable)
    description = models.CharField(_('Description'), max_length=500)
    quantity = models.DecimalField(
        _('Quantity'), max_digits=10, decimal_places=3,
        default=Decimal('1'),
    )
    unit_price = models.DecimalField(
        _('Unit Price'), max_digits=12, decimal_places=2,
    )
    discount_percent = models.DecimalField(
        _('Discount %'), max_digits=5, decimal_places=2,
        default=Decimal('0'),
    )
    tax_rate = models.DecimalField(
        _('Tax Rate %'), max_digits=5, decimal_places=2,
        default=Decimal('21.00'),
    )

    # Calculated
    total = models.DecimalField(
        _('Line Total'), max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
    )

    # Order
    order = models.PositiveSmallIntegerField(_('Order'), default=0)

    class Meta(HubBaseModel.Meta):
        db_table = 'invoicing_line'
        verbose_name = _('Invoice Line')
        verbose_name_plural = _('Invoice Lines')
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'{self.description} x {self.quantity}'

    def calculate_total(self):
        """Calculate line total with discount."""
        subtotal = self.quantity * self.unit_price
        discount = subtotal * (self.discount_percent / Decimal('100'))
        self.total = subtotal - discount
        return self.total

    def save(self, *args, **kwargs):
        self.calculate_total()
        super().save(*args, **kwargs)
