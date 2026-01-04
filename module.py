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

# Target Industries (business verticals this module is designed for)
MODULE_INDUSTRIES = [
    "retail",       # Retail stores
    "wholesale",    # Wholesale distributors
    "restaurant",   # Restaurants
    "consulting",   # Professional services
    "manufacturing",# Manufacturing
]

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
# Format: (action_suffix, display_name) -> becomes "invoicing.action_suffix"
PERMISSIONS = [
    ("view_invoice", _("Can view invoices")),
    ("add_invoice", _("Can create invoices")),
    ("change_invoice", _("Can edit invoices")),
    ("delete_invoice", _("Can delete invoices")),
    ("send_invoice", _("Can send invoices")),
    ("print_invoice", _("Can print invoices")),
    ("void_invoice", _("Can void invoices")),
    ("view_invoiceseries", _("Can view invoice series")),
    ("add_invoiceseries", _("Can create invoice series")),
    ("change_invoiceseries", _("Can edit invoice series")),
    ("delete_invoiceseries", _("Can delete invoice series")),
    ("view_reports", _("Can view invoicing reports")),
]

# Role Permissions - Default permissions for each system role in this module
# Keys are role names, values are lists of permission suffixes (without module prefix)
# Use ["*"] to grant all permissions in this module
ROLE_PERMISSIONS = {
    "admin": ["*"],  # Full access to all invoicing permissions
    "manager": [
        "view_invoice",
        "add_invoice",
        "change_invoice",
        "send_invoice",
        "print_invoice",
        "void_invoice",
        "view_invoiceseries",
        "add_invoiceseries",
        "change_invoiceseries",
        "view_reports",
    ],
    "employee": [
        "view_invoice",
        "add_invoice",
        "print_invoice",
        "view_invoiceseries",
    ],
}
