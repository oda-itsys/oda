# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo import tools

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    delivery_status = fields.Selection([
        ('delivery', 'Delivered'),
        ('not_delivery', 'Not Delivered')
    ], compute='_get_dev_not',store=True,copy=False)

    @api.depends('move_ids.state')
    def _get_dev_not(self):
        for line in self:
            line.delivery_status = 'not_delivery'
            for l in line.move_ids:
                if l.state == 'done':
                    line.delivery_status='delivery'



class SaleReport(models.Model):
    _inherit = "sale.report"
    delivery_status = fields.Selection([
        ('delivery', 'Delivered'),
        ('not_delivery', 'Not Delivered')
    ])


    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['delivery_status'] = ",l.delivery_status as delivery_status"
        groupby += ',l.delivery_status'
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)

