var doctype_customized = "Sales Invoice";

frappe.ui.form.on(doctype_customized, {
    setup(frm)
    {
        SetSriPuntoQueries(frm);
    },
	refresh(frm)
    {

        if (frm.doc.status == 'Cancelled' || frm.doc.status == 'Draft')
        {
            return false;
        }
        
        SetFormSriButtons(frm, doctype_customized);      
        //console.log(frm);
        //console.log(frm.doctype_customized);
    },
    estab: function(frm)
    {
        ClearSriPuntoIfMismatch(frm);
    },
})
