# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import datetime
import frappe
import frappe.utils
from frappe import _
import json
from types import SimpleNamespace
import requests
from erpnext_ec.utilities.encryption import encrypt_string

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# from bson import json_util
# import json

import re

def build_comment(comments):
    str_comment = ''
    for comment in comments:
        # print(comment)
        str_comment = comment.get('content', '')
        str_comment = strip_html(str_comment)
        str_comment = normalize_string(str_comment)
        break  # Sale del bucle después de procesar el primer comentario
    
    # Aquí puedes manejar si str_comment está vacío después del bucle
    # if not str_comment:
    #     pass
    return str_comment

def strip_html(input_string):
    """Elimina todas las etiquetas HTML de una cadena."""
    return re.sub('<[^>]*>', '', input_string)

def normalize_string(source_str):
    """Normaliza una cadena eliminando caracteres especiales y espacios extra."""
    try:
        normalized_str = source_str.strip()
        normalized_str = re.sub('[^a-zA-Z0-9 ]+', '', normalized_str.normalize('NFD'))
    except Exception as e:
        print('Error: NormalizeString')
        print('Data: ' + source_str)
        # Aquí puedes manejar el error según tus necesidades
        normalized_str = source_str  # Considera devolver la cadena original o manejar de otra manera
    return normalized_str

def build_infoAdicional_sri(doc_name, customer_email_id, customer_phone):

    commentsApi = frappe.get_all('Comment', filters = { 'reference_name': doc_name }, fields='*' );
    # print('COMENTAAAAAARIOOOOOOSSSSSS')
    # print(commentsApi)

    strComment = build_comment(commentsApi)

    infoAdicionalData = "";
    infoAdicionalData = [{
                            "nombre":"email",
                            "valor": customer_email_id
                            },
                            {
                            "nombre":"tel.",
                            "valor": customer_phone
                            },
                            {
                            "nombre":"Doc. Ref.",
                            "valor":doc_name
                            },
                            {
                            "nombre":"Coment.",
                            "valor":strComment
                            }
                        ];

    return infoAdicionalData

def get_payments_sri(doc_name):
    sri_validated = ''
    sri_validated_message = ''
      
    #paymentsEntryApi = frappe.get_list('Payment Entry Reference', filters = { 'reference_name': doc_name }, 
    #                                   fields = ['name', 'reference_doctype','reference_name','payment_term','parent','parentfield','parenttype','allocated_amount'])
    
    paymentsEntryReferenceApi = frappe.get_all('Payment Entry Reference', fields='*', filters = { 'reference_name': doc_name })

    #print(paymentsEntryReferenceApi)

    if not paymentsEntryReferenceApi:
        #paymentsApi = frappe.get_list('Payment Request', filters = { 'reference_name': doc_name })
        paymentsApi = frappe.get_all('Payment Request', fields='*', filters = { 'reference_name': doc_name })
        # print(paymentsApi)

        if not paymentsApi and  not paymentsEntryReferenceApi:
            # Venta a crédito sin pago aún: se usa el calendario de pagos de la factura
            # (forma de pago + plazo en días desde la fecha de emisión)
            schedule = frappe.get_all('Payment Schedule',
                                      fields=['mode_of_payment', 'payment_amount', 'due_date'],
                                      filters={'parent': doc_name, 'parenttype': 'Sales Invoice'},
                                      order_by='idx asc')
            if schedule:
                posting_date = frappe.db.get_value('Sales Invoice', doc_name, 'posting_date')
                resultados = []
                for row in schedule:
                    plazo = 0
                    if row.due_date and posting_date:
                        plazo = max((frappe.utils.getdate(row.due_date) - frappe.utils.getdate(posting_date)).days, 0)
                    resultados.append(frappe._dict(mode_of_payment=row.mode_of_payment,
                                                   grand_total=row.payment_amount,
                                                   plazo=plazo))
                return resultados
            sri_validated = 'error'
            sri_validated_message += 'No se ha definido ni solicitud de pago ni entrada de pago-'
        else:
            return paymentsApi
    else:
        
        paymentResults = []

        for paymentEntryReference in paymentsEntryReferenceApi:
            paymentEntries = frappe.get_all('Payment Entry', fields='*', filters = { 'name': paymentEntryReference.parent })
            #print('Pagos' )
            #print(paymentEntries)
            if(paymentEntries):
                for paymentEntry in paymentEntries:
                    paymentResults.append(paymentEntry)
            else:
                paymentResults.append(paymentEntryReference)        
        
        return paymentResults    
    return None

#devolver formaPago, plazo, total
def build_pagos(paymentResults):
    pagos = []
    if paymentResults:
        for paymentEntry in paymentResults:
            mode_of_payment = frappe.get_all('Mode of Payment', fields='*', filters = { 'name': paymentEntry.mode_of_payment })
            if(mode_of_payment):
                pago_item = {}
                pago_item['formaPago'] = mode_of_payment[0].formapago
                pago_item['formaPagoDescripcion'] = mode_of_payment[0].name
                pago_item['plazo'] = paymentEntry.get('plazo') or 0
                pago_item['unidadTiempo'] = 'dias'

                if (not paymentEntry.grand_total is None):
                    pago_item['total'] = paymentEntry.grand_total
                else:
                    pago_item['total'] = paymentEntry.paid_amount
                    
                #print(paymentEntry)           
                pagos.append(pago_item)
    return pagos

