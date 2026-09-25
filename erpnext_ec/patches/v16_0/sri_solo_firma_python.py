# -*- coding: utf-8 -*-
# La firma se hace solo con el firmador Python nativo (xades_tool_v4). Se quita
# el selector "Herramienta de firma" de Compañía (el binario XadesSignerCmd se
# eliminó del app).

import frappe


def execute():
	for name in frappe.get_all(
		"Custom Field", filters={"dt": "Company", "fieldname": "sri_signature_tool"}, pluck="name"
	):
		frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
	frappe.clear_cache(doctype="Company")
	frappe.db.commit()
