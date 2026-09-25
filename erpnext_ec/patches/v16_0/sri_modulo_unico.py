# -*- coding: utf-8 -*-
# pre_model_sync: los módulos "Erpnext Ec" y "Erpnext Sri" se unen en el módulo "SRI"
# (carpeta erpnext_ec/sri). Se hace antes del sync para que los DocType ya
# apunten al módulo nuevo cuando se lean sus JSON y controladores.
#
# rename_doc actualiza todos los campos Link a Module Def (DocType.module,
# Page.module, Workspace.module, Report.module, Print Format.module, ...).

import frappe
from frappe.model.rename_doc import rename_doc

NUEVO = "SRI"
ANTERIORES = ("Erpnext Ec", "Erpnext Sri")


def execute():
	existentes = [m for m in ANTERIORES if frappe.db.exists("Module Def", m)]
	if not existentes:
		return

	for viejo in existentes:
		if not frappe.db.exists("Module Def", NUEVO):
			# validate=False: Module Def solo permite renombrar módulos custom
			rename_doc("Module Def", viejo, NUEVO, force=True, validate=False, show_alert=False, rebuild_search=False)
		else:
			rename_doc("Module Def", viejo, NUEVO, force=True, merge=True, validate=False, show_alert=False, rebuild_search=False)

	frappe.db.set_value("Module Def", NUEVO, {"app_name": "erpnext_ec", "custom": 0}, update_modified=False)

	# Workspace Sidebar.module es texto libre (no Link)
	frappe.db.sql(
		"update `tabWorkspace Sidebar` set module=%s where module in %s", (NUEVO, ANTERIORES)
	)
	frappe.clear_cache()
	frappe.db.commit()
