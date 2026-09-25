// Bloque "Estado SRI" del workspace SRI. root_element lo provee Frappe.
(function () {
	const body = root_element.querySelector(".sri-estado-body");
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

	frappe.call({ method: "erpnext_ec.utilities.tools.validate_sri_settings" }).then((r) => {
		const groups = (r.message && r.message.groups) || [];
		if (!groups.length) {
			body.innerHTML = esc(__("No hay empresas configuradas."));
			return;
		}
		body.classList.remove("text-muted");
		body.innerHTML = groups
			.map((g) => {
				const estado = (g.header || []).find((h) => h.description === "Estado");
				const filas = (g.header || [])
					.filter((h) => !["Estado", "Empresa"].includes(h.description))
					.map((h) => `<tr><td class="sri-k">${esc(h.description)}</td><td>${esc(h.value)}</td></tr>`)
					.join("");
				const alertas = (g.alerts || [])
					.map((a) => `<div class="sri-alert">${esc(a.description)}${a.help ? " — " + esc(a.help) : ""}</div>`)
					.join("");
				return `<div class="sri-card">
					<div class="sri-card-head"><h5>${esc(g.value)}</h5>${estado ? estado.value : ""}</div>
					<table>${filas}</table>${alertas}</div>`;
			})
			.join("");
	});
})();
