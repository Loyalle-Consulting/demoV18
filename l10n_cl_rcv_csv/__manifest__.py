{
    "name": "RCV CSV Chile",
    "version": "18.0.1.0.0",
    "category": "Accounting/Chile",
    "summary": "Importación, conciliación y creación de facturas desde Libros RCV (CSV) del SII Chile",
    "author": "Loyalle Consulting",
    "website": "https://www.loyalle.cl",
    "license": "LGPL-3",

    # ---------------------------------------------------------
    # DEPENDENCIAS
    # ---------------------------------------------------------
    "depends": [
        "account",
        "l10n_cl",
    ],

    # ---------------------------------------------------------
    # DATOS CARGADOS POR EL MÓDULO
    # ---------------------------------------------------------
    "data": [
        # Seguridad
        "security/ir.model.access.csv",

        # Menú principal
        "views/rcv_menu_views.xml",

        # Modelos principales
        "views/rcv_book_views.xml",
        "views/rcv_line_views.xml",

        # Wizards
        "views/rcv_import_wizard_views.xml",
        "views/rcv_create_move_wizard_views.xml",
    ],

    # ---------------------------------------------------------
    # CONFIGURACIÓN
    # ---------------------------------------------------------
    "installable": True,
    "application": False,
    "auto_install": False,

    # ---------------------------------------------------------
    # METADATOS
    # ---------------------------------------------------------
    "maintainers": ["Loyalle Consulting"],
}