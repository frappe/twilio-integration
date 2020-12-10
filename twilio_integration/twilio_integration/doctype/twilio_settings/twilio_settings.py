# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils.password import get_decrypted_password
from frappe.utils import get_request_site_address

from six import string_types
import re
from json import loads, dumps
from random import randrange

from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse, Dial
from frappe.website.render import build_response

class TwilioSettings(Document):
	friendly_resource_name = "ERPNext" # Name used by twilio applications and API keys created behind the scenes.

	def validate(self):
		self.validate_twilio_account()

	def on_update(self):
		twilio = Client(self.account_sid, self.get_password("auth_token"))
		self.set_api_credentials(twilio)
		self.set_application_credentials(twilio)
		self.reload()

	def validate_twilio_account(self):
		try:
			twilio = Client(self.account_sid, self.get_password("auth_token"))
			twilio.api.accounts(self.account_sid).fetch()
			return twilio
		except Exception:
			frappe.throw(_("Invalid Account SID or Auth Token."))

	def set_api_credentials(self, twilio):
		"""Generate Twilio API credentials if not exist and update them.
		"""
		if self.api_key and self.api_secret:
			return
		new_key = self.create_api_key(twilio)
		self.api_key = new_key.sid
		self.api_secret = new_key.secret
		frappe.db.set_value('Twilio Settings', 'Twilio Settings', {
			'api_key': self.api_key,
			'api_secret': self.api_secret
		})

	def set_application_credentials(self, twilio):
		"""Generate TwiML app credentials if not exist and update them.
		"""
		credentials = self.get_application(twilio) or self.create_application(twilio)
		self.twiml_sid = credentials.sid
		frappe.db.set_value('Twilio Settings', 'Twilio Settings', 'twiml_sid', self.twiml_sid)

	def create_api_key(self, twilio):
		"""Create API keys in twilio account.
		"""
		try:
			return twilio.new_keys.create(friendly_name=self.friendly_resource_name)
		except Exception:
			frappe.log_error(title=_("Twilio API credential creation error."))
			frappe.throw(_("Twilio API credential creation error."))

	def get_twilio_voice_url(self):
		#TODO: FixMe
		voice_url = "/api/method/twilio_integration.twilio_integration.doctype.twilio_settings.twilio_settings.voice"
		# return frappe.utils.get_url(voice_url)
		return "http://127.0.0.1" + voice_url

	def get_application(self, twilio, friendly_name=None):
		"""Get TwiML App from twilio account if exists.
		"""
		friendly_name = friendly_name or self.friendly_resource_name
		applications = twilio.applications.list(friendly_name)
		return applications and applications[0]

	def create_application(self, twilio, friendly_name=None):
		"""Create TwilML App in twilio account.
		"""
		friendly_name = friendly_name or self.friendly_resource_name
		application = twilio.applications.create(
						voice_method='GET',
						voice_url=self.get_twilio_voice_url(),
						friendly_name=friendly_name
					)
		return application


def send_whatsapp_message(sender, receiver_list, message):
	twilio_settings = frappe.get_doc("Twilio Settings")
	if not twilio_settings.enabled:
		frappe.throw(_("Please enable twilio settings before sending WhatsApp messages"))

	if isinstance(receiver_list, string_types):
		receiver_list = loads(receiver_list)
		if not isinstance(receiver_list, list):
			receiver_list = [receiver_list]

	auth_token = get_decrypted_password("Twilio Settings", "Twilio Settings", 'auth_token')
	client = Client(twilio_settings.account_sid, auth_token)
	args = {
		"from_": 'whatsapp:{}'.format(sender),
		"body": message
	}

	failed_delivery = []
	for rec in receiver_list:
		args.update({"to": 'whatsapp:{}'.format(rec)})
		resp = _send_whatsapp(args, client)
		if not resp or resp.error_message:
			failed_delivery.append(rec)

	if failed_delivery:
		frappe.log_error(_("The message wasn't correctly delivered to: {}".format(", ".join(failed_delivery))), _('Delivery Failed'))


def _send_whatsapp(message_dict, client):
	response = frappe._dict()
	try:
		response = client.messages.create(**message_dict)
	except Exception as e:
		frappe.log_error(e, title = _('Twilio WhatsApp Message Error'))

	return response


@frappe.whitelist(allow_guest=True)
def voice(**kwargs):
	try:
		twilio_settings = frappe.get_doc("Twilio Settings")
		default_outgoing = twilio_settings.outgoing_voice_medium
		args = frappe._dict(kwargs)
		phone_pattern = re.compile(r"^[\d\+\-\(\) ]+$")
		resp = VoiceResponse()
		if args.To != '':
			phone = args.To
			recording_status_callback = get_request_site_address(True) + "/api/method/twilio_integration.twilio_integration.doctype.twilio_settings.twilio_settings.update_recording_info"

			dial = Dial(caller_id=default_outgoing, record=twilio_settings.record_calls,
				recording_status_callback=recording_status_callback, recording_status_callback_event='completed')

			# wrap the phone number or client name in the appropriate TwiML verb
			# by checking if the number given has only digits and format symbols
			if phone_pattern.match(phone):
				dial.number(phone)
			else:
				dial.client(phone)
			resp.append(dial)
			create_call_log(args)
		else:
			resp.say("Thanks for calling!")

		return build_response('', str(resp), 200, headers = {"Content-Type": "text/xml; charset=utf-8"})
	except Exception:
		frappe.log_error("Twilio call Error")

@frappe.whitelist()
def create_call_log(call_payload):
	default_outgoing = frappe.db.get_single_value("Twilio Settings", "outgoing_voice_medium")
	call_log = frappe.get_doc({
		"doctype": "Call Log",
		"id": call_payload.get("CallSid"),
		"to": call_payload.get("To"),
		"status": "Ringing",
		"medium": default_outgoing,
		"from": default_outgoing
	})
	call_log.flags.ignore_permissions = True
	call_log.save()

@frappe.whitelist()
def update_call_log(call_sid, status="In Progress"):
	# update the call log status

	if not frappe.db.exists("Call Log", call_sid): return

	call_details = get_call_info(call_sid)
	call_log = frappe.get_doc("Call Log", call_sid)
	call_log.status = status
	call_log.duration = call_details.duration
	call_log.flags.ignore_permissions = True
	call_log.save()

def get_call_info(call_sid):
	twilio_settings = frappe.get_doc("Twilio Settings")
	client = Client(twilio_settings.account_sid, twilio_settings.get_password("auth_token"))
	return client.calls(call_sid).fetch()

@frappe.whitelist(allow_guest=True)
def update_recording_info(**kwargs):
	try:
		args = frappe._dict(kwargs)
		recording_url = args.RecordingUrl
		call_sid = args.CallSid
		frappe.db.set_value("Call Log", call_sid, "recording_url", recording_url)
	except:
		frappe.log_error(title=_("Failed to capture Twilio recording"))
