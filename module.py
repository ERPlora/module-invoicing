"""
Invoicing Module Configuration

This file defines the module metadata and navigation for the Invoicing module.
Used by the @module_view decorator to automatically render navigation tabs.
"""
from django.utils.translation import gettext_lazy as _

# Module Identification
MODULE_ID = "invoicing"
MODULE_NAME = _("Invoicing")
MODULE_ICON = "document-text-outline"
MODULE_VERSION = "1.0.0"
MODULE_CATEGORY = "accounting"

# Sidebar Menu Configuration
MENU = {
    "label": _("Invoicing"),
    "icon": "document-text-outline",
    "order": 30,
    "show": True,
}

# Internal Navigation (Tabs)
NAVIGATION = [
    {
        "id": "dashboard",
        "label": _("Overview"),
        "icon": "grid-outline",
        "view": "",
    },
    {
        "id": "invoices",
        "label": _("Invoices"),
        "icon": "document-text-outline",
        "view": "invoices",
    },
    {
        "id": "series",
        "label": _("Series"),
        "icon": "list-outline",
        "view": "series",
    },
    {
        "id": "settings",
        "label": _("Settings"),
        "icon": "settings-outline",
        "view": "settings",
    },
]

# Module Dependencies
DEPENDENCIES = ["sales>=1.0.0"]

# Default Settings
SETTINGS = {
    "default_series": "F",
    "auto_generate_invoice": False,
    "require_customer_for_invoice": True,
}

# Permissions
PERMISSIONS = [
    "invoicing.view_invoice",
    "invoicing.add_invoice",
    "invoicing.change_invoice",
    "invoicing.delete_invoice",
    "invoicing.view_invoiceseries",
    "invoicing.add_invoiceseries",
    "invoicing.change_invoiceseries",
    "invoicing.delete_invoiceseries",
]
