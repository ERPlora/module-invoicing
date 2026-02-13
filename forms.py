"""Invoicing forms."""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import InvoiceSeries, InvoicingSettings


class InvoiceSeriesForm(forms.ModelForm):
    class Meta:
        model = InvoiceSeries
        fields = [
            'prefix', 'name', 'description',
            'number_digits', 'is_active', 'is_default',
        ]
        widgets = {
            'prefix': forms.TextInput(attrs={'class': 'input', 'style': 'text-transform:uppercase'}),
            'name': forms.TextInput(attrs={'class': 'input'}),
            'description': forms.Textarea(attrs={'class': 'textarea', 'rows': 2}),
            'number_digits': forms.NumberInput(attrs={'class': 'input', 'min': '1', 'max': '10'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'toggle'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'toggle'}),
        }


class InvoicingSettingsForm(forms.ModelForm):
    class Meta:
        model = InvoicingSettings
        fields = [
            'company_name', 'company_tax_id', 'company_address',
            'company_phone', 'company_email',
            'default_series_prefix', 'auto_generate_invoice',
            'require_customer', 'invoice_footer',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'input'}),
            'company_tax_id': forms.TextInput(attrs={'class': 'input'}),
            'company_address': forms.Textarea(attrs={'class': 'textarea', 'rows': 2}),
            'company_phone': forms.TextInput(attrs={'class': 'input'}),
            'company_email': forms.EmailInput(attrs={'class': 'input'}),
            'default_series_prefix': forms.TextInput(attrs={'class': 'input'}),
            'auto_generate_invoice': forms.CheckboxInput(attrs={'class': 'toggle'}),
            'require_customer': forms.CheckboxInput(attrs={'class': 'toggle'}),
            'invoice_footer': forms.Textarea(attrs={'class': 'textarea', 'rows': 3}),
        }
