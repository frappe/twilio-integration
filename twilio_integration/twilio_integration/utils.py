from pyngrok import ngrok
import frappe
from frappe.utils import get_url


def get_public_url(path: str=None, use_ngrok: bool=False):
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


def merge_dicts(d1: dict, d2: dict):
	"""Merge dicts of dictionaries.
	>>> merge_dicts(
		{'name1': {'age': 20}, 'name2': {'age': 30}},
		{'name1': {'phone': '+xxx'}, 'name2': {'phone': '+yyy'}, 'name3': {'phone': '+zzz'}}
	)
	... {'name1': {'age': 20, 'phone': '+xxx'}, 'name2': {'age': 30, 'phone': '+yyy'}}
	"""
	return {k:{**v, **d2.get(k, {})} for k, v in d1.items()}
