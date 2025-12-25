# Changelog

All notable changes to the Invoicing module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-25

### Added

- Initial release of Invoicing module
- **Core Features**
  - Invoice generation from sales
  - Multiple invoice series support (F, R, etc.)
  - Tax calculation and management
  - PDF generation for printing
  - Invoice numbering sequences
  - Draft, Issued, Paid, Cancelled states

- **Models**
  - `Invoice`: Invoice header with totals
  - `InvoiceLine`: Individual line items
  - `InvoiceSeries`: Series configuration (prefix, next number)
  - `InvoicingConfig`: Module settings

- **Views**
  - Invoice list with filters
  - Invoice detail view
  - Invoice creation form
  - Invoice PDF generation
  - Series management

- **Invoice Types**
  - Standard Invoice (with customer data)
  - Simplified Invoice (ticket/receipt)
  - Rectifying Invoice

- **Internationalization**
  - English translations (base)
  - Spanish translations

### Technical Details

- Auto-generate invoice on sale completion (optional)
- Customer data required for standard invoices
- Integration with Sales module
- Integration with Customers module
- Integration with Verifactu module for Spanish compliance

---

## [Unreleased]

### Planned

- Recurring invoices
- Invoice templates customization
- Email sending
- Payment reminders
- Multi-currency support
- Export to accounting software
