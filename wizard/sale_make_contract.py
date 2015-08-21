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
from datetime import timedelta, datetime


class sale_make_contract(osv.osv_memory):
    """ Make contract for sale """

    _name = "sale.make.contract"
    _description = "Make contract"
    
    def _selectPartner(dtype):
        def _getPartner(self, cr, uid, context=None):
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
            res=''
            res = sale_obj.read(cr, uid, active_id, ['partner_id'])
            if dtype=='partner_id':
                return res['partner_id'][0]
            if dtype=='name':
                partner = self.pool.get('res.partner').browse(cr,uid,res['partner_id'][0],context)
                res = _('Contract: ') + partner.name
                return res
        return _getPartner

    def view_init(self, cr, uid, fields_list, context=None):
        return super(sale_make_contract, self).view_init(cr, uid, fields_list, context=context)

    def makeContract(self, cr, uid, ids, context=None):
        """
        This function  create Maintenance Order on given case.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of sale make contract' ids
        @param context: A standard dictionary for contextual values
        @return: Dictionary value of created contract.
        """
        if context is None:
            context = {}

        contract_obj = self.pool.get('account.analytic.account')
        date_start = self.pool.get('account.analytic.account')
        date = self.pool.get('account.analytic.account')
        sale_obj = self.pool.get('sale.order')
        partner_obj = self.pool.get('res.partner')
        geneasset_obj=self.pool.get('generic.assets')
        analserv_obj=self.pool.get('account.analytic.services')

        data = context and context.get('active_ids', []) or []


        for make in self.browse(cr, uid, ids, context=context):
            partner = make.partner_id
            new_ids = []
            for sale in sale_obj.browse(cr, uid, data, context=context):
                if not partner and sale.partner_id:
                    partner = sale.partner_id

                vals = {
                    'name': make.description,
                    'type': 'contract',
                    'partner_id': make.partner_id.id,
                    'manager_id': make.partner_id.user_id and make.partner_id.user_id.id or False,
                    'date_start': time.strftime('%Y-%m-%d'),
                    'date': (datetime.strptime(time.strftime('%Y-%m-%d'), '%Y-%m-%d')
                    + timedelta(days=sale.validity)).strftime('%Y-%m-%d'),
                    'description': sale.note,
                    'note_intern': sale.note_interne

                }

                # if vals.get('partner_id') is not None:
                #     vals['date_start'] = time.strftime('%Y-%m-%d'),

                # if sale.validity is not None:
                #     vals['date'] = str(
                #         datetime.strptime(vals.get('date_start'), '%Y-%m-%d')
                #     + timedelta(days=vals.get('validity')))

                # if sale.note is not None:
                #     vals['description'] = str(vals.get('note'))

                # if sale.note_interne is not None:
                #     vals['note_intern'] = str(vals.get('note_interne'))

                new_id = contract_obj.create(cr, uid, vals, context=context)
                sale_obj.write(cr,uid,sale.id,{'project_id':new_id},context)

                for line in sale.order_line:
                    vals1 = {
                        'name': line.name,
                        'service_id': line.product_id.id,
                        'price': line.price_unit,
                        'contract_id': new_id,
                    }
                    serv_id=analserv_obj.create(cr,uid,vals1,context=context)
                    if line.assets_id:
                        geneasset_obj.write(cr,uid,line.assets_id.id,{'contract_id':new_id},context=context)
                        contract_obj.write(cr,uid,new_id,{'asset_ids':[(4,line.assets_id.id)]},context=context)
                        analserv_obj.write(cr,uid,serv_id,{'asset_id':line.assets_id.id},context=context)



#                for line in make.asset_ids:
#                    vals = {
#                        'name': line.name,
#                        'asset_id': line.id,
#                        'contract_id': new_id,
#                        'partner_id': partner.id,
#                    }
#                    self.pool.get('generic.assets').create(cr,uid,vals,context=context)
#
#                for line in make.service_ids:
#                    vals = {
#                        'name': line.name,
#                        'service_id': line.product_id.id,
#                        'price': line.price_subtotal,
#                        'contract_id': new_id,
#                    }
#                    self.pool.get('account.analytic.services').create(cr,uid,vals,context=context)
#
                contract = contract_obj.browse(cr, uid, new_id, context=context)
                new_ids.append(new_id)
                message = _("<em>%s</em> has been <b>created</b>.") % (contract.name)
                sale.message_post(body=message)
            #~ if not new_ids:
            return {'type': 'ir.actions.act_window_close'}
            #~ if len(new_ids)<=1:
                #~ value = {
                    #~ 'domain': str([('id', 'in', new_ids)]),
                    #~ 'view_type': 'form',
                    #~ 'view_mode': 'form',
                    #~ 'res_model': 'mro.order',
                    #~ 'view_id': False,
                    #~ 'type': 'ir.actions.act_window',
                    #~ 'name' : _('Maintenance Order'),
                    #~ 'res_id': new_ids and new_ids[0]
                #~ }
            #~ else:
                #~ value = {
                    #~ 'domain': str([('id', 'in', new_ids)]),
                    #~ 'view_type': 'form',
                    #~ 'view_mode': 'tree,form',
                    #~ 'res_model': 'mro.order',
                    #~ 'view_id': False,
                    #~ 'type': 'ir.actions.act_window',
                    #~ 'name' : _('Maintenance Order'),
                    #~ 'res_id': new_ids
                #~ }
            #~ return value

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
                if line.product_id.contract:
                    duration = line.product_uom_qty
        return duration
        
    def _get_assets(self, cr, uid, context=None):
        if context is None:
            context = {}
        sale_obj = self.pool.get('sale.order')
        active_id = context and context.get('active_id', False) or False
        if not active_id:
            return False
        assets = []
        for sale in sale_obj.browse(cr, uid, [active_id], context=context):
            for line in sale.order_line:
#                if line.product_id.mro_type=='asset':
#                    assets.append(line.product_id.id)
                if line.assets_id:
                    assets.append(line.assets_id.asset_id.id)
        return assets
        
    def _get_services(self, cr, uid, context=None):
        if context is None:
            context = {}
        sale_obj = self.pool.get('sale.order')
        active_id = context and context.get('active_id', False) or False
        if not active_id:
            return False
        services = []
        for sale in sale_obj.browse(cr, uid, [active_id], context=context):
            for line in sale.order_line:
                if line.product_id.contract:
                    services.append(line.id)
        return services
        
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Customer', required=True, domain=[('customer','=',True)]),
        'description': fields.char('Description', size=64, required=True),
        'asset_ids': fields.many2many('product.product', string='Assets', required=False),
        'service_ids': fields.many2many('sale.order.line', string='Contract services', required=False),
        'date_planned': fields.datetime('Planned Date', required=True),
        'duration': fields.float('Duration'),
    }
    _defaults = {
        'duration': _get_duration,
        'partner_id': _selectPartner('partner_id'),
        'description': _selectPartner('name'),
        'asset_ids': _get_assets,
        'service_ids': _get_services,
        'date_planned': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
