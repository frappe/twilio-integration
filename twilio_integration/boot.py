from __future__ import unicode_literals
import frappe

def boot_session(bootinfo):
    """Include twilio enabled flag into boot.
    """     
    bootinfo.twilio_settings_enabled = frappe.db.get_single_value('Twilio Settings', 'enabled')
