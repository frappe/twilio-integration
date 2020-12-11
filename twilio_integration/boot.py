from __future__ import unicode_literals
import frappe

def boot_session(bootinfo):
	"""Include twilio enabled flag into boot.
	"""
	twilio_settings_enabled = frappe.db.get_single_value('Twilio Settings', 'enabled')
	twilio_enabled_for_user = frappe.db.get_value('Voice Call Settings', frappe.session.user, 'twilio_number')
	bootinfo.twilio_enabled = twilio_settings_enabled and twilio_enabled_for_user
