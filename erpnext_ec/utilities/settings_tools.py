# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import datetime, date, timedelta
import time
import frappe
from frappe import _
import erpnext
#from frappe.utils.pdf import get_pdf

import json
from types import SimpleNamespace

from erpnext_ec.patches.v15_0 import print_formats, import_tools, email_template
from erpnext_ec.patches.v15_0 import print_formats_online, email_template_online

@frappe.whitelist()
def load_accounts():
	#accounts.execute()
	import_tools.execute()
	print('Terminada la importación y configuracion de cuentas para el SRI')
	pass

@frappe.whitelist()
def load_print_format_sri():
	print_formats.execute()
	print('Terminada la importación de formatos de impresión para el SRI')
	email_template.execute()
	print('Terminada la importación de plantillas de email para el SRI')
	pass

@frappe.whitelist()
def load_print_format_sri_online():
	print_formats_online.execute()
	print('Terminada la importación de formatos de impresión para el SRI')
	email_template_online.execute()
	print('Terminada la importación de plantillas de email para el SRI')
	pass
