
frappe.ui.form.on('Voice Call Settings', {
	onload: function(frm) {
		frappe.call({
			method: "twilio_integration.twilio_integration.api.get_twilio_phone_numbers",
			callback: function(resp) {
				if (resp.message.length) {
					//FIXME: I am messy
					resp.message.push('')
					frm.set_df_property('twilio_number', 'options', resp.message);
					frm.refresh_field('twilio_number');
				}
				else {
					frappe.show_alert({
						message:__('Voice settings rely on twilio settings. Please make sure that twilio settings are configured & enabled.'),
						indicator:'red'
					}, 6);
				}
			}
		});
	}
});
