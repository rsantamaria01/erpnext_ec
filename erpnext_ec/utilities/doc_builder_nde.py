import frappe
from frappe import _
import erpnext
import json
from types import SimpleNamespace
from erpnext_ec.utilities.doc_builder_tools import *
from erpnext_ec.utilities.doc_render_tools import *

@frappe.whitelist()
def build_doc_nde_with_images(doc_name):
	doc_response = build_doc_nde(doc_name)
	doc_response.numeroautorizacion_img = get_barcode_base64(clave_para_barcode(doc_response))
	doc_response.logo_img = get_barcode_base64(clave_para_barcode(doc_response))
	return doc_response

#Nota de Crédito
@frappe.whitelist()
def build_doc_nde(doc_name):
	# DireccionMatriz = ''
	# dirEstablecimiento = ''
	# direccionComprador = ''
	# emailComprador = ''	
    
	docs = frappe.get_all('Sales Invoice', filters={"name": doc_name}, fields = ['*'])
	customer_email_id =  ''

	sri_validated = 'ok';
	sri_validated_message = ''

	if docs:
		doc = docs[0]
		
		doc.taxes = get_full_taxes(doc.name)

		# Ficha Técnica SRI 2.33 (julio 2026) - RIDE: subtotal de tarifa especial (IVA diferenciado)
		doc.subtotalTarifaEspecial = sum(
			(t.baseImponible or 0)
			for t in doc.taxes
			if getattr(t, "codigoPorcentaje", None) in (8, 10)
		)
		
		doc.items = get_full_items(doc.name, doc)
		#print(doc.items)

		#Datos completos de la compañia emisora
		company_full = get_full_company_sri(doc.company)

		#print('Compañia')
		#print(company_full)

		doc.razonSocial = company_full['razonSocial'] #La razon social es el nombre normal de la empresa emisora
		doc.nombreComercial = company_full['nombreComercial']
		doc.company_name = doc.company
		
		doc.tax_id = company_full['ruc']
		doc.DireccionMatriz = company_full['dirMatriz']
		doc.dirEstablecimiento = company_full['dirMatriz'] # TODO: temporal, la dirección del establecimiento debe ser definida
		doc.contribuyenteRimpe = company_full['contribuyenteRimpe']
		doc.obligadoContabilidad = company_full['obligadoContabilidad']
		doc.agenteRetencion = company_full['agenteRetencion']
		doc.contribuyenteEspecial = company_full['contribuyenteEspecial']
		set_ambiente_sri(doc)  # ambiente y correo de pruebas según el punto de emisión

		# Ficha Técnica SRI 2.34 (julio 2026) - Anexos 24 y 26
		doc.granContribuyente = company_full['granContribuyente']
		doc.granContribuyenteResolucion = company_full['granContribuyenteResolucion']
		doc.rucProveedor = company_full['rucProveedor']

		#Datos completos del cliente
		customer_full = get_full_customer_sri(doc.customer)
		doc.customer_tax_id = customer_full['customer_tax_id']		
		doc.tipoIdentificacionComprador = customer_full['tipoIdentificacionComprador']
		doc.direccionComprador = customer_full['direccionComprador']
		customer_phone = customer_full['customer_phone']
		customer_email_id = customer_full['customer_email_id'] or company_full.get('defaultEmail') or ''

		doc.customer_phone = customer_phone
		doc.customer_email_id = customer_email_id

		if(doc.return_against):
			docs_ret_ag = frappe.get_all('Sales Invoice', filters={"name": doc.return_against}, fields = ['*'])
			
			if(docs_ret_ag):
				docs_ret_ag = docs_ret_ag[0]
				print(docs_ret_ag)
				doc.codDocModificado = '01'
				#valorModificacion
				#motivo
				#docs_ret_ag.numeroautorizacion
				doc.numDocModificado = docs_ret_ag.docidsri 
				doc.fechaEmisionDocSustento = docs_ret_ag.fechaautorizacion
				doc.valorModificacion = docs_ret_ag.grand_total
				doc.motivo = 'DEVOLUCION'

		doc.infoAdicional = build_infoAdicional_sri(doc_name, customer_email_id, customer_phone)

		# Formas de pago (el RIDE de la nota de débito las muestra)
		doc.paymentsItems = get_payments_sri(doc.name)
		doc.pagos = build_pagos(doc.paymentsItems) or []

		#Simulando error
		sri_validated = 'error'
		sri_validated_message += 'Cliente requerido-'
		sri_validated_message += 'No se han definido datos de dirección del cliente-'
		sri_validated_message += 'No se ha definido Email del cliente-'
		sri_validated_message += 'Establecimiento incorrecto-'
		sri_validated_message += 'Punto de emisión incorrecto-'
		sri_validated_message += 'No se ha definido ni solicitud de pago ni entrada de pago-'
		#Simulando error-----------fin

		if sri_validated == 'ok':
			sri_validated_message = 'Listo!';
		
		doc.sri_validated = sri_validated
		doc.sri_validated_message = sri_validated_message

		if(not doc.secuencial or doc.secuencial == 0):
			new_secuencial = setSecuencial(doc, 'NDE')
			if new_secuencial > 0:
				doc.secuencial = new_secuencial			

		tipoDocumento = '04'
		tipoAmbiente = doc.ambiente
		tipoEmision = 1

		fechaEmision = doc.posting_date
		puntoEmision_rec = get_full_ptoemi(doc.ptoemi)
		if not puntoEmision_rec:
			frappe.throw(_("No se ha definido el punto de emisión (ptoEmi). Configure los datos SRI para emitir el comprobante electrónico."))
		doc.ptoemi = puntoEmision_rec.record_name
		puntoEmision = doc.ptoemi
		secuencial = doc.secuencial
		ruc = doc.company_tax_id
		establecimiento_rec = get_full_establishment(doc.estab)
		if not establecimiento_rec:
			frappe.throw(_("No se ha definido el establecimiento (estab). Configure los datos SRI para emitir el comprobante electrónico."))
		doc.estab = establecimiento_rec.record_name
		establecimiento = doc.estab

		claveAcceso = GenerarClaveAcceso(tipoDocumento, 
                                     fechaEmision, 
                                     puntoEmision, 
                                     secuencial, 
                                     tipoEmision, 
									ruc,
									tipoAmbiente,
									establecimiento)
		
		print(f'Clave de acceso creada: {claveAcceso}')

		doc.claveAcceso = claveAcceso

		return doc

