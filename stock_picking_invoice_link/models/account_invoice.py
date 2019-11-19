# Copyright 2013-15 Agile Business Group sagl (<http://www.agilebg.com>)
# Copyright 2015-2016 AvanzOSC
# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2017 Jacques-Etienne Baudoux <je@bcim.be>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models,api


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    picking_ids = fields.Many2many(
        comodel_name='stock.picking',
        string='Related Pickings',
        readonly=True,
        copy=False,
        help="Related pickings "
             "(only when the invoice has been generated from a sale order).",
    )

    def _prepare_invoice_line_from_po_line(self, line):
        vals = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)
        move_ids = line.mapped('move_ids').filtered(
            lambda x:
            not x.invoice_line_id and
            not x.scrapped and (
                x.location_id.usage == 'supplier' or
                (x.location_dest_id.usage == 'supplier' and
                 x.to_refund)
            )).ids
        vals['move_line_ids'] = [(6, 0,move_ids)]
        return vals


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    move_line_ids = fields.One2many(
        comodel_name='stock.move',
        inverse_name='invoice_line_id',
        string='Related Stock Moves',
        copy=False,
        help="Related stock moves "
             "(only when the invoice has been generated from a sale order).",
    )

    delivery_status = fields.Selection([
        ('delivery', 'Delivered'),
        ('not_delivery', 'Not Delivered')
    ], compute='_get_dev_not')

    @api.depends('move_line_ids')
    def _get_dev_not(self):
        for line in self:
            line.delivery_status = 'not_delivery'
            for l in line.move_line_ids:
                if l.state == 'done':
                    line.delivery_status='delivery'
