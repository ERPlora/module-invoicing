from django.urls import path
from . import views

app_name = 'invoicing'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Invoices
    path('invoices/', views.invoices_list, name='invoices'),
    path('invoices/ajax/', views.invoices_list_ajax, name='invoices_ajax'),
    path('invoices/new/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:invoice_id>/issue/', views.invoice_issue, name='invoice_issue'),
    path('invoices/<int:invoice_id>/cancel/', views.invoice_cancel, name='invoice_cancel'),
    path('invoices/<int:invoice_id>/print/', views.invoice_print, name='invoice_print'),

    # Series
    path('series/', views.series_list, name='series'),
    path('series/new/', views.series_create, name='series_create'),
    path('series/<int:series_id>/edit/', views.series_edit, name='series_edit'),
    path('series/<int:series_id>/delete/', views.series_delete, name='series_delete'),

    # Settings
    path('settings/', views.settings_view, name='settings'),
]
