import re
import json
from twilio.rest import Client as TwilioClient
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse, Dial

import frappe
from .utils import get_public_url, merge_dicts

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

	def generate_voice_access_token(self, from_number: str, identity: str, ttl=60*60):
		"""Generates a token required to make voice calls from the browser.
		"""
		# identity is used by twilio to identify the user uniqueness at browser(or any endpoints).
		identity = self.safe_identity(identity)

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
		"""Create a safe identity by replacing unsupported special charaters `@` with (at)).
		Twilio Client JS fails to make a call connection if identity has special characters like @, [, / etc)
		https://www.twilio.com/docs/voice/client/errors (#31105)
		"""
		return identity.replace('@', '(at)')

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


class IncomingCall:
	def __init__(self, from_number, to_number, meta=None):
		self.from_number = from_number
		self.to_number = to_number
		self.meta = meta

	def process(self):
		"""Process the incoming call
		* Figure out who is going to pick the call (call attender)
		* Check call attender settings and forward the call to Phone
		"""
		twilio = Twilio.connect()

		owners = get_twilio_number_owners(self.to_number)
		attender = get_the_call_attender(owners)
		# if attender.voice_call_settings.call_receiving_device == 'Phone':
		# 	return twilio.generate_twilio_dial_response(from_number, attender.phone_number)
		return twilio.generate_twilio_dial_response(self.from_number, attender['mobile_no'])

def get_twilio_number_owners(phone_number):
	"""Get list of users who is using the phhone_number.
	"""
	user_voice_settings = frappe.get_all(
		'Voice Call Settings',
		filters={'twilio_number': phone_number},
		fields=["name", "call_receiving_device"]
	)
	user_wise_voice_settings = {user['name']: user for user in user_voice_settings}

	user_general_settings = frappe.get_all(
		'User',
		filters = [['name', 'IN', user_wise_voice_settings.keys()]],
		fields = ['name', 'mobile_no']
	)
	user_wise_general_settings = {user['name']: user for user in user_general_settings}

	return merge_dicts(user_wise_general_settings, user_wise_voice_settings)

def get_the_call_attender(owners):
	"""Get attender details from list of owners
	"""
	if not owners: return
	for name, details in owners.items():
		if details['mobile_no']:
			return details
