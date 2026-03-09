# Invoicing

## Overview

| Property | Value |
|----------|-------|
| **Module ID** | `invoicing` |
| **Version** | `1.0.0` |
| **Dependencies** | `customers`, `sales`, `inventory` |

## Dependencies

This module requires the following modules to be installed:

- `customers`
- `sales`
- `inventory`

## Models

### `InvoicingSettings`

Per-hub invoicing configuration.

| Field | Type | Details |
|-------|------|---------|
| `company_name` | CharField | max_length=255, optional |
| `company_tax_id` | CharField | max_length=50, optional |
| `company_address` | TextField | optional |
| `company_phone` | CharField | max_length=50, optional |
| `company_email` | EmailField | max_length=254, optional |
| `default_series_prefix` | CharField | max_length=10 |
| `auto_generate_invoice` | BooleanField |  |
| `require_customer` | BooleanField |  |
| `invoice_footer` | TextField | optional |

**Methods:**

- `get_settings()`

### `InvoiceSeries`

Invoice numbering series.
Examples: F (facturas), R (rectificativas), T (tickets).

| Field | Type | Details |
|-------|------|---------|
| `prefix` | CharField | max_length=10 |
| `name` | CharField | max_length=100 |
| `description` | TextField | optional |
| `next_number` | PositiveIntegerField |  |
| `is_active` | BooleanField |  |
| `is_default` | BooleanField |  |
| `number_digits` | PositiveSmallIntegerField |  |

**Methods:**

- `get_next_number()` — Get and increment the next invoice number.

### `Invoice`

Fiscal invoice document.

| Field | Type | Details |
|-------|------|---------|
| `series` | ForeignKey | → `invoicing.InvoiceSeries`, on_delete=PROTECT |
| `number` | CharField | max_length=50, optional |
| `invoice_type` | CharField | max_length=20, choices: invoice, simplified, rectifying |
| `status` | CharField | max_length=20, choices: draft, issued, paid, cancelled |
| `issue_date` | DateField |  |
| `due_date` | DateField | optional |
| `customer_name` | CharField | max_length=255, optional |
| `customer_tax_id` | CharField | max_length=50, optional |
| `customer_address` | TextField | optional |
| `customer_email` | EmailField | max_length=254, optional |
| `customer_phone` | CharField | max_length=50, optional |
| `customer` | ForeignKey | → `customers.Customer`, on_delete=SET_NULL, optional |
| `sale` | ForeignKey | → `sales.Sale`, on_delete=SET_NULL, optional |
| `subtotal` | DecimalField |  |
| `tax_rate` | DecimalField |  |
| `tax_amount` | DecimalField |  |
| `total` | DecimalField |  |
| `payment_method` | CharField | max_length=50, optional |
| `paid_amount` | DecimalField |  |
| `paid_at` | DateTimeField | optional |
| `notes` | TextField | optional |
| `rectified_invoice` | ForeignKey | → `invoicing.Invoice`, on_delete=SET_NULL, optional |
| `employee` | ForeignKey | → `accounts.LocalUser`, on_delete=SET_NULL, optional |

**Methods:**

- `calculate_totals()` — Recalculate totals from lines.
- `issue()` — Issue the invoice: assign number and mark as issued.

### `InvoiceLine`

Individual line item in an invoice.

| Field | Type | Details |
|-------|------|---------|
| `invoice` | ForeignKey | → `invoicing.Invoice`, on_delete=CASCADE |
| `product` | ForeignKey | → `inventory.Product`, on_delete=SET_NULL, optional |
| `product_sku` | CharField | max_length=50, optional |
| `description` | CharField | max_length=500 |
| `quantity` | DecimalField |  |
| `unit_price` | DecimalField |  |
| `discount_percent` | DecimalField |  |
| `tax_rate` | DecimalField |  |
| `total` | DecimalField |  |
| `order` | PositiveSmallIntegerField |  |

**Methods:**

- `calculate_total()` — Calculate line total with discount.

## Cross-Module Relationships

| From | Field | To | on_delete | Nullable |
|------|-------|----|-----------|----------|
| `Invoice` | `series` | `invoicing.InvoiceSeries` | PROTECT | No |
| `Invoice` | `customer` | `customers.Customer` | SET_NULL | Yes |
| `Invoice` | `sale` | `sales.Sale` | SET_NULL | Yes |
| `Invoice` | `rectified_invoice` | `invoicing.Invoice` | SET_NULL | Yes |
| `Invoice` | `employee` | `accounts.LocalUser` | SET_NULL | Yes |
| `InvoiceLine` | `invoice` | `invoicing.Invoice` | CASCADE | No |
| `InvoiceLine` | `product` | `inventory.Product` | SET_NULL | Yes |

## URL Endpoints

Base path: `/m/invoicing/`

