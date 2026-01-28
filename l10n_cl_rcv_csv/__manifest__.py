{
    "name": "RCV CSV Chile",
    "version": "18.0.1.0.0",
    "category": "Accounting/Chile",
    "summary": "Importación, conciliación y creación de facturas desde Libros RCV (CSV) del SII Chile",
    "author": "Loyalle Consulting",
    "license": "LGPL-3",

    "depends": [
        "account",
        "l10n_cl",
    ],

    "data": [
        # --------------------------------------------------
        # SEGURIDAD
        # --------------------------------------------------
        "security/ir.model.access.csv",

        # --------------------------------------------------
        # VISTAS PRINCIPALES (modelos)
        # --------------------------------------------------
        "views/rcv_book_views.xml",
        "views/rcv_line_views.xml",

        # --------------------------------------------------
        # ACCIONES SERVER (OBLIGATORIO antes de menús)
        # --------------------------------------------------
        "data/rcv_line_actions.xml",

        # --------------------------------------------------
        # WIZARDS
        # --------------------------------------------------
        "views/rcv_import_wizard_views.xml",
        "views/rcv_create_move_wizard_views.xml",

        # --------------------------------------------------
        # MENÚS (SIEMPRE AL FINAL)
        # --------------------------------------------------
        "views/rcv_menu_views.xml",
    ],

    "installable": True,
    "application": False,
}
