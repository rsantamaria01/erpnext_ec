import frappe
from frappe import _
import erpnext
import json
import re
from types import SimpleNamespace
from erpnext_ec.utilities.doc_builder_tools import *
from erpnext_ec.utilities.doc_render_tools import *

@frappe.whitelist()
def build_doc_fac_with_images(doc_name):
	doc_response = build_doc_fac(doc_name)
	doc_response.numeroautorizacion_img = get_barcode_base64(doc_response.numeroautorizacion)
	doc_response.logo_img = get_barcode_base64(doc_response.numeroautorizacion)
	return doc_response

#Factura de Venta
@frappe.whitelist()
def build_doc_fac(doc_name):
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
		#print("TAXEEESSS")
		#print(doc.taxes)

		# Ficha Técnica SRI 2.33 (julio 2026) - RIDE: subtotal de tarifa especial (IVA diferenciado)
		doc.subtotalTarifaEspecial = sum(
			(t.baseImponible or 0)
			for t in doc.taxes
			if getattr(t, "codigoPorcentaje", None) in (8, 10)
		)
  
		#print("ITEEEEMMMMSSSS")
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
		doc.ambiente = company_full['ambiente']

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
		customer_email_id = customer_full['customer_email_id']

		doc.customer_phone = customer_phone
		doc.customer_email_id = customer_email_id

		# 		if customerAddress:
		# 			emailComprador = customerAddress[0].email_id
		# 			doc.customer_email_id = emailComprador
		# 		else:
		# 			sri_validated = 'error'
		# 			sri_validated_message += 'No se ha definido Email del cliente-'
		# 	else:
		# 		sri_validated = 'error'
		# 		sri_validated_message += 'No se han definido datos de dirección del cliente-'
		# else:
		# 	sri_validated = 'error'
		# 	sri_validated_message += 'Cliente requerido'

		# 	if not paymentsApi and  not paymentsEntryApi:
		# 		sri_validated = 'error'
		# 		sri_validated_message += 'No se ha definido ni solicitud de pago ni entrada de pago-'

		doc.paymentsItems = get_payments_sri(doc.name)
		doc.pagos = build_pagos(doc.paymentsItems)

		#for paym in  doc.paymentsItems:
		#	print(paym)

		doc.infoAdicional = build_infoAdicional_sri(doc_name, customer_email_id, customer_phone)

		# print(doc.infoAdicional)
		#doc.taxes_full = get_full_taxes(doc.taxes)		

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
			new_secuencial = setSecuencial(doc, 'FAC')
			if new_secuencial > 0:
				doc.secuencial = new_secuencial			

		tipoDocumento = '01'
		tipoAmbiente = doc.ambiente
		tipoEmision = 1

		fechaEmision = doc.posting_date		
		secuencial = doc.secuencial
		ruc = doc.tax_id #doc.company_tax_id
		
		puntoEmision_rec = get_full_ptoemi(doc.ptoemi)
		if not puntoEmision_rec:
			frappe.throw(_("No se ha definido el punto de emisión (ptoEmi). Configure los datos SRI para emitir el comprobante electrónico."))
		doc.ptoemi = puntoEmision_rec.record_name
		puntoEmision = doc.ptoemi
		
		establecimiento_rec = get_full_establishment(doc.estab)
		if not establecimiento_rec:
			frappe.throw(_("No se ha definido el establecimiento (estab). Configure los datos SRI para emitir el comprobante electrónico."))
		doc.estab = establecimiento_rec.record_name
		establecimiento = doc.estab

		if(ruc == None):
			ruc = '0000000000000'

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

