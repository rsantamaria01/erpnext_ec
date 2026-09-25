# -*- coding: utf-8 -*-
# Patch ERPNext v16 - Elimina los workspaces legacy "ERPNext Ec" y el duplicado
# "Sri", junto con su Workspace Sidebar y Desktop Icon. El unico workspace
# canonico pasa a ser "SRI" (definido en erpnext_ec/sri/workspace/sri/sri.json).
#
# Se ejecuta como pre_model_sync para eliminar los registros ANTES de que
# frappe.model.sync cree el workspace "SRI". La colacion de la base de datos es
# utf8mb4_unicode_ci (case-insensitive), por lo que "Sri" y "SRI" colisionan en
# la clave primaria: si "Sri" existiera al momento del sync, la creacion de "SRI"
# fallaria o actualizaria el registro equivocado. Por eso se comparan los nombres
# con BINARY para no borrar "SRI" por error.

import frappe

LEGACY_NAMES = ("ERPNext Ec", "Sri")
LEGACY_DOCTYPES = ("Desktop Icon", "Workspace Sidebar", "Workspace")


def _exact_exists(doctype, name):
	"""True solo si existe un registro cuyo `name` coincide exactamente (case-sensitive)."""
	return bool(
		frappe.db.sql(f"SELECT name FROM `tab{doctype}` WHERE BINARY name = %s", name)
	)


def execute():
	for name in LEGACY_NAMES:
		for doctype in LEGACY_DOCTYPES:
			if _exact_exists(doctype, name):
				frappe.delete_doc(doctype, name, force=True, ignore_missing=True)
	frappe.db.commit()
