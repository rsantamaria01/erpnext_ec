# El SRI rechaza el punto de emisión 000 (error 58: "El punto de emisión debe
# ser mayor a cero"). El punto de pruebas (DES) por defecto pasa de 000 a 999;
# el registro se conserva (mismo PTO-xxxxx y contadores).

import frappe


def execute():
	for pto in frappe.get_all(
		"SRI Punto de Emision",
		filters={"record_name": "000"},
		fields=["name", "sri_establishment_lnk"],
	):
		if frappe.db.exists(
			"SRI Punto de Emision",
			{"sri_establishment_lnk": pto.sri_establishment_lnk, "record_name": "999", "name": ("!=", pto.name)},
		):
			frappe.db.set_value("SRI Punto de Emision", pto.name, "disabled", 1, update_modified=False)
		else:
			frappe.db.set_value("SRI Punto de Emision", pto.name, "record_name", "999", update_modified=False)
