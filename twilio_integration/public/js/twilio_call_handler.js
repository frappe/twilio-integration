var onload_script = function() {
	frappe.provide('frappe.phone_call');
	frappe.provide('frappe.twilio_conn_dialog_map')
	let device;

	if (frappe.boot.twilio_enabled){
		frappe.run_serially([
			() => setup_device(),
			() => dialer_screen()
		]);
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
					Object.values(frappe.twilio_conn_dialog_map).forEach(function(popup){
						popup.set_header('available');
					})
				});

				device.on("error", function (error) {
					Object.values(frappe.twilio_conn_dialog_map).forEach(function(popup){
						popup.set_header('Failed');
					})
					device.disconnectAll();
					console.log("Twilio Device Error:" + error.message);
				});

				device.on("disconnect", function (conn) {
					update_call_log(conn);
					const popup = frappe.twilio_conn_dialog_map[conn];
					// Reomove the connection from map object
					delete frappe.twilio_conn_dialog_map[conn]
					popup.dialog.enable_primary_action();
					popup.show_close_button();
					window.onbeforeunload = null;
					popup.set_header("available");
					popup.hide_mute_button();
					popup.hide_hangup_button();
					// Make sure that dialog is closed when incoming call is disconnected.
					if (conn.direction == 'INCOMING'){
						popup.close();
					}
				});

				device.on("cancel", function () {
					Object.values(frappe.twilio_conn_dialog_map).forEach(function(popup){
						popup.close();
					})
				});

				device.on("connect", function (conn) {
					const popup = frappe.twilio_conn_dialog_map[conn];
					popup.setup_mute_button(conn);
					popup.dialog.set_secondary_action_label("Hang Up")
					popup.set_header("in-progress");
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

	function dialer_screen() {
		frappe.phone_call.handler = (to_number, frm) => {
			let to_numbers;
			let outgoing_call_popup;

			if (Array.isArray(to_number)) {
				to_numbers = to_number;
			} else {
				to_numbers = to_number.split('\n');
			}
			outgoing_call_popup = new OutgoingCallPopup(device, to_numbers);
			outgoing_call_popup.show();
		}
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

	function call_screen(conn) {
		frappe.call({
			type: "GET",
			method: "twilio_integration.twilio_integration.api.get_contact_details",
			args: {
				'phone': conn.parameters.From
			},
			callback: (data) => {
				let incoming_call_popup = new IncomingCallPopup(device, conn);
				incoming_call_popup.show(data.message);
			}
		});
	}
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

class TwilioCallPopup {
	constructor(twilio_device) {
		this.twilio_device = twilio_device;
	}

	hide_hangup_button() {
		this.dialog.get_secondary_btn().addClass('hide');
	}

	set_header(status) {
		if (!this.dialog){
			return;
		}
		this.dialog.set_title(frappe.model.unscrub(status));
		const indicator_class = get_status_indicator(status);
		this.dialog.header.find('.indicator').attr('class', `indicator ${indicator_class}`);
	}

	setup_mute_button(twilio_conn) {
		let me = this;
		let mute_button = me.dialog.custom_actions.find('.btn-mute');
		mute_button.removeClass('hide');
		mute_button.on('click', function (event) {
			if ($(this).text().trim() == 'Mute') {
				twilio_conn.mute(true);
				$(this).html('Unmute');
			}
			else {
				twilio_conn.mute(false);
				$(this).html('Mute');
			}
		});
	}

	hide_mute_button() {
		let mute_button = this.dialog.custom_actions.find('.btn-mute');
		mute_button.addClass('hide');
	}

	show_close_button() {
		this.dialog.get_close_btn().show();
	}

	close() {
		this.dialog.cancel();
	}

}

class OutgoingCallPopup extends TwilioCallPopup {
	constructor(twilio_device, phone_numbers) {
		super(twilio_device);
		this.phone_numbers = phone_numbers;
	}

	show() {
		this.dialog = new frappe.ui.Dialog({
			'static': 1,
			'title': __('Make a Call'),
			'minimizable': true,
			'fields': [{
				'fieldname': 'to_number',
				'label': 'To Number',
				'fieldtype': 'Autocomplete',
				'ignore_validation': true,
				'options': this.phone_numbers,
				'default': this.phone_numbers[0],
				'read_only': 0,
				'reqd': 1
			}],
			primary_action: () => {
				this.dialog.disable_primary_action();
				var params = {
					To: this.dialog.get_value('to_number')
				};

				if (this.twilio_device) {
					let me = this;
					let outgoingConnection = this.twilio_device.connect(params);
					frappe.twilio_conn_dialog_map[outgoingConnection] = this;
					outgoingConnection.on("ringing", function () {
						me.set_header('ringing');
					});
				} else {
					this.dialog.enable_primary_action();
				}
			},
			primary_action_label: __('Call'),
			secondary_action: () => {
				if (this.twilio_device) {
					this.twilio_device.disconnectAll();
				}
			},
			onhide: () => {
				if (this.twilio_device) {
					this.twilio_device.disconnectAll();
				}
			}
		});
		this.dialog.add_custom_action('Mute', null, 'btn-mute hide');
		this.dialog.get_secondary_btn().addClass('hide');
		this.dialog.show();
		this.dialog.get_close_btn().show();
	}
}

class IncomingCallPopup extends TwilioCallPopup {
	constructor(twilio_device, conn) {
		super(twilio_device);
		this.conn = conn;
		frappe.twilio_conn_dialog_map[conn] = this; // CHECK: Is this the place?
	}

	get_title(caller_details) {
		let title;
		if (caller_details){
			title = __('Incoming Call From {0}', [caller_details.first_name]);
		} else {
			title = __('Incoming Call From {0}', [this.conn.parameters.From]);
		}
		return title;
	}

	set_dialog_body(caller_details) {
		var caller_info = $(`<div></div>`);
		let caller_details_html = '';
		if (caller_details) {
			for (const [key, value] of Object.entries(caller_details)) {
				caller_details_html += `<div>${key}: ${value}</div>`;
			}
		} else {
			caller_details_html += `<div>Phone Number: ${this.conn.parameters.From}</div>`;
		}
		$(`<div>${caller_details_html}</div>`).appendTo(this.dialog.modal_body);
	}

	show(caller_details) {
		this.dialog = new frappe.ui.Dialog({
			'static': 1,
			'title': this.get_title(caller_details),
			'minimizable': true,
			primary_action: () => {
				this.dialog.disable_primary_action();
				this.conn.accept();
			},
			primary_action_label: __('Answer'),
			secondary_action: () => {
				if (this.twilio_device) {
					if (this.conn.status() == 'pending') {
						this.conn.reject();
						this.close();
					}
					this.twilio_device.disconnectAll();
				}
			},
			secondary_action_label: __('Hang Up'),
			onhide: () => {
				if (this.twilio_device) {
					if (this.conn.status() == 'pending') {
						this.conn.reject();
						this.close();
					}
					this.twilio_device.disconnectAll();
				}
			}
		});
		this.set_dialog_body(caller_details);
		this.show_close_button();
		this.dialog.add_custom_action('Mute', null, 'btn-mute hide');
		this.dialog.show();
	}
}

var script = document.createElement('script');
document.head.appendChild(script);
script.onload = onload_script;
script.src = "https://sdk.twilio.com/js/client/releases/1.13.0/twilio.min.js";