def build_doc_nde_sri(data_object):
	
	#print(data_object)
	#return ""

	totalConImpuestos = []

	for taxItem in data_object.taxes:
		totalConImpuestos.append({
			"totalImpuesto": {
						"codigo": taxItem.sricode,
						"codigoPorcentaje": taxItem.codigoPorcentaje,
						"baseImponible": "{:.2f}".format(abs(taxItem.baseImponible)),						
						"valor": "{:.2f}".format(abs(taxItem.tax_amount))
					}
		})

	#print(data_object['items'])

	detalles = []

	for item in data_object['items']:

		#print(item)
		impuestos = []

		for impuesto in item.impuestos:
			#print(impuesto)

			impuestos.append({
					"impuesto": {
						"codigo": impuesto['codigo'],
						"codigoPorcentaje": impuesto['codigoPorcentaje'],
						"tarifa": "{:.2f}".format(impuesto['tarifa']),
						"baseImponible": "{:.2f}".format(abs(impuesto['baseImponible'])),
						"valor": "{:.2f}".format(abs(impuesto['valor'])) #impuesto['valor']
					}})

		#ErpNext coloca descuento negativo cuando el precio es modificado a un precio mas alto
		# es decir , llena el campo discount_amount pero no el discount_percentage
		#if (item.discount_amount < 0 and item.discount_percentage == 0):
		#	item.discount_amount = 0

		detalles.append({
                "codigoInterno": item.item_code,
                "descripcion": item.description.upper(),
                "cantidad": abs(item.qty),
                "precioUnitario": "{:.2f}".format(abs(item.precioUnitario)),
                "descuento": "{:.2f}".format(abs(item.qty * item.discount_amount)),
                "precioTotalSinImpuesto": "{:.2f}".format(abs(item.precioTotalSinImpuesto)),
                "impuestos": impuestos
            })

	infoAdicional = []
	for infoAdicionalItem in data_object.infoAdicional:
		if(infoAdicionalItem['valor']):
			infoAdicional.append(
			{
				"nombre": infoAdicionalItem['nombre'],
				"valor": infoAdicionalItem['valor'].upper()
			})

	# Ficha Técnica SRI 2.33 (julio 2026) - Anexo 24: leyenda Gran Contribuyente
	if getattr(data_object, 'granContribuyente', 0):
		infoAdicional.append({
			"nombre": "Gran Contribuyente",
			"valor": (data_object.granContribuyenteResolucion or "Gran Contribuyente").upper()
		})

	# Ficha Técnica SRI 2.34 (julio 2026) - Anexo 26: RUC del proveedor de sistemas
	if getattr(data_object, 'rucProveedor', ''):
		infoAdicional.append({
			"nombre": "RUC Proveedor",
			"valor": data_object.rucProveedor
		})
		
	obligadoContabilidad = 'NO'
	if(data_object.obligadoContabilidad == 1):
		obligadoContabilidad = 'SI'

	data = {
        "infoTributaria": {
            "ambiente": data_object.ambiente,
            "tipoEmision": "1",
            "razonSocial": data_object.razonSocial.upper(),
            "nombreComercial": data_object.nombreComercial.upper(),
			
            "ruc": data_object.tax_id,
            "claveAcceso": data_object.claveAcceso,
            "codDoc": "04",
            "estab" : data_object.estab,
            "ptoEmi" : data_object.ptoemi,
            "secuencial" : '{:09d}'.format(data_object.secuencial),
            "dirMatriz" : data_object.DireccionMatriz.upper(),
			"contribuyenteRimpe": "CONTRIBUYENTE RÉGIMEN RIMPE" if data_object.contribuyenteRimpe == 1 else None
        },
        "infoNotaDebito": {
            "fechaEmision": data_object.posting_date.strftime("%d/%m/%Y"), # data_object.posting_date,
            "dirEstablecimiento": data_object.dirEstablecimiento.upper(),
			"tipoIdentificacionComprador": data_object.tipoIdentificacionComprador,
            "razonSocialComprador": data_object.customer_name.upper(),
            "identificacionComprador": data_object.customer_tax_id,
            "contribuyenteEspecial": data_object.contribuyenteEspecial,
            "obligadoContabilidad": obligadoContabilidad,
			
			"codDocModificado": data_object.codDocModificado,
			"numDocModificado": data_object.numDocModificado,
			"fechaEmisionDocSustento": data_object.fechaEmisionDocSustento.strftime("%d/%m/%Y"),
            
            "totalSinImpuestos": "{:.2f}".format(abs(data_object.base_total)),
            "valorModificacion": data_object.valorModificacion,
			"moneda": "DOLAR",
            "totalConImpuestos": totalConImpuestos,            
            
			"motivo": data_object.motivo,
        },
        "detalles": {
            "detalle": detalles
        },
        "infoAdicional": {
            "campoAdicional": infoAdicional
        }
    }

	return data
