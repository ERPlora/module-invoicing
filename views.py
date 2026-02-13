"""Invoicing views."""

from decimal import Decimal

from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render as django_render
from django.views.decorators.http import require_POST, require_http_methods
from django.db.models import Q, Sum, Count
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils import timezone
from django.contrib import messages

from apps.accounts.decorators import login_required
from apps.core.htmx import htmx_view
from apps.core.services import export_to_csv, export_to_excel
from apps.modules_runtime.navigation import with_module_nav

from .models import InvoicingSettings, InvoiceSeries, Invoice, InvoiceLine
from .forms import InvoiceSeriesForm, InvoicingSettingsForm


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PER_PAGE_CHOICES = [10, 25, 50, 100]

INVOICE_SORT_FIELDS = {
    'number': 'number',
    'date': 'issue_date',
    'customer': 'customer_name',
    'total': 'total',
    'created': 'created_at',
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hub(request):
    return request.session.get('hub_id')


def _employee(request):
    from apps.accounts.models import LocalUser
    uid = request.session.get('local_user_id')
    if uid:
        return LocalUser.objects.filter(pk=uid).first()
    return None


def _render_invoice_list(request, hub):
    """Render the invoices table partial after a mutation."""
    invoices = Invoice.objects.filter(hub_id=hub, is_deleted=False).order_by('-created_at')
    paginator = Paginator(invoices, 10)
    page_obj = paginator.get_page(1)
    return django_render(request, 'invoicing/partials/invoices_table.html', {
        'invoices': page_obj,
        'page_obj': page_obj,
        'search': '',
        'sort_field': 'created',
        'sort_dir': 'desc',
        'status_filter': '',
        'type_filter': '',
        'per_page': 10,
    })


def _render_series_list(request, hub):
    """Render the series list partial after a mutation."""
    series = InvoiceSeries.objects.filter(
        hub_id=hub, is_deleted=False,
    ).annotate(
        invoice_count=Count(
            'invoice', filter=Q(invoice__is_deleted=False),
        ),
    ).order_by('prefix')
    return django_render(request, 'invoicing/partials/series_table.html', {
        'series_list': series,
    })


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
@with_module_nav('invoicing', 'dashboard')
@htmx_view('invoicing/pages/dashboard.html', 'invoicing/partials/dashboard_content.html')
def index(request):
    return _dashboard_context(request)


@login_required
@with_module_nav('invoicing', 'dashboard')
@htmx_view('invoicing/pages/dashboard.html', 'invoicing/partials/dashboard_content.html')
def dashboard(request):
    return _dashboard_context(request)


def _dashboard_context(request):
    hub = _hub(request)
    invoices = Invoice.objects.filter(hub_id=hub, is_deleted=False)

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Monthly stats
    monthly = invoices.filter(
        issue_date__gte=month_start.date(),
        status__in=['issued', 'paid'],
    ).aggregate(
        sum_total=Sum('total'),
        count=Count('id'),
        sum_paid=Sum('total', filter=Q(status='paid')),
    )

    # Overall stats
    draft_count = invoices.filter(status='draft').count()
    issued_count = invoices.filter(status='issued').count()
    paid_count = invoices.filter(status='paid').count()

    recent = invoices.order_by('-created_at')[:10]

    return {
        'monthly_total': monthly['sum_total'] or Decimal('0.00'),
        'monthly_count': monthly['count'] or 0,
        'monthly_paid': monthly['sum_paid'] or Decimal('0.00'),
        'draft_count': draft_count,
        'issued_count': issued_count,
        'paid_count': paid_count,
        'recent_invoices': recent,
    }


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------

@login_required
@with_module_nav('invoicing', 'invoices')
@htmx_view('invoicing/pages/invoices.html', 'invoicing/partials/invoices_content.html')
def invoices_list(request):
    hub = _hub(request)
    qs = Invoice.objects.filter(hub_id=hub, is_deleted=False)

    # --- Search ---
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(number__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(customer_tax_id__icontains=search)
        )

    # --- Filters ---
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    type_filter = request.GET.get('type', '')
    if type_filter:
        qs = qs.filter(invoice_type=type_filter)

    # --- Sort ---
    sort_field = request.GET.get('sort', 'created')
    sort_dir = request.GET.get('dir', 'desc')
    order_by = INVOICE_SORT_FIELDS.get(sort_field, 'created_at')
    if sort_dir == 'desc':
        order_by = f'-{order_by}'
    qs = qs.order_by(order_by)

    # --- Export (before pagination -- exports all filtered results) ---
    export_format = request.GET.get('export')
    if export_format in ('csv', 'excel'):
        export_fields = [
            'number', 'customer_name', 'customer_tax_id',
            'issue_date', 'due_date', 'subtotal', 'tax_amount',
            'total', 'status',
        ]
        export_headers = [
            str(_('Number')), str(_('Customer')), str(_('Tax ID')),
            str(_('Issue Date')), str(_('Due Date')), str(_('Subtotal')),
            str(_('Tax')), str(_('Total')), str(_('Status')),
        ]
        export_formatters = {
            'status': lambda v: str(_(v.capitalize())) if v else '',
        }
        if export_format == 'csv':
            return export_to_csv(
                qs,
                fields=export_fields,
                headers=export_headers,
                field_formatters=export_formatters,
                filename='invoices.csv',
            )
        return export_to_excel(
            qs,
            fields=export_fields,
            headers=export_headers,
            field_formatters=export_formatters,
            filename='invoices.xlsx',
            sheet_name=str(_('Invoices')),
        )

    # --- Pagination ---
    per_page = int(request.GET.get('per_page', 10))
    if per_page not in PER_PAGE_CHOICES:
        per_page = 10
    page_number = request.GET.get('page', 1)

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page_number)

    context = {
        'invoices': page_obj,
        'page_obj': page_obj,
        'search': search,
        'sort_field': sort_field,
        'sort_dir': sort_dir,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'per_page': per_page,
    }

    # HTMX partial: swap only datatable body (search, sort, filter, paginate)
    if request.htmx and request.htmx.target == 'datatable-body':
        return django_render(request, 'invoicing/partials/invoices_table.html', context)

    return context


