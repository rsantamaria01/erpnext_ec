# -*- coding: utf-8 -*-
# pre_model_sync: nombres en español con prefijo "SRI" para los DocType del app.
#
# rename_doc("DocType") renombra la tabla, actualiza los campos Link/Table que
# apuntan al DocType (incluidos Custom Field y Property Setter), los parenttype
# y los enlaces dinámicos. Los registros conservan su nombre (PTO-00001, ...).

import frappe
from frappe.model.rename_doc import rename_doc

RENOMBRAR = (
	("Purchase Withholding Sri Ec", "SRI Comprobante de Retencion"),
	("Sri External Establishment", "SRI Establecimiento Externo"),
	("Sri Establishment", "SRI Establecimiento"),
	("Sri Ptoemi", "SRI Punto de Emision"),
	("Sri Environment", "SRI Ambiente"),
	("Sri Signature", "SRI Firma Electronica"),
	("Sri Type Doc", "SRI Tipo de Comprobante"),
	("Sri Type Id", "SRI Tipo de Identificacion"),
	("Xml Responses", "SRI Respuestas XML"),
)


def _existe(nombre):
	# Comparación exacta: la colación de la base no distingue mayúsculas
	return bool(frappe.db.sql("select name from `tabDocType` where BINARY name=%s", nombre))


def execute():
	for viejo, nuevo in RENOMBRAR:
		if not _existe(viejo) or _existe(nuevo):
			continue
		rename_doc("DocType", viejo, nuevo, force=True, show_alert=False, rebuild_search=False)
		frappe.db.commit()

	# Textos que guardan el nombre del DocType fuera de un campo Link
	for viejo, nuevo in RENOMBRAR:
		# Contraseñas (p. ej. la clave del .p12 en SRI Firma Electronica):
		# rename_doc no actualiza la tabla __Auth
		frappe.db.sql("update `__Auth` set doctype=%s where doctype=%s", (nuevo, viejo))
		if frappe.db.table_exists("SRI Respuestas XML"):
			frappe.db.sql(
				"update `tabSRI Respuestas XML` set doc_type=%s where doc_type=%s", (nuevo, viejo)
			)
		frappe.db.sql(
			"update `tabWorkspace Sidebar Item` set link_to=%s where link_type='DocType' and link_to=%s",
			(nuevo, viejo),
		)
		frappe.db.sql(
			"update `tabWorkspace Shortcut` set link_to=%s where type='DocType' and link_to=%s",
			(nuevo, viejo),
		)

	frappe.clear_cache()
	frappe.db.commit()
