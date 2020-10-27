frappe.ui.form.on('Notification', {
	onload: function(frm) {
		frm.set_query('twilio_number', function() {
			return {
				filters: {
					communication_channel: "Twilio",
					communication_medium_type: "WhatsApp"
				}
			};
		});
	},

	refresh: function(frm) {
		frm.events.setup_whatsapp_template(frm);
	},

	channel: function(frm) {
		frm.events.setup_whatsapp_template(frm);
	},

	setup_whatsapp_template: function(frm) {
		let template = '';
		if (frm.doc.channel === 'WhatsApp') {
			template = `<h5 style='display: inline-block'>Warning:</h5> Only Use Pre-Approved WhatsApp for Business Template
<h5>Message Example</h5>

<pre>
Your appointment is coming up on {{ doc.date }} at {{ doc.time }}
</pre>`;
		}
		if (template) {
			frm.set_df_property('message_examples', 'options', template);
		}

	}
});