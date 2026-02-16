from django.utils.translation import gettext_lazy as _

MODULE_ID = 'invoicing'
MODULE_NAME = _('Invoicing')
MODULE_VERSION = '1.0.0'

MENU = {
    'label': _('Invoicing'),
    'icon': 'document-text-outline',
    'order': 30,
}

NAVIGATION = [
    {'id': 'dashboard', 'label': _('Overview'), 'icon': 'stats-chart-outline', 'view': ''},
    {'id': 'invoices', 'label': _('Invoices'), 'icon': 'document-text-outline', 'view': 'invoices'},
    {'id': 'series', 'label': _('Series'), 'icon': 'layers-outline', 'view': 'series'},
    {'id': 'settings', 'label': _('Settings'), 'icon': 'settings-outline', 'view': 'settings'},
]

# Module Dependencies
DEPENDENCIES = ['customers', 'sales', 'inventory']
