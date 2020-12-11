import re
import json
from werkzeug.wrappers import Response
from twilio.rest import Client as TwilioClient
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse, Dial

import frappe
from .utils import get_public_url

class Twilio:
	"""Twilio connector over TwilioClient.
	"""
	def __init__(self, settings):
		"""
		:param settings: `Twilio Settings` doctype
		"""
		self.settings = settings
		self.account_sid = settings.account_sid
		self.application_sid = settings.twiml_sid
		self.api_key = settings.api_key
		self.api_secret = settings.get_password("api_secret")
		self.twilio_client = TwilioClient(self.account_sid, settings.get_password("auth_token"))

	@classmethod
	def connect(self):
		"""Make a twilio connection.
		"""
		settings = frappe.get_doc("Twilio Settings")
		if not (settings and settings.enabled):
			return
		return Twilio(settings=settings)

	def get_phone_numbers(self):
		"""Get account's twilio phone numbers.
		"""
		numbers = self.twilio_client.incoming_phone_numbers.list()
		return [n.phone_number for n in numbers]

	def generate_voice_access_token(self, from_number: str, identity_postfix=None, ttl=60*60):
		"""Generates a token required to make voice calls from the browser.
		"""
		# identity is used by twilio to identify the user uniqueness at browser(or any endpoints).
		identity = from_number
		if identity_postfix:
			identity = '_'.join([identity, self.safe_identity(identity_postfix)])

		# Create access token with credentials
		token = AccessToken(self.account_sid, self.api_key, self.api_secret, identity=identity, ttl=ttl)

		# Create a Voice grant and add to token
		voice_grant = VoiceGrant(
			outgoing_application_sid=self.application_sid,
			incoming_allow=True, # Allow incoming calls
		)
		token.add_grant(voice_grant)
		return token.to_jwt()

	@classmethod
	def safe_identity(cls, identity: str):
		"""Create a safe identity by replacing unsupported special charaters with '-'.
		Twilio Client JS fails to make a call connection if identity has special characters like @, [, / etc)
		https://www.twilio.com/docs/voice/client/errors (#31105)
		"""
		return re.sub(r'[^a-zA-Z0-9_.-]+', '-', identity).strip()

	def generate_twilio_dial_response(self, from_number: str, to_number: str):
		"""Generates voice call instructions needed for twilio.
		"""
		url_path = "/api/method/twilio_integration.twilio_integration.api.update_recording_info"
		recording_status_callback = get_public_url(url_path)

		resp = VoiceResponse()
		dial = Dial(
			caller_id=from_number,
			record=self.settings.record_calls,
			recording_status_callback=recording_status_callback,
			recording_status_callback_event='completed'
		)
		dial.number(to_number)
		resp.append(dial)
		return resp

	def get_call_info(self, call_sid):
		return self.twilio_client.calls(call_sid).fetch()


@frappe.whitelist()
def get_twilio_phone_numbers():
	twilio = Twilio.connect()
	return (twilio and twilio.get_phone_numbers()) or []

@frappe.whitelist()
def generate_access_token():
	"""Returns access token that is required to authenticate Twilio Client SDK.
	"""
	twilio = Twilio.connect()
	if not twilio:
		return {}

	from_number = frappe.db.get_value('Voice Call Settings', frappe.session.user, 'twilio_number')
	if not from_number:
		return {
			"ok": False,
			"error": "caller_phone_identity_missing",
			"detail": "Phone number is not mapped to the caller"
		}

	token=twilio.generate_voice_access_token(from_number=from_number, identity_postfix=frappe.session.user)
	return {
		'token': token.decode('utf-8')
	}

@frappe.whitelist(allow_guest=True)
def voice(**kwargs):
	"""This is a webhook called by twilio to get instructions when the voice call request comes to twilio server.
	"""
	def _get_caller_number(user):
		return user.replace('client:', '').split('_')[0]

	args = frappe._dict(kwargs)
	twilio = Twilio.connect()
	if not twilio:
		return

	assert args.AccountSid == twilio.account_sid
	assert args.ApplicationSid == twilio.application_sid

	# Generate TwiML instructions to make a call
	args.from_number = _get_caller_number(args.Caller)
	args.to_number = args.To
	resp = twilio.generate_twilio_dial_response(args.from_number, args.to_number)
	create_call_log(args)

	return Response(resp.to_xml(), mimetype='text/xml')

@frappe.whitelist()
def create_call_log(call_payload):
	call_log = frappe.get_doc({
		"doctype": "Call Log",
		"id": call_payload.get("CallSid"),
		"to": call_payload.get("to_number"),
		"status": "Ringing",
		"medium": call_payload.get("from_number"),
		"from": call_payload.get("from_number")
	})
	call_log.flags.ignore_permissions = True
	call_log.save()

@frappe.whitelist()
def update_call_log(call_sid, status="In Progress"):
	"""Update call log status.
	"""
	twilio = Twilio.connect()
	if not (twilio and frappe.db.exists("Call Log", call_sid)): return

	call_details = twilio.get_call_info(call_sid)
	call_log = frappe.get_doc("Call Log", call_sid)
	call_log.status = status
	call_log.duration = call_details.duration
	call_log.flags.ignore_permissions = True
	call_log.save()

@frappe.whitelist(allow_guest=True)
def update_recording_info(**kwargs):
	try:
		args = frappe._dict(kwargs)
		recording_url = args.RecordingUrl
		call_sid = args.CallSid
		frappe.db.set_value("Call Log", call_sid, "recording_url", recording_url)
	except:
		frappe.log_error(title=_("Failed to capture Twilio recording"))
