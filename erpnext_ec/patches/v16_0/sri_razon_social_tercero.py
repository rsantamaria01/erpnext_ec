# "Nombre Comercial" de Cliente/Proveedor pasa a ser "Razón social (SRI)": solo
# se llena si el nombre legal difiere del nombre del tercero. Se vacía donde
# repetía el mismo nombre, y el tipo viejo "04 RUC" queda como "04".

import frappe


def execute():
	for dt, campo in (("Customer", "customer_name"), ("Supplier", "supplier_name")):
		for r in frappe.get_all(dt, fields=["name", campo, "nombrecomercial", "typeidtax"]):
			cambios = {}
			if r.nombrecomercial and r.nombrecomercial.strip() in (r.get(campo), r.name):
				cambios["nombrecomercial"] = None
			if r.typeidtax and len(r.typeidtax) > 2:
				cambios["typeidtax"] = r.typeidtax[:2]
			if cambios:
				frappe.db.set_value(dt, r.name, cambios, update_modified=False)