def build_doc_fac_sri(data_object):
	
	#print(data_object)
	#return ""

	totalConImpuestos = []

	for taxItem in data_object.taxes:
		totalConImpuestos.append({
			"totalImpuesto": {
						"codigo": taxItem.sricode,
						"codigoPorcentaje": taxItem.codigoPorcentaje,
						"baseImponible": "{:.2f}".format(taxItem.baseImponible),
						"tarifa": "{:.2f}".format(taxItem.rate),
						"valor": "{:.2f}".format(taxItem.tax_amount)
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
						"baseImponible": "{:.2f}".format(impuesto['baseImponible']),
						"valor": "{:.2f}".format(impuesto['valor']) #impuesto['valor']
					}})

		#ErpNext coloca descuento negativo cuando el precio es modificado a un precio mas alto
		# es decir , llena el campo discount_amount pero no el discount_percentage
		#if (item.discount_amount < 0 and item.discount_percentage == 0):
		#	item.discount_amount = 0

		detalle_item = {
                "codigoPrincipal": item.item_code,
            }
		codigo_auxiliar = getattr(item, 'codigoAuxiliar', '')
		if codigo_auxiliar:
			# El codigoAuxiliar debe ir después de codigoPrincipal (Anexos 23 y 25 Ficha 2026)
			detalle_item["codigoAuxiliar"] = codigo_auxiliar
		detalle_item.update({
                "descripcion": item.description.upper(),
                "cantidad": "{:.6f}".format(item.qty),
                "precioUnitario": "{:.6f}".format(item.precioUnitario),
                "descuento": "{:.2f}".format(item.qty * item.discount_amount),
                "precioTotalSinImpuesto": "{:.2f}".format(item.precioTotalSinImpuesto),
                "impuestos": impuestos                
            })
		detalles.append(detalle_item)

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
	
	pagos = []
	#print(data_object.pagos)
	
	for pagoItem in data_object.pagos:
		pagos.append({
					"pago":
					{
						"formaPago": pagoItem['formaPago'],
						"total": "{:.2f}".format(pagoItem['total']),
						"plazo": pagoItem['plazo'],
						"unidadTiempo": pagoItem['unidadTiempo']
					}})

	#print(pagos)

	obligadoContabilidad = 'NO'
	if(data_object.obligadoContabilidad == 1):
		obligadoContabilidad = 'SI'
	
	agenteRetencion = None
	if(not data_object.agenteRetencion == None and 
		not data_object.agenteRetencion == '' and
		not data_object.agenteRetencion == '0'):
		agenteRetencion = data_object.agenteRetencion

	contribuyenteRimpe = "CONTRIBUYENTE RÉGIMEN RIMPE"
	if(data_object.contribuyenteRimpe != 1):
		contribuyenteRimpe = None

	# Ficha Técnica SRI 2.34 (julio 2026) - Anexo 25: placa del vehículo para
	# operadoras de transporte comercial (entre <moneda> y <pagos>)
	placa = getattr(data_object, 'sri_placa', None)
	# el campo viene con default "0"; "0" o vacío = sin placa
	if placa and str(placa).strip() not in ("0", ""):
		placa = re.sub(r"[\s-]", "", str(placa)).upper()
	else:
		placa = None

	data = {
        "infoTributaria": {
            "ambiente": data_object.ambiente,
            "tipoEmision": "1",
            "razonSocial": data_object.razonSocial.upper(),
            "nombreComercial": data_object.nombreComercial.upper(),
            "ruc": data_object.tax_id,
            "claveAcceso": data_object.claveAcceso,
            "codDoc": "01",
            "estab" : data_object.estab,
            "ptoEmi" : data_object.ptoemi,
            "secuencial" : '{:09d}'.format(data_object.secuencial),
            "dirMatriz" : data_object.DireccionMatriz.upper(),
			"agenteRetencion": agenteRetencion,
			"contribuyenteRimpe": contribuyenteRimpe
        },
        "infoFactura": {
            "fechaEmision": data_object.posting_date.strftime("%d/%m/%Y"), # data_object.posting_date,
            "dirEstablecimiento": data_object.dirEstablecimiento.upper(),
            "contribuyenteEspecial": data_object.contribuyenteEspecial,
            "obligadoContabilidad": obligadoContabilidad,
            "tipoIdentificacionComprador": data_object.tipoIdentificacionComprador,
            "razonSocialComprador": data_object.customer_name.upper(),
            "identificacionComprador": data_object.customer_tax_id,
            "totalSinImpuestos": "{:.2f}".format(data_object.base_total),
            "totalDescuento": "{:.2f}".format(data_object.totalDescuento),
            "totalConImpuestos": totalConImpuestos,
            "propina": "0.00",
            "importeTotal": "{:.2f}".format(data_object.grand_total),
            "moneda": "DOLAR",
        },
        "detalles": {
            "detalle": detalles
        },
        "infoAdicional": {
            "campoAdicional": infoAdicional
        }
    }

	# El orden del XSD 1.1.0 es: importeTotal, moneda, placa, pagos
	if placa:
		data["infoFactura"]["placa"] = placa
	data["infoFactura"]["pagos"] = pagos

	return data
