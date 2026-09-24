from __future__ import unicode_literals
import os
import frappe
import json


def get_last_sequencial_found(company_id, sri_type_doc_lnk, establishment, ptoemi):
	doctype_map = {
		"FAC": "Sales Invoice",
		"GRS": "Delivery Note",
		"CRE": "Purchase Withholding Sri Ec",
	}
	doctype = doctype_map.get(sri_type_doc_lnk)
	if not doctype:
		return 0
	filters = {"company": company_id}
	if establishment:
		filters["estab"] = establishment
	if ptoemi:
		filters["ptoemi"] = ptoemi
	docs_found = frappe.get_all(
		doctype,
		filters=filters,
		fields=["secuencial"],
		order_by="secuencial desc",
		limit_page_length=1,
	)
	return docs_found[0].get("secuencial") or 0 if docs_found else 0


def upsert_ptoemi(establishment_doc, establishment_record_name, company_id, child):
	record_name = child.get("record_name")
	environment = child.get("sri_environment_lnk")

	sec_factura = get_last_sequencial_found(
		company_id, "FAC", establishment_record_name, record_name
	) or 0
	sec_guiaremision = get_last_sequencial_found(
		company_id, "GRS", establishment_record_name, record_name
	) or 0
	sec_comprobanteretencion = get_last_sequencial_found(
		company_id, "CRE", establishment_record_name, record_name
	) or 0

	values = {
		"record_name": record_name,
		"description": child.get("description") or record_name,
		"sri_establishment_lnk": establishment_doc.name,
		"sri_environment_lnk": environment,
		"sec_factura": sec_factura,
		"sec_notacredito": child.get("sec_notacredito") or 0,
		"sec_notadebito": child.get("sec_notadebito") or 0,
		"sec_comprobanteretencion": sec_comprobanteretencion,
		"sec_liquidacioncompra": child.get("sec_liquidacioncompra") or 0,
		"sec_guiaremision": sec_guiaremision,
	}

	existing = frappe.get_all(
		"Sri Ptoemi",
		filters={
			"record_name": record_name,
			"sri_establishment_lnk": establishment_doc.name,
			"sri_environment_lnk": environment,
		},
		fields=["name"],
	)

	if existing:
		ptoemi_doc = frappe.get_doc("Sri Ptoemi", existing[0].name)
		for key, value in values.items():
			setattr(ptoemi_doc, key, value)
		ptoemi_doc.save(ignore_permissions=True)
		print("  Ptoemi actualizado:", ptoemi_doc.name, record_name, environment)
	else:
		values["doctype"] = "Sri Ptoemi"
		values["naming_series"] = child.get("naming_series") or "PTO-."
		ptoemi_doc = frappe.get_doc(values)
		ptoemi_doc.insert(ignore_permissions=True)
		print("  Ptoemi creado:", ptoemi_doc.name, record_name, environment)


def insert_update(DocTypeName, JsonPath, company=None):
	print("insert_update_data")

	with open(JsonPath, "r") as file:
		contenido_json_modificado = file.read()

	target_company = company or frappe.defaults.get_user_default("Company")
	print("Company:", target_company)

	if not target_company:
		frappe.throw("No se pudo determinar la compania destino.")

	data = json.loads(contenido_json_modificado)

	for record in data:
		record = dict(record)
		record["company_link"] = target_company
		record["name"] = record["name"].replace("*", "")
		record.pop("company", None)

		ptoemi_rows = record.pop("sri_ptoemi_detail", []) or []

		print("Procesando:", record["name"])

		try:
			existing = frappe.get_all(
				DocTypeName,
				filters={
					"record_name": record["record_name"],
					"company_link": target_company,
				},
				fields=["name"],
			)

			if existing:
				document_object = frappe.get_doc(DocTypeName, existing[0].name)
				print("Actualizando:", record["name"])
				for key, value in record.items():
					if key not in ["name", "doctype", "naming_series"]:
						setattr(document_object, key, value)
				document_object.save(ignore_permissions=True)
			else:
				print("Creando:", record.get("name", "<sin name>"))
				document_object = frappe.get_doc(record)
				document_object.insert(ignore_permissions=True)

			for child in ptoemi_rows:
				upsert_ptoemi(
					document_object,
					record["record_name"],
					target_company,
					child,
				)

			frappe.db.commit()

		except Exception as e:
			print("Error en registro:", record.get("name"), "-", str(e))
			frappe.db.rollback()

	print("Proceso terminado insert_update.")


def execute(company=None):
	dir_path = os.path.dirname(os.path.realpath(__file__))

	source_list = [
		{
			"doctype": "Sri Establishment",
			"json_file": "sri_establishment.json",
			"action": "update",
		},
	]

	for source_item in source_list:
		print(source_item)
		filepathfull = os.path.join(
			dir_path, "../../fixtures/specials", source_item["json_file"]
		)

		try:
			if source_item["action"] == "update":
				insert_update(source_item["doctype"], filepathfull, company)
		except Exception as e:
			return {"message": "Failed import.", "error": str(e)}
