# -*- coding: utf-8 -*-
import datetime
import time
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import datetime
from odoo.addons import decimal_precision as dp
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import UserError, ValidationError


class SalesOrder(models.Model):
    _inherit = 'sale.order'
    discount_total_sale = fields.Float(compute='_amount_all',
                                       string='Total Additional Discount')

    @api.depends('order_line.price_total', 'order_line.sale_additional_discount')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amount_discount += ((line.price_unit * line.product_uom_qty) * (1-(line.discount or 0.0) / 100.0)) * ((line.sale_additional_discount or 0.0) / 100.0)
            order.update({
                'discount_total_sale': amount_discount,
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })


class SalesOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sale_additional_discount = fields.Float('Additional Discount (%)')

    @api.onchange('sale_additional_discount')
    def check_sales_discount(self):
        for rec in self:
            if rec.sale_additional_discount < 0:
                raise ValidationError(_(
                    'The Additional Discount must not be negative value '))
            if rec.sale_additional_discount > 100:
                raise ValidationError(_(
                    'The Additional Discount must be between 0 and 100 '))

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'sale_additional_discount')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = (line.price_unit * (1 - (line.discount or 0.0) / 100.0)) * (
                1 - (line.sale_additional_discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)

            price_tax = 0.0
            # disc = (line.order_id.sale_additional_discount / max(line.order_id.amount_untaxed, 1)) * 100
            if line.tax_id:
                for tax in line.tax_id:
                    price_tax += (taxes['total_excluded']) * (tax.amount / 100)
            line.update({
                # 'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_tax': price_tax,
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],

            })

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SalesOrderLine, self)._prepare_invoice_line(qty)
        res.update({'sale_additional_discount': self.sale_additional_discount})
        return res


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    discount_total_sale = fields.Float(readonly=True,
                                       string='Total Global Discount', compute='_compute_amount_total')

    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.invoice_line_ids:
            if not line.account_id:
                continue
            price_unit = (line.price_unit * (1 - (line.discount or 0.0) / 100.0)) * (
                1 - (line.sale_additional_discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id,
                                                          self.partner_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
        return tax_grouped

    @api.multi
    def _compute_amount_total(self):
        for item in self:
            for rec in item.invoice_line_ids:
                item.discount_total_sale += ((rec.price_unit * rec.quantity) * (1-(rec.discount or 0.0) / 100.0)) * ((rec.sale_additional_discount or 0.0) / 100.0)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    sale_additional_discount = fields.Float('Additional Discount (%)')

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
                 'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
                 'invoice_id.date_invoice', 'invoice_id.date', 'sale_additional_discount')
    def _compute_price(self):
        for item in self:

            currency = item.invoice_id and item.invoice_id.currency_id or None
            price = (item.price_unit * (1 - (item.discount or 0.0) / 100.0)) * (
                1 - (item.sale_additional_discount or 0.0) / 100.0)
            taxes = False
            if item.invoice_line_tax_ids:
                taxes = item.invoice_line_tax_ids.compute_all(price, currency, item.quantity, product=item.product_id,
                                                              partner=item.invoice_id.partner_id)
            item.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else (item.quantity * price)
            item.price_total = taxes['total_included'] if taxes else item.price_subtotal
            if item.invoice_id.currency_id and item.invoice_id.currency_id != item.invoice_id.company_id.currency_id:
                currency = item.invoice_id.currency_id
                date = item.invoice_id._get_currency_rate_date()
                price_subtotal_signed = currency._convert(price_subtotal_signed, item.invoice_id.company_id.currency_id,
                                                          item.company_id or item.env.user.company_id,
                                                          date or fields.Date.today())
            sign = item.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
            item.price_subtotal_signed = price_subtotal_signed * sign
