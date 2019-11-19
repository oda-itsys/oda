# -*- coding: utf-8 -*-
{
    'name': "Sale Order Report ",

    'description': """
        Editing Sale order report template
    """,

    'author': "Marwa Ahmed",
    'website': "http://www.yourcompany.com",
    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','sale','sales_report_product_image','web'],

    # always loaded
    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],

}