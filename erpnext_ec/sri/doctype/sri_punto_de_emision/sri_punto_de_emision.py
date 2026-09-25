import re

import frappe
from frappe import _
from frappe.model.document import Document


class SRIPuntodeEmision(Document):
	def validate(self):
		self.record_name = (self.record_name or "").strip()
		if not re.fullmatch(r"\d{3}", self.record_name):
			frappe.throw(_("El código del punto de emisión debe tener 3 dígitos (p. ej. 001)."))

		if self.sri_environment_lnk != "DES":
			self.test_dev_email = None

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
