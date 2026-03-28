# Test Spec: Invoicing

## Pages

| Tab ID | URL | Expected Content |
|--------|-----|-----------------|
| dashboard | /m/invoicing/ or /m/invoicing/dashboard/ | Monthly totals, draft/issued/paid counts, recent invoices |
| invoices | /m/invoicing/invoices/ | Invoice list with search (customer/number), filter (status/date), pagination |
| create | /m/invoicing/invoices/new/ | Create invoice form with line items |
| detail | /m/invoicing/invoices/<uuid>/ | Full invoice with lines, status actions |
| print | /m/invoicing/invoices/<uuid>/print/ | Print-friendly view with company info, lines, totals, footer |
| series | /m/invoicing/series/ | Invoice series list with prefix, name, next number |
| series_add | /m/invoicing/series/add/ | Series form |
| series_edit | /m/invoicing/series/<uuid>/edit/ | Edit series |
| settings | /m/invoicing/settings/ | Company info + invoicing settings |
| api | /m/invoicing/api/invoices/ | JSON invoice list |

## CRUD Operations

### Invoice
- **Create**: New page -> select series, invoice_type (invoice|simplified|rectifying), customer info (name, tax_id, address, email, phone), customer FK (optional), due_date, payment_method, notes -> add InvoiceLines: product (FK optional), product_sku, description*, quantity*, unit_price*, discount_percent, tax_rate, order -> POST -> status=draft
- **Read**: Detail shows all fields + lines with calculated totals + status actions
- **Issue**: POST /m/invoicing/invoices/<uuid>/issue/ -> assigns number from series (prefix + zero-padded next_number), status=issued
- **Cancel**: POST /m/invoicing/invoices/<uuid>/cancel/ -> status=cancelled
- **Delete**: POST /m/invoicing/invoices/<uuid>/delete/ (only draft)
- **Print**: GET /m/invoicing/invoices/<uuid>/print/ -> print-formatted view

### InvoiceSeries
- **Create**: Series page -> form: prefix* (max 10 chars), name*, description, number_digits (default 6), is_active, is_default -> POST /m/invoicing/series/add/
- **Update**: POST /m/invoicing/series/<uuid>/edit/
- **Delete**: POST /m/invoicing/series/<uuid>/delete/
- **Toggle**: POST /m/invoicing/series/<uuid>/toggle/ -> toggle is_active

### InvoicingSettings
- **Update**: POST /m/invoicing/settings/save/ (JSON) or toggle/input/reset endpoints
- **Fields**: company_name, company_tax_id, company_address, company_phone, company_email, default_series_prefix, auto_generate_invoice, require_customer, invoice_footer

## Business Logic

1. **Create draft invoice**: New invoice -> add lines -> calculate totals -> save as draft.
2. **Line total calculation**: InvoiceLine.total = quantity * unit_price * (1 - discount_percent/100). Auto-calculated on save.
3. **Invoice total calculation**: subtotal = sum(line.total), tax_amount = subtotal * (tax_rate/100), total = subtotal + tax_amount.
4. **Issue invoice**: Draft -> click Issue -> number assigned from series: prefix + zero-padded next_number (e.g., F000001). Series.next_number increments. Status=issued.
5. **Series number format**: Prefix "F", number_digits=6, next_number=1 -> "F000001". Next -> "F000002". Prefix "R" for rectifying series.
6. **Multiple series**: F (standard), R (rectifying), T (simplified) -> each with own counter.
7. **Default series**: Only one is_default per hub. New invoices default to this series.
8. **Rectifying invoice**: invoice_type=rectifying -> must set rectified_invoice FK -> shows relationship to original.
9. **Cancel invoice**: Issued -> cancel -> status=cancelled. Draft -> cancel -> status=cancelled.
10. **Mark paid**: Issued invoice -> record payment -> status=paid, paid_amount set, paid_at set.
11. **Print invoice**: Print view shows company info (from InvoicingSettings), customer info, lines with totals, invoice_footer.
12. **Auto-generate from sale**: If auto_generate_invoice=True -> completing a sale auto-creates draft invoice with sale data.
13. **Search and filter**: Search by customer name, tax_id, or invoice number. Filter by status (draft/issued/paid/cancelled), date range.
14. **Dashboard stats**: Monthly totals, count per status, recent invoices list.

## Cross-Module Interactions

### With sales
- Invoice.sale FK links to sales.Sale
- Auto-generate invoice on sale completion (if auto_generate_invoice=True)
- Sale.sale_number referenced in invoice

### With customers
- Invoice.customer FK links to customers.Customer
- Customer info auto-filled from customer record (name, tax_id, address, email, phone)

### With verifactu
- Issued invoice can trigger VerifactuRecord creation
- Invoice number/date/type used in VeriFactu XML

### With tax
- Invoice line tax_rate comes from tax configuration
- Tax amounts feed into TaxReport totals

## Settings

- **company_name**: Company name on invoices
- **company_tax_id**: CIF/NIF on invoices
- **company_address**: Company address on invoices
- **company_phone**: Company phone on invoices
- **company_email**: Company email on invoices
- **default_series_prefix**: Default series for new invoices (e.g., "F")
- **auto_generate_invoice** (False): Auto-create invoice on sale completion
- **require_customer** (True): Require customer info on invoice
- **invoice_footer**: Custom footer text on invoices

## Permissions

- Invoice: view/add/change/delete/void
- Series: view/add/change/delete
- Reports: view_reports
- Settings: manage_settings

## Edge Cases

- Issue invoice from series that has been deactivated -> should fail or use default
- Delete issued invoice -> should fail (only draft can be deleted)
- Rectifying invoice without rectified_invoice FK -> should fail/warn
- Invoice with 0 lines -> should fail
- Line with quantity=0 -> should fail
- Line with negative unit_price -> should fail (or allow for credit notes?)
- Duplicate invoice number -> prevented by series auto-increment
- Empty company settings -> issue should warn that company info is missing
- Invoice footer with very long text -> should truncate or wrap on print
- Series next_number should never decrement
- Two invoices issued simultaneously from same series -> no number collision
- Discount > 100% on line -> should fail
