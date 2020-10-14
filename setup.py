# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in twilio_integration/__init__.py
from twilio_integration import __version__ as version

setup(
	name='twilio_integration',
	version=version,
	description='Custom Frappe Application for Twilio Integration',
	author='Frappe',
	author_email='developers@frappe.io',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
