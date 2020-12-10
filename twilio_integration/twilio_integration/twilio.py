import re
import frappe

from twilio.rest import Client as TwilioClient
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant

class Twilio:
	def __init__(self, settings):
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
			# TODO: FixMe
			return
		return Twilio(settings=settings)

	def get_phone_numbers(self):
		"""Get account's twilio phone numbers.
		"""
		numbers = self.twilio_client.incoming_phone_numbers.list()
		return [n.phone_number for n in numbers]

	def generate_voice_access_token(self, identity, ttl=60*60):
		""":type int: Time to live of the JWT in seconds, defaults to 1 hour"""
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
	def safe_identity(cls, identity):
		"""Create a safe identity by replacing unsupported special charaters with '-'.

		Twilio Client JS fails to make a call connection if identity has special characters like @, [, / etc)
		"""
		return re.sub(r'[^a-zA-Z0-9_.-]+', '-', identity).strip()


@frappe.whitelist()
def get_twilio_phone_numbers():
	twilio = Twilio.connect()
	return (twilio and twilio.get_phone_numbers()) or []

@frappe.whitelist()
def generate_access_token():
	twilio_settings = frappe.get_doc("Twilio Settings")
	twilio = Twilio(twilio_settings)

	# identity is used by twilio to identify the user uniqueness at browser(or any endpoints).
	token=twilio.generate_voice_access_token(identity=frappe.session.user)

	return {
		'token': token.decode('utf-8')
	}
