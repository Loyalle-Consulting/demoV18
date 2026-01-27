{
    "name": "Importador RCV SII Chile",
    "version": "18.0.1.0.0",
    "category": "Accounting/Chile",
    "summary": "Importación del Registro de Compras y Ventas (RCV) desde el SII de Chile",
    "author": "Loyalle Consulting",
    "website": "https://www.loyalle.cl",
    "license": "LGPL-3",

    # Dependencias necesarias y reales
    "depends": [
        "account",
        "l10n_cl",
        "l10n_cl_edi",
        "certificate",  # ⬅️ CLAVE: modelo certificate.certificate
    ],

    # Datos cargados por el módulo
    "data": [
        # Seguridad
        "security/ir.model.access.csv",

        # Vistas principales
        "views/rcv_import_views.xml",
        "views/rcv_line_views.xml",

        # Wizard
        "views/rcv_wizard_views.xml",

        # Menús
        "views/rcv_menu_views.xml",
    ],

    # Configuración del módulo
    "installable": True,
    "application": False,
    "auto_install": False,

    # Indicador técnico (útil en Odoo.sh)
    "maintainers": ["Loyalle Consulting"],
}
