import frappe


def check_app_permission():
	"""Mostrar el icono SRI en la pantalla de aplicaciones solo a quien puede usarlo."""
	if frappe.session.user == "Administrator":
		return True

	# Los usuarios web no entran al desk; mostrarles el icono los llevaría a un 403.
	if frappe.get_cached_value("User", frappe.session.user, "user_type") == "Website User":
		return False

	return bool(frappe.has_permission("SRI Punto de Emision", ptype="read"))
