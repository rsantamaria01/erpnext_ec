"""Envío automático al SRI.

Tarea programada (cada minuto) que, para cada compañía cuya configuración
regional tenga activo "Envío automático al SRI", revisa si toca correr según el
campo "Temporizador/Cron" (por defecto */5 * * * *) y envía las facturas y
notas de crédito emitidas que todavía no se han enviado.

Reglas de seguridad:
- Sólo Sales Invoice (factura y nota de crédito). Guías de remisión,
  retenciones, notas de débito y liquidaciones siguen siendo manuales.
- Sólo documentos validados (docstatus 1), con establecimiento y punto de
  emisión, sin autorización (sri_estado 0) y SIN ninguna respuesta previa del
  SRI: si el SRI ya contestó algo (devuelta, rechazada, en proceso) no se
  reintenta solo; se corrige y se envía a mano.
- Se deja pasar 3 minutos desde la última modificación, para no chocar con
  un envío manual hecho justo después de validar.
- Si el envío lanza una excepción (red, firma, validación) se registra en
  Error Log y ese documento no se reintenta hasta dentro de una hora.
- No corre si la compañía está en modo simulación.
"""

import json

import frappe
from frappe.utils import add_to_date, now_datetime

CRON_POR_DEFECTO = "*/5 * * * *"
ESPERA_MINUTOS = 3
PAUSA_TRAS_FALLO_SEG = 3600


def enviar_pendientes():
	companias = frappe.get_all(
		"Company", fields=["name", "regional_settings_ec", "use_simulation_mode"]
	)
	for compania in companias:
		if not compania.regional_settings_ec or compania.use_simulation_mode:
			continue

		ajustes = frappe.db.get_value(
			"Regional Settings Ec",
			compania.regional_settings_ec,
			["send_sri_auto", "send_sri_batch_docs", "send_sri_cron"],
			as_dict=True,
		)
		if not ajustes or not ajustes.send_sri_auto:
			continue
		if not _toca_ahora(ajustes.send_sri_cron):
			continue

		limite = ajustes.send_sri_batch_docs or 20
		for factura in _pendientes(compania.name, limite):
			_enviar(factura)


def _toca_ahora(expresion):
	from croniter import croniter

	expresion = (expresion or "").strip() or CRON_POR_DEFECTO
	ahora = now_datetime().replace(second=0, microsecond=0)
	try:
		return croniter.match(expresion, ahora)
	except Exception:
		frappe.log_error(
			title="SRI envío automático: cron inválido",
			message=f"'{expresion}' no es una expresión cron válida; se usa {CRON_POR_DEFECTO}",
		)
		return croniter.match(CRON_POR_DEFECTO, ahora)


def _pendientes(compania, limite):
	hasta = add_to_date(now_datetime(), minutes=-ESPERA_MINUTOS)
	return frappe.db.sql(
		"""
		select si.name, si.is_return
		from `tabSales Invoice` si
		where si.company = %(compania)s
			and si.docstatus = 1
			and ifnull(si.is_debit_note, 0) = 0
			and ifnull(si.sri_estado, 0) = 0
			and ifnull(si.estab, '') != ''
			and ifnull(si.ptoemi, '') != ''
			and si.modified < %(hasta)s
			and not exists (
				select 1 from `tabXml Responses` x where x.doc_ref = si.name
			)
		order by si.creation asc
		limit %(limite)s
		""",
		{"compania": compania, "hasta": hasta, "limite": int(limite)},
		as_dict=True,
	)


def _enviar(factura):
	from erpnext_ec.utilities.sri_ws import send_doc_native

	clave_pausa = f"sri_auto_fallo:{factura.name}"
	if frappe.cache.get_value(clave_pausa):
		return

	tipo = "NCR" if factura.is_return else "FAC"
	try:
		send_doc_native(
			json.dumps({"name": factura.name}), tipo, "Sales Invoice", frappe.local.site
		)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.cache.set_value(clave_pausa, 1, expires_in_sec=PAUSA_TRAS_FALLO_SEG)
		frappe.log_error(
			title=f"SRI envío automático: {factura.name}",
			message=frappe.get_traceback(),
		)
