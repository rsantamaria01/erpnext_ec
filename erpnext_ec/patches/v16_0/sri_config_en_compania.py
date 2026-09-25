# -*- coding: utf-8 -*-
# La configuración SRI pasa de "Regional Settings Ec" a la pestaña "SRI" de Compañía.
# - Crea los campos nuevos de Compañía (fixtures) antes de copiar los valores.
# - Copia herramienta de firma, timeout y envío automático desde el registro
#   de Regional Settings Ec enlazado a cada compañía.
# - Elimina el enlace Company.regional_settings_ec y los datos de Regional
#   Settings Ec (el DocType lo elimina el migrate al no existir su carpeta).

import frappe
from frappe.utils.fixtures import sync_fixtures


def _rs_para(company):
	if not frappe.db.table_exists("Regional Settings Ec"):
		return None
	nombre = None
	if frappe.db.has_column("Company", "regional_settings_ec"):
		nombre = frappe.db.sql("select regional_settings_ec from `tabCompany` where name=%s", company)
		nombre = nombre[0][0] if nombre else None
	filtro = "where name=%(n)s" if nombre else ""
	filas = frappe.db.sql(
		f"select * from `tabRegional Settings Ec` {filtro} order by modified desc limit 1",
		{"n": nombre},
		as_dict=True,
	)
	return filas[0] if filas else None


def execute():
	sync_fixtures("erpnext_ec")

	for company in frappe.get_all("Company", pluck="name"):
		rs = _rs_para(company)
		valores = {"sri_timeout": 10}
		if rs:
			valores.update(
				{
					"sri_timeout": rs.get("server_timeout") or 10,
					"sri_send_auto": rs.get("send_sri_auto") or 0,
					"sri_send_batch_docs": rs.get("send_sri_batch_docs") or 20,
					"sri_send_cron": rs.get("send_sri_cron") or "*/5 * * * *",
				}
			)
		frappe.db.set_value("Company", company, valores, update_modified=False)

	for fieldname in ("regional_settings_ec", "column_break_10001"):
		for name in frappe.get_all(
			"Custom Field", filters={"dt": "Company", "fieldname": fieldname}, pluck="name"
		):
			frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)

	# Usuario y contraseña del antiguo servicio externo guardados en Regional Settings Ec
	frappe.db.delete("__Auth", {"doctype": "Regional Settings Ec"})
	# El migrate borra el DocType huérfano pero no su tabla
	frappe.db.sql_ddl("drop table if exists `tabRegional Settings Ec`")

	frappe.clear_cache(doctype="Company")
	frappe.db.commit()