def get_full_company_sri(def_company):
    # Variable de retorno
    compania_sri = {}

    # Obteniendo la compañía por defecto si def_company es None
    # def_company = def_company or frappe.defaults.get_user_default("Company")

    docs = frappe.get_all('Company', fields='*', filters={'name': def_company})
    #print(docs)
    
    if docs:
        doc = docs[0]
        compania_sri['razonSocial'] = doc.name
        
        if(not doc.nombrecomercial is None and not str.strip(doc.nombrecomercial) == ''):
            compania_sri['nombreComercial'] = doc.nombrecomercial
        else:
            compania_sri['nombreComercial'] = doc.name

        compania_sri['ruc'] = doc.tax_id
        compania_sri['obligadoContabilidad'] = doc.obligadocontabilidad
        compania_sri['contribuyenteRimpe'] = doc.contribuyenterimpe
        compania_sri['agenteRetencion'] = doc.agenteretencion
        compania_sri['contribuyenteEspecial'] = doc.contribuyenteespecial

        # Ficha Técnica SRI 2.34 (julio 2026) - Anexos 24 y 26
        compania_sri['granContribuyente'] = getattr(doc, 'sri_gran_contribuyente', 0)
        compania_sri['granContribuyenteResolucion'] = getattr(doc, 'sri_gran_contribuyente_resolucion', '') or ''
        compania_sri['rucProveedor'] = getattr(doc, 'sri_ruc_proveedor', '') or ''

        # El ambiente SRI ya no es de la compañía: lo define el punto de emisión
        # de cada documento (ver set_ambiente_sri).

        company_address_primary = None
        company_address_first = None

        din_link_api = frappe.get_all('Dynamic Link', fields=["name","parent","link_title"],
                                                filters={'link_doctype': 'Company', 'parenttype': 'Address', 'link_name': def_company})
        #print(din_link_api)

        if din_link_api:
            found_primary = False
            for i, link in enumerate(din_link_api):
                company_address = frappe.get_all('Address', fields='*', filters={'name': link.parent})
                # print(company_address)

                if company_address:
                    if i == 0:
                        company_address_first = company_address[0]

                    if company_address[0].get('is_primary_address'):
                        found_primary = True
                        company_address_primary = company_address[0]
                        break

            if not found_primary and company_address_first:
                company_address_primary = company_address_first

        #print(company_address_primary)

        if company_address_primary:
            compania_sri['dirMatriz'] = company_address_primary.address_line1
        else:
            compania_sri['dirMatriz'] = ''

        #print(compania_sri)
        return compania_sri
    

def get_ptoemi_sri(doc):
    """Punto de emisión del documento, validado contra su establecimiento y compañía.

    El punto de emisión es la única fuente del ambiente SRI (DES/PRO) del documento.
    doc.ptoemi / doc.estab son nombres de Link (PTO-00001 / EST-00001); para el
    establecimiento se acepta también el código SRI (001) por compatibilidad.
    """
    if not doc.get('ptoemi'):
        frappe.throw(_("No se ha definido el punto de emisión (ptoEmi). Configure los datos SRI para emitir el comprobante electrónico."))

    pto = frappe.db.get_value('Sri Ptoemi', doc.ptoemi,
        ['name', 'record_name', 'sri_establishment_lnk', 'sri_environment_lnk', 'disabled', 'test_dev_email'],
        as_dict=True)
    if not pto:
        frappe.throw(_("No existe el punto de emisión {0}.").format(doc.ptoemi))
    if pto.disabled:
        frappe.throw(_("El punto de emisión {0} ({1}) está deshabilitado.").format(pto.name, pto.record_name))

    estab = frappe.db.get_value('Sri Establishment', pto.sri_establishment_lnk,
        ['name', 'record_name', 'company_link', 'disabled'], as_dict=True)
    if not estab:
        frappe.throw(_("El punto de emisión {0} no tiene un establecimiento válido.").format(pto.name))
    if doc.get('estab') and doc.estab not in (estab.name, estab.record_name):
        frappe.throw(_("El punto de emisión {0} ({1}) no pertenece al establecimiento {2}.").format(
            pto.name, pto.record_name, doc.estab))
    if estab.company_link and doc.get('company') and estab.company_link != doc.company:
        frappe.throw(_("El establecimiento {0} no pertenece a la compañía {1}.").format(estab.name, doc.company))
    if estab.disabled:
        frappe.throw(_("El establecimiento {0} ({1}) está deshabilitado.").format(estab.name, estab.record_name))

    ambiente = frappe.utils.cint(frappe.db.get_value('Sri Environment', pto.sri_environment_lnk, 'id'))
    if ambiente not in (1, 2):
        frappe.throw(_("El punto de emisión {0} no tiene un ambiente SRI válido.").format(pto.name))

    pto.ambiente = ambiente
    pto.estab_name = estab.name
    return pto


