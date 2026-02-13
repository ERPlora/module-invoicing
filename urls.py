"""Invoicing URL Configuration."""

from django.urls import path
from . import views

app_name = 'invoicing'

urlpatterns = [
    # Dashboard
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Invoices
    path('invoices/', views.invoices_list, name='invoices'),
    path('invoices/new/', views.invoice_create, name='invoice_create'),
    path('invoices/<uuid:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<uuid:pk>/issue/', views.invoice_issue, name='invoice_issue'),
    path('invoices/<uuid:pk>/cancel/', views.invoice_cancel, name='invoice_cancel'),
    path('invoices/<uuid:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('invoices/<uuid:pk>/print/', views.invoice_print, name='invoice_print'),

    # Series
    path('series/', views.series_list, name='series'),
    path('series/add/', views.series_add, name='series_add'),
    path('series/<uuid:pk>/edit/', views.series_edit, name='series_edit'),
    path('series/<uuid:pk>/delete/', views.series_delete, name='series_delete'),
    path('series/<uuid:pk>/toggle/', views.series_toggle, name='series_toggle'),

    # Settings
    path('settings/', views.settings, name='settings'),
    path('settings/save/', views.settings_save, name='settings_save'),
    path('settings/toggle/', views.settings_toggle, name='settings_toggle'),
    path('settings/input/', views.settings_input, name='settings_input'),
    path('settings/reset/', views.settings_reset, name='settings_reset'),

    # API
    path('api/invoices/', views.api_invoices, name='api_invoices'),
]
