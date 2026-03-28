"""Scheduled task handlers for invoicing module."""
import logging
logger = logging.getLogger(__name__)

def send_overdue_reminders(payload):
    """Send payment reminders for overdue invoices."""
    logger.info('invoicing.send_overdue_reminders called')
    return {'status': 'not_implemented'}
