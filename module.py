from django.utils.translation import gettext_lazy as _

MODULE_ID = 'invoicing'
MODULE_NAME = _('Invoicing')
MODULE_VERSION = '1.0.1'
MODULE_ICON = 'document-text-outline'
MODULE_DESCRIPTION = _('Create and manage invoices, credit notes, and billing')
MODULE_AUTHOR = 'ERPlora'
MODULE_CATEGORY = 'finance'
HAS_MODELS = True

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

ROLE_PERMISSIONS = {
    "admin": ["*"],
    "manager": [
        "add_invoice",
        "add_series",
        "change_invoice",
        "change_series",
        "view_invoice",
        "view_reports",
        "view_series",
        "void_invoice",
    ],
    "employee": [
        "add_invoice",
        "view_invoice",
        "view_series",
    ],
}

SCHEDULED_TASKS = [
    {
        'task': 'invoicing.send_overdue_reminders',
        'cron': '0 9 * * *',
        'description': 'Send payment reminders for overdue invoices',
    },
]
