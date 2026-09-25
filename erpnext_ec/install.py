from __future__ import unicode_literals

import click
import frappe


def before_install():
	print("before_install erpnext_ec")


def after_install():
	try:
		print("Setting ERPNext Ecuador...")
		click.secho("Thank you for installing ERPNext Ecuador!", fg="green")
	except Exception as e:
		click.secho(
			"Installation for ERPNext Ecuador app failed due to an error."
			" Please try re-installing the app.",
			fg="bright_red",
		)
		raise e


def before_migrate():
	"""Descarta el mapa de módulos en caché antes de migrar.

	Frappe guarda en Redis la lista de módulos de cada app (modules.txt). Si el
	fork cambia sus módulos (p. ej. "Erpnext Ec"/"Erpnext Sri" -> "SRI"), el
	migrate leería la lista vieja y fallaría al buscar carpetas que ya no existen.
	"""
	frappe.cache.delete_value("app_modules")
	try:
		frappe.client_cache.delete_value("installed_app_modules")
	except Exception:
		pass
	frappe.setup_module_map()
	frappe.setup_module_map(include_all_apps=False)


def after_migrate():
	ensure_sri_tab_position()


def ensure_sri_tab_position():
	"""La pestaña SRI de Compañía va después de "HR & Payroll" (HRMS). Si HRMS no
	está instalado, ese campo no existe y Frappe desordenaría la pestaña, así que
	se ancla al final (después de "Tablero")."""
	if not frappe.db.exists("Custom Field", "Company-sri_tab"):
		return
	meta = frappe.get_meta("Company")
	ancla = "default_payroll_payable_account" if meta.has_field("default_payroll_payable_account") else "dashboard_tab"
	if frappe.db.get_value("Custom Field", "Company-sri_tab", "insert_after") != ancla:
		frappe.db.set_value("Custom Field", "Company-sri_tab", "insert_after", ancla)
		frappe.clear_cache(doctype="Company")
