// Establecimientos: se mantienen desde Compañía → SRI → "Establecimientos en el RUC".
frappe.listview_settings['SRI Establecimiento'] = {
    refresh: function(listview) {
        listview.page.add_inner_button(__('Sincronizar con el RUC'), function() {
            let company = frappe.defaults.get_user_default('Company') || frappe.boot.sysdefaults.company;
            frappe.call({
                method: 'erpnext_ec.utilities.sri_establecimientos.sincronizar',
                args: { company: company },
                freeze: true,
                callback: function(r) {
                    if (!(r.message || []).length) {
                        frappe.show_alert({ message: __('Todo está al día'), indicator: 'green' }, 5);
                    }
                    listview.refresh();
                },
            });
        });
    },
};
