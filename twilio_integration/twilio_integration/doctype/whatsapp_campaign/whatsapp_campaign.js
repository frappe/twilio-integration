// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Campaign', {
	refresh: function(frm) {
		if(frm.doc.status == 'Completed') {
			frm.disable_form();
			frm.disable_save();
		}
		if(!frm.is_new() && frm.doc.status!='Completed') {
			frm.add_custom_button(('Send Now'), function(){
				frappe.call({
					doc: frm.doc,
					method: 'send_now',
					freeze: true,
					callback: (r) => {
						frm.reload_doc();
					}
				})
			});
		}
	}
});
