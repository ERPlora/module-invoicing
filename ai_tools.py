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
        items = inv.items.all()
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