def set_ambiente_sri(doc):
    """Asigna doc.ambiente (1 = pruebas, 2 = producción) y doc.test_dev_email
    según el punto de emisión del documento.

    Si el documento ya fue autorizado, el ambiente se toma de su número de
    autorización (dígito 24 de la clave de acceso), así el RIDE de un
    documento antiguo no cambia aunque luego se cambie el ambiente del punto.
    """
    pto = get_ptoemi_sri(doc)
    doc.ambiente = pto.ambiente

    numero = (doc.get('numeroautorizacion') or '').strip()
    if len(numero) == 49 and numero.isdigit() and numero[23] in ('1', '2'):
        doc.ambiente = int(numero[23])

    doc.test_dev_email = pto.test_dev_email if doc.ambiente == 1 else None
    return pto


def get_full_customer_sri(def_customer):
    # Variable de retorno
    customer_sri = {}

    # Obteniendo la compañía por defecto si def_company es None
    # def_company = def_company or frappe.defaults.get_user_default("Company")

    docs = frappe.get_all('Customer', fields='*', filters={'name': def_customer})    
    
    #print(docs)

    if docs:
        doc = docs[0]
        #print(doc)
        customer_sri['customer_tax_id'] = doc.tax_id
        if(doc.nombrecomercial):
            customer_sri['customer_name'] = doc.nombrecomercial
        else:
            customer_sri['customer_name'] = doc.name


        should_update_typeidtax = False

        if len(doc.typeidtax) > 2:
            print(doc.typeidtax[:2])
            doc.typeidtax = doc.typeidtax[:2]
            should_update_typeidtax = True        
        
        if len(doc.typeidtax) == 0:            
            doc.typeidtax = '04'
            #Cuando el campo typeidtax esta vacio
            if(len(doc.tax_id) == 10):
                #Se asumira que es CEDULA
                doc.typeidtax = '05'
            #if(len(doc.tax_id) == 13):
                #Se asumira que es RUC
            #    doc.typeidtax = '04'
            
            should_update_typeidtax = True
        

        #Se fuerza la actualizacion del dato del cliente
        # para que tenga seleccionado un RUC o CEDULA
        # ya que si el dato esta siendo migrado desde el modo viejo
        # habran datos almacenados similares a 04 RUC (debe ser solo 04)
        # o estará vacío
        if (should_update_typeidtax):
            document_for_update = frappe.get_last_doc('Customer', filters = { 'name': doc.name})
            if(document_for_update):
                document_for_update.db_set('typeidtax', doc.typeidtax)

        customer_sri['tipoIdentificacionComprador'] = doc.typeidtax
        customer_sri['customer_email_id']  = ''
        customer_sri['customer_phone']  = ''

        customer_address_primary = None
        customer_address_first = None

        din_link_api = frappe.get_all('Dynamic Link', fields=["name","parent","link_title"],
                                                filters={'link_doctype': 'Customer', 'parenttype': 'Address', 'link_name': def_customer})
        # print('DIRECCCCCCCCCCIIIIIIIONNNNNNN CUSTOMMMMERRRR')
        # print(din_link_api)

        if din_link_api:
            found_primary = False
            for i, link in enumerate(din_link_api):
                customer_address = frappe.get_all('Address', fields='*', filters={'name': link.parent})
                #print(customer_address)

                if customer_address:
                    if i == 0:
                        customer_address_first = customer_address[0]

                    if customer_address[0].get('is_primary_address'):
                        found_primary = True
                        customer_address_primary = customer_address[0]
                        break

            if not found_primary and customer_address_first:
                customer_address_primary = customer_address_first
        else:
            #Sino se encuentra una dirección vinculada se busca una direccion primaria del cliente
            customer_address = frappe.get_all('Address', fields='*', filters={'name': docs[0].customer_primary_address})
            if customer_address:
                customer_address_primary = customer_address[0]
            else:
                print('---')
                
        if customer_address_primary:
            customer_sri['customer_email_id']  = customer_address_primary.email_id
            customer_sri['customer_phone']  = customer_address_primary.phone
            customer_sri['address_line1']  = customer_address_primary.address_line1 if customer_address_primary.address_line1 is not None else ''
            customer_sri['address_line2']  = customer_address_primary.address_line2 if customer_address_primary.address_line2 is not None else ''
            customer_sri['direccionComprador']  = customer_sri['address_line1'] + ' ' + customer_sri['address_line2']
        else:
            customer_sri['customer_email_id']  = ''
            customer_sri['customer_phone']  = ''
            customer_sri['address_line1']  = ''
            customer_sri['address_line2']  = ''
            customer_sri['direccionComprador']  = ''

        #print(compania_sri)
        return customer_sri

