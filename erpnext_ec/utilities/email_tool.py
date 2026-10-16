import frappe

def sendmail(doc, recipients, title, msg_template, attachments = None):    
    #print(attachments)

    email_args = {
        'recipients': recipients,
        'message': msg_template,
        'subject': title,
        'reference_doctype': doc.doctype,
        'reference_name': doc.name,
        'attachments': attachments
        #'template': 'Factura SRI Body'
    }

    #if attachments: email_args['attachments'] = attachments

    # Remitente: el email de la compañía (p. ej. facturacion@) si tiene cuenta de correo saliente;
    # si no, Frappe usa la cuenta Default Outgoing.
    company = getattr(doc, 'company', None)
    company_email = company and frappe.db.get_value('Company', company, 'email')
    if company_email and frappe.db.exists('Email Account', {'email_id': company_email, 'enable_outgoing': 1}):
        email_args['sender'] = company_email

    result_queue = frappe.enqueue(method= frappe.sendmail, queue = 'short', timeout = 30000, **email_args)
    #print(result_queue)

    # frappe.sendmail(
    # recipients=recipients,
    # subject=frappe._('Birthday Reminder'),
    # template='birthday_reminder',
    # args=dict(
    #     reminder_text=reminder_text,
    #     birthday_persons=birthday_persons,
    #     message=message,
    # ),
    # header=_('Birthday Reminder 🎂')
    #)