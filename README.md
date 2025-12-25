# Invoicing Module

Invoice and receipt management for ERPlora Hub.

## Features

- Invoice generation from sales
- Multiple invoice series support
- Tax calculation and management
- PDF generation for printing
- Invoice numbering sequences
- Integration with Sales module

## Installation

This module is installed automatically via the ERPlora Marketplace.

**Dependencies**: Requires `sales` module.

## Configuration

Access settings via: **Menu > Facturación > Settings**

| Setting | Description |
|---------|-------------|
| `default_series` | Default prefix for invoice numbers (e.g., "F") |
| `auto_generate_invoice` | Auto-create invoice when sale completes |
| `require_customer_for_invoice` | Require customer data for invoices |

## Usage

Access via: **Menu > Facturación**

### Invoice Management

- **Create Invoice**: Generate invoice from completed sale
- **View Invoices**: List all invoices with filters
- **Print/PDF**: Generate printable invoice
- **Series**: Manage invoice series (F, R, etc.)

### Invoice Types

| Type | Description |
|------|-------------|
| Invoice | Standard invoice with full customer data |
| Simplified | Ticket/receipt without customer requirement |

## Models

| Model | Description |
|-------|-------------|
| `Invoice` | Invoice header with totals |
| `InvoiceLine` | Individual line items |
| `InvoiceSeries` | Series configuration (prefix, next number) |
| `InvoicingConfig` | Module settings |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Invoice dashboard |
| `/invoices/` | GET | List invoices |
| `/invoices/create/` | POST | Create invoice |
| `/invoices/<id>/` | GET | View invoice |
| `/invoices/<id>/pdf/` | GET | Download PDF |
| `/series/` | GET | List invoice series |

## Permissions

| Permission | Description |
|------------|-------------|
| `invoicing.view_invoice` | View invoices |
| `invoicing.add_invoice` | Create invoices |
| `invoicing.change_invoice` | Edit invoices |
| `invoicing.delete_invoice` | Delete invoices |

## Integration with Verifactu

When the `verifactu` module is installed, invoices are automatically:
- Assigned a hash for chain integrity
- Submitted to AEAT in real-time
- QR codes added for verification

## License

MIT

## Author

ERPlora Team - support@erplora.com
