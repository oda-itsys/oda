# -*- coding: utf-8 -*-
{
    'name': "Invoice Order Report",



    'description': """
       Invoice Order Report
    """,

    'author': "Marwa Ahmed",
    'website': "http://www.yourcompany.com",

    'category': 'Account',
    'version': '0.1',

    'depends': ['base','account','stock_picking_invoice_link'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ]

}