@login_required
@with_module_nav('invoicing', 'invoices')
@htmx_view('invoicing/pages/invoice_form.html', 'invoicing/partials/invoice_form_content.html')
def invoice_create(request):
    hub = _hub(request)

    if request.method == 'POST':
        series_id = request.POST.get('series_id')
        series = InvoiceSeries.objects.filter(
            pk=series_id, hub_id=hub, is_deleted=False, is_active=True,
        ).first()
        if not series:
            return {'error': _('Invalid series')}

        invoice = Invoice(
            hub_id=hub,
            series=series,
            invoice_type=request.POST.get('invoice_type', 'invoice'),
            customer_name=request.POST.get('customer_name', ''),
            customer_tax_id=request.POST.get('customer_tax_id', ''),
            customer_address=request.POST.get('customer_address', ''),
            customer_email=request.POST.get('customer_email', ''),
            customer_phone=request.POST.get('customer_phone', ''),
            notes=request.POST.get('notes', ''),
            tax_rate=Decimal(request.POST.get('tax_rate', '21.00')),
            employee=_employee(request),
        )

        # Link customer FK if provided
        customer_id = request.POST.get('customer_id')
        if customer_id:
            from customers.models import Customer
            customer = Customer.objects.filter(
                pk=customer_id, hub_id=hub, is_deleted=False,
            ).first()
            if customer:
                invoice.customer = customer
                if not invoice.customer_name:
                    invoice.customer_name = customer.name
                if not invoice.customer_tax_id:
                    invoice.customer_tax_id = getattr(customer, 'tax_id', '')

        # Link sale if provided
        sale_id = request.POST.get('sale_id')
        if sale_id:
            from sales.models import Sale
            sale = Sale.objects.filter(
                pk=sale_id, hub_id=hub, is_deleted=False,
            ).first()
            if sale:
                invoice.sale = sale

        # Rectifying invoice reference
        rectified_id = request.POST.get('rectified_invoice_id')
        if rectified_id and invoice.invoice_type == 'rectifying':
            ref = Invoice.objects.filter(
                pk=rectified_id, hub_id=hub, is_deleted=False,
            ).first()
            if ref:
                invoice.rectified_invoice = ref

        invoice.save()

        # Parse lines from POST
        line_idx = 0
        while True:
            desc = request.POST.get(f'line_{line_idx}_description')
            if desc is None:
                break
            qty = Decimal(request.POST.get(f'line_{line_idx}_quantity', '1'))
            price = Decimal(request.POST.get(f'line_{line_idx}_unit_price', '0'))
            discount = Decimal(request.POST.get(f'line_{line_idx}_discount', '0'))
            tax = Decimal(request.POST.get(f'line_{line_idx}_tax_rate', str(invoice.tax_rate)))
            sku = request.POST.get(f'line_{line_idx}_sku', '')

            InvoiceLine.objects.create(
                hub_id=hub,
                invoice=invoice,
                description=desc,
                quantity=qty,
                unit_price=price,
                discount_percent=discount,
                tax_rate=tax,
                product_sku=sku,
                order=line_idx,
            )
            line_idx += 1

        invoice.calculate_totals()
        invoice.save(update_fields=[
            'subtotal', 'tax_amount', 'total', 'updated_at',
        ])

        return JsonResponse({'ok': True, 'id': str(invoice.pk)})

    series = InvoiceSeries.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    )

    return {
        'series_list': series,
    }


