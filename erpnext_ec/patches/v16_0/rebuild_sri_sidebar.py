# -*- coding: utf-8 -*-
# Patch ERPNext v16 - Reconstruye el Workspace Sidebar y el Desktop Icon del
# workspace "SRI" (y de cualquier otro workspace publico que no los tenga).
# Se ejecuta como post_model_sync, despues de que frappe.model.sync haya creado
# el workspace "SRI" a partir de erpnext_ec/sri/workspace/sri/sri.json.

from frappe.utils.install import auto_generate_icons_and_sidebar


def execute():
	auto_generate_icons_and_sidebar()
