# -*- coding: utf-8 -*-
# Patch ERPNext v16 - Sidebar y Desktop Icon de "ERPNext Ec"
# En Frappe 16 el sidebar y el conmutador de workspaces se construyen desde
# los doctypes Workspace Sidebar y Desktop Icon. Se generan en after_app_install,
# pero el workspace "ERPNext Ec" se creo despues, por lo que hay que generarlos
# explicitamente. La funcion es idempotente.
# (La página sri-estado se reemplazó por el bloque "Estado SRI" del workspace.)

import frappe
from frappe.utils.install import auto_generate_icons_and_sidebar


def execute():
	auto_generate_icons_and_sidebar()