@login_required
@with_module_nav('invoicing', 'invoices')
@htmx_view('invoicing/pages/invoice_detail.html', 'invoicing/partials/invoice_detail_content.html')
def invoice_detail(request, pk):
    hub = _hub(request)
    invoice = Invoice.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False,
    ).select_related('series', 'customer', 'sale', 'employee', 'rectified_invoice').first()

    if not invoice:
        return {'error': _('Invoice not found')}

    lines = InvoiceLine.objects.filter(
        invoice=invoice, is_deleted=False,
    ).order_by('order')

    return {
        'invoice': invoice,
        'lines': lines,
    }


@login_required
@require_POST
def invoice_issue(request, pk):
    """Issue a draft invoice (assign number, mark as issued)."""
    hub = _hub(request)
    invoice = Invoice.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False, status='draft',
    ).first()

    if not invoice:
        return JsonResponse({'ok': False, 'error': _('Invoice not found or not a draft')}, status=400)

    success = invoice.issue()
    if not success:
        return JsonResponse({'ok': False, 'error': _('Could not issue invoice')}, status=400)

    return JsonResponse({'ok': True, 'number': invoice.number})


@login_required
@require_POST
def invoice_cancel(request, pk):
    """Cancel an issued invoice."""
    hub = _hub(request)
    invoice = Invoice.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False,
    ).first()

    if not invoice:
        return JsonResponse({'ok': False, 'error': _('Invoice not found')}, status=404)

    if invoice.status not in ('draft', 'issued'):
        return JsonResponse({'ok': False, 'error': _('Cannot cancel this invoice')}, status=400)

    invoice.status = 'cancelled'
    invoice.save(update_fields=['status', 'updated_at'])

    return JsonResponse({'ok': True})


@login_required
@require_POST
def invoice_delete(request, pk):
    """Soft-delete a draft invoice."""
    hub = _hub(request)
    invoice = Invoice.objects.filter(pk=pk, hub_id=hub, is_deleted=False).first()
    if not invoice:
        return JsonResponse({'ok': False}, status=404)
    if invoice.status not in ('draft',):
        messages.error(request, _('Only draft invoices can be deleted'))
        return _render_invoice_list(request, hub)
    invoice.is_deleted = True
    invoice.deleted_at = timezone.now()
    invoice.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    messages.success(request, _('Invoice deleted successfully'))
    return _render_invoice_list(request, hub)


@login_required
def invoice_print(request, pk):
    """Render invoice for printing."""
    hub = _hub(request)
    invoice = Invoice.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False,
    ).select_related('series', 'employee', 'rectified_invoice').first()

    if not invoice:
        return HttpResponse(_('Invoice not found'), status=404)

    lines = InvoiceLine.objects.filter(
        invoice=invoice, is_deleted=False,
    ).order_by('order')

    settings_obj = InvoicingSettings.get_settings(hub)

    html = render_to_string('invoicing/print/invoice.html', {
        'invoice': invoice,
        'lines': lines,
        'settings': settings_obj,
    })
    return HttpResponse(html)


# ---------------------------------------------------------------------------
# Series
# ---------------------------------------------------------------------------

@login_required
@with_module_nav('invoicing', 'series')
@htmx_view('invoicing/pages/series.html', 'invoicing/partials/series_content.html')
def series_list(request):
    hub = _hub(request)
    series = InvoiceSeries.objects.filter(
        hub_id=hub, is_deleted=False,
    ).annotate(
        invoice_count=Count(
            'invoice', filter=Q(invoice__is_deleted=False),
        ),
    ).order_by('prefix')

    context = {'series_list': series}

    # HTMX partial: swap only datatable body
    if request.htmx and request.htmx.target == 'datatable-body':
        return django_render(request, 'invoicing/partials/series_table.html', context)

    return context


@login_required
@with_module_nav('invoicing', 'series')
@htmx_view('invoicing/pages/series_form.html', 'invoicing/partials/series_form_content.html')
def series_add(request):
    hub = _hub(request)

    if request.method == 'POST':
        form = InvoiceSeriesForm(request.POST)
        if form.is_valid():
            series = form.save(commit=False)
            series.hub_id = hub
            series.save()
            return JsonResponse({'ok': True, 'id': str(series.pk)})
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    return {'form': InvoiceSeriesForm()}


