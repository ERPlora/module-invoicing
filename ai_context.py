"""
AI context for the Invoicing module.
Loaded into the assistant system prompt when this module's tools are active.
"""

CONTEXT = """
## Module Knowledge: Invoicing

### Models

**InvoicingSettings** (singleton per hub)
- `company_name`, `company_tax_id`, `company_address`, `company_phone`, `company_email`
- `default_series_prefix` (default `F`)
- `auto_generate_invoice` (bool): create invoice automatically on sale
- `require_customer` (bool, default True): customer required before issuing
- `invoice_footer` (TextField): printed at bottom of invoices
- Access via `InvoicingSettings.get_settings(hub_id)`

**InvoiceSeries**
- `prefix` (CharField, max 10): e.g. `F`, `R`, `T` — unique per hub
- `name`, `description`
- `next_number` (PositiveInt, default 1): auto-increments on each issue
- `number_digits` (default 6): zero-pads number, e.g. `F000001`
- `is_active` (bool), `is_default` (bool, only one per hub)
- `get_next_number()`: returns formatted string and increments counter

**Invoice**
- `series` (FK InvoiceSeries, PROTECT)
- `number` (CharField): assigned on issue, e.g. `F000001`
- `invoice_type`: `invoice`, `simplified`, `rectifying`
- `status`: `draft` → `issued` → `paid` | `cancelled`
- Customer snapshot fields (immutable after issue): `customer_name`, `customer_tax_id`, `customer_address`, `customer_email`, `customer_phone`
- `customer` (FK customers.Customer, nullable): live reference
- `sale` (FK sales.Sale, nullable): originating sale
- `subtotal`, `tax_rate`, `tax_amount`, `total` (Decimal)
- `payment_method`, `paid_amount`, `paid_at`
- `rectified_invoice` (FK self, nullable): for rectifying invoices
- `employee` (FK accounts.LocalUser, nullable)
- `issue()`: assigns number from series, sets status=issued

**InvoiceLine**
- `invoice` (FK Invoice, CASCADE)
- `product` (FK inventory.Product, nullable): optional reference
- `product_sku`, `description`, `quantity`, `unit_price`, `discount_percent`, `tax_rate`
- `total` (Decimal): auto-calculated as `qty * price * (1 - discount%)`
- `order` (int): display order

### Key flows

**Issue an invoice:**
1. Create `Invoice` in `draft` status with customer snapshot data
2. Add `InvoiceLine` records (totals auto-calculated on save)
3. Call `invoice.calculate_totals()` to update header amounts
4. Call `invoice.issue()` → assigns number from series, sets `issued`

**Rectifying invoice:**
- Create new `Invoice` with `invoice_type='rectifying'`
- Set `rectified_invoice` FK to the original invoice

### Relationships
- Invoice → InvoiceSeries (FK)
- Invoice → customers.Customer (FK, nullable)
- Invoice → sales.Sale (FK, nullable)
- Invoice → accounts.LocalUser as employee (FK, nullable)
- Invoice → Invoice as rectified (self FK)
- InvoiceLine → Invoice (FK)
- InvoiceLine → inventory.Product (FK, nullable)
- facturae_b2b.EInvoice → Invoice (OneToOne, related_name `einvoice`)
- verifactu.VerifactuRecord → Invoice (FK, related_name `verifactu_records`)
"""
