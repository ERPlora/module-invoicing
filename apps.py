from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class InvoicingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'invoicing'
    label = 'invoicing'
    verbose_name = _('Invoicing')

    def ready(self):
        pass
