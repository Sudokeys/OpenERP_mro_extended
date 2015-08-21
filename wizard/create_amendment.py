# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class services_assets_wizard(osv.osv_memory):

    _name = "services.assets.wizard"
    _description = "Contract services / Assets"

    _columns = {
        'service_id': fields.many2one('product.product', 'Contract service', required=True),
        'service_real_id': fields.many2one('account.analytic.services', 'Contract service real id'),
        'asset_id': fields.many2one('product.product', 'Asset'),#required=True
        'serial_id': fields.many2one('product.serial', 'Serial #', select=True),
        'price': fields.float('Price'),
        'create_amendment_id_old': fields.many2one('create.amendment', 'Amendment creation old'),
        'create_amendment_id_new': fields.many2one('create.amendment', 'Amendment creation new'),
        'quantity': fields.integer(u'Quantité', help=u'Defini la quantité'),
        'total': fields.float('Total', help='Total'),
        #~ 'create_amendment_id_remove': fields.many2one('create.amendment', 'Amendment creation remove'),
    }


    def onchange_quantity(self, cr, uid, ids, price, quantity, asset_id, context=None):
        result = {}
        if quantity > 1:
            result['asset_id'] = False
            result['total'] = price * quantity
        return {'value': result}

    def onchange_asset(self, cr, uid, ids, asset_id, quantity, price, context=None):
        result = {}
        if asset_id:
            result['quantity'] = 1
            result['total'] = price * quantity
        return {'value': result}

