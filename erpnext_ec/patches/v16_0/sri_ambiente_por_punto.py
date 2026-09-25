# -*- coding: utf-8 -*-
# El ambiente SRI (DES/PRO) pasa a definirlo cada punto de emisión.
# - Elimina el campo Company.sri_active_environment (ya no se usa).
# - Copia el correo de pruebas global (Regional Settings Ec.dummy_email_target)
#   al nuevo campo "Test Dev Environment Email" de los puntos de emisión DES.
# - Quita del sidebar SRI el enlace a "Sri Sequence" (doctype eliminado).

import frappe


def execute():
	for name in frappe.get_all(
		"Custom Field", filters={"dt": "Company", "fieldname": "sri_active_environment"}, pluck="name"
	):
		frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)

	correo = None
	if frappe.db.table_exists("Regional Settings Ec") and frappe.db.has_column(
		"Regional Settings Ec", "dummy_email_target"
	):
		correo = frappe.db.sql(
			"""select dummy_email_target from `tabRegional Settings Ec`
			where ifnull(dummy_email_target, '') != '' order by modified desc limit 1"""
		)
		correo = correo[0][0] if correo else None

	if correo and frappe.db.has_column("SRI Punto de Emision", "test_dev_email"):
		for pto in frappe.get_all(
			"SRI Punto de Emision",
			filters={"sri_environment_lnk": "DES"},
			fields=["name", "test_dev_email"],
		):
			if not pto.test_dev_email:
				frappe.db.set_value("SRI Punto de Emision", pto.name, "test_dev_email", correo, update_modified=False)

	frappe.db.delete("Workspace Sidebar Item", {"link_type": "DocType", "link_to": "Sri Sequence"})
	# El migrate borra el DocType huérfano "Sri Sequence" pero no su tabla (12 registros en 0)
	frappe.db.sql_ddl("drop table if exists `tabSri Sequence`")
	frappe.db.commit()
