from frappe import _

def get_data():
    return [
        {
            "label": _("ERPNext Ecuador"),
            "icon": "octicon octicon-book",
            "items": [
                {
                    "type": "doctype",
                    "name": "Sri Signature",
                    "label": _("Firmas"),
                    "description": _("Firmas electrónicas"),
                    "onboard": 1,
                }
            ]
        }
    ]