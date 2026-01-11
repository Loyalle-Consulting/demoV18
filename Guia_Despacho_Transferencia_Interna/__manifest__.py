# -*- coding: utf-8 -*-
{
    'name': 'CL DTE Guía desde Traslado Interno',
    'summary': 'Emitir Guía de Despacho Electrónica (52) desde transferencias internas (stock.picking) para Chile',
    'version': '18.0.1.0.4',
    'author': 'Loyalle Consulting',
    'website': 'https://tu-dominio.cl',
    'category': 'Inventory/Localization',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'l10n_cl',
        'l10n_cl_edi',
        'l10n_cl_edi_stock',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
        'views/internal_dispatch_wizard_views.xml',
    ],
    'application': False,
    'installable': True,
}