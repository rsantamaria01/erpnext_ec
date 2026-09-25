# -*- coding: utf-8 -*-
# Configuración SRI de la compañía (pestaña "SRI" de Compañía).
# Reemplaza al antiguo doctype "Regional Settings Ec".

import frappe
from frappe.utils import cint

TIMEOUT_POR_DEFECTO = 10


def get_sri_settings(company):
	"""Configuración SRI de la compañía como frappe._dict."""
	c = frappe.get_cached_doc("Company", company)
	return frappe._dict(
		company=company,
		signature=c.get("sri_signature"),
		signature_tool=c.get("sri_signature_tool") or "Python",
		timeout=cint(c.get("sri_timeout")) or TIMEOUT_POR_DEFECTO,
		simulation=cint(c.get("use_simulation_mode")),
		send_auto=cint(c.get("sri_send_auto")),
		send_batch_docs=cint(c.get("sri_send_batch_docs")) or 20,
		send_cron=c.get("sri_send_cron") or "*/5 * * * *",
		default_email=c.get("sri_default_email"),
	)


def firmar_xml(xml_string, settings, doc_data=None):
	"""Firma el comprobante con la firma electrónica y la herramienta de la compañía."""
	from frappe import _

	if not settings.signature:
		frappe.throw(_("La compañía {0} no tiene firma electrónica (pestaña SRI).").format(settings.company))

	firmas = frappe.get_all("Sri Signature", filters={"name": settings.signature}, fields=["*"])
	if not firmas:
		frappe.throw(_("No existe la firma electrónica {0}.").format(settings.signature))

	if settings.signature_tool == "XadesSignerCmd":
		from erpnext_ec.utilities.signature_tool import SriXmlData

		return SriXmlData.sign_xml_cmd(SriXmlData, xml_string, firmas[0])

	from erpnext_ec.utilities.xades_tool_v4 import XadesToolV4

	return XadesToolV4.sign_xml(XadesToolV4, xml_string, doc_data, firmas[0])
