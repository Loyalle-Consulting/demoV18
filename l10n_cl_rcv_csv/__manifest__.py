{
    "name": "RCV CSV Chile",
    "version": "18.0.1.0.1",
    "category": "Accounting/Chile",
    "summary": "Importación, conciliación y análisis de Libros RCV (CSV) del SII Chile",
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
        # MENÚ RAÍZ (SIEMPRE PRIMERO)
        # --------------------------------------------------
        "views/rcv_menu_views.xml",

        # --------------------------------------------------
        # VISTAS BASE
        # --------------------------------------------------
        "views/rcv_book_views.xml",
        "views/rcv_line_views.xml",

        # --------------------------------------------------
        # VISTAS CONSOLIDADAS
        # (dependen del menú raíz)
        # --------------------------------------------------
        "views/rcv_line_consolidated_views.xml",

        # --------------------------------------------------
        # ACCIONES SERVER
        # --------------------------------------------------
        "data/rcv_line_actions.xml",

        # --------------------------------------------------
        # WIZARDS
        # --------------------------------------------------
        "views/rcv_import_wizard_views.xml",
        "views/rcv_create_move_wizard_views.xml",
    ],

    "installable": True,
    "application": False,
}
