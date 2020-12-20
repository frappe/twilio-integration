from werkzeug.wrappers import Response
import frappe
from .twilio_handler import Twilio, IncomingCall

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

	token=twilio.generate_voice_access_token(from_number=from_number, identity=frappe.session.user)
	return {
		'token': token.decode('utf-8')
	}

@frappe.whitelist(allow_guest=True)
def voice(**kwargs):
	"""This is a webhook called by twilio to get instructions when the voice call request comes to twilio server.
	"""
	def _get_caller_number(caller):
		user = caller.replace('client:', '').split('_')[0]
		return frappe.db.get_value('Voice Call Settings', user, 'twilio_number')

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

@frappe.whitelist(allow_guest=True)
def twilio_incoming_call_handler(**kwargs):
	args = frappe._dict(kwargs)
	args.from_number = args.From
	args.to_number = args.To
	create_call_log(args)

	resp = IncomingCall(args.from_number, args.to_number).process()
	return Response(resp.to_xml(), mimetype='text/xml')

@frappe.whitelist()
def create_call_log(call_payload):
	is_outbound = call_payload.get('Caller', '').lower().startswith('client')
	direction = (is_outbound and 'Outbound') or 'Inbound'

	call_log = frappe.get_doc({
		"doctype": "Call Log",
		"direction": direction,
		"status": call_payload.get('CallStatus', '').title(),
		"id": call_payload.get("CallSid"),
		"to": call_payload.get("to_number"),
		"medium": call_payload.get("from_number"),
		"from": call_payload.get("from_number"),
	})
	call_log.flags.ignore_permissions = True
	call_log.save()

@frappe.whitelist()
def update_call_log(call_sid, status=None):
	"""Update call log status.
	"""
	twilio = Twilio.connect()
	if not (twilio and frappe.db.exists("Call Log", call_sid)): return

	call_details = twilio.get_call_info(call_sid)
	call_log = frappe.get_doc("Call Log", call_sid)
	call_log.status = status or call_details.CallStatus.title()
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
