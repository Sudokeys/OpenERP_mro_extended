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
import logging
_logger = logging.getLogger(__name__)


class sale_order(osv.osv):
    _inherit = 'sale.order'

    _columns = {
        'mro_order_ids': fields.one2many('mro.order','order_id','Maintenance Orders'),
    }


class sale_order_line(osv.osv):
    _inherit='sale.order.line'

    _columns={
        'assets_id':fields.many2one('generic.assets',u'Asset'),#Changement d'objet, vider la colonne avant update (update sale_order_line set assets_id = NULL )
        'assets_partner':fields.many2one('res.partner',u'Asset partner filter'),
        'is_contract':fields.boolean(u'Is contract'),
        'assets_no_domain':fields.boolean(u'All assets'),
        'asset_rel_ids':fields.many2many('generic.assets',string=u'Domaine assets'),

    }

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}
        res=super(sale_order_line,self).product_id_change(cr, uid, ids, pricelist, product, qty,
            uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, context)
        res['is_contract'] = False        
        if product:
            prod=self.pool.get('product.product').browse(cr,uid,product,context)
            if prod and prod.contract:
                res['is_contract'] = True
        if partner_id:
            assets=[]
            partner=self.pool.get('res.partner').browse(cr,uid,partner_id,context)
            if partner and partner.asset_ids:
                for asset in partner.asset_ids:
                    assets.append(asset.id)
                res['asset_rel_ids'] = [(6,0,assets)]
        return {'value': res}

    def onchange_domain(self, cr, uid, ids, asset_rel_ids,assets_no_domain,assets_partner,partner_id, context=None):
        context = context or {}
        domain = {}
        domain['assets_id']=[('id','in',asset_rel_ids[0][2])]
        if assets_no_domain and not assets_partner:
            domain['assets_id']=[]
            return {'domain': domain}
        active_partner = assets_partner or partner_id
        if active_partner:
            assets=[]
            partner=self.pool.get('res.partner').browse(cr,uid,active_partner,context)
            for asset in partner.asset_ids:
                assets.append(asset.id)
            domain['assets_id']=[('id','in',assets)]
        return {'domain': domain}
