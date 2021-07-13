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
			'from_': self.from_,
			'to': self.to,
			'body': self.message,
			'status_callback': 'https://01d3954808ab.ngrok.io/api/method/twilio_integration.twilio_integration.api.whatsapp_message_status'
		}
		if self.media_link:
			args['media_url'] = [self.media_link]

		return args

def send_bulk_whatsapp_message(receiver_list, message, doctype, docname, media=None):
	if isinstance(receiver_list, string_types):
		receiver_list = loads(receiver_list)
		if not isinstance(receiver_list, list):
			receiver_list = [receiver_list]

	for rec in receiver_list:
		_send_whatsapp(rec, message, doctype, docname)

def _send_whatsapp(to, message, doctype=None, docname=None, media=None):
	response = frappe._dict()
	sender = frappe.db.get_single_value('Twilio Settings', 'whatsapp_no')
	wa_msg = frappe.get_doc({
			'doctype': 'WhatsApp Message',
			'from_': 'whatsapp:{}'.format(sender),
			'to': 'whatsapp:{}'.format(to),
			'message': message,
			'reference_doctype': doctype,
			'reference_document_name': docname,
			'media_link': media
		}).insert(ignore_permissions=True)

	wa_msg.send()

def incoming_message(args):
	wa_msg = frappe.get_doc({
			'doctype': 'WhatsApp Message',
			'from_': args.From,
			'to': args.To,
			'message': args.Body,
			'profile_name': args.ProfileName,
			'sent_received': args.SmsStatus.title(),
			'id': args.MessageSid,
			'send_on': frappe.utils.now(),
			'status': 'Received'
		}).insert(ignore_permissions=True)

