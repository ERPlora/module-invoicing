"""AI tools for the Invoicing module."""
from assistant.tools import AssistantTool, register_tool


@register_tool
class ListInvoices(AssistantTool):
    name = "list_invoices"
    description = "List invoices with optional filters. Returns number, customer, status, total, dates."
    module_id = "invoicing"
    required_permission = "invoicing.view_invoice"
    parameters = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "description": "Filter: draft, issued, paid, cancelled"},
            "search": {"type": "string", "description": "Search by customer name or invoice number"},
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from invoicing.models import Invoice
        qs = Invoice.objects.all().order_by('-issue_date')
        if args.get('status'):
            qs = qs.filter(status=args['status'])
        if args.get('search'):
            from django.db.models import Q
            s = args['search']
            qs = qs.filter(Q(customer_name__icontains=s) | Q(number__icontains=s))
        limit = args.get('limit', 20)
        return {
            "invoices": [
                {
                    "id": str(inv.id),
                    "number": inv.number,
                    "customer_name": inv.customer_name,
                    "status": inv.status,
                    "total": str(inv.total),
                    "issue_date": str(inv.issue_date) if inv.issue_date else None,
                    "due_date": str(inv.due_date) if inv.due_date else None,
                }
                for inv in qs[:limit]
            ],
            "total": qs.count(),
        }


@register_tool
class GetPendingInvoices(AssistantTool):
    name = "get_pending_invoices"
    description = "Get invoices that are issued but not yet paid, with aging info."
    module_id = "invoicing"
    required_permission = "invoicing.view_invoice"
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from datetime import date
        from django.db.models import Sum
        from invoicing.models import Invoice
        pending = Invoice.objects.filter(status='issued').order_by('due_date')
        total_pending = pending.aggregate(total=Sum('total'))['total'] or 0
        overdue = pending.filter(due_date__lt=date.today())
        total_overdue = overdue.aggregate(total=Sum('total'))['total'] or 0
        return {
            "pending_count": pending.count(),
            "total_pending": str(total_pending),
            "overdue_count": overdue.count(),
            "total_overdue": str(total_overdue),
            "invoices": [
                {
                    "number": inv.number,
                    "customer_name": inv.customer_name,
                    "total": str(inv.total),
                    "due_date": str(inv.due_date) if inv.due_date else None,
                    "is_overdue": inv.due_date < date.today() if inv.due_date else False,
                }
                for inv in pending[:20]
            ],
        }


