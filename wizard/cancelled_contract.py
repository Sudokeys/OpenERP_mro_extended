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


class cancelled_contract(osv.osv_memory):

    _name = "cancelled.contract"
    _description = "Cancelled Contract"
    
    def confirm(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        contract_obj = self.pool.get('account.analytic.account')

        wiz = self.browse(cr,uid,ids,context=context)
        #~ for contract in contract_obj.browse(cr, uid, data, context=context):

        contract_id=wiz[0].id
        date_refused=wiz[0].date_refused
        if contract_id and date_refused:
            contract_obj.write(cr,uid,[contract_id],{'state':'cancelled','date_refused':wiz[0].date_refused},context=context)
            return {
                    'domain': str([('id', '=', contract_id)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'account.analytic.account',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name' : _('Contract'),
                    'res_id': contract_id
                }
        else:
            return {'type': 'ir.actions.act_window_close'}

            
    _columns = {
        #~ 'contract_id': fields.many2one('account.analytic.account', 'Contract'),
        #~ 'partner_id': fields.many2one('res.partner', 'Customer', required=True, domain=[('customer','=',True)]),
        #~ 'description': fields.char('Description', size=64, required=True),
        #~ 'asset_ids': fields.many2many('product.product', string='Assets', required=True),
        #~ 'maintenance_type': fields.selection(MAINTENANCE_TYPE_SELECTION, 'Maintenance Type', required=True),
        'date_refused': fields.date('Refused Date', required=True),
        #~ 'duration': fields.float('Duration'),
    }
    _defaults = {
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
