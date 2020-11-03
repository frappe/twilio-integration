var onload_script = function() {
	frappe.provide('frappe.phone_call');
	class TwilioCall {
		constructor(to_number, frm) {
			frappe.call({
				method: "twilio_integration.twilio_integration.doctype.twilio_settings.twilio_settings.generate_access_token",
				callback: (data) => {
					frappe.run_serially([
						() => this.setup_device(data.token),
						() => this.setup_device_listener(),
						() => this.setup_call_info(frm, to_number),
						() => this.make()
					]);
				}
			})
		}

		make() {
			this.dialog = new frappe.ui.Dialog({
				'static': 1,
				'title': __('Make a Call'),
				'minimizable': true,
				'fields': [{
					'fieldname': 'to_number',
					'label': 'To Number',
					'fieldtype': 'Autocomplete',
					'ignore_validation': true,
					'options': this.to_numbers,
					'read_only': 0,
					'reqd': 1
				}],
				primary_action: () => {
					this.dialog.disable_primary_action();
					var params = {
						To: this.dialog.get_value('to_number')
					};

					if (this.device) {
						let me = this;
						var outgoingConnection = this.device.connect(params);
						outgoingConnection.on("ringing", function () {
							me.set_header('ringing');
						});
					} else {
						this.dialog.enable_primary_action();
					}
				},
				primary_action_label: __('Call'),
				secondary_action: () => {
					if (this.device) {
						this.device.disconnectAll();
						this.device.destroy();
					}
				}
			});
			this.dialog.show();
			this.dialog.get_close_btn().show();
		}

		setup_device_listener() {
			var me = this;
			me.device.on("ready", function (device) {
				me.set_header('available');
			});

			me.device.on("error", function (error) {
				me.set_header("failed");
				this.device.disconnectAll();
				frappe.throw(__("Twilio Device Error: " + error.message));
			});

			me.device.on("disconnect", function (conn) {
				me.dialog.set_secondary_action_label("Close")
				me.dialog.enable_primary_action();
				me.set_call_as_complete();
				window.onbeforeunload = null;
				me.set_header("available");
				me.update_call_log(conn)
			});

			me.device.on("connect", function (conn) {
				me.dialog.set_secondary_action_label("Hang Up")
				me.set_header("in-progress");
				window.onbeforeunload = function() {
					return "you can not refresh the page";
				}
			});

			me.device.on("incoming", function (conn) {
				console.log("Incoming connection from " + conn.parameters.From);
				var archEnemyPhoneNumber = "+12093373517";
		
				if (conn.parameters.From === archEnemyPhoneNumber) {
					conn.reject();
					log("It's your nemesis. Rejected call.");
				} else {
					// accept the incoming connection and start two-way audio
					conn.accept();
				}
			});
		}

		setup_device(access_token) {
			// Setup Twilio Device
			this.device = new Twilio.Device(access_token, {
				codecPreferences: ["opus", "pcmu"],
				fakeLocalDTMF: true,
				enableRingingState: true,
			});
		}

		setup_call_info(frm, to_number) {
			// to_number call be string or array
			// like '12345' or ['1234', '4567'] or '1234\n4567'
			if (Array.isArray(to_number)) {
				this.to_numbers = to_number;
			} else {
				this.to_numbers = to_number.split('\n');
			}

			// record the document to link
			if (frm) {
				this.document_to_link = {
					'link_doctype': frm.doctype,
					'link_name': frm.docname
				};
			}
		}

		setup_call_status_updater() {
			if (!this.updater) {
				this.updater = setInterval(this.set_call_status.bind(this), 1000);
			}
		}

		set_call_as_complete() {
			this.dialog.get_close_btn().show();
			clearInterval(this.updater);
		}

		set_header(status) {
			this.dialog.set_title(frappe.model.unscrub(status));
			const indicator_class = this.get_status_indicator(status);
			this.dialog.header.find('.indicator').attr('class', `indicator ${indicator_class}`);
		}

		get_status_indicator(status) {
			const indicator_map = {
				'available': 'blue',
				'completed': 'blue',
				'failed': 'red',
				'busy': 'yellow',
				'no-answer': 'orange',
				'queued': 'orange',
				'ringing': 'green blink',
				'in-progress': 'green blink'
			};
			const indicator_class = `indicator ${indicator_map[status] || 'blue blink'}`;
			return indicator_class;
		}

		update_call_log(conn, status="Completed") {
			if (!conn.parameters.CallSid) return
			frappe.call({
				"method": "twilio_integration.twilio_integration.doctype.twilio_settings.twilio_settings.update_call_log",
				"args": {
					"call_sid": conn.parameters.CallSid,
					"status": status
				}
			})
		}
	}

	frappe.db.get_single_value('Twilio Settings', 'enabled').then(is_integration_enabled => {
		if (is_integration_enabled) {
			frappe.phone_call.handler = (to_number, frm) => new TwilioCall(to_number, frm);
		}
	});
}

var script = document.createElement('script');
document.head.appendChild(script);
script.onload = onload_script;
script.src = "//sdk.twilio.com/js/client/releases/1.10.1/twilio.js";