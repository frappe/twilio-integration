# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_site_url
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
		attachment = self.get_attachments()
		if attachment:
			if attachment.file_size > 16777216:
				frappe.throw(_('Attachment size must be less than 16MB.'))

			if attachment.is_private:
				frappe.throw(_('Attachment must be public.'))

			if attachment.get_extension() not in ['jpg', 'jpeg', 'png', 'mp3', 'ogg', 'amr', 'pdf', 'mp4']:
				frappe.throw(_('Attachment format not supported.'))

	# def get_attachment(self):
	# 	return frappe.get_doc(doctype = "File",
	# 		filters = {"attached_to_name": self.doctype, "attached_to_doctype": self.name, "is_private":0})

	def get_whatsapp_contact(self):
		contacts = []

		for row in self.recipients:
			if row.whatsapp_no:
				contacts.append(row.whatsapp_no)	
		
		return contacts
	
	def save(self):
		for recipient in self.recipients:
			if not recipient.whatsapp_no:
				recipient.whatsapp_no = frappe.db.get_value(recipient.campaign_for, recipient.recipient, 'whatsapp_no')
		
		self.total_participants = len(self.recipients)

	@frappe.whitelist()
	def get_doctype_list(self):
		doctypes = list(frappe.db.sql_list("""SELECT dt.parent FROM `tabDocField` 
			df INNER JOIN `tabDoctype` dt ON dt.name = dt.parent
			WHERE df.fieldname='whatsapp_no' and dt.istable = 0 and dt.issingle = 0 and dt.is_tree = 0""") + 
			frappe.db.sql_list("""SELECT dt FROM `tabCustom Field`
			cf INNER JOIN `tabDoctype` dt ON dt.name = cf.dt
			WHERE cf.fieldname='whatsapp_no' and dt.istable = 0 and dt.issingle = 0 and dt.is_tree = 0"""))

		return doctypes

	@frappe.whitelist()
	def send_now(self):
		self.validate_attachment()
		media = self.get_attachments()
		if media:
			media = get_site_url() + media.file_url

		send_bulk_whatsapp_message(
			sender = '+14155238886',
			receiver_list = self.get_whatsapp_contact(),
			message = self.message,
			doctype = self.doctype,
			docname = self.name,
			media = media
		)



