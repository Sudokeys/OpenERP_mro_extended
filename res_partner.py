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

import time

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp import netsvc

class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    _columns = {
        'technician': fields.many2one('hr.employee','Technician'),
        'asset_ids': fields.many2many('product.product', string='Assets'),
        #~ 'asset_ids': fields.one2many('res.partner.assets','partner_id', string='Assets'),
    }
    
class res_partner_assets(osv.osv):
    _name = 'res.partner.assets'
    _description = 'Partner Assets'
    
    _columns = {
        'name': fields.many2one('product.product', 'Asset', required=True),
        'default_code': fields.related('name','default_code', string='Reference',type='char', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', select=True),
        'serial_id': fields.many2one('product.serial', 'Serial #', domain="[('parent_id','=',name)]"),
    }
