# -*- coding: utf-8 -*-
{
    'name': "Sales Additional Discount",

    'summary': """
        sales_additional_discount """,

    'description': """
        sales_additional_discount
    """,

    'author': "ITsys-Corportion Doaa Khaled",
    'website': "http://www.it-syscorp.com",

    'category': 'Sale',
    'version': '0.1',

    'depends': ['base','sale','account','purchase'],

    'data': [
        'security/discount_security.xml',
        'views/sale_order_view.xml',

    ],

}