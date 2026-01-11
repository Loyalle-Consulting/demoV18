{
    "name": "Guía de Despacho Valorizada",
    "version": "18.1.2",
    "category": "Inventory/Stock",
    "summary": "Añade precio unitario, subtotal y total a la guía; precio editable en operaciones.",
    "author": "Loyalle Consulting",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "sale",
        "l10n_cl_edi_stock",  # sigue en depends porque usas la guía CL, pero NO heredamos su wrapper
    ],
    "data": [
        "views/stock_picking_form_view.xml",
        "views/delivery_guide_copy_template.xml",
        "views/report_delivery_guide_valorizada.xml",
    ],
    "installable": True,
    "application": False,
}