| Path | Name | Method |
|------|------|--------|
| `(root)` | `index` | GET |
| `dashboard/` | `dashboard` | GET |
| `invoices/` | `invoices` | GET |
| `invoices/new/` | `invoice_create` | GET/POST |
| `invoices/<uuid:pk>/` | `invoice_detail` | GET |
| `invoices/<uuid:pk>/issue/` | `invoice_issue` | GET |
| `invoices/<uuid:pk>/cancel/` | `invoice_cancel` | GET |
| `invoices/<uuid:pk>/delete/` | `invoice_delete` | GET/POST |
| `invoices/<uuid:pk>/print/` | `invoice_print` | GET |
| `series/` | `series` | GET |
| `series/add/` | `series_add` | GET/POST |
| `series/<uuid:pk>/edit/` | `series_edit` | GET |
| `series/<uuid:pk>/delete/` | `series_delete` | GET/POST |
| `series/<uuid:pk>/toggle/` | `series_toggle` | GET |
| `settings/` | `settings` | GET |
| `settings/save/` | `settings_save` | GET/POST |
| `settings/toggle/` | `settings_toggle` | GET |
| `settings/input/` | `settings_input` | GET |
| `settings/reset/` | `settings_reset` | GET |
| `api/invoices/` | `api_invoices` | GET |

## Permissions

| Permission | Description |
|------------|-------------|
| `invoicing.view_invoice` | View Invoice |
| `invoicing.add_invoice` | Add Invoice |
| `invoicing.change_invoice` | Change Invoice |
| `invoicing.delete_invoice` | Delete Invoice |
| `invoicing.void_invoice` | Void Invoice |
| `invoicing.view_series` | View Series |
| `invoicing.add_series` | Add Series |
| `invoicing.change_series` | Change Series |
| `invoicing.delete_series` | Delete Series |
| `invoicing.view_reports` | View Reports |
| `invoicing.manage_settings` | Manage Settings |

**Role assignments:**

- **admin**: All permissions
- **manager**: `add_invoice`, `add_series`, `change_invoice`, `change_series`, `view_invoice`, `view_reports`, `view_series`, `void_invoice`
- **employee**: `add_invoice`, `view_invoice`, `view_series`

## Navigation

| View | Icon | ID | Fullpage |
|------|------|----|----------|
| Overview | `stats-chart-outline` | `dashboard` | No |
| Invoices | `document-text-outline` | `invoices` | No |
| Series | `layers-outline` | `series` | No |
| Settings | `settings-outline` | `settings` | No |

## AI Tools

Tools available for the AI assistant:

### `list_invoices`

List invoices with optional filters. Returns number, customer, status, total, dates.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | Filter: draft, issued, paid, cancelled |
| `search` | string | No | Search by customer name or invoice number |
| `limit` | integer | No | Max results (default 20) |

### `get_pending_invoices`

Get invoices that are issued but not yet paid, with aging info.

### `get_invoice`

Get detailed info for a specific invoice including items.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_id` | string | No |  |
| `number` | string | No |  |

### `get_invoicing_summary`

Get invoicing summary: total invoiced, total paid, total pending, by period.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date_from` | string | No |  |
| `date_to` | string | No |  |

### `create_invoice`

Create a new invoice with line items.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `customer_name` | string | Yes | Customer name |
| `customer_tax_id` | string | No | Customer tax ID / VAT |
| `customer_email` | string | No | Customer email |
| `customer_address` | string | No | Customer address |
| `invoice_type` | string | No | Type: invoice, simplified, rectifying |
| `due_date` | string | No | Due date (YYYY-MM-DD) |
| `notes` | string | No | Invoice notes |
| `tax_rate` | number | No | Tax rate percentage (default from settings) |
| `lines` | array | Yes | Line items |

### `update_invoice_status`

Update invoice status: issue (draft→issued), mark paid, or cancel.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_id` | string | No | Invoice ID |
| `number` | string | No | Invoice number (alternative to ID) |
| `status` | string | Yes | New status: issued, paid, cancelled |
| `payment_method` | string | No | Payment method (when marking as paid) |

## File Structure

```
CHANGELOG.md
README.md
__init__.py
ai_tools.py
apps.py
forms.py
locale/
  en/
    LC_MESSAGES/
      django.po
  es/
    LC_MESSAGES/
      django.po
migrations/
  0001_initial.py
  0002_customer_name_optional.py
  __init__.py
models.py
module.py
static/
  icons/
    icon.svg
    ion/
templates/
  invoicing/
    pages/
      dashboard.html
      invoice_detail.html
      invoice_form.html
      invoices.html
      series.html
      series_form.html
      settings.html
    partials/
      dashboard_content.html
      invoice_detail_content.html
      invoice_form_content.html
      invoices_content.html
      invoices_table.html
      series_content.html
      series_form_content.html
      series_table.html
      settings_content.html
    print/
      invoice.html
tests/
  __init__.py
  test_models.py
  test_views.py
urls.py
views.py
```
