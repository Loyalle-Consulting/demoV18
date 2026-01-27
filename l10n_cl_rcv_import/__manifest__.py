{
    "name": "Importador RCV SII Chile",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localization",
    "summary": "Importación Registro de Compras y Ventas (RCV) desde SII Chile",
    "author": "Loyalle Consulting",
    "license": "LGPL-3",
    "depends": [
        "account",
        "l10n_cl",
        "l10n_cl_edi",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/rcv_wizard_views.xml",
        "views/rcv_import_views.xml",
        "views/rcv_line_views.xml",        
        "views/rcv_menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