def get_full_supplier_sri(def_customer):
    # Variable de retorno
    supplier_sri = {}

    # Obteniendo la compañía por defecto si def_company es None
    # def_company = def_company or frappe.defaults.get_user_default("Company")

    docs = frappe.get_all('Supplier', fields='*', filters={'name': def_customer})    
    
    #print(docs)

    if docs:
        doc = docs[0]
        print(doc)
        #print(doc)
        #print('doc.typeidtax')
        #print(doc.typeidtax)
        supplier_sri['supplier_tax_id'] = doc.tax_id
        if(doc.nombrecomercial):
            supplier_sri['supplier_name'] = doc.nombrecomercial
        else:
            supplier_sri['supplier_name'] = doc.supplier_name
        supplier_sri['tipoIdentificacionProveedor'] = doc.typeidtax
        supplier_sri['supplier_email_id']  = ''
        supplier_sri['supplier_phone']  = ''
        
        #supplier_sri["razonSocialProveedor"] = doc.nombrecomercial.upper(),

        supplier_address_primary = None
        supplier_address_first = None

        din_link_api = frappe.get_all('Dynamic Link', fields=["name","parent","link_title"],
                                                filters={'link_doctype': 'Supplier', 'parenttype': 'Address', 'link_name': def_customer})
        
        # print(din_link_api)

        if din_link_api:
            found_primary = False
            for i, link in enumerate(din_link_api):
                supplier_address = frappe.get_all('Address', fields='*', filters={'name': link.parent})
                #print(customer_address)

                if supplier_address:
                    if i == 0:
                        supplier_address_first = supplier_address[0]

                    if supplier_address[0].get('is_primary_address'):
                        found_primary = True
                        supplier_address_primary = supplier_address[0]
                        break

            if not found_primary and supplier_address_first:
                supplier_address_primary = supplier_address_first
        else:
            print (docs)
            #Sino se encuentra una dirección vinculada se busca una direccion primaria del proveedor
            supplier_address = frappe.get_all('Address', fields='*', filters={'name': docs[0].supplier_primary_address})
            if supplier_address:
                supplier_address_primary = supplier_address[0]
            else:
                print('---')
        
        #print('supplier_address_primary')
        #print(supplier_address_primary)

        if supplier_address_primary:
            supplier_sri['supplier_email_id']  = supplier_address_primary.email_id
            supplier_sri['supplier_phone']  = supplier_address_primary.phone
            supplier_sri['address_line1']  = supplier_address_primary.address_line1 if supplier_address_primary.address_line1 is not None else ''
            supplier_sri['address_line2']  = supplier_address_primary.address_line2 if supplier_address_primary.address_line2 is not None else ''
            supplier_sri['direccionSujetoRetenido'] = supplier_sri['address_line1'] + ' ' + supplier_sri['address_line2']
            supplier_sri['direccionProveedor'] = supplier_sri['address_line1'] + ' ' + supplier_sri['address_line2']
        else:
            supplier_sri['supplier_email_id']  = ''
            supplier_sri['supplier_phone']  = ''
            supplier_sri['address_line1']  = ''
            supplier_sri['address_line2']  = ''
            supplier_sri['direccionSujetoRetenido']  = ''
            supplier_sri['direccionProveedor'] = None
            

        #print(compania_sri)
        return supplier_sri


def build_item_impuestos(item, doc_parent):
    """Impuestos por ítem para el XML del SRI.

    ERPNext v16 reemplazó el JSON `item_wise_tax_detail` de cada fila de impuestos
    por la tabla hija `Item Wise Tax Detail` (item_row, tax_row, rate, amount,
    taxable_amount). Se lee de ahí; si no existe (v15) se usa el JSON antiguo.
    """
    impuestos = []
    taxes_by_row = {t.name: t for t in (doc_parent.taxes or [])}

    details = []
    if frappe.db.table_exists("Item Wise Tax Detail"):
        details = frappe.get_all("Item Wise Tax Detail",
                                 filters={"parent": doc_parent.name, "item_row": item.name},
                                 fields=["tax_row", "rate", "amount", "taxable_amount"],
                                 order_by="idx asc")

    if details:
        for d in details:
            tax = taxes_by_row.get(d.tax_row)
            if not tax or getattr(tax, "sricode", None) is None:
                continue
            impuestos.append({
                "codigo": tax.sricode,
                "codigoPorcentaje": tax.codigoPorcentaje,
                "tarifa": tax.rate,
                "baseImponible": d.taxable_amount if d.taxable_amount is not None else item.net_amount,
                "valor": d.amount or 0,
            })
        return impuestos

    # Compatibilidad v15: JSON {item_code: [rate, amount]} en cada fila de impuestos
    for tax in (doc_parent.taxes or []):
        raw = getattr(tax, "item_wise_tax_detail", None)
        if not raw:
            continue
        detail = json.loads(raw)
        if item.item_code in detail and getattr(tax, "sricode", None) is not None:
            impuestos.append({
                "codigo": tax.sricode,
                "codigoPorcentaje": tax.codigoPorcentaje,
                "tarifa": tax.rate,
                "baseImponible": item.net_amount,
                "valor": detail[item.item_code][1],
            })
    return impuestos


