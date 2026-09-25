# -*- coding: utf-8 -*-
# Establecimientos según el RUC: Compañía → SRI → "Establecimientos en el RUC".
# Se inicializa en 1 (si está vacío) y se sincroniza: 001..N activos, cada uno
# con punto 000 (DES) y 001 (PRO); lo demás se deshabilita (no se borra).

import frappe
from frappe.utils import cint
from frappe.utils.fixtures import sync_fixtures

from erpnext_ec.utilities.sri_establecimientos import sincronizar_establecimientos


def execute():
	sync_fixtures("erpnext_ec")
	frappe.clear_cache(doctype="Company")

	for company in frappe.get_all("Company", pluck="name"):
		if cint(frappe.db.get_value("Company", company, "sri_num_establecimientos")) < 1:
			frappe.db.set_value("Company", company, "sri_num_establecimientos", 1, update_modified=False)
		for cambio in sincronizar_establecimientos(company):
			print(f"{company}: {cambio}")

	frappe.db.commit()
