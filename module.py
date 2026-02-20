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

PERMISSIONS = [
    'invoicing.view_invoice',
    'invoicing.add_invoice',
    'invoicing.change_invoice',
    'invoicing.delete_invoice',
    'invoicing.void_invoice',
    'invoicing.view_series',
    'invoicing.add_series',
    'invoicing.change_series',
    'invoicing.delete_series',
    'invoicing.view_reports',
    'invoicing.manage_settings',
]

# Module Dependencies
DEPENDENCIES = ['customers', 'sales', 'inventory']
