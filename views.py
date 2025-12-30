from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum, Count
from django.utils.translation import gettext as _
from django.utils import timezone
from decimal import Decimal
import json

from apps.core.htmx import htmx_view
from .models import Invoice, InvoiceLine, InvoiceSeries, InvoicingConfig


# =============================================================================
# DASHBOARD
# =============================================================================

@require_http_methods(["GET"])
@htmx_view('invoicing/pages/dashboard.html', 'invoicing/partials/dashboard_content.html')
def dashboard(request):
    """
    Main invoicing dashboard with stats.
    """
    from apps.core.services.currency_service import format_currency

    today = timezone.now().date()
    current_month = today.replace(day=1)

    # Stats
    total_invoices = Invoice.objects.exclude(status=Invoice.Status.CANCELLED).count()
    month_invoices = Invoice.objects.filter(
        issue_date__gte=current_month
    ).exclude(status=Invoice.Status.CANCELLED).count()

    month_total = Invoice.objects.filter(
        issue_date__gte=current_month,
        status__in=[Invoice.Status.ISSUED, Invoice.Status.PAID]
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')

    pending_amount = Invoice.objects.filter(
        status=Invoice.Status.ISSUED
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')

    return {
        'page_title': _('Facturación'),
        'total_invoices': total_invoices,
        'month_invoices': month_invoices,
        'month_total_formatted': format_currency(month_total),
        'pending_amount_formatted': format_currency(pending_amount),
    }


# =============================================================================
# INVOICES
# =============================================================================

@require_http_methods(["GET"])
def invoices_list(request):
    """
    List all invoices with filters and infinite scroll.
    """
    from apps.core.htmx import InfiniteScrollPaginator

    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    invoices = Invoice.objects.select_related('series').all()

    # Filters
    if status_filter:
        invoices = invoices.filter(status=status_filter)

    if date_from:
        invoices = invoices.filter(issue_date__gte=date_from)

    if date_to:
        invoices = invoices.filter(issue_date__lte=date_to)

    if search:
        invoices = invoices.filter(
            Q(number__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(customer_tax_id__icontains=search)
        )

    invoices = invoices.order_by('-issue_date', '-created_at')

    # Pagination with infinite scroll
    per_page = int(request.GET.get('per_page', 25))
    paginator = InfiniteScrollPaginator(invoices, per_page=per_page)
    page_data = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title': _('Facturas'),
        'invoices': page_data['items'],
        'has_next': page_data['has_next'],
        'next_page': page_data['next_page'],
        'total_count': page_data['total_count'],
        'page_number': page_data['page_number'],
        'search': search,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'per_page': per_page,
    }

    # Determine which template to render
    is_htmx = request.headers.get('HX-Request') or request.GET.get('partial') == 'true'
    page_num = page_data['page_number']

    # HTMX partial for table only (filters use this target)
    if request.headers.get('HX-Target') == 'invoices-table-container':
        return render(request, 'invoicing/partials/invoices_table.html', context)

    if not is_htmx:
        return render(request, 'invoicing/pages/invoices.html', context)

    if page_num > 1:
        # Subsequent pages - only return table rows + loader
        return render(request, 'invoicing/partials/invoices_rows_infinite.html', context)

    # First HTMX request - return full content partial
    return render(request, 'invoicing/partials/invoices_content.html', context)


@require_http_methods(["GET"])
def invoices_list_ajax(request):
    """
    API: List invoices for AJAX table.
    """
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    invoices = Invoice.objects.select_related('series').all()

    # Filters
    if status_filter:
        invoices = invoices.filter(status=status_filter)

    if date_from:
        invoices = invoices.filter(issue_date__gte=date_from)

    if date_to:
        invoices = invoices.filter(issue_date__lte=date_to)

    if search:
        invoices = invoices.filter(
            Q(number__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(customer_tax_id__icontains=search)
        )

    invoices = invoices.order_by('-issue_date', '-created_at')[:100]

    data = []
    for inv in invoices:
        data.append({
            'id': inv.id,
            'number': inv.number or _('Borrador'),
            'customer_name': inv.customer_name,
            'customer_tax_id': inv.customer_tax_id,
            'issue_date': inv.issue_date.strftime('%Y-%m-%d'),
            'total': float(inv.total),
            'status': inv.status,
            'status_display': inv.get_status_display(),
            'invoice_type': inv.invoice_type,
            'invoice_type_display': inv.get_invoice_type_display(),
        })

    return JsonResponse({'success': True, 'invoices': data})


@require_http_methods(["GET"])
@htmx_view('invoicing/pages/invoice_detail.html', 'invoicing/partials/invoice_detail_content.html')
def invoice_detail(request, invoice_id):
    """
    View invoice details.
    """
    invoice = get_object_or_404(Invoice.objects.prefetch_related('lines'), id=invoice_id)

    return {
        'invoice': invoice,
        'page_title': f'{_("Factura")}: {invoice.number or _("Borrador")}',
    }


@htmx_view('invoicing/pages/invoice_form.html', 'invoicing/partials/invoice_form_content.html')
def _invoice_form_view(request, series=None, invoice=None):
    """
    Helper view for invoice form (create/edit).
    """
    series_list = InvoiceSeries.objects.filter(is_active=True)
    config = InvoicingConfig.get_config()

    return {
        'page_title': _('Nueva Factura') if not invoice else f'{_("Editar Factura")}: {invoice.number or _("Borrador")}',
        'series_list': series_list,
        'config': config,
        'series': series,
        'invoice': invoice,
    }


@require_http_methods(["GET", "POST"])
def invoice_create(request):
    """
    Create a new invoice.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

            # Get or create default series
            series = InvoiceSeries.objects.filter(is_default=True).first()
            if not series:
                series = InvoiceSeries.objects.first()
            if not series:
                series = InvoiceSeries.objects.create(
                    prefix='F',
                    name=_('Facturas'),
                    is_default=True
                )

            invoice = Invoice.objects.create(
                series=series,
                customer_name=data.get('customer_name', ''),
                customer_tax_id=data.get('customer_tax_id', ''),
                customer_address=data.get('customer_address', ''),
                customer_email=data.get('customer_email', ''),
                customer_phone=data.get('customer_phone', ''),
                customer_id=data.get('customer_id'),
                sale_id=data.get('sale_id'),
                tax_rate=Decimal(data.get('tax_rate', '21')),
                notes=data.get('notes', ''),
                status=Invoice.Status.DRAFT,
            )

            # Add lines
            lines_data = data.get('lines', [])
            for i, line in enumerate(lines_data):
                InvoiceLine.objects.create(
                    invoice=invoice,
                    product_id=line.get('product_id'),
                    product_sku=line.get('sku', ''),
                    description=line.get('description', ''),
                    quantity=Decimal(str(line.get('quantity', 1))),
                    unit_price=Decimal(str(line.get('unit_price', 0))),
                    discount_percent=Decimal(str(line.get('discount', 0))),
                    tax_rate=Decimal(str(line.get('tax_rate', 21))),
                    order=i,
                )

            # Calculate totals
            invoice.calculate_totals()
            invoice.save()

            return JsonResponse({
                'success': True,
                'message': _('Factura creada correctamente'),
                'invoice_id': invoice.id
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # GET - show form
    return _invoice_form_view(request)


@require_http_methods(["POST"])
def invoice_issue(request, invoice_id):
    """
    Issue a draft invoice (assign number and change status).
    """
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)

        if invoice.status != Invoice.Status.DRAFT:
            return JsonResponse({
                'success': False,
                'error': _('Solo se pueden emitir facturas en borrador')
            })

        # Generate number and issue
        invoice.number = invoice.series.get_next_number()
        invoice.status = Invoice.Status.ISSUED
        invoice.issue_date = timezone.now().date()
        invoice.save()

        return JsonResponse({
            'success': True,
            'message': _('Factura emitida correctamente'),
            'number': invoice.number
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
def invoice_cancel(request, invoice_id):
    """
    Cancel an invoice.
    """
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)

        if invoice.status == Invoice.Status.CANCELLED:
            return JsonResponse({
                'success': False,
                'error': _('La factura ya está anulada')
            })

        invoice.status = Invoice.Status.CANCELLED
        invoice.save()

        return JsonResponse({
            'success': True,
            'message': _('Factura anulada correctamente')
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["GET"])
def invoice_print(request, invoice_id):
    """
    Printable view of invoice (for window.print()).
    """
    invoice = get_object_or_404(Invoice.objects.prefetch_related('lines'), id=invoice_id)
    config = InvoicingConfig.get_config()

    context = {
        'invoice': invoice,
        'config': config,
    }

    return render(request, 'invoicing/print/invoice.html', context)


# =============================================================================
# SERIES
# =============================================================================

@require_http_methods(["GET"])
@htmx_view('invoicing/pages/series.html', 'invoicing/partials/series_content.html')
def series_list(request):
    """
    List invoice series.
    """
    series = InvoiceSeries.objects.all()

    return {
        'page_title': _('Series de Facturación'),
        'series_list': series,
    }


@htmx_view('invoicing/pages/series_form.html', 'invoicing/partials/series_form_content.html')
def _series_form_view(request, series=None):
    """
    Helper view for series form (create/edit).
    """
    return {
        'page_title': _('Nueva Serie') if not series else f'{_("Editar Serie")}: {series.prefix}',
        'series': series,
    }


@require_http_methods(["GET", "POST"])
def series_create(request):
    """
    Create a new invoice series.
    """
    if request.method == 'POST':
        try:
            prefix = request.POST.get('prefix', '').upper().strip()
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            number_digits = int(request.POST.get('number_digits', 6))
            is_default = request.POST.get('is_default') == 'on'

            if not prefix or not name:
                return JsonResponse({
                    'success': False,
                    'error': _('Prefijo y nombre son obligatorios')
                })

            if InvoiceSeries.objects.filter(prefix=prefix).exists():
                return JsonResponse({
                    'success': False,
                    'error': _('Ya existe una serie con ese prefijo')
                })

            InvoiceSeries.objects.create(
                prefix=prefix,
                name=name,
                description=description,
                number_digits=number_digits,
                is_default=is_default,
            )

            return JsonResponse({
                'success': True,
                'message': _('Serie creada correctamente')
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # GET - show form
    return _series_form_view(request)


@require_http_methods(["GET", "POST"])
def series_edit(request, series_id):
    """
    Edit an invoice series.
    """
    series = get_object_or_404(InvoiceSeries, id=series_id)

    if request.method == 'POST':
        try:
            series.name = request.POST.get('name', '').strip()
            series.description = request.POST.get('description', '').strip()
            series.number_digits = int(request.POST.get('number_digits', 6))
            series.is_active = request.POST.get('is_active') == 'on'
            series.is_default = request.POST.get('is_default') == 'on'
            series.save()

            return JsonResponse({
                'success': True,
                'message': _('Serie actualizada correctamente')
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # GET - show form
    return _series_form_view(request, series=series)


@require_http_methods(["POST"])
def series_delete(request, series_id):
    """
    Delete an invoice series (only if no invoices use it).
    """
    try:
        series = get_object_or_404(InvoiceSeries, id=series_id)

        if Invoice.objects.filter(series=series).exists():
            return JsonResponse({
                'success': False,
                'error': _('No se puede eliminar: hay facturas con esta serie')
            })

        series.delete()

        return JsonResponse({
            'success': True,
            'message': _('Serie eliminada correctamente')
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# =============================================================================
# SETTINGS
# =============================================================================

@require_http_methods(["GET"])
@htmx_view('invoicing/pages/settings.html', 'invoicing/partials/settings_content.html')
def settings_view(request):
    """
    Invoicing module settings.
    """
    config = InvoicingConfig.get_config()
    series_list = InvoiceSeries.objects.filter(is_active=True)

    # Build series options for setting_select component
    series_options = [
        {'value': s.prefix, 'label': f"{s.prefix} - {s.name}"}
        for s in series_list
    ]
    if not series_options:
        series_options = [{'value': 'F', 'label': 'F - Default'}]

    return {
        'page_title': _('Configuración'),
        'config': config,
        'series_options': series_options,
    }


@require_http_methods(["POST"])
def settings_save(request):
    """Save invoicing settings via JSON."""
    try:
        data = json.loads(request.body)
        config = InvoicingConfig.get_config()

        # Company Information
        config.company_name = data.get('company_name', '').strip()
        config.company_tax_id = data.get('company_tax_id', '').strip()
        config.company_address = data.get('company_address', '').strip()
        config.company_phone = data.get('company_phone', '').strip()
        config.company_email = data.get('company_email', '').strip()

        # Invoice Settings
        config.default_series = data.get('default_series', 'F').strip()
        config.auto_generate_invoice = data.get('auto_generate_invoice', False)
        config.require_customer = data.get('require_customer', False)

        # Invoice Footer
        config.invoice_footer = data.get('invoice_footer', '').strip()

        config.save()
        return JsonResponse({'success': True, 'message': _('Settings saved')})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': _('Invalid JSON')}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
