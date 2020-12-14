
frappe.ui.form.on('Voice Call Settings', {
	onload: function(frm) {
		if (!frappe.user_roles.includes('System Manager')){
			frm.set_value('user', frappe.session.user)
		}
	},
	refresh: function(frm) {
		frappe.call({
			method: "twilio_integration.twilio_integration.api.get_twilio_phone_numbers",
			callback: function(resp) {
				if (resp.message.length) {
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
	},
	user: function(frm) {
		frappe.db.exists('Voice Call Settings', frm.doc.user).then( exists => {
			if (exists) {
				var doc_url = `/desk#Form/${frm.doc.doctype}/${frm.doc.user}`;
				var link_html = `<a href="${doc_url}">here</a>`;
				frappe.msgprint(__('Voice call settings already exists for this user. You can edit them {0}', [link_html]));
			}
		});
	}
});