@register_tool
class GetInvoice(AssistantTool):
    name = "get_invoice"
    description = "Get detailed info for a specific invoice including items."
    module_id = "invoicing"
    required_permission = "invoicing.view_invoice"
    parameters = {
        "type": "object",
        "properties": {
            "invoice_id": {"type": "string"}, "number": {"type": "string"},
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from invoicing.models import Invoice
        if args.get('invoice_id'):
            inv = Invoice.objects.get(id=args['invoice_id'])
        elif args.get('number'):
            inv = Invoice.objects.get(number=args['number'])
        else:
            return {"error": "Provide invoice_id or number"}
        items = inv.lines.all()
        return {
            "id": str(inv.id), "number": inv.number, "status": inv.status,
            "customer_name": inv.customer_name, "customer_tax_id": inv.customer_tax_id,
            "subtotal": str(inv.subtotal), "tax_amount": str(inv.tax_amount), "total": str(inv.total),
            "issue_date": str(inv.issue_date) if inv.issue_date else None,
            "due_date": str(inv.due_date) if inv.due_date else None,
            "items": [
                {"description": i.description, "quantity": i.quantity, "unit_price": str(i.unit_price), "total": str(i.total)}
                for i in items
            ],
        }


@register_tool
class GetInvoicingSummary(AssistantTool):
    name = "get_invoicing_summary"
    description = "Get invoicing summary: total invoiced, total paid, total pending, by period."
    module_id = "invoicing"
    required_permission = "invoicing.view_invoice"
    parameters = {
        "type": "object",
        "properties": {
            "date_from": {"type": "string"}, "date_to": {"type": "string"},
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from datetime import date
        from django.db.models import Sum, Count, Q
        from invoicing.models import Invoice
        qs = Invoice.objects.all()
        if args.get('date_from'):
            qs = qs.filter(issue_date__gte=args['date_from'])
        if args.get('date_to'):
            qs = qs.filter(issue_date__lte=args['date_to'])
        stats = qs.aggregate(
            total_invoiced=Sum('total'),
            total_paid=Sum('total', filter=Q(status='paid')),
            total_pending=Sum('total', filter=Q(status='issued')),
            count=Count('id'),
        )
        return {
            "total_invoiced": str(stats['total_invoiced'] or 0),
            "total_paid": str(stats['total_paid'] or 0),
            "total_pending": str(stats['total_pending'] or 0),
            "invoice_count": stats['count'],
        }


@register_tool
class CreateInvoice(AssistantTool):
    name = "create_invoice"
    description = "Create a new invoice with line items."
    module_id = "invoicing"
    required_permission = "invoicing.change_invoice"
    requires_confirmation = True
    examples = [
        {"customer_name": "María García", "lines": [{"description": "Corte + Peinado", "quantity": 1, "unit_price": "25.00"}]},
    ]
    parameters = {
        "type": "object",
        "properties": {
            "customer_name": {"type": "string", "description": "Customer name"},
            "customer_tax_id": {"type": "string", "description": "Customer tax ID / VAT"},
            "customer_email": {"type": "string", "description": "Customer email"},
            "customer_address": {"type": "string", "description": "Customer address"},
            "invoice_type": {"type": "string", "description": "Type: invoice, simplified, rectifying"},
            "due_date": {"type": "string", "description": "Due date (YYYY-MM-DD)"},
            "notes": {"type": "string", "description": "Invoice notes"},
            "tax_rate": {"type": "number", "description": "Tax rate percentage (default from settings)"},
            "lines": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_price": {"type": "string"},
                        "discount_percent": {"type": "number"},
                    },
                    "required": ["description", "unit_price"],
                },
                "description": "Line items",
            },
        },
        "required": ["customer_name", "lines"],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from decimal import Decimal
        from invoicing.models import Invoice, InvoiceLine, InvoiceSeries
        series = InvoiceSeries.objects.filter(is_default=True, is_active=True).first()
        if not series:
            series = InvoiceSeries.objects.filter(is_active=True).first()
        if not series:
            return {"error": "No invoice series configured"}

        inv = Invoice.objects.create(
            series=series,
            customer_name=args['customer_name'],
            customer_tax_id=args.get('customer_tax_id', ''),
            customer_email=args.get('customer_email', ''),
            customer_address=args.get('customer_address', ''),
            invoice_type=args.get('invoice_type', 'invoice'),
            notes=args.get('notes', ''),
            tax_rate=Decimal(str(args.get('tax_rate', 21))),
        )
        if args.get('due_date'):
            inv.due_date = args['due_date']
            inv.save(update_fields=['due_date'])

        for i, line in enumerate(args.get('lines', [])):
            InvoiceLine.objects.create(
                invoice=inv,
                description=line['description'],
                quantity=Decimal(str(line.get('quantity', 1))),
                unit_price=Decimal(line['unit_price']),
                discount_percent=Decimal(str(line.get('discount_percent', 0))),
                tax_rate=inv.tax_rate,
                order=i,
            )
        inv.calculate_totals()
        inv.save()
        return {"id": str(inv.id), "number": inv.number, "total": str(inv.total), "created": True}


@register_tool
class UpdateInvoiceStatus(AssistantTool):
    name = "update_invoice_status"
    description = "Update invoice status: issue (draft→issued), mark paid, or cancel."
    module_id = "invoicing"
    required_permission = "invoicing.change_invoice"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "invoice_id": {"type": "string", "description": "Invoice ID"},
            "number": {"type": "string", "description": "Invoice number (alternative to ID)"},
            "status": {"type": "string", "description": "New status: issued, paid, cancelled"},
            "payment_method": {"type": "string", "description": "Payment method (when marking as paid)"},
        },
        "required": ["status"],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from django.utils import timezone
        from invoicing.models import Invoice
        if args.get('invoice_id'):
            inv = Invoice.objects.get(id=args['invoice_id'])
        elif args.get('number'):
            inv = Invoice.objects.get(number=args['number'])
        else:
            return {"error": "Provide invoice_id or number"}

        new_status = args['status']
        if new_status == 'issued' and inv.status == 'draft':
            inv.status = 'issued'
            inv.save(update_fields=['status'])
        elif new_status == 'paid':
            inv.status = 'paid'
            inv.paid_amount = inv.total
            inv.paid_at = timezone.now()
            if args.get('payment_method'):
                inv.payment_method = args['payment_method']
            inv.save(update_fields=['status', 'paid_amount', 'paid_at', 'payment_method'])
        elif new_status == 'cancelled':
            inv.status = 'cancelled'
            inv.save(update_fields=['status'])
        else:
            return {"error": f"Cannot transition from '{inv.status}' to '{new_status}'"}
        return {"id": str(inv.id), "number": inv.number, "status": inv.status}
