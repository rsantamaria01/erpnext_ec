# -*- coding: utf-8 -*-
# Patch ERPNext v16 - Ficha Técnica SRI 2.34 (julio 2026)
# - Campos personalizados nuevos (Anexos 23, 24, 25 y 26)
# - Corrección del código de documento de Liquidación de Compra (03)
# - Catálogo de tipos de identificación (Tabla 6)

import frappe


def ensure_custom_field(dt, fieldname, label, fieldtype, insert_after, description="", options=None, read_only=0):
	if frappe.get_all("Custom Field", filters={"dt": dt, "fieldname": fieldname}):
		return
	print(f"Creando Custom Field {dt}-{fieldname}")
	cf = frappe.get_doc({
		"doctype": "Custom Field",
		"dt": dt,
		"fieldname": fieldname,
		"label": label,
		"fieldtype": fieldtype,
		"insert_after": insert_after,
		"description": description,
		"options": options,
		"read_only": read_only,
		"translatable": 0,
		"no_copy": 1,
	})
	cf.insert(ignore_permissions=True)
	frappe.db.commit()


def execute():
	# Anexo 25 - placa del vehículo (transporte comercial)
	ensure_custom_field(
		"Sales Invoice", "sri_placa", "Placa (SRI)", "Data", "sri_estado",
		"Anexo 25 Ficha SRI 2026: placa del vehículo en facturas de transporte comercial",
	)

	# Anexo 24 - Gran Contribuyente
	ensure_custom_field(
		"Company", "sri_gran_contribuyente", "Gran Contribuyente (SRI)", "Check", "agenteretencion",
		"Anexo 24 Ficha SRI 2026: leyenda Gran Contribuyente en el XML/RIDE",
	)
	ensure_custom_field(
		"Company", "sri_gran_contribuyente_resolucion", "Resolución Gran Contribuyente (SRI)", "Data",
		"sri_gran_contribuyente", "Número de resolución de calificación como Gran Contribuyente",
	)

	# Anexo 26 - RUC del proveedor de sistemas de facturación
	ensure_custom_field(
		"Company", "sri_ruc_proveedor", "RUC Proveedor (SRI)", "Data", "sri_gran_contribuyente_resolucion",
		"Anexo 26 Ficha SRI 2026: RUC del proveedor de sistemas informáticos o servicios de facturación electrónica",
	)

	# Anexos 23 y 25 - codigoAuxiliar en el detalle
	ensure_custom_field(
		"Item", "codigo_auxiliar_sri", "Código Auxiliar SRI", "Data", "item_code",
		"Anexos 23 y 25 Ficha SRI 2026: materiales de construcción y transporte comercial",
	)

	# Corrección del catálogo SRI Tipo de Comprobante: Liquidación de Compra = 03
	for sri_type in frappe.get_all("SRI Tipo de Comprobante", fields=["name", "document_type"]):
		if sri_type.name == "LIQ" and sri_type.document_type != "03":
			frappe.db.set_value("SRI Tipo de Comprobante", "LIQ", "document_type", "03")
			print("SRI Tipo de Comprobante LIQ: document_type corregido a 03")
			break

	# Catálogo de tipos de identificación (Tabla 6 Ficha SRI 2026)
	tipo_ids = {
		"04": "RUC",
		"05": "CÉDULA",
		"06": "PASAPORTE",
		"07": "VENTA A CONSUMIDOR FINAL",
		"08": "IDENTIFICACIÓN DEL EXTERIOR",
		"09": "PLACA",
	}
	for tipo_id, desc in tipo_ids.items():
		if not frappe.db.exists("SRI Tipo de Identificacion", tipo_id):
			frappe.get_doc({
				"doctype": "SRI Tipo de Identificacion",
				"sri_id": tipo_id,
				"description": desc,
			}).insert(ignore_permissions=True)
			print(f"SRI Tipo de Identificacion {tipo_id} - {desc} creado")

	frappe.db.commit()
