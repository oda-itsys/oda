# -*- coding: utf-8 -*-

from odoo import api, models, _,fields
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT




class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    info=fields.Text()


class StockRule(models.Model):
    _inherit = 'stock.rule'


    def get_info(self,origin,product_id):
        sale_id=False
        info=''
        for each_sale in self.env['sale.order'].search([('name', 'like', origin)]):
            sale_id=each_sale.id
        if sale_id:
            for each_sale_line in self.env['sale.order.line'].search([('order_id', '=', sale_id),('product_id', '=', product_id.id)]):
                info= each_sale_line.info
        return info

    def get_commitment_date(self,origin,product_id):
        sale_id=False
        commitment_date=''
        for each_sale in self.env['sale.order'].search([('name', 'like', origin)]):
            sale_id=each_sale.id
        if sale_id:
            for each_sale in self.env['sale.order'].search([('id', '=', sale_id)]):
                commitment_date= each_sale.commitment_date
        return commitment_date


    @api.multi
    def _run_buy(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        cache = {}

        suppliers = product_id.seller_ids \
            .filtered(lambda r: (not r.company_id or r.company_id == values['company_id']) and (
                    not r.product_id or r.product_id == product_id))
        if not suppliers:
            msg = _('There is no vendor associated to the product %s. Please define a vendor for this product.') % (
            product_id.display_name,)
            raise UserError(msg)
        supplier = self._make_po_select_supplier(values, suppliers)
        partner = supplier.name
        # we put `supplier_info` in values for extensibility purposes
        values['supplier'] = supplier

        commitment_date=self.get_commitment_date(origin, product_id)

        domain = self._make_po_get_domain(values, partner)
        if domain in cache:
            po = cache[domain]
        else:
            po = self.env['purchase.order'].sudo().search([dom for dom in domain])
            po = po[0] if po else False
            cache[domain] = po
        if not po:
            vals = self._prepare_purchase_order(product_id, product_qty, product_uom, origin, values, partner,commitment_date)
            company_id = values.get('company_id') and values['company_id'].id or self.env.user.company_id.id
            po = self.env['purchase.order'].with_context(force_company=company_id).sudo().create(vals)
            cache[domain] = po
        elif not po.origin or origin not in po.origin.split(', '):
            if po.origin:
                if origin:
                    po.write({'origin': po.origin + ', ' + origin,'commitment_date':commitment_date})
                else:
                    po.write({'origin': po.origin,'commitment_date':commitment_date})
            else:
                po.write({'origin': origin,'commitment_date':commitment_date})

        # Create Line
        info=''
        info = self.get_info(origin, product_id)
        po_line = False
        for line in po.order_line:
            if line.product_id == product_id and line.product_uom == product_id.uom_po_id:
                
                info_modify=str(line.info)+'\n'+str(info)
                if line._merge_in_existing_line(product_id, product_qty, product_uom, location_id, name, origin,
                                                values):
                    vals = self._update_purchase_order_line(product_id, product_qty, product_uom, values, line, partner)
                    line.write({'info': info_modify})
                    po_line = line.write(vals)

                    print(info_modify)
                    break
        if not po_line:
            vals = self._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, partner,info)
            self.env['purchase.order.line'].sudo().create(vals)


    @api.multi
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, values, po, partner,info):
        procurement_uom_po_qty = product_uom._compute_quantity(product_qty, product_id.uom_po_id)
        seller = product_id._select_seller(
            partner_id=partner,
            quantity=procurement_uom_po_qty,
            date=po.date_order and po.date_order.date(),
            uom_id=product_id.uom_po_id)

        taxes = product_id.supplier_taxes_id
        fpos = po.fiscal_position_id
        taxes_id = fpos.map_tax(taxes, product_id, seller.name) if fpos else taxes
        if taxes_id:
            taxes_id = taxes_id.filtered(lambda x: x.company_id.id == values['company_id'].id)

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price, product_id.supplier_taxes_id,
                                                                             taxes_id,
                                                                             values['company_id']) if seller else 0.0
        if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, po.currency_id, po.company_id, po.date_order or fields.Date.today())

        product_lang = product_id.with_context({
            'lang': partner.lang,
            'partner_id': partner.id,
        })
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        date_planned = self.env['purchase.order.line']._get_date_planned(seller, po=po).strftime(
            DEFAULT_SERVER_DATETIME_FORMAT)


        return {
            'name': name,
            'product_qty': procurement_uom_po_qty,
            'product_id': product_id.id,
            'product_uom': product_id.uom_po_id.id,
            'price_unit': price_unit,
            'date_planned': date_planned,
            'orderpoint_id': values.get('orderpoint_id', False) and values.get('orderpoint_id').id,
            'taxes_id': [(6, 0, taxes_id.ids)],
            'order_id': po.id,
            'move_dest_ids': [(4, x.id) for x in values.get('move_dest_ids', [])],
            'info':info
        }


    def _prepare_purchase_order(self, product_id, product_qty, product_uom, origin, values, partner,commitment_date):
        schedule_date = self._get_purchase_schedule_date(values)
        purchase_date = self._get_purchase_order_date(product_id, product_qty, product_uom, values, partner, schedule_date)
        fpos = self.env['account.fiscal.position'].with_context(force_company=values['company_id'].id).get_fiscal_position(partner.id)

        gpo = self.group_propagation_option
        group = (gpo == 'fixed' and self.group_id.id) or \
                (gpo == 'propagate' and values.get('group_id') and values['group_id'].id) or False

        return {
            'partner_id': partner.id,
            'picking_type_id': self.picking_type_id.id,
            'company_id': values['company_id'].id,
            'currency_id': partner.with_context(force_company=values['company_id'].id).property_purchase_currency_id.id or self.env.user.company_id.currency_id.id,
            'dest_address_id': values.get('partner_id', False),
            'origin': origin,
            'payment_term_id': partner.with_context(force_company=values['company_id'].id).property_supplier_payment_term_id.id,
            'date_order': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'fiscal_position_id': fpos,
            'group_id': group,
            'commitment_date':commitment_date
        }




class PurchaseOrderLine(models.Model):

    _inherit = "purchase.order.line"

    info=fields.Text()

class PurchaseOrder(models.Model):

    _inherit = "purchase.order"

    commitment_date=fields.Datetime()