import frappe
import socket
from erpnext_ec.utilities.sri_ws import verify_signature
import json
from datetime import datetime

@frappe.whitelist()
def get_full_url():
    # Obtener el nombre del host desde la solicitud actual
    host_name = frappe.utils.get_host_name_from_request()
    port = ''

    # Verificar si está en modo DNS multitenant
    if not frappe.local.conf.get('dns_multitenant'):    
        port = ':' + str(frappe.local.conf.nginx_port)

    #full_url = f"{host_name}"
    
    #if(not {port} in {host_name}):
    
    # Construir la URL completa con el protocolo y el puerto
    full_url = f"{host_name}{port}"

    return full_url

@frappe.whitelist(allow_guest=True)
def set_cookie(cookie_name, cookie_value):
	if hasattr(frappe.local, "cookie_manager") and frappe.local.cookie_manager:
		frappe.local.cookie_manager.set_cookie(cookie_name, cookie_value)
	return '{status}'

#Esta función servirá para evaluar la configuración actual del sistem
# y determinar si es que esta apta para empezar a realizar documentos
# electrónicos del SRI
def get_puntos_emision_activos(company):
    """Puntos de emisión activos de la compañía, con su código estab-pto y ambiente."""
    establecimientos = frappe.get_all('SRI Establecimiento',
        filters={'company_link': company, 'disabled': 0}, fields=['name', 'record_name'])
    puntos = []
    for est in establecimientos:
        for pto in frappe.get_all('SRI Punto de Emision',
                filters={'sri_establishment_lnk': est.name, 'disabled': 0},
                fields=['name', 'record_name', 'sri_environment_lnk', 'test_dev_email'],
                order_by='record_name asc'):
            puntos.append(frappe._dict(
                name=pto.name,
                codigo=f"{est.record_name}-{pto.record_name}",
                ambiente=pto.sri_environment_lnk,
                test_dev_email=pto.test_dev_email,
            ))
    return puntos

@frappe.whitelist()
def validate_sri_settings():
    result = {}
    groups=[]
    
    
    company_object = frappe.get_all('Company',fields=["*"],)

    for company_item in company_object:
        SettingsAreReady = True
        header = []
        alerts = []
        
        header.append({"index": 0, "description": "Empresa", "value": company_item.name})
        
        # Ambiente SRI: lo define cada punto de emisión (DES = pruebas, PRO = producción)
        puntos = get_puntos_emision_activos(company_item.name)
        if puntos:
            for ambiente in ("PRO", "DES"):
                codigos = [p.codigo for p in puntos if p.ambiente == ambiente]
                if codigos:
                    header.append({"index": 0, "description": f"Puntos de emisión {ambiente}", "value": ", ".join(codigos)})
            sin_correo = [p.codigo for p in puntos if p.ambiente == "DES" and not p.test_dev_email]
            if sin_correo:
                alerts.append({"index": 0,
                               "description": "Puntos de pruebas sin correo de pruebas: " + ", ".join(sin_correo),
                               "help": "Configure 'Test Dev Environment Email' en esos puntos de emisión.",
                               "type": "error"})
                SettingsAreReady = False
        else:
            alerts.append({"index": 0, "description": "No hay puntos de emisión activos",
                           "help": "Cree un establecimiento y un punto de emisión (con su ambiente) para la compañía.",
                           "type": "error"})
            SettingsAreReady = False

        header.append({"index": 0, "description": "Herramienta de firma", "value": company_item.get("sri_signature_tool") or "Python"})
        header.append({"index": 0, "description": "Envío automático", "value": "Sí" if company_item.get("sri_send_auto") else "No"})
        if company_item.get("use_simulation_mode"):
            header.append({"index": 0, "description": "Modo simulación", "value": "Activo (no se envía al SRI)"})

        print_formats = frappe.get_all('Print Format', filters = { "name": ["in", ['Factura SRI','Retención SRI','Guía de Remisión SRI']] })
        #print('---------PRINTS')
        #print(print_formats)
        if(len(print_formats)==0):
            #print('SIN FORMATOS')
            alerts.append({"index": 0, 
                           "description": "Formatos de Impresión no creados", 
                           "help":"Vaya a Formatos de Impresión y haga clic en el botón 'Crear Secuencias''", 
                           "type":"error"})
            SettingsAreReady = False
        else:
            header.append({"index": 0, "description": "Formatos de impresión", "value": len(print_formats)})

        accounts = frappe.get_all('Account', 
                                       filters = [
                ["sricode", "!=", "0"],
                ["sricode", "is", "set"],
                ["sricode", "!=", ""]
            ])

        if(len(accounts)==0):            
            alerts.append({"index": 0, 
                           "description": "Cuentas contables para SRI no creados", 
                           "help":"Vaya a Cuentas Contables y haga clic en el botón 'Crear Datos SRI', o cree los datos de forma manual.", 
                           "type":"error"})
            SettingsAreReady = False
        else:
            header.append({"index": 0, "description": "Cuentas contables para SRI", "value": len(accounts)})

        #Si es que se ha seleccionado firma electrónica
        if(company_item.sri_signature):
            sri_signature = frappe.get_all('SRI Firma Electronica', 
                                        filters = [
                    ["name", "=", company_item.sri_signature]
                ])

            #if(len(sri_signature)==0):                
            #else:
            #    header.append({"index": 0, "description": "Cuentas contables para SRI", "value": len(sri_signature)})
            header.append({"index": 0, "description": "Firma Electrónica seleccionada", "value": company_item.sri_signature})
            if(sri_signature and len(sri_signature) > 0):
                first_record = sri_signature[0]
                first_record_json = json.dumps(first_record, indent=4)
                verify_data = verify_signature(first_record_json)
                print('===============================')
                print(verify_data)
                expiry_date = verify_data['not_valid_after']

                # Obtener la fecha actual
                current_date = datetime.now()

                expiry_date_str = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
                # Comparar las fechas
                if expiry_date < current_date:
                    #print("La fecha está expirada.")
                    alerts.append({"index": 0,
                            "description": f"Firma Electrónica expirada {expiry_date_str}", 
                            "help": f"Debe emitir una nueva firma electrónica.", 
                            "type": "error"})
                    SettingsAreReady = False
                else:                    
                    header.append({"index": 0, "description": "Firma Electrónica fecha expiración", "value": expiry_date_str})
        else:
            alerts.append({"index": 0,
                            "description": "Firma Electrónica no seleccionada", 
                            "help": f"Vaya a Compañia {company_item.name} y seleccione una firma electrónica válida.", 
                            "type":"error"})
            SettingsAreReady = False
        
        if(not SettingsAreReady):
            #print(result)
            create_notification_log(
                user="administrator",
                subject= f"Configuración incompatible con el SRI - {company_item.name}",
                body="Revise la configuración del sistema y corrija para poder crear documentos electrónicos compatibles con el SRI."
            )
            header.append({"index": 0, "description": "Estado", "value": '<span class="indicator-pill red filterable no-indicator-dot ellipsis"><span class="ellipsis"> Fail</span></span>'})
        else:
            header.append({"index": 0, "description": "Estado", "value": '<span class="indicator-pill blue filterable no-indicator-dot ellipsis"><span class="ellipsis"> Ready</span></span>'})
        
        groups.append({
            "index": 0, 
            "description": "Grupo", 
            "value": company_item.name,
            "header": header,
            "alerts": alerts,
            "SettingsAreReady": SettingsAreReady
            })
        
    #result = {
    #    "header": header,
    #    "alerts": alerts,
        #"doctype_erpnext": doctype_erpnext,
        #"typeDocSri": "typeDocSri",
    #    "SettingsAreReady": SettingsAreReady
    #}
    result = {
        "groups": groups
    }    

    return result

@frappe.whitelist(allow_guest=True)
def on_login_auto():
    set_cookie('login_boot', 'yes')
    set_cookie('sri_settings_alert', '0')


def create_notification_log(user, subject, body):
    # Crear un nuevo documento de Notification Log
    notification_log = frappe.get_doc({
        "doctype": "Notification Log",
        "subject": subject,
        "email_content": body,
        "type": "Alert",  # Tipos: Alert, Warning, Error, Success
        "for_user": user,
        "document_type": "",
        "document_name": "",  # Nombre del documento relacionado
        "from_user": frappe.session.user,
        "read": 0,  # 0 = no leído, 1 = leído
    })
    
    # Guardar el documento en la base de datos
    notification_log.insert(ignore_permissions=True)
    
    # Confirmar los cambios
    frappe.db.commit()

