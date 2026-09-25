app_name = "erpnext_ec"
app_title = "ERPNext Ec"
app_publisher = "Raúl Santamaría"
app_description = "ERPNext Ecuador - Localización ecuatoriana SRI"
app_email = "raulsantamariaobando@gmail.com"
app_license = "mit"
required_apps = [
	"erpnext"
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_js = [
	"/assets/erpnext_ec/js/sri_custom.js",
	"/assets/erpnext_ec/js/sales_invoice_tools.js",
	"/assets/erpnext_ec/js/delivery_note_tools.js",
	"/assets/erpnext_ec/js/withholding_tools.js",
	"/assets/erpnext_ec/js/frappe_sri_ui_tools.js",
	"/assets/erpnext_ec/js/purchase_receipt_tools.js",

	"/assets/erpnext_ec/js/libs/jsonTree/jsonTree.js",
	"/assets/erpnext_ec/js/libs/monthpicker/jquery.ui.monthpicker.min.js",
	"/assets/erpnext_ec/js/utils/desk.custom.js",
]

app_include_css = [
	"/assets/erpnext_ec/js/libs/jsonTree/jsonTree.css",
	"/assets/erpnext_ec/js/libs/monthpicker/qunit.min.css",
	"/assets/erpnext_ec/js/libs/monthpicker/jquery-ui.css",
]

# include js in doctype views
doctype_js = {
	"Sales Invoice": "public/js/overrides/sales_invoice_form_sri.js",
	"Delivery Note": "public/js/overrides/delivery_note_form_sri.js",
	"Purchase Invoice": "public/js/overrides/purchase_invoice_form_sri.js",
	"Company": "public/js/overrides/company_form_sri.js",
}
doctype_list_js = {
	"Sales Invoice": "public/js/overrides/sales_invoice_list_sri.js",
	"Purchase Invoice": "public/js/overrides/purchase_invoice_list_sri.js",
	"Delivery Note": "public/js/overrides/delivery_note_list_sri.js",
	"Print Format": "public/js/overrides/print_format_list_sri.js",
	"SRI Establecimiento": "public/js/overrides/sri_establishment_list.js",
}
doctype_tree_js = {
	"Account": "public/js/overrides/account_list_sri.js",
}

# Jinja (Frappe >= 14)
# add methods and filters to jinja environment
jinja = {
	"methods": [
		"erpnext_ec.utilities.doc_builder_fac.build_doc_fac_with_images",
		"erpnext_ec.utilities.doc_builder_cre.build_doc_cre_with_images",
		"erpnext_ec.utilities.doc_builder_grs.build_doc_grs_with_images",
		"erpnext_ec.utilities.doc_builder_ncr.build_doc_ncr_with_images",
		"erpnext_ec.utilities.doc_builder_liq.build_doc_liq_with_images",
		"erpnext_ec.utilities.tools.get_full_url",
	],
	"filters": [],
}

# Installation
# ------------

before_install = "erpnext_ec.install.before_install"
after_install = ["erpnext_ec.install.after_install"]
before_migrate = ["erpnext_ec.install.before_migrate"]

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"SRI Respuestas XML": {
		"validate": "erpnext_ec.sri.doctype.sri_respuestas_xml.events.validate",
		"on_update": "erpnext_ec.sri.doctype.sri_respuestas_xml.events.on_update",
		"after_insert": "erpnext_ec.sri.doctype.sri_respuestas_xml.events.after_insert",
	}
}

# Envío automático al SRI: corre cada minuto y decide según el cron de
# Compañía, pestaña SRI (sri_send_auto / sri_send_cron / sri_send_batch_docs)
scheduler_events = {
	"cron": {
		"* * * * *": ["erpnext_ec.utilities.sri_auto.enviar_pendientes"],
	},
}

on_session_creation = [
	"erpnext_ec.utilities.tools.on_login_auto",
]
