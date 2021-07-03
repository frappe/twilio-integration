# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from six import string_types
from frappe.utils.password import get_decrypted_password
from frappe import _
from twilio_integration.twilio_integration.doctype.twilio_settings.twilio_settings import get_twilio_client

class WhatsAppMessage(Document):
	def send(self):
		client = get_twilio_client()
		message_dict = self.get_message_dict()
		response = frappe._dict()

		try:
			response = client.messages.create(**message_dict)
			print('`````````````````````````````````')
			print(response.__dict__)
			print('`````````````````````````````````')
			self.sent_received = 'Sent'
			self.status = response.status.title()
			self.id = response.sid
			self.send_on = response.date_sent
			self.save(ignore_permissions=True)
		
		except Exception as e:
			self.db_set('status', "Error")
			frappe.log_error(e, title = _('Twilio WhatsApp Message Error'))
	
	def get_message_dict(self):
		args = {
			"media_url": ['http://commondatastorage.googleapis.com/codeskulptor-assets/gutenberg.jpg'],
			"from_": self.from_,
			"to": self.to,
			"body": self.message
		}
		return args

def send_bulk_whatsapp_message(sender, receiver_list, message, doctype, docname):
	if isinstance(receiver_list, string_types):
		receiver_list = loads(receiver_list)
		if not isinstance(receiver_list, list):
			receiver_list = [receiver_list]

	for rec in receiver_list:
		_send_whatsapp(sender, rec, message, doctype, docname)

def _send_whatsapp(from_, to, message, doctype=None, docname=None):
	response = frappe._dict()

	wa_msg = frappe.get_doc({
			'doctype': 'WhatsApp Message',
			'from_': 'whatsapp:{}'.format(from_),
			'to': 'whatsapp:{}'.format(to),
			'message': message,
			'reference_doctype': doctype,
			'reference_document_name': docname
		}).insert(ignore_permissions=True)

	wa_msg.send()

	
