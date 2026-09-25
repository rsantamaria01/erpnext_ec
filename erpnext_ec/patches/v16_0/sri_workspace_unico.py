# -*- coding: utf-8 -*-
# Workspace SRI único:
# - Bloque "Estado SRI" (Custom HTML Block) al inicio del workspace; reemplaza
#   la página sri-estado.
# - Elimina la página sri-estado.

import os

import frappe

BLOQUE = "Estado SRI"


def _leer(nombre):
	ruta = os.path.join(frappe.get_app_path("erpnext_ec", "sri", "estado"), nombre)
	with open(ruta, encoding="utf-8") as f:
		return f.read()


def execute():
	valores = {
		"html": _leer("estado_sri.html"),
		"script": _leer("estado_sri.js"),
		"style": _leer("estado_sri.css"),
		"private": 0,
	}
	if frappe.db.exists("Custom HTML Block", BLOQUE):
		bloque = frappe.get_doc("Custom HTML Block", BLOQUE)
		bloque.update(valores)
		bloque.save(ignore_permissions=True)
	else:
		bloque = frappe.new_doc("Custom HTML Block")
		bloque.update(valores)
		bloque.insert(ignore_permissions=True, set_name=BLOQUE)

	if frappe.db.exists("Page", "sri-estado"):
		frappe.delete_doc("Page", "sri-estado", force=True, ignore_permissions=True)
	frappe.db.delete("Workspace Sidebar Item", {"link_type": "Page", "link_to": "sri-estado"})

	frappe.db.commit()