class create_amendment(osv.osv_memory):

    _name = "create.amendment"
    _description = "Create Amendment"

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(create_amendment, self).default_get(cr, uid, fields, context=context)
        service_asset_ids = []
        service_asset_obj = self.pool.get('services.assets.wizard')
        contract_obj = self.pool.get('account.analytic.account')
        contract = contract_obj.browse(cr, uid, [context['active_id']])[0]
        res['date_begin'] = contract.date
        res['date_end'] = (datetime.strptime(contract.date,'%Y-%m-%d')+relativedelta(years=1)).strftime('%Y-%m-%d')
        for service in contract.service_ids:
            if service.asset_id:
                service_asset_ids.append({'service_id':service.service_id.id,
                                        'service_real_id':service.id or False,
                                        'asset_id':service.asset_id.asset_id.id or False,
                                        'serial_id':service.asset_id.serial_id and service.asset_id.serial_id.id or False,
                                        'price':service.price,
                                        })
        res['service_asset_ids_old'] = service_asset_ids
        res['contract_id'] = contract.id
        return res

    def confirm(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        contract_obj = self.pool.get('account.analytic.account')
        amendment_obj = self.pool.get('account.analytic.amendments')
        service_asset_obj = self.pool.get('services.assets')
        service_obj = self.pool.get('account.analytic.services')
        asset_obj = self.pool.get('generic.assets')
        contract_id = context and context.get('active_id', False) or False
        wiz = self.browse(cr,uid,ids,context=context)[0]
        amendment_id=amendment_obj.create(cr,uid,{'name':wiz.name,'date':wiz.date,'contract_id':contract_id,'price_rise':wiz.price_rise})
        if wiz.renewal:
            amendment_obj.write(cr,uid,amendment_id,{'new_date_begin':wiz.date_begin,'new_date_end':wiz.date_end})
            #~ contract_obj.write(cr,uid,[contract_id],{'date_start':wiz.date_begin,'date':wiz.date_end})
        if amendment_id:
            amendment=amendment_obj.browse(cr,uid,amendment_id,context=context)
            #~ for s in amendment.contract_id.service_ids:
                #~ service_obj.write(cr,uid,s.id,{'price':s.price + (s.price*wiz.price_rise)/100})
            service_removed_ids=[]
            asset_removed_ids=[]
            #REMOVE
            for sa_remove in wiz.service_asset_ids_remove:
                service_asset_obj.create(cr,uid,{'service_id':sa_remove.service_id.id,
                                                'service_real_id':sa_remove.id,
                                                'asset_id':sa_remove.asset_id.asset_id.id,
                                                'serial_id':sa_remove.asset_id.serial_id and sa_remove.asset_id.serial_id.id or False,
                                                'price':sa_remove.price,
                                                'amendment_id':amendment_id,
                                                'move_type':'remove',
                                                'order_number':sa_remove.order_number,
                                                'date_invoice': sa_remove.date_invoice,
                                                'invoice_number': sa_remove.invoice_number,
                                                })
                service_removed_ids.append(sa_remove.id)
                asset_removed_ids.append(sa_remove.asset_id.asset_id.id)
                #~ service_obj.unlink(cr,uid,sa_remove.id)
                #~ asset_obj.unlink(cr,uid,sa_remove.asset_id.id)
            #REMAIN
            for sa_old in wiz.service_asset_ids_old:
                if sa_old.service_real_id.id not in service_removed_ids and sa_old.asset_id.id not in asset_removed_ids:
                    service_asset_obj.create(cr,uid,{'service_id':sa_old.service_id.id,
                                                    'service_real_id':sa_old.service_real_id.id,
                                                    'asset_id':sa_old.asset_id.id,
                                                    'serial_id':sa_old.serial_id and sa_old.serial_id.id or False,
                                                    'price':sa_old.price + (sa_old.price*wiz.price_rise)/100,
                                                    'amendment_id':amendment_id,
                                                    'move_type':'remain',
                                                    'order_number':sa_old.order_number,
                                                    'date_invoice': sa_old.date_invoice,
                                                    'invoice_number': sa_old.invoice_number,
                                                    })
            #ADD
            for sa_new in wiz.service_asset_ids_new:
                service_asset_obj.create(cr,uid,{'service_id':sa_new.service_id.id,
                                                'asset_id':sa_new.asset_id.id,
                                                'serial_id':sa_new.serial_id and sa_new.serial_id.id or False,
                                                'price':sa_new.price,
                                                'amendment_id':amendment_id,
                                                'move_type':'add',
                                                'quantity': sa_new.quantity,
                                                'total': sa_new.total,
                                                'order_number':sa_new.order_number,
                                                'date_invoice': sa_new.date_invoice,
                                                'invoice_number': sa_new.invoice_number,
                                                })
                #~ service_id=service_obj.create(cr,uid,{'service_id':sa_new.service_id.id,
                                                #~ 'name':sa_new.service_id.name,
                                                #~ 'price':sa_new.price,
                                                #~ 'contract_id':contract_id,
                                                #~ })
                #~ asset_id=asset_obj.create(cr,uid,{'service_id':service_id,
                                                #~ 'asset_id':sa_new.asset_id.id,
                                                #~ 'name':sa_new.asset_id.name,
                                                #~ 'serial_id':sa_new.serial_id and sa_new.serial_id.id or False,
                                                #~ 'contract_id':contract_id,
                                                #~ })
                #~ service_obj.write(cr,uid,service_id,{'asset_id':asset_id})

        return {'type': 'ir.actions.act_window_close'}


    _columns = {
        'name': fields.char('Description', size=128),
        'date': fields.date('Date'),
        'date_begin': fields.date('Date Begin',readonly="True"),
        'date_end': fields.date('Date End',readonly="True"),
        'renewal': fields.boolean('Contract Renewal'),
        'contract_id': fields.many2one('account.analytic.account','Contract'),
        'service_asset_ids_old': fields.one2many('services.assets.wizard','create_amendment_id_old','Contract services / Assets',readonly="True"),
        'service_asset_ids_new': fields.one2many('services.assets.wizard','create_amendment_id_new','Contract services / Assets'),
        'service_asset_ids_remove': fields.many2many('account.analytic.services',string='Contract services / Assets'),
        'price_rise': fields.float('Price Rise (%)'),
        'order_number':fields.char(u'N° de commande'),
        'date_invoice': fields.date('Date de facture'),
        'invoice_number': fields.char(u'N° de facture'),
        'quantity': fields.integer(u'Quantité', help=u'Defini la quantité'),
        'total': fields.float('Total', help='Total'),
        }
    _defaults = {
        'price_rise': 3.00,
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
