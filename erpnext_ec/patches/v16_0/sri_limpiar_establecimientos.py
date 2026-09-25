# -*- coding: utf-8 -*-
# Limpieza única: borra establecimientos y puntos que sobran (quedan solo los
# del RUC con 000 DES y 001 PRO). Lo que ya tiene documentos no se puede
# borrar y queda deshabilitado; se borrará al sincronizar cuando ya no tenga
# documentos (p. ej. tras limpiar las facturas de prueba).

import frappe

from erpnext_ec.utilities.sri_establecimientos import (
	PUNTO_PRO,
	_borrar_o_deshabilitar,
	sincronizar_establecimientos,
)

SECUENCIALES = (
	"sec_factura", "sec_notacredito", "sec_notadebito",
	"sec_comprobanteretencion", "sec_liquidacioncompra", "sec_guiaremision",
)


def execute():
	for company in frappe.get_all("Company", pluck="name"):
		for cambio in sincronizar_establecimientos(company):
			print(f"{company}: {cambio}")

		# Puntos PRO extra que nunca emitieron nada (p. ej. 001-002 de la carga inicial)
		for p in frappe.db.sql(
			f"""select p.name, p.record_name, e.record_name estab, {", ".join("p." + c for c in SECUENCIALES)}
			from `tabSRI Punto de Emision` p
			join `tabSRI Establecimiento` e on e.name = p.sri_establishment_lnk
			where e.company_link = %s and p.sri_environment_lnk = 'PRO' and p.record_name != %s""",
			(company, PUNTO_PRO),
			as_dict=True,
		):
			if any(p[c] for c in SECUENCIALES):
				continue
			r = _borrar_o_deshabilitar("SRI Punto de Emision", p.name)
			print(f"{company}: Punto {p.estab}-{p.record_name} (PRO) {r}")

	frappe.db.commit()
