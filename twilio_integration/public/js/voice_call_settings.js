
frappe.ui.form.on('Voice Call Settings', {
	onload: function(frm) {
		frappe.call({
			method: "twilio_integration.twilio_integration.twilio.get_twilio_phone_numbers",
			callback: function(resp) {
				if (resp.message) {
					frm.set_df_property('twilio_number', 'options', resp.message);
					frm.refresh_field('twilio_number');
				}
			}
		});
	}
});
