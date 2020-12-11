from pyngrok import ngrok
import frappe
from frappe.utils import get_url


def get_public_url(path=None, use_ngrok=True):
	"""Returns a public accessible url of a site using ngrok.
	"""
	if frappe.conf.developer_mode and use_ngrok:
		tunnels = ngrok.get_tunnels()
		if tunnels:
			domain = tunnels[0].public_url
		else:
			port = frappe.conf.http_port or frappe.conf.webserver_port
			domain = ngrok.connect(port)
		return '/'.join(map(lambda x: x.strip('/'), [domain, path or '']))
	return get_url(path)

