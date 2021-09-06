# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_site_url
from twilio_integration.twilio_integration.doctype.whatsapp_message.whatsapp_message import WhatsAppMessage

supported_file_ext = ['jpg', 
	'jpeg',
	'png',
	'mp3',
	'ogg',
	'amr',
	'pdf',
	'mp4'
]

class WhatsAppCampaign(Document):
	def validate(self):
		if self.scheduled_time and self.status != 'Completed':
			current_time = frappe.utils.now_datetime()
			scheduled_time = frappe.utils.get_datetime(self.scheduled_time)

			if scheduled_time < current_time:
				frappe.throw(_("Scheduled Time must be a future time."))

			self.status = 'Scheduled'

		self.all_missing_recipients()
	
	def validate_attachment(self):
		attachment = self.get_attachment()
		if attachment:
			if attachment.file_size > 16777216:
				frappe.throw(_('Attachment size must be less than 16MB.'))

			if attachment.is_private:
				frappe.throw(_('Attachment must be public.'))

			if attachment.get_extension() not in supported_file_ext:
				frappe.throw(_('Attachment format not supported.'))

	def get_attachment(self):
		file = frappe.db.get_value("File", {"attached_to_name": self.doctype, "attached_to_doctype": self.name, "is_private":0}, 'name')

		if file:
			return frappe.get_doc('File', file)
		return None

	def get_whatsapp_contact(self):
		contacts = [recipient.whatsapp_no for recipient in self.recipients if recipient.whatsapp_no]

		return contacts
	
	def all_missing_recipients(self):
		for recipient in self.recipients:
			if not recipient.whatsapp_no:
				recipient.whatsapp_no = frappe.db.get_value(recipient.campaign_for, recipient.recipient, 'whatsapp_no')
		
		self.total_participants = len(self.recipients)

	@frappe.whitelist()
	def get_doctype_list(self):
		standard_doctype = frappe.db.sql_list("""SELECT dt.parent FROM `tabDocField` 
			df INNER JOIN `tabDoctype` dt ON dt.name = dt.parent
			WHERE df.fieldname='whatsapp_no' AND dt.istable = 0 AND dt.issingle = 0 AND dt.is_tree = 0""")
		
		custom_doctype = frappe.db.sql_list("""SELECT dt FROM `tabCustom Field`
			cf INNER JOIN `tabDoctype` dt ON dt.name = cf.dt
			WHERE cf.fieldname='whatsapp_no' AND dt.istable = 0 AND dt.issingle = 0 AND dt.is_tree = 0""")

		return standard_doctype + custom_doctype

	@frappe.whitelist()
	def send_now(self):
		self.validate_attachment()
		media = self.get_attachment()
		self.db_set('status', 'In Progress')
		if media:
			media = get_site_url(frappe.local.site) + media.file_url

		WhatsAppMessage.send_whatsapp_message(
			receiver_list = self.get_whatsapp_contact(),
			message = self.message,
			doctype = self.doctype,
			docname = self.name,
			media = media
		)

		self.db_set('status', 'Completed')


