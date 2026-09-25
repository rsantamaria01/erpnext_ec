# -*- coding: utf-8 -*-
# Formato RIDE y plantilla de correo de la Nota de Débito (faltaban) y su
# asignación en Compañía → SRI cuando el campo está vacío.

import os

import frappe

from erpnext_ec.patches.v15_0.email_template import create_email_template
from erpnext_ec.patches.v15_0.print_formats import create_print_format

FORMATO = "Nota de Débito SRI"
PLANTILLA = "Nota de Débito SRI Body"


def _leer(nombre):
	ruta = os.path.join(frappe.get_app_path("erpnext_ec"), "public", "jinja", nombre)
	with open(ruta, encoding="utf-8") as f:
		return f.read()


def execute():
	create_print_format(
		{
			"doc_type": "Sales Invoice",
			"name": FORMATO,
			"module": "Accounts",
			"standard": 0,
			"custom_format": 1,
			"print_format_type": "Jinja",
			"default_print_language": "es-EC",
			"disabled": 0,
		},
		_leer("debit_note_sri_ride.html"),
	)

	if not frappe.db.exists("Email Template", PLANTILLA):
		create_email_template(
			{"name": PLANTILLA, "subject": "Nota de Débito -"},
			_leer("debit_note_sri_email.html"),
		)

	for company in frappe.get_all(
		"Company", fields=["name", "sri_ride_dn_format", "sri_ride_dn_template_email"]
	):
		valores = {}
		if not company.sri_ride_dn_format:
			valores["sri_ride_dn_format"] = FORMATO
		if not company.sri_ride_dn_template_email:
			valores["sri_ride_dn_template_email"] = PLANTILLA
		if valores:
			frappe.db.set_value("Company", company.name, valores, update_modified=False)

	frappe.db.commit()