@login_required
@with_module_nav('invoicing', 'series')
@htmx_view('invoicing/pages/series_form.html', 'invoicing/partials/series_form_content.html')
def series_edit(request, pk):
    hub = _hub(request)
    series = InvoiceSeries.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False,
    ).first()

    if not series:
        return {'error': _('Series not found')}

    if request.method == 'POST':
        form = InvoiceSeriesForm(request.POST, instance=series)
        if form.is_valid():
            form.save()
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    return {'form': InvoiceSeriesForm(instance=series), 'series': series}


@login_required
@require_POST
def series_delete(request, pk):
    hub = _hub(request)
    series = InvoiceSeries.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False,
    ).first()

    if not series:
        return JsonResponse({'ok': False, 'error': _('Series not found')}, status=404)

    # Check for existing invoices
    has_invoices = Invoice.objects.filter(
        series=series, is_deleted=False,
    ).exists()
    if has_invoices:
        return JsonResponse({
            'ok': False,
            'error': _('Cannot delete series with existing invoices'),
        }, status=400)

    series.is_deleted = True
    series.deleted_at = timezone.now()
    series.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])

    return JsonResponse({'ok': True})


@login_required
@require_POST
def series_toggle(request, pk):
    """Toggle a series active/inactive status."""
    hub = _hub(request)
    series = InvoiceSeries.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False,
    ).first()

    if not series:
        return JsonResponse({'ok': False, 'error': _('Series not found')}, status=404)

    series.is_active = not series.is_active
    series.save(update_fields=['is_active', 'updated_at'])

    status = _('activated') if series.is_active else _('deactivated')
    messages.success(request, _('Series %(status)s successfully') % {'status': status})
    return _render_series_list(request, hub)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@login_required
@with_module_nav('invoicing', 'settings')
@htmx_view('invoicing/pages/settings.html', 'invoicing/partials/settings_content.html')
def settings(request):
    hub = _hub(request)
    settings_obj = InvoicingSettings.get_settings(hub)
    form = InvoicingSettingsForm(instance=settings_obj)
    return {'form': form, 'settings': settings_obj}


@login_required
@require_POST
def settings_save(request):
    hub = _hub(request)
    settings_obj = InvoicingSettings.get_settings(hub)
    form = InvoicingSettingsForm(request.POST, instance=settings_obj)
    if form.is_valid():
        form.save()
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def settings_toggle(request):
    hub = _hub(request)
    settings_obj = InvoicingSettings.get_settings(hub)
    field = request.POST.get('field')
    allowed = {
        'auto_generate_invoice', 'require_customer',
    }
    if field not in allowed:
        return JsonResponse({'ok': False, 'error': _('Invalid field')}, status=400)

    current = getattr(settings_obj, field)
    setattr(settings_obj, field, not current)
    settings_obj.save(update_fields=[field, 'updated_at'])
    return JsonResponse({'ok': True, 'value': not current})


@login_required
@require_POST
def settings_input(request):
    hub = _hub(request)
    settings_obj = InvoicingSettings.get_settings(hub)
    field = request.POST.get('field')
    value = request.POST.get('value', '')
    allowed = {
        'company_name', 'company_tax_id', 'company_address',
        'company_phone', 'company_email', 'default_series_prefix',
        'invoice_footer',
    }
    if field not in allowed:
        return JsonResponse({'ok': False, 'error': _('Invalid field')}, status=400)

    setattr(settings_obj, field, value)
    settings_obj.save(update_fields=[field, 'updated_at'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def settings_reset(request):
    hub = _hub(request)
    settings_obj = InvoicingSettings.get_settings(hub)

    settings_obj.company_name = ''
    settings_obj.company_tax_id = ''
    settings_obj.company_address = ''
    settings_obj.company_phone = ''
    settings_obj.company_email = ''
    settings_obj.default_series_prefix = 'F'
    settings_obj.auto_generate_invoice = False
    settings_obj.require_customer = True
    settings_obj.invoice_footer = ''
    settings_obj.save()

    return JsonResponse({'ok': True})


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET'])
def api_invoices(request):
    """API endpoint to search invoices (e.g. for rectifying invoice lookup)."""
    hub = _hub(request)
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    invoices = Invoice.objects.filter(
        hub_id=hub, is_deleted=False,
        status__in=['issued', 'paid'],
    ).filter(
        Q(number__icontains=q) | Q(customer_name__icontains=q)
    ).values(
        'id', 'number', 'customer_name', 'total', 'issue_date', 'status',
    )[:20]

    return JsonResponse({'results': list(invoices)})
