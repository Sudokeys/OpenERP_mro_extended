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


class sale_make_mro(osv.osv_memory):
    """ Make mro order for sale """

    _name = "sale.make.mro"
    _description = "Make mro orders"
    
    MAINTENANCE_TYPE_SELECTION = [
        ('bm', 'Breakdown'),
        ('cm', 'Corrective'),
        ('pm', 'Preventive'),
        ('im', 'Implementation'),
        ('mm', 'Metrology')
    ]

    def _selectPartner(self, cr, uid, context=None):
        """
        This function gets default value for partner_id field.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        @return: default value of partner_id field.
        """
        if context is None:
            context = {}

        sale_obj = self.pool.get('sale.order')
        active_id = context and context.get('active_id', False) or False
        if not active_id:
            return False

        sale = sale_obj.read(cr, uid, active_id, ['partner_id'])
        return sale['partner_id']

    def view_init(self, cr, uid, fields_list, context=None):
        return super(sale_make_mro, self).view_init(cr, uid, fields_list, context=context)

    def makeOrder(self, cr, uid, ids, context=None):
        """
        This function  create Maintenance Order on given case.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of sale make mro' ids
        @param context: A standard dictionary for contextual values
        @return: Dictionary value of created mro order.
        """
        if context is None:
            context = {}
        # update context: if come from phonecall, default state values can make the quote crash lp:1017353
        context.pop('default_state', False)        
        
        mro_obj = self.pool.get('mro.order')
        sale_obj = self.pool.get('sale.order')
        partner_obj = self.pool.get('res.partner')
        data = context and context.get('active_ids', []) or []

        for make in self.browse(cr, uid, ids, context=context):
            partner = make.partner_id
            new_ids = []
            for sale in sale_obj.browse(cr, uid, data, context=context):
                if not partner and sale.partner_id:
                    partner = sale.partner_id

                vals = {
                    'origin': sale.name,
                    'order_id': sale.id,
                    'contract_id': make.contract_id.id or False,
                    'partner_id': partner.id,
                    'description': make.description,
                    'asset_id': make.asset_id.id,
                    'maintenance_type': make.maintenance_type,
                    'date_planned': make.date_planned,
                    'date_scheduled': make.date_planned,
                    'date_execution': make.date_planned,
                    'duration': make.duration,
                }
                if partner.id:
                    vals['technician'] = partner.technician and partner.technician.id or False
                new_id = mro_obj.create(cr, uid, vals, context=context)
                
                for line in sale.order_line:
                    if line.product_id.mro_type=='part':
                        vals = {
                            'name': line.name,
                            'parts_id': line.product_id.id,
                            'parts_qty': line.product_uom_qty,
                            'parts_uom': line.product_uom.id,
                            'maintenance_id': new_id,
                        }
                        self.pool.get('mro.order.parts.line').create(cr,uid,vals,context=context)
                    
                    
                
                mro_order = mro_obj.browse(cr, uid, new_id, context=context)
                new_ids.append(new_id)
                message = _("Maintenance Order <em>%s</em> has been <b>created</b>.") % (mro_order.name)
                sale.message_post(body=message)
            if not new_ids:
                return {'type': 'ir.actions.act_window_close'}
            if len(new_ids)<=1:
                value = {
                    'domain': str([('id', 'in', new_ids)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mro.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name' : _('Maintenance Order'),
                    'res_id': new_ids and new_ids[0]
                }
            else:
                value = {
                    'domain': str([('id', 'in', new_ids)]),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'mro.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name' : _('Maintenance Order'),
                    'res_id': new_ids
                }
            return value

    def _get_contract_id(self, cr, uid, context=None):
        if context is None:
            context = {}

        sale_obj = self.pool.get('sale.order')
        active_id = context and context.get('active_id', False) or False
        if not active_id:
            return False

        sale = sale_obj.read(cr, uid, active_id, ['project_id'])
        return sale['project_id']
        
    def _get_duration(self, cr, uid, context=None):
        if context is None:
            context = {}
        sale_obj = self.pool.get('sale.order')
        active_id = context and context.get('active_id', False) or False
        if not active_id:
            return False
        duration = 0.0
        for sale in sale_obj.browse(cr, uid, [active_id], context=context):
            for line in sale.order_line:
                if line.product_id.mro_type=='labor':
                    duration = line.product_uom_qty
        return duration
        
    _columns = {
        'contract_id': fields.many2one('account.analytic.account', 'Contract'),
        'partner_id': fields.many2one('res.partner', 'Customer', required=True, domain=[('customer','=',True)]),
        'description': fields.char('Description', size=64, required=True),
        'asset_id': fields.many2one('asset.asset', 'Asset', required=True),
        'maintenance_type': fields.selection(MAINTENANCE_TYPE_SELECTION, 'Maintenance Type', required=True),
        'date_planned': fields.datetime('Planned Date', required=True),
        'duration': fields.float('Duration'),
    }
    _defaults = {
        'contract_id': _get_contract_id,
        'duration': _get_duration,
        'partner_id': _selectPartner,
        'date_planned': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
