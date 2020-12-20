var onload_script = function() {
	frappe.provide('frappe.phone_call');
	var device;
	var dialog;

	if (frappe.boot.twilio_enabled){
		frappe.run_serially([
			() => setup_device(),
			() => dialer()
		]);
	}

	function dialer() {
		frappe.phone_call.handler = (to_number, frm) => {
			var to_numbers;
			if (Array.isArray(to_number)) {
				to_numbers = to_number;
			} else {
				to_numbers = to_number.split('\n');
			}

			// TODO: Make sure that device is available
			dialog = new frappe.ui.Dialog({
				'static': 1,
				'title': __('Make a Call'),
				'minimizable': true,
				'fields': [{
					'fieldname': 'to_number',
					'label': 'To Number',
					'fieldtype': 'Autocomplete',
					'ignore_validation': true,
					'options': to_numbers,
					'default': to_numbers[0],
					'read_only': 0,
					'reqd': 1
				}],
				primary_action: () => {
					dialog.disable_primary_action();
					var params = {
						To: dialog.get_value('to_number') // FIXME: how to access dialog?
					};

					if (device) {
						var outgoingConnection = device.connect(params);
						outgoingConnection.on("ringing", function () {
							set_header('ringing');
						});
					} else {
						dialog.enable_primary_action();
					}
				},
				primary_action_label: __('Call'),
				secondary_action: () => {
					if (device) {
						device.disconnectAll();
					}
				}
			});
			$('<input type="button" class="btn btn-mute hide" value="Mute"/>').appendTo(dialog.buttons);
			dialog.show();
			dialog.get_close_btn().show();
		}
	}

	function set_header(status){
		if (!dialog){
			return;
		}
		dialog.set_title(frappe.model.unscrub(status));
		const indicator_class = get_status_indicator(status);
		dialog.header.find('.indicator').attr('class', `indicator ${indicator_class}`);
	}

	function get_status_indicator(status) {
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

	function setup_device() {
		frappe.call( {
			method: "twilio_integration.twilio_integration.api.generate_access_token",
			callback: (data) => {
				device = new Twilio.Device(data.message.token, {
					codecPreferences: ["opus", "pcmu"],
					fakeLocalDTMF: true,
					enableRingingState: true,
				});

				device.on("ready", function (device) {
					set_header('available');
				});

				device.on("error", function (error) {
					set_header("failed");
					device.disconnectAll();
					// FIXME: log this error into console instead of popup
					frappe.throw(__("Twilio Device Error: " + error.message));
				});

				device.on("disconnect", function (conn) {
					dialog.set_secondary_action_label("Close")
					dialog.enable_primary_action();
					set_call_as_complete();
					window.onbeforeunload = null;
					set_header("available");
					hide_mute_button();
					update_call_log(conn);
				});

				device.on("connect", function (conn) {
					setup_mute_button(conn);
					dialog.set_secondary_action_label("Hang Up")
					set_header("in-progress");
					window.onbeforeunload = function() {
						return "you can not refresh the page";
					}
				});

				device.on("incoming", function (conn) {
					console.log("Incoming connection from " + conn.parameters.From);
					call_screen(conn);
				});
			}
		});
	}

	function setup_mute_button(twilio_conn) {
		var mute_button = dialog.buttons.find('.btn-mute');
		mute_button.removeClass('hide');
		mute_button.on('click', function (event) {
			if (this.value == 'Mute') {
				twilio_conn.mute(true);
				this.value='Unmute';
			}
			else {
				twilio_conn.mute(false);
				this.value = 'Mute';
			}
		});
	}

	function hide_mute_button() {
		var mute_button = dialog.buttons.find('.btn-mute');
		mute_button.addClass('hide');
	}

	function update_call_log(conn, status="Completed") {
		if (!conn.parameters.CallSid) return
		frappe.call({
			"method": "twilio_integration.twilio_integration.api.update_call_log",
			"args": {
				"call_sid": conn.parameters.CallSid,
				"status": status
			}
		})
	}

	function set_call_as_complete() {
		dialog.get_close_btn().show();
	}

	function call_screen(conn) {
		dialog = new frappe.ui.Dialog({
			'static': 1,
			'title': __('Incoming Call'),
			'minimizable': true,
			primary_action: () => {
				dialog.disable_primary_action();
				conn.accept();
			},
			primary_action_label: __('Answer'),
			secondary_action: () => {
				if (device) {
					device.disconnectAll();
				}
			}
		});
		dialog.show();
		dialog.get_close_btn().show();
	}
}

var script = document.createElement('script');
document.head.appendChild(script);
script.onload = onload_script;
script.src = "https://sdk.twilio.com/js/client/releases/1.13.0/twilio.js";
