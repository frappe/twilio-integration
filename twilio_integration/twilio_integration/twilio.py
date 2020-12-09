import frappe

from twilio.rest import Client as TwilioClient

class Twilio:
	def __init__(self, client):
		self.client = client

	@classmethod
	def connect(self):
		"""Make a twilio connection.
		"""
		twilio_settings = frappe.get_doc("Twilio Settings")
		if not (twilio_settings and  twilio_settings.enabled):
			# TODO: FixMe
			return
		client = TwilioClient(twilio_settings.account_sid, twilio_settings.get_password("auth_token"))
		return Twilio(client = client)

	def get_phone_numbers(self):
		"""Get account's twilio phone numbers.
		"""
		numbers = self.client.incoming_phone_numbers.list()
		return [n.phone_number for n in numbers]

@frappe.whitelist()
def get_twilio_phone_numbers():
	twilio = Twilio.connect()
	return (twilio and twilio.get_phone_numbers()) or []
