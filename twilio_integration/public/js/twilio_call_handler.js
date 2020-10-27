var onload_script = function() {
	frappe.provide('frappe.phone_call');
	class TwilioCall {
		constructor(to_number, frm) {
			var me = this;
			frappe.call({
				method: "twilio_integration.twilio_integration.doctype.twilio_settings.twilio_settings.generate_access_token",
				callback: (data) => {
					console.log(data.token);
					this.setup_device(data.token);
				}
			}).then(() => {
				this.setup_device_listener();
				this.setup_call_info(frm, to_number);
				this.make();
			})
		}

		make() {
			me.dialog = new frappe.ui.Dialog({
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
				}, {
					'fieldname': 'select_audio',
					'label': 'Active Audio Output',
					'fieldtype': 'Select',
					'ignore_validation': true,
					'options': ["Default - Internal Speakers (Built-in)", "Internal Speakers (Built-in)", "krisp speaker (Virtual)"],
					'read_only': 0,
					'reqd': 1
				}],
				primary_action: () => {
					me.dialog.disable_primary_action();
					var params = {
						debug: true,
						To: me.dialog.get_value('to_number')
					};

					if (this.device) {
						var outgoingConnection = this.device.connect(params);
						console.log(outgoingConnection)
						outgoingConnection.on("ringing", function () {
							set_header('ringing');
						});
					} else {
						me.dialog.enable_primary_action();
					}
				},
				primary_action_label: __('Call')
			});
			me.dialog.show();
			me.dialog.get_close_btn().show();
		}

		setup_device_listener() {
			this.device.on("ready", function (device) {
				set_header('available');
			});

			this.device.on("error", function (error) {
				set_header("failed");
				frappe.throw(__("Twilio.Device Error: " + error.message));
			});

			this.device.on("disconnect", function (conn) {
				me.dialog.enable_primary_action();
				this.set_call_as_complete();
				window.onbeforeunload = null;
				frappe.call({
					"method": "twilio_integration.twilio_integration.doctype.twilio_settings.twilio_settings.update_call_log",
					"args": {
						"call_sid": this.call_sid,
						"status": "Completed"
					}
				})
				set_header("completed");
			});

			this.device.on("connect", function (conn) {
				set_header("in-progress");
				window.onbeforeunload = function() {
					return "you can not refresh the page";
				}
			});

			this.device.on("incoming", function (conn) {
				log("Incoming connection from " + conn.parameters.From);
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
				debug: true
			});
			console.log(this.device)
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
			me.dialog.get_close_btn().show();
			clearInterval(this.updater);
		}

		set_header(status) {
			me.dialog.set_title(frappe.model.unscrub(status));
			const indicator_class = this.get_status_indicator(status);
			me.dialog.header.find('.indicator').attr('class', `indicator ${indicator_class}`);
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

		get_audio_devices() {
			let selected_devices = [];

			this.device.audio.availableOutputDevices.forEach(function (device, id) {
				selected_devices.push(device.label);
			});
			return selected_devices;
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