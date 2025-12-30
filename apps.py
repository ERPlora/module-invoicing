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
        - invoicing.filter_lines: Modify invoice lines before creation
        - invoicing.filter_totals: Modify invoice totals

        This module provides SLOTS:
        - invoicing.header: Invoice header area
        - invoicing.footer: Invoice footer area
        - invoicing.line_extra: Extra info per line item
        """
        self._register_signal_handlers()

    def _register_signal_handlers(self):
        """Register handlers for signals from other modules."""
        from django.dispatch import receiver
        from apps.core.signals import sale_completed

        @receiver(sale_completed)
        def on_sale_completed(sender, sale, user, **kwargs):
            """
            Optionally auto-generate invoice for completed sales.
            Depends on configuration settings.
            """
            # Check if auto-invoice is enabled
            # from .models import InvoicingConfig
            # config = InvoicingConfig.get_config()
            # if config.auto_invoice_on_sale:
            #     create_invoice_from_sale(sale, user)
            pass
