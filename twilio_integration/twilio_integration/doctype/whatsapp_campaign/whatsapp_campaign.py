# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from twilio_integration.twilio_integration.doctype.whatsapp_message.whatsapp_message import send_bulk_whatsapp_message

class WhatsAppCampaign(Document):
	def validate(self):
		if self.scheduled_time and self.status != 'Completed':
			current_time = frappe.utils.now_datetime()
			scheduled_time = frappe.utils.get_datetime(self.scheduled_time)

			if scheduled_time < current_time:
				frappe.throw(_("Scheduled Time must be a future time."))

			self.status = 'Scheduled'
	
	def validate_attachment(self):
		attachment = self.get_attachment()
		if attachment:
			if attachment.file_size > 16777216:
				frappe.throw(_('Attachment size must be less than 16MB.'))

			if attachment.is_private:
				frappe.throw(_('Attachment must be public.'))

	def get_attachment(self):
		return frappe.db.get_doc("File",
			filters = {"attached_to_name": self.doctype, "attached_to_doctype": self.name, "is_private":0})

	def get_whatsapp_contact(self):
		contacts = ['+919807046460', '+918554066835']

		for row in self.recipients:
			rec = {
				'Lead': 'mobile_no',
				'Contact': 'mobile_no',
				'Customer': 'mobile_no'
			}
			if row.campaign_for:
				mobile_no = frappe.db.get_value(row.campaign_for, row.recipient, rec[row.campaign_for])
				if mobile_no:
					contacts.append(mobile_no)	
		
		return contacts
	
	@frappe.whitelist()
	def send_now(self):
		self.validate_attachment()
		send_bulk_whatsapp_message(
			sender = '+14155238886',
			receiver_list = self.get_whatsapp_contact(),
			message = self.message,
			doctype = self.doctype,
			docname = self.name
		)



