# -*- coding: utf-8 -*-

import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from mro_extended import mro_extended

class sale_import_assets(osv.osv_memory):
    _name = "sale.import.assets"
    _description = "Import assets into sale lines"
    
    def view_init(self, cr, uid, fields_list, context=None):
        return super(sale_import_assets, self).view_init(cr, uid, fields_list, context=context)
    
    def _selectPartner(self, cr, uid, context=None):
        if context is None:
            context = {}

        sale_obj = self.pool.get('sale.order')
        active_id = context and context.get('active_id', False) or False
        if not active_id:
            return False

        sale = sale_obj.read(cr, uid, active_id, ['partner_id'])
        return sale['partner_id']

    _columns = {
        'product_contract_id': fields.many2one('product.product', 'Prestation contractuelle', required=True),
        'asset_ids': fields.many2many('generic.assets', string=u'Équipements', required=True),
        'partner_id': fields.many2one('res.partner', 'Customer'),
    }
    _defaults = {
        'partner_id': _selectPartner,
    }
    
    def importer(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        mro_obj = self.pool.get('mro.order')
        sale_obj = self.pool.get('sale.order')
        sale_line_obj = self.pool.get('sale.order.line')
        partner_obj = self.pool.get('res.partner')
        data = context and context.get('active_id', False) or False
        sale = sale_obj.browse(cr, uid, data, context=context)
        if not context.get('partner_id'):
            context['partner_id']=sale.partner_id.id
        for w in self.browse(cr, uid, ids, context=context):
            new_ids = []
            for asset in w.asset_ids:
                res = sale_line_obj.product_id_change(cr, uid, [sale.id], sale.pricelist_id.id,
                    w.product_contract_id.id, qty=1.0, uom=w.product_contract_id.uom_id.id,qty_uos=1.0, uos=False, name='', partner_id=sale.partner_id.id,
                    lang=False, update_tax=True, date_order=sale.date_order,packaging=False, fiscal_position=False,flag=False, context=context)
                
                vals = {
                    'order_id':sale.id,
                    'product_id':w.product_contract_id.id,
                    'product_uom_qty':1.0,
                    'product_uom':w.product_contract_id.uom_id.id,
                    'is_contract':w.product_contract_id.contract,
                    'assets_id':asset.id,
                    'assets_partner':  asset.partner_id.id
                }
                vals.update(res['value']['value'])
                if not vals.get('name'):
                    vals['name']=asset.asset_id.name
                sale_line_obj.create(cr,uid,vals,context=context)
        return True