def get_full_items(doc_name, doc_parent):

    items = frappe.get_all('Sales Invoice Item',
                           filters={'parent': doc_name},
                           fields=['*'],
                           order_by='idx asc'
                        #    fields=['item_code', 'item_name', 'rate', 'qty', 'amount']
                                       )
    
    total_items_discount = 0

    if (items):
        for item in items:
            item.impuestos = []
            total_items_discount += item.discount_amount

            item.precioUnitario = item.base_price_list_rate #rate #precio del item
            item.precioTotalSinImpuesto = item.base_net_amount #subtotal del item

            # Ficha Técnica SRI 2.33/2.34 - Anexos 23 y 25: codigoAuxiliar obligatorio
            # para transferencia local de materiales de construcción y transporte comercial
            item.codigoAuxiliar = frappe.db.get_value("Item", item.item_code, "codigo_auxiliar_sri") or ""

            item.impuestos = build_item_impuestos(item, doc_parent)
                            
                #if (not doc_parent.taxes_and_charges is None):
                #    item["item_tax_template"] = doc_parent.taxes_and_charges 

            #item_tax_rate = {"VAT - RSCV": 12.0}
            #item_tax_template = Ecuador Tax - RSCV

            #"item_tax_rate" :"{}",
            #"item_tax_template" : null,
            #<impuestos>
            #<impuesto>
            #<codigo>2</codigo>
            #<codigoPorcentaje>0</codigoPorcentaje>
            #<tarifa>12</tarifa>
            #<baseImponible>20</baseImponible>
            #<valor>2.40</valor>
            #</impuesto>
            #</impuestos>
        
        #Coloca el total de descuentos de los items en el documento padre
        doc_parent.totalDescuento = total_items_discount
    return items

def get_full_items_purchase_receipt(doc_name, doc_parent):

    items = frappe.get_all('Purchase Receipt Item',
                           filters={'parent': doc_name},
                           fields=['*'],
                           order_by='idx asc'
                            )
    
    total_items_discount = 0

    if (items):
        for item in items:
            item.impuestos = []
            total_items_discount += item.discount_amount

            item.precioUnitario = item.base_price_list_rate #rate #precio del item
            item.precioTotalSinImpuesto = item.base_net_amount #subtotal del item

            item.impuestos = build_item_impuestos(item, doc_parent)
        
        doc_parent.totalDescuento = total_items_discount
    return items

def get_full_items_purchase_invoice(doc_name, doc_parent):

    items = frappe.get_all('Purchase Invoice Item',
                           filters={'parent': doc_name},
                           fields=['*'],
                           order_by='idx asc'
                            )
    
    total_items_discount = 0

    if (items):
        for item in items:
            item.impuestos = []
            total_items_discount += item.discount_amount

            item.precioUnitario = item.base_price_list_rate #rate #precio del item
            item.precioTotalSinImpuesto = item.base_net_amount #subtotal del item

            item.impuestos = build_item_impuestos(item, doc_parent)
        
        doc_parent.totalDescuento = total_items_discount
    return items


def get_full_items_delivery_note(doc_name):    
    items = frappe.get_all('Delivery Note Item',
                           filters={'parent': doc_name},
                           fields=['*']
                        #    fields=['item_code', 'item_name', 'rate', 'qty', 'amount']
                                       )

    return items

def get_full_taxes(doc_name):
    
    impuestos = frappe.get_all('Sales Taxes and Charges', filters={'parent': doc_name}, fields=['*'])
    #    fields=['charge_type', 'account_head', 'tax_amount']
    
    for taxItem in impuestos:
        accountApi = frappe.get_doc('Account', taxItem.account_head)
        # print('CUENTAAAAAAAAAAAAA')
        #print(taxItem)
        #print(accountApi.sricode)
        #print(accountApi.codigoporcentaje)
        #print(accountApi.tax_rate)

        if accountApi.sricode:
            taxItem.sricode =  int(accountApi.sricode)
              
        if accountApi.codigoporcentaje:
            taxItem.codigoPorcentaje = int(accountApi.codigoporcentaje)
            #taxItem.codigoPorcentaje = accountApi.codigoporcentaje
                
        if accountApi.compute_label_sri:
            taxItem.compute_label_sri = accountApi.compute_label_sri
        else:
            if taxItem.sricode == 2 or taxItem.sricode == 4:
                taxItem.compute_label_sri = "IVA " + str(int(accountApi.tax_rate)) + "%"
            #se deberian agregar manualmente los otros tipos de impuestos

        if (taxItem.total == taxItem.base_total):
            taxItem.baseImponible = taxItem.base_total - taxItem.tax_amount
        else:            
            taxItem.baseImponible = taxItem.base_total
        #print(taxItem.compute_label_sri)

        #print(accountApi.tax_rate)
        
        #TODO: Probablemente un bug en la version 13, no se ha replicado en la version 15
        if (taxItem.rate == 0 and  taxItem.rate != accountApi.tax_rate):
            taxItem.rate = accountApi.tax_rate

    return impuestos

