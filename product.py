# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 ADN (<http://adn-france.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import math
import re


from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp

class product_product(osv.osv):
    _inherit = "product.product"
    
    _columns = {
        'mro_type': fields.selection([('part','Part'),('labor','Labor'),('asset','Asset')],string="Maintenance product type"),
        'property_stock_asset': fields.property(
          'stock.location',
          type='many2one',
          relation='stock.location',
          string="Asset Location",
          view_load=True,
          help="This location will be used as the destination location for installed parts during asset life."),
        'childs_serial': fields.one2many('product.serial','product_id', 'Serials #'),
    }
    
        
    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context={}
        if not default:
            default = {}

        default.update(childs_serial=[])
        return super(product_product, self).copy(cr, uid, id, default=default,
                    context=context)
    
    
class product_template(osv.osv):
    _inherit = "product.template"
    
    _columns = {
        'contract': fields.boolean('Contract service'),
    }

class product_serial(osv.osv):
    _name = "product.serial"

    _columns = {
        'name': fields.char('Serial #', size=255),
        'product_id': fields.many2one('product.product', 'Parent product', select=True),
    }

    _defaults = {
    }
    
    
    _sql_constraints = [
                     ('name_unique', 
                      'unique(name,product_id)',
                      'Serial number must be unique per product')
    ]
    

