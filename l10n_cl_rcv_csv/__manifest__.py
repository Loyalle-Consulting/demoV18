{
    "name": "RCV CSV Chile",
    "version": "18.0.1.0.0",
    "category": "Accounting/Chile",
    "summary": "Importación y conciliación de Libros RCV (CSV) desde SII Chile",
    "author": "Loyalle Consulting",
    "license": "LGPL-3",

    "depends": [
        "account",
        "l10n_cl",
    ],

    "data": [
        # Seguridad
        "security/ir.model.access.csv",

        # VISTAS BASE (acciones primero)
        "views/rcv_book_views.xml",
        "views/rcv_line_views.xml",

        # Wizards
        "views/rcv_import_wizard_views.xml",
        "views/rcv_create_move_wizard_views.xml",

        # Menús (SIEMPRE AL FINAL)
        "views/rcv_menu_views.xml",
    ],

    "installable": True,
    "application": False,
}