def get_full_taxes_purchases(doc_name):
    
    impuestos = frappe.get_all('Purchase Taxes and Charges', 
                               filters={'parent': doc_name}, 
                               fields=['*'])
    #    fields=['charge_type', 'account_head', 'tax_amount']
    
    for taxItem in impuestos:
        accountApi = frappe.get_doc('Account', taxItem.account_head)

        #accountApi = frappe.get_doc(
        #{
        #    "doctype": "Account", 
        #    "name": taxItem.account_head, 
        #    "company": taxItem.company
        #})


        print("accountApi")
        print(accountApi)

        if accountApi.sricode:
            taxItem.sricode =  int(accountApi.sricode)
              
        if accountApi.codigoporcentaje:
            taxItem.codigoPorcentaje = int(accountApi.codigoporcentaje)
                
        if accountApi.compute_label_sri:
            taxItem.compute_label_sri = accountApi.compute_label_sri
        else:
            if taxItem.sricode == 2 or taxItem.sricode == 4:
                taxItem.compute_label_sri = "IVA " + str(int(accountApi.tax_rate)) + "%"
            #se deberian agregar manualmente los otros tipos de impuestos

        if (taxItem.total == taxItem.base_total):
            taxItem.baseImponible = taxItem.base_total - taxItem.tax_amount
        else:            
            taxItem.baseImponible = taxItem.base_total
        
        #TODO: Probablemente un bug en la version 13, no se ha replicado en la version 15
        if (taxItem.rate == 0 and  taxItem.rate != accountApi.tax_rate):
            taxItem.rate = accountApi.tax_rate

    return impuestos

def get_address_by_name(link_name, primary_address, link_doctype):
    address_data = {}
    customer_address_primary = None
    customer_address_first = None

    din_link_api = frappe.get_all('Dynamic Link', fields=["name","parent","link_title"],
                                                filters={'link_doctype': link_doctype, 'parenttype': 'Address', 'link_name': link_name})
        
    # print('DIRECCCCCCCCCCIIIIIIIONNNNNNN CUSTOMMMMERRRR')
    print(din_link_api)

    if din_link_api:
        found_primary = False
        for i, link in enumerate(din_link_api):
            customer_address = frappe.get_all('Address', fields='*', filters={'name': link.parent})
            #print(customer_address)

            if customer_address:
                if i == 0:
                    customer_address_first = customer_address[0]

                if customer_address[0].get('is_primary_address'):
                    found_primary = True
                    customer_address_primary = customer_address[0]
                    break

        if not found_primary and customer_address_first:
            customer_address_primary = customer_address_first
    else:
        #Sino se encuentra una dirección vinculada se busca una direccion primaria del cliente
        customer_address = frappe.get_all('Address', fields='*', filters={'name':  primary_address})
        if customer_address:
            customer_address_primary = customer_address[0]
        else:
            print('---')
            
    if customer_address_primary:
        address_data['email_id']  = customer_address_primary.email_id
        address_data['phone']  = customer_address_primary.phone
        #address_data['address_line1']  = customer_address_primary.address_line1
        #address_data['address_line2']  = customer_address_primary.address_line2
        #address_data['direccion']  = customer_address_primary.address_line1 + ' ' + customer_address_primary.address_line2

        address_data['address_line1']  = customer_address_primary.address_line1 if customer_address_primary.address_line1 is not None else ''
        address_data['address_line2']  = customer_address_primary.address_line2 if customer_address_primary.address_line2 is not None else ''
        address_data['direccion']  = address_data['address_line1'] + ' ' + address_data['address_line2']
        
    else:
        address_data['email_id']  = ''
        address_data['phone']  = ''
        address_data['address_line1']  = ''
        address_data['address_line2']  = ''
        address_data['direccion']  = ''
    
    return address_data


def get_invoice_by_link(link_name, link_doctype):
    invoice_data = {}   

    din_link_api = frappe.get_all('Dynamic Link', fields=["name","parent","link_title"],
                                                filters={'link_doctype': link_doctype, 'parenttype': 'Sales Invoice', 'link_name': link_name})        
    
    print(din_link_api)

    if din_link_api:
        found_primary = False
        for i, link in enumerate(din_link_api):
            pass

