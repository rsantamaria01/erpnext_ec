# Identificación SRI de clientes y proveedores (pestaña Impuesto → "Identificación SRI").
#
# Tipos (SRI Tipo de Identificacion): 04 RUC, 05 cédula, 06 pasaporte,
# 07 consumidor final, 08 identificación del exterior, 09 placa.

import re

import frappe
from frappe import _

CONSUMIDOR_FINAL = "9999999999999"
RUC, CEDULA, PASAPORTE, CONS_FINAL, EXTERIOR, PLACA = "04", "05", "06", "07", "08", "09"


def normalizar(identificacion):
	"""Quita espacios, guiones y puntos."""
	return re.sub(r"[\s\-\.]", "", identificacion or "").upper()


def inferir_tipo(identificacion):
	"""Tipo deducible solo por la forma del número; None si no se puede."""
	if identificacion == CONSUMIDOR_FINAL:
		return CONS_FINAL
	if identificacion.isdigit():
		if len(identificacion) == 13:
			return RUC
		if len(identificacion) == 10:
			return CEDULA
	return None


def cedula_valida(cedula):
	"""Dígito verificador módulo 10 de la cédula ecuatoriana."""
	if len(cedula) != 10 or not cedula.isdigit():
		return False
	provincia, tercero = int(cedula[:2]), int(cedula[2])
	if not (1 <= provincia <= 24 or provincia == 30) or tercero >= 6:
		return False
	suma = 0
	for i, c in enumerate(cedula[:9]):
		n = int(c) * (2 if i % 2 == 0 else 1)
		suma += n - 9 if n > 9 else n
	return (10 - suma % 10) % 10 == int(cedula[9])


def revisar(tipo, identificacion):
	"""Devuelve (error, aviso). error bloquea el guardado; aviso solo informa.

	El formato (longitud, solo dígitos) se exige. El dígito verificador solo
	avisa: hay RUC de sociedades y entidades públicas que no siguen la regla.
	"""
	if tipo == CONS_FINAL:
		if identificacion != CONSUMIDOR_FINAL:
			return _("Consumidor final debe tener la identificación {0}.").format(CONSUMIDOR_FINAL), None
		return None, None

	if tipo == CEDULA:
		if not (identificacion.isdigit() and len(identificacion) == 10):
			return _("La cédula debe tener 10 dígitos."), None
		if not cedula_valida(identificacion):
			return None, _("La cédula {0} no pasa la verificación del dígito final. Revísala.").format(identificacion)
		return None, None

	if tipo == RUC:
		if not (identificacion.isdigit() and len(identificacion) == 13):
			return _("El RUC debe tener 13 dígitos."), None
		if identificacion == CONSUMIDOR_FINAL:
			return _("9999999999999 es consumidor final; elige ese tipo de identificación."), None
		if identificacion[10:] == "000":
			return _("El RUC termina en el establecimiento (001, 002…), nunca en 000."), None
		if int(identificacion[2]) < 6 and not cedula_valida(identificacion[:10]):
			return None, _("Los 10 primeros dígitos del RUC {0} no forman una cédula válida. Revísalo.").format(identificacion)
		return None, None

	if tipo in (PASAPORTE, EXTERIOR, PLACA):
		if len(identificacion) > 20:
			return _("La identificación no puede pasar de 20 caracteres."), None
		if not identificacion.isalnum():
			return _("La identificación solo puede tener letras y números."), None

	return None, None


def validate(doc, method=None):
	"""doc_events validate de Customer y Supplier."""
	identificacion = normalizar(doc.tax_id)
	doc.tax_id = identificacion or None

	tipo = (doc.get("typeidtax") or "")[:2] or None  # datos viejos: "04 RUC" -> "04"
	if not identificacion:
		doc.typeidtax = tipo
		return

	if not tipo:
		tipo = inferir_tipo(identificacion)
		if not tipo:
			frappe.throw(
				_("Elige el tipo de identificación (pestaña Impuesto) para {0}.").format(identificacion),
				title=_("Identificación SRI"),
			)
	doc.typeidtax = tipo

	error, aviso = revisar(tipo, identificacion)
	if error:
		frappe.throw(error, title=_("Identificación SRI"))
	if aviso:
		frappe.msgprint(aviso, title=_("Identificación SRI"), indicator="orange")


def datos_comprador(nombre, identificacion, tipo, quien):
	"""Valida lo mínimo que exige el XML antes de armar un comprobante."""
	if not identificacion:
		frappe.throw(
			_("{0} {1} no tiene identificación (pestaña Impuesto → Identificación SRI).").format(quien, nombre),
			title=_("Identificación SRI"),
		)
	tipo = (tipo or "")[:2] or inferir_tipo(identificacion)
	if not tipo:
		frappe.throw(
			_("{0} {1} no tiene tipo de identificación (pestaña Impuesto → Identificación SRI).").format(quien, nombre),
			title=_("Identificación SRI"),
		)
	return tipo
