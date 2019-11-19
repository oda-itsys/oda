from odoo import fields, models, _, api, exceptions
import datetime
from datetime import timedelta

class StockMove(models.Model):
    _inherit = 'stock.move'

    notes = fields.Char()
