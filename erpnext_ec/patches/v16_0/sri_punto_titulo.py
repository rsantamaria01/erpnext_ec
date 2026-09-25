# Los puntos de emisión muestran "001-999 (DES)" en vez de PTO-00001 al elegirlos
# en un documento (title_field = titulo, show_title_field_in_link).

import frappe

from erpnext_ec.sri.doctype.sri_punto_de_emision.sri_punto_de_emision import titulo_punto


def execute():
	for p in frappe.get_all(
		"SRI Punto de Emision",
		fields=["name", "record_name", "sri_establishment_lnk", "sri_environment_lnk"],
	):
		frappe.db.set_value(
			"SRI Punto de Emision", p.name, "titulo",
			titulo_punto(p.sri_establishment_lnk, p.record_name, p.sri_environment_lnk),
			update_modified=False,
		)
