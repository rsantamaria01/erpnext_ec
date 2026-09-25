import re

import frappe
from frappe import _
from frappe.model.document import Document


class SRIEstablecimiento(Document):
	def validate(self):
		self.record_name = (self.record_name or "").strip()
		if not re.fullmatch(r"\d{3}", self.record_name) or self.record_name == "000":
			frappe.throw(_("El código del establecimiento debe tener 3 dígitos y ser mayor a 000 (p. ej. 001)."))

		if not self.disabled:
			duplicado = frappe.db.exists(
				"SRI Establecimiento",
				{
					"company_link": self.company_link,
					"record_name": self.record_name,
					"disabled": 0,
					"name": ("!=", self.name),
				},
			)
			if duplicado:
				frappe.throw(
					_("Ya existe un establecimiento activo {0} para {1} ({2}).").format(
						self.record_name, self.company_link, duplicado
					)
				)

	def on_update(self):
		# el título de sus puntos (001-999 (DES)) incluye el código del establecimiento
		if self.has_value_changed("record_name"):
			from erpnext_ec.sri.doctype.sri_punto_de_emision.sri_punto_de_emision import titulo_punto

			for p in frappe.get_all(
				"SRI Punto de Emision",
				filters={"sri_establishment_lnk": self.name},
				fields=["name", "record_name", "sri_environment_lnk"],
			):
				frappe.db.set_value(
					"SRI Punto de Emision", p.name, "titulo",
					titulo_punto(self.name, p.record_name, p.sri_environment_lnk),
					update_modified=False,
				)
