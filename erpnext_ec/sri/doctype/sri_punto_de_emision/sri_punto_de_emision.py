import re

import frappe
from frappe import _
from frappe.model.document import Document


class SRIPuntodeEmision(Document):
	def validate(self):
		self.record_name = (self.record_name or "").strip()
		if not re.fullmatch(r"\d{3}", self.record_name) or self.record_name == "000":
			frappe.throw(_("El código del punto de emisión debe tener 3 dígitos y ser mayor a 000 (p. ej. 001)."))

		self.titulo = titulo_punto(self.sri_establishment_lnk, self.record_name, self.sri_environment_lnk)

		if self.sri_environment_lnk != "DES":
			self.test_dev_email = None
		elif not self.test_dev_email and not self.disabled:
			frappe.throw(
				_("Un punto de emisión de pruebas (DES) necesita 'Test Dev Environment Email': "
				  "sus documentos solo se envían a ese correo.")
			)

		if not self.disabled:
			duplicado = frappe.db.exists(
				"SRI Punto de Emision",
				{
					"sri_establishment_lnk": self.sri_establishment_lnk,
					"record_name": self.record_name,
					"disabled": 0,
					"name": ("!=", self.name),
				},
			)
			if duplicado:
				frappe.throw(
					_("Ya existe un punto de emisión activo {0} en el establecimiento {1} ({2}).").format(
						self.record_name, self.sri_establishment_lnk, duplicado
					)
				)


def titulo_punto(establecimiento, codigo, ambiente):
	"""Texto que se ve al elegir el punto en un documento: 001-999 (DES)."""
	estab = frappe.db.get_value("SRI Establecimiento", establecimiento, "record_name") if establecimiento else None
	titulo = f"{estab}-{codigo}" if estab else (codigo or "")
	return f"{titulo} ({ambiente})" if ambiente else titulo
