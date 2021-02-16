# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "twilio_integration"
app_title = "Twilio Integration"
app_publisher = "Frappe"
app_description = "Custom Frappe Application for Twilio Integration"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "developers@frappe.io"
app_license = "MIT"
fixtures = [{"dt": "Custom Field", "filters": [
		[
			"name", "in", [
				"Notification-twilio_number", "Voice Call Settings-twilio_number"
			]
		]
	]}
, "Property Setter"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/twilio_integration/css/twilio_call_handler.css"
app_include_js = "/assets/js/twilio-call-handler.js"

# include js, css files in header of web template
# web_include_css = "/assets/twilio_integration/css/twilio_integration.css"
# web_include_js = "/assets/twilio_integration/js/twilio_integration.js"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}
doctype_js = {
	"Notification" : "public/js/Notification.js",
	"Voice Call Settings": "public/js/voice_call_settings.js"
}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "twilio_integration.install.before_install"
# after_install = "twilio_integration.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "twilio_integration.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"twilio_integration.tasks.all"
# 	],
# 	"daily": [
# 		"twilio_integration.tasks.daily"
# 	],
# 	"hourly": [
# 		"twilio_integration.tasks.hourly"
# 	],
# 	"weekly": [
# 		"twilio_integration.tasks.weekly"
# 	]
# 	"monthly": [
# 		"twilio_integration.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "twilio_integration.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "twilio_integration.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "twilio_integration.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

override_doctype_class = {
	"Notification": "twilio_integration.overrides.notification.SendNotification"
}

# boot
# ----------
boot_session = "twilio_integration.boot.boot_session"
