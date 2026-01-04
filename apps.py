from django.apps import AppConfig


class InvoicingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'invoicing'
    verbose_name = 'Invoicing'

    def ready(self):
        """
        Register extension points for the Invoicing module.

        This module EMITS signals:
        - invoice_created: When an invoice is generated
        - invoice_sent: When an invoice is sent to customer
        - invoice_paid: When an invoice is marked as paid

        This module LISTENS to:
        - sale_completed: To optionally auto-generate invoices

        This module provides HOOKS:
        - invoicing.before_invoice_create: Before creating an invoice
        - invoicing.after_invoice_create: After creating an invoice
        - invoicing.filter_invoice_lines: Modify invoice lines before creation
        - invoicing.filter_invoice_totals: Modify invoice totals

        This module provides SLOTS:
        - invoicing.invoice_header: Invoice header area
        - invoicing.invoice_footer: Invoice footer area
        - invoicing.invoice_line_extra: Extra info per line item
        """
        self._register_signal_handlers()
        self._register_hooks()
        self._register_slots()

    def _register_signal_handlers(self):
        """Register handlers for signals from other modules."""
        pass

    def _register_hooks(self):
        """
        Register hooks that this module OFFERS to other modules.

        Other modules can use these hooks to:
        - Validate invoices before creation
        - Add fiscal data (Verifactu integration)
        - Modify invoice lines
        """
        pass

    def _register_slots(self):
        """
        Register slots that this module OFFERS to other modules.

        Slots are template injection points where other modules
        can add their content.
        """
        pass

    # =========================================================================
    # Hook Helper Methods (called from views)
    # =========================================================================

    @staticmethod
    def do_before_invoice_create(sale, customer, lines, user=None):
        """
        Execute before_invoice_create hook.

        Called before creating an invoice. Other modules can:
        - Validate the invoice data
        - Add fiscal information
        - Check customer data

        Args:
            sale: Original sale instance
            customer: Customer for the invoice
            lines: Invoice line items
            user: User creating the invoice

        Raises:
            ValidationError: If a hook wants to block the creation
        """
        from apps.core.hooks import hooks

        hooks.do_action(
            'invoicing.before_invoice_create',
            sale=sale,
            customer=customer,
            lines=lines,
            user=user
        )

    @staticmethod
    def do_after_invoice_create(invoice, sale, user=None):
        """
        Execute after_invoice_create hook.

        Called after an invoice is created. Other modules can:
        - Register with fiscal systems (Verifactu)
        - Send notifications
        - Update accounting systems

        Args:
            invoice: Created invoice instance
            sale: Original sale instance
            user: User who created the invoice
        """
        from apps.core.hooks import hooks

        hooks.do_action(
            'invoicing.after_invoice_create',
            invoice=invoice,
            sale=sale,
            user=user
        )

    @staticmethod
    def filter_invoice_lines(lines, sale=None, customer=None, user=None):
        """
        Apply filter_invoice_lines hook.

        Called before finalizing invoice lines. Other modules can:
        - Add additional lines (shipping, etc.)
        - Modify descriptions
        - Add fiscal codes

        Args:
            lines: List of invoice line dicts
            sale: Related sale
            customer: Customer for invoice
            user: User creating invoice

        Returns:
            Modified lines list
        """
        from apps.core.hooks import hooks

        return hooks.apply_filters(
            'invoicing.filter_invoice_lines',
            lines,
            sale=sale,
            customer=customer,
            user=user
        )

    @staticmethod
    def filter_invoice_totals(totals, invoice=None, user=None):
        """
        Apply filter_invoice_totals hook.

        Called before saving invoice totals. Other modules can:
        - Add fiscal calculations
        - Modify tax amounts
        - Add surcharges

        Args:
            totals: Dict with subtotal, tax, total
            invoice: Invoice instance
            user: User creating invoice

        Returns:
            Modified totals dict
        """
        from apps.core.hooks import hooks

        return hooks.apply_filters(
            'invoicing.filter_invoice_totals',
            totals,
            invoice=invoice,
            user=user
        )
