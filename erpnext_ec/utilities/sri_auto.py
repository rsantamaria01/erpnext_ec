"""Envío automático al SRI.

Tarea programada (cada minuto) que, para cada compañía que tenga activo
"Envío automático al SRI" (pestaña SRI de Compañía), revisa si toca correr según el
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
from datetime import datetime

from frappe.utils import add_to_date, get_datetime, now_datetime

CRON_POR_DEFECTO = "*/5 * * * *"
ESPERA_MINUTOS = 3
PAUSA_TRAS_FALLO_SEG = 3600


def enviar_pendientes():
	from erpnext_ec.utilities.sri_settings import get_sri_settings

	for compania in frappe.get_all("Company", pluck="name"):
		ajustes = get_sri_settings(compania)
		if ajustes.simulation or not ajustes.send_auto:
			continue
		if not _toca_ahora(compania, ajustes.send_cron):
			continue

		for factura in _pendientes(compania, ajustes.send_batch_docs):
			_enviar(factura)


def _toca_ahora(compania, expresion):
	"""True si desde la última corrida pasó al menos un instante del cron.

	El scheduler de Frappe no corre exactamente cada minuto (en producción
	suele hacerlo cada ~4 min), así que no se compara el minuto actual con
	el cron: se compara la última ejecución con el instante previo del cron.
	"""
	from croniter import croniter

	expresion = (expresion or "").strip() or CRON_POR_DEFECTO
	ahora = now_datetime()
	try:
		previo = croniter(expresion, ahora).get_prev(datetime)
	except Exception:
		frappe.log_error(
			title="SRI envío automático: cron inválido",
			message=f"'{expresion}' no es una expresión cron válida; se usa {CRON_POR_DEFECTO}",
		)
		previo = croniter(CRON_POR_DEFECTO, ahora).get_prev(datetime)

	clave = f"sri_auto_ultima_corrida:{compania}"
	ultima = frappe.cache.get_value(clave)
	if ultima and get_datetime(ultima) >= previo:
		return False

	frappe.cache.set_value(clave, str(ahora))
	return True


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
				select 1 from `tabSRI Respuestas XML` x where x.doc_ref = si.name
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
	except Exception as e:
		frappe.db.rollback()
		# Un choque de bloqueo (deadlock / error 1020) es transitorio: se
		# reintenta en la próxima corrida en vez de pausar una hora.
		if not isinstance(e, (frappe.QueryDeadlockError, frappe.QueryTimeoutError)):
			frappe.cache.set_value(clave_pausa, 1, expires_in_sec=PAUSA_TRAS_FALLO_SEG)
		frappe.log_error(
			title=f"SRI envío automático: {factura.name}",
			message=frappe.get_traceback(),
		)