def get_full_delivery_trips(doc):
    
    #print(doc['items'])

    doc_name = doc.name

    # document_links = frappe.get_all('Document link', filters={'parent': doc_name}, fields=['*'])
    # print("document_links")
    # print(document_links)

    delivery_trips = frappe.get_all('Delivery Trip', filters={'delivery_note': doc_name}, fields=['*'])
    #    fields=['charge_type', 'account_head', 'tax_amount']
    
    main_against_sales_invoice = ''
    numAutDocSustento = ''
    codEstabDestino = ''
    numDocSustento = ''
    # print(delivery_trips)
    for delivery_note_item in doc['items']:
        print("against_sales_invoice----")
        #print(doc.against_sales_invoice)
        #print(delivery_tripItem.against_sales_invoice)
        print(delivery_note_item.against_sales_invoice)
        main_against_sales_invoice = delivery_note_item.against_sales_invoice
        docs_si = frappe.get_all('Sales Invoice', filters={"name": main_against_sales_invoice}, fields = ['*'])

        if docs_si:
            #doc = docs[0]
            print(docs_si[0])
            codEstabDestino = docs_si[0].estab
            #secuencial = docs_si[0].secuencial
            numAutDocSustento = docs_si[0].numeroautorizacion
            numDocSustento = docs_si[0].estab + '-' + docs_si[0].ptoemi + '-' + format(docs_si[0].secuencial, '09')
            print(numAutDocSustento)
            print(numDocSustento)


    for delivery_tripItem in delivery_trips:
        delivery_stops = frappe.get_all('Delivery Stop', filters={'parent': delivery_tripItem.name}, fields=['*'])
        
        for delivery_stops_item in delivery_stops:
            #dirDestinatario
            #numAutDocSustento
            #get_address_by_name(link_name, primary_address, link_doctype, parenttype)
            print(delivery_stops_item.address)
            primary_address = delivery_stops_item.address
            address_data = get_address_by_name(delivery_stops_item.address, primary_address, 'Customer')            
            #delivery_stops_item.customer
            print('address_data')
            print(address_data)
            delivery_stops_item.dirDestinatario = address_data['direccion']

            print(delivery_stops_item.name)
            print(delivery_stops_item.delivery_note)            

            delivery_stops_item.numAutDocSustento = numAutDocSustento
            delivery_stops_item.numDocSustento = numDocSustento
            delivery_stops_item.codEstabDestino = codEstabDestino

            pass

        #obtener datos del conductor y direccion de partida
        
        #obtener datos del vehículo

        # print('CUENTAAAAAAAAAAAAA')
        #print("delivery_trips")
        #print(delivery_tripItem)

        #print("delivery_stops")
        #print(delivery_stops)
        # print(accountApi.codigoporcentaje)
        delivery_tripItem.delivery_stops = delivery_stops
        
        #delivery_trip_driver = frappe.get_last_doc('Driver', filters={'name': delivery_tripItem.driver})
        delivery_trip_driver = frappe.get_all('Driver', filters={'name': delivery_tripItem.driver}, fields=['*'])
        delivery_tripItem.trip_driver = delivery_trip_driver
        #print(delivery_trip_driver)
     
        #delivery_trip_vehicle = frappe.get_last_doc('Vehicle', filters={'name': delivery_tripItem.vehicle})
        delivery_trip_vehicle = frappe.get_all('Vehicle', filters={'name': delivery_tripItem.vehicle}, fields=['*'])
        delivery_tripItem.trip_vehicle = delivery_trip_vehicle
        #print(delivery_trip_vehicle)
        
    return delivery_trips


def get_full_taxes_withhold(doc_name):
    
    impuestos = frappe.get_all('Purchase Taxes and Charges Ec', filters={'parent': doc_name}, fields=['*'])
    #    fields=['charge_type', 'account_head', 'tax_amount']
    
    for taxItem in impuestos:
        accountApi = frappe.get_doc('Account', taxItem.codigoRetencion)
        # print('CUENTAAAAAAAAAAAAA')
        print(accountApi)
        # print(accountApi.sricode)
        # print(accountApi.codigoporcentaje)

        if accountApi.sricode:
            taxItem.sricode =  int(accountApi.sricode)
              
        if accountApi.codigoporcentaje:
            taxItem.codigoPorcentaje = int(accountApi.codigoporcentaje)
        
        if accountApi.codigoretencion:
             taxItem.codigoRetencionId = int(accountApi.codigoretencion)

    return impuestos

def GenerarClaveAcceso(tipoDocumento, fechaEmision, puntoEmision, secuencial, tipoEmision, 
                       ruc,
                       tipoAmbiente,
                       establecimiento):
    
    #Se hace la conversión a entero para poder luego convertirlo de forma segura
    secuencial = int(secuencial)

    cadenaNumeros = "{0}{1}{2}{3}{4}{5}{6}{7}{8}".format(
        fechaEmision.strftime("%d%m%Y"),
        tipoDocumento,
        ruc,
        tipoAmbiente,
        establecimiento,
        puntoEmision,
        '{:09d}'.format(secuencial),
        "12345678",
        tipoEmision
    )
    
    #return "{0}{1}".format(cadenaNumeros, ObtenerModulo11(cadenaNumeros))    
    return "{0}{1}".format(cadenaNumeros, compute_mod11(cadenaNumeros))

#FAILS
def ObtenerModulo11(cadenaNumeros):
    base_max = 7
    multiplicador = 2
    total = 0
    substrings = list(cadenaNumeros) #substrings = re.split("", cadenaNumeros)

    for i in range(len(substrings) - 1, 0, -1): #for i in range(len(substrings) - 1, 0, -1):        
        #if substrings[i] != "":        
        num_aux = int(substrings[i])
        total += (num_aux * multiplicador)
        multiplicador += 1
        if multiplicador > base_max:
            multiplicador = 2

    verificador = 11 - total % 11
    print(verificador)
    return CheckDigitBring(verificador)

