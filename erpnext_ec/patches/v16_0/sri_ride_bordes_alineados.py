# -*- coding: utf-8 -*-
# Recarga el HTML de los RIDE con los bordes alineados (el estilo de impresión de
# Frappe fuerza padding con !important y desalineaba los recuadros). Solo
# actualiza los formatos que ya existen; no crea ninguno.

import os

import frappe

FORMATOS = {
	"Factura SRI": "sales_invoice_sri_ride.html",
	"Nota de Crédito SRI": "credit_note_sri_ride.html",
	"Nota de Débito SRI": "debit_note_sri_ride.html",
	"Retención SRI": "withdraw_purchase_sri_ride.html",
	"Guía de Remisión SRI": "delivery_note_sri_ride.html",
	"Liquidación de Compra SRI": "purchase_settlement_sri_ride.html",
}


def execute():
	carpeta = os.path.join(frappe.get_app_path("erpnext_ec"), "public", "jinja")
	for nombre, archivo in FORMATOS.items():
		if not frappe.db.exists("Print Format", nombre):
			continue
		with open(os.path.join(carpeta, archivo), encoding="utf-8") as f:
			html = f.read()
		frappe.db.set_value("Print Format", nombre, "html", html, update_modified=True)
	frappe.clear_cache(doctype="Print Format")
