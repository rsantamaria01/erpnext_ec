# -*- coding: utf-8 -*-
# Establecimientos y puntos de emisión según el RUC.
#
# En Compañía → SRI se indica cuántos establecimientos tiene el RUC (certificado
# del SRI). Con ese número se mantienen los establecimientos 001..N y, en cada
# uno, dos puntos de emisión por defecto:
#   000 -> ambiente DES (pruebas)     001 -> ambiente PRO (producción)
# Se pueden agregar más puntos PRO a mano (002, 003, ...). Nada se borra: lo que
# sobra se deshabilita.

import frappe
from frappe import _
from frappe.utils import cint

PUNTO_DES = "000"
PUNTO_PRO = "001"


def on_company_update(doc, method=None):
	"""Company.on_update: sincroniza cuando cambia el número de establecimientos."""
	if doc.has_value_changed("sri_num_establecimientos") and cint(doc.get("sri_num_establecimientos")) > 0:
		sincronizar_establecimientos(doc.name, mostrar=True)


@frappe.whitelist()
def sincronizar(company):
	frappe.only_for(("System Manager", "Accounts Manager"))
	return sincronizar_establecimientos(company, mostrar=True)


def sincronizar_establecimientos(company, mostrar=False):
	n = cint(frappe.db.get_value("Company", company, "sri_num_establecimientos"))
	if n < 1:
		frappe.throw(_("Indique en Compañía → SRI cuántos establecimientos tiene el RUC."))

	cambios = []
	establecimientos = frappe.get_all(
		"SRI Establecimiento",
		filters={"company_link": company},
		fields=["name", "record_name", "disabled"],
		order_by="creation asc",
	)

	for i in range(1, n + 1):
		codigo = f"{i:03d}"
		mismos = [e for e in establecimientos if (e.record_name or "").strip() == codigo]
		activo = next((e for e in mismos if not e.disabled), None)
		if activo:
			nombre = activo.name
		elif mismos:
			nombre = mismos[0].name
			_set(frappe.get_doc("SRI Establecimiento", nombre), disabled=0)
			cambios.append(_("Establecimiento {0} habilitado").format(codigo))
		else:
			est = frappe.get_doc(
				{
					"doctype": "SRI Establecimiento",
					"company_link": company,
					"record_name": codigo,
					"description": f"Establecimiento {codigo}",
				}
			).insert(ignore_permissions=True)
			nombre = est.name
			cambios.append(_("Establecimiento {0} creado").format(codigo))
		cambios += _asegurar_puntos(company, nombre, codigo)

	for e in establecimientos:
		codigo = (e.record_name or "").strip()
		if e.disabled or not codigo.isdigit() or int(codigo) <= n:
			continue
		_set(frappe.get_doc("SRI Establecimiento", e.name), disabled=1)
		cambios.append(_("Establecimiento {0} deshabilitado (no está en el RUC)").format(codigo))
		for pto in frappe.get_all(
			"SRI Punto de Emision", filters={"sri_establishment_lnk": e.name, "disabled": 0}, pluck="name"
		):
			_set(frappe.get_doc("SRI Punto de Emision", pto), disabled=1)

	if mostrar and cambios:
		frappe.msgprint("<br>".join(cambios), title=_("Establecimientos SRI"), indicator="green")
	return cambios


def _asegurar_puntos(company, establecimiento, codigo_est):
	cambios = []
	puntos = frappe.get_all(
		"SRI Punto de Emision",
		filters={"sri_establishment_lnk": establecimiento},
		fields=["name", "record_name", "sri_environment_lnk", "disabled", "test_dev_email"],
		order_by="creation asc",
	)

	# DES: un único punto de pruebas, con código 000
	for p in puntos:
		if p.sri_environment_lnk == "DES" and not p.disabled and p.record_name != PUNTO_DES:
			_set(frappe.get_doc("SRI Punto de Emision", p.name), disabled=1)
			p.disabled = 1
			cambios.append(_("Punto {0}-{1} (DES) deshabilitado; pruebas usa {0}-{2}").format(codigo_est, p.record_name, PUNTO_DES))

	cambios += _asegurar_punto(company, establecimiento, codigo_est, puntos, PUNTO_DES, "DES")
	cambios += _asegurar_punto(company, establecimiento, codigo_est, puntos, PUNTO_PRO, "PRO")
	return cambios


def _asegurar_punto(company, establecimiento, codigo_est, puntos, codigo, ambiente):
	existente = next(
		(p for p in puntos if p.record_name == codigo and p.sri_environment_lnk == ambiente), None
	)
	if existente and not existente.disabled:
		return []

	valores = {"disabled": 0}
	if ambiente == "DES":
		valores["test_dev_email"] = (existente and existente.test_dev_email) or _correo_pruebas(company)

	if existente:
		_set(frappe.get_doc("SRI Punto de Emision", existente.name), **valores)
		return [_("Punto {0}-{1} ({2}) habilitado").format(codigo_est, codigo, ambiente)]

	frappe.get_doc(
		{
			"doctype": "SRI Punto de Emision",
			"record_name": codigo,
			"description": "Pruebas" if ambiente == "DES" else "Producción",
			"sri_establishment_lnk": establecimiento,
			"sri_environment_lnk": ambiente,
			**valores,
		}
	).insert(ignore_permissions=True)
	return [_("Punto {0}-{1} ({2}) creado").format(codigo_est, codigo, ambiente)]


def _correo_pruebas(company):
	"""Correo para un punto DES nuevo: el de otro punto DES de la compañía o,
	si no hay, el correo por defecto de Compañía → SRI."""
	correo = frappe.db.sql(
		"""select p.test_dev_email from `tabSRI Punto de Emision` p
		join `tabSRI Establecimiento` e on e.name = p.sri_establishment_lnk
		where e.company_link = %s and ifnull(p.test_dev_email, '') != ''
		order by p.disabled asc, p.modified desc limit 1""",
		company,
	)
	correo = (correo and correo[0][0]) or frappe.db.get_value("Company", company, "sri_default_email")
	if not correo:
		frappe.throw(
			_("Para crear el punto de pruebas (DES) configure 'Correo por defecto' en Compañía → SRI.")
		)
	return correo


def _set(doc, **valores):
	doc.update(valores)
	doc.save(ignore_permissions=True)