def CheckDigitBring(digit):
    if digit == 10:
        digit = 1
    elif digit == 11:
        digit = 0
    return digit

_MODULO_11 = {
        'BASE': 11,
        'FACTOR': 2,
        'RETORNO11': 0,
        'RETORNO10': 1,
        'PESO': 2,
        'MAX_WEIGHT': 7
    }


def compute_mod11(dato):
        """
        Calculo mod 11
        return int
        """
        total = 0
        weight = _MODULO_11['PESO']
        
        for item in reversed(dato):
            total += int(item) * weight
            weight += 1
            if weight > _MODULO_11['MAX_WEIGHT']:
                weight = _MODULO_11['PESO']
        mod = 11 - total % _MODULO_11['BASE']

        mod = _eval_mod11(mod)
        return mod

def _eval_mod11(modulo):
        if modulo == _MODULO_11['BASE']:
            return _MODULO_11['RETORNO11']
        elif modulo == _MODULO_11['BASE'] - 1:
            return _MODULO_11['RETORNO10']
        else:
            return modulo
        
def ObtenerModulo10(cadenaNumeros):
    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    index = 0
    suma = 0
    for ch in cadenaNumeros[::-1]:
        producto = int(ch) * coeficientes[index]
        suma += producto if producto < 10 else producto - 9
        index += 1
    residuo = suma % 10
    return 10 - residuo if residuo != 0 else 0


def setSecuencial(doc, typeDocSri):
    company_object = frappe.get_last_doc('Company', filters = { 'name': doc.company  })
    
    if typeDocSri ==  "FAC":
        document_object = frappe.get_last_doc('Sales Invoice', filters = { 'name': doc.name})
        if(document_object):
            if(document_object.secuencial > 0):
                print("Secuencial ya asignado!")
                print(document_object.secuencial)
                return 0

    elif typeDocSri ==  "NCR":			
        #print(doc)
        document_object = frappe.get_last_doc('Sales Invoice', filters = { 'name': doc.name})
        if(document_object):
            if(document_object.secuencial > 0):
                print("Secuencial ya asignado!")
                print(document_object.secuencial)
                return 0
    elif typeDocSri ==  "GRS":
			
        #print(doc)
        document_object = frappe.get_last_doc('Delivery Note', filters = { 'name': doc.name})
        if(document_object):
            if(document_object.secuencial > 0):
                print("Secuencial ya asignado!")
                print(document_object.secuencial)
                return 0
    
    elif typeDocSri ==  "CRE":
			
        #print(doc)
        document_object = frappe.get_last_doc('Purchase Withholding Sri Ec', filters = { 'name': doc.name})
        if(document_object):
            if(document_object.secuencial > 0):
                print("Secuencial ya asignado!")
                print(document_object.secuencial)
                return 0
    
    elif typeDocSri ==  "LIQ":			
        #print(doc)
        document_object = frappe.get_last_doc('Purchase Invoice', filters = {'name': doc.name})
        if(document_object):
            if(document_object.secuencial > 0):
                print("Secuencial ya asignado!")
                print(document_object.secuencial)
                return 0
    elif typeDocSri ==  "NDE":
        pass	
    
    print("--------------------------")
    nuevo_secuencial = 0

    # El documento apunta directamente a su punto de emisión (PTO-00001); ese
    # registro define el ambiente y lleva los contadores. Ya no hay "gemelos"
    # DES/PRO por código.
    pto = get_ptoemi_sri(doc)
    ptoemi_name = pto.name

    seq_field = {
        "FAC": "sec_factura",
        "NCR": "sec_notacredito",
        "GRS": "sec_guiaremision",
        "CRE": "sec_comprobanteretencion",
        "LIQ": "sec_liquidacioncompra",
        "NDE": "sec_notadebito",
    }.get(typeDocSri)

    if seq_field:
        # Bloqueo de fila para que dos envíos simultáneos no tomen el mismo número
        actual = frappe.db.get_value('Sri Ptoemi', ptoemi_name, seq_field, for_update=True) or 0
        nuevo_secuencial = int(actual) + 1
        frappe.db.set_value('Sri Ptoemi', ptoemi_name, seq_field, nuevo_secuencial, update_modified=False)
        document_object.db_set('secuencial', nuevo_secuencial)
        frappe.db.commit()

    return nuevo_secuencial
    
def get_full_establishment(record_name):
    if not record_name:
        return None
    docs = frappe.get_all('Sri Establishment', fields='*', filters={'name': record_name})

    if docs:
        doc = docs[0]
        return doc
    return None

def get_full_ptoemi(record_name):
    if not record_name:
        return None
    docs = frappe.get_all('Sri Ptoemi', fields='*', filters={'name': record_name})

    if docs:
        doc = docs[0]
        return doc
    return None