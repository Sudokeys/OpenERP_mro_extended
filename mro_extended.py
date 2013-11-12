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

import time
from datetime import datetime, timedelta, date
from dateutil import parser
from dateutil import rrule
from dateutil.relativedelta import relativedelta
import pytz
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp import netsvc

class mro_order(osv.osv):
    """
    Maintenance Orders
    """
    _inherit = 'mro.order'
    
    MAINTENANCE_TYPE_SELECTION = [
        #~ ('bm', 'Breakdown'),
        ('cm', 'Corrective'),
        ('pm', 'Preventive'),
        ('im', 'Implementation'),
        ('mm', 'Metrology')
    ]
    
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('released', 'Waiting parts'),
        ('ready', 'Ready to maintenance'),
        ('parts_except', 'Parts exception'),
        ('meeting', 'Meeting fixed'),
        ('progress', 'In progress'),
        ('done', 'Done'),
        ('cancel', 'Canceled')
    ]
    
    def onchange_partner(self, cr, uid, ids, partner_id):
        """
        onchange handler of partner_id.
        """
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
        return {'value': {'technician': partner.technician.id}}
        
    def onchange_technician(self, cr, uid, ids, technician, partner_id):
        """
        onchange handler of technician.
        """
        value={}
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if technician and not partner.technician :
                self.pool.get('res.partner').write(cr,uid,partner.id,{'technician':technician})
        return value
        
    def onchange_subcontractor(self, cr, uid, ids, description, subcontract, subcontractor_id):
        value={}
        print description.split('[Subcontract'),description.split('Subcontract]')
        if subcontract and subcontractor_id:
            subcontractor = self.pool.get('res.partner').browse(cr, uid, subcontractor_id)
            value['description']=_('%s [Subcontract: %s]') % (description.split(' [Subcontract') and description.split(' [Subcontract')[0] or '' +description.split('Subcontract]') and description.split('Subcontract]')[1] or '',subcontractor.name)
        else:
            value['description']='%s' % (description.split(' [Subcontract') and description.split(' [Subcontract')[0] or '' +description.split('Subcontract]') and description.split('Subcontract]')[1] or '')
        print 'value',value
        return {'value':value}
        
    def onchange_dates(self, cr, uid, ids, start_date, duration=False, end_date=False, allday=False, date_type=False, context=None):
        """Returns duration and/or end date based on values passed
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user's ID for security checks,
        @param ids: List of calendar event's IDs.
        @param start_date: Starting date
        @param duration: Duration between start date and end date
        @param end_date: Ending Datee
        @param context: A standard dictionary for contextual values
        """
        if context is None:
            context = {}
            
        value = {}
            
        if not start_date:
            return value
        if not end_date and not duration:
            duration = 1.00
            value['duration'] = duration

        start = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        if allday: # For all day event
            duration = 24.0
            value['duration'] = duration
            # change start_date's time to 00:00:00 in the user's timezone
            user = self.pool.get('res.users').browse(cr, uid, uid)
            tz = pytz.timezone(user.tz) if user.tz else pytz.utc
            start = pytz.utc.localize(start).astimezone(tz)     # convert start in user's timezone
            start = start.replace(hour=0, minute=0, second=0)   # change start's time to 00:00:00
            start = start.astimezone(pytz.utc)                  # convert start back to utc
            start_date = start.strftime("%Y-%m-%d %H:%M:%S")
            value['date'] = start_date

        if end_date and not duration:
            end = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            diff = end - start
            duration = float(diff.days)* 24 + (float(diff.seconds) / 3600)
            value['duration'] = round(duration, 2)
        elif not end_date:
            end = start + timedelta(hours=duration)
            value['date_deadline'] = end.strftime("%Y-%m-%d %H:%M:%S")
        elif end_date and duration and not allday:
            # we have both, keep them synchronized:
            # set duration based on end_date (arbitrary decision: this avoid
            # getting dates like 06:31:48 instead of 06:32:00)
            end = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            diff = end - start
            duration = float(diff.days)* 24 + (float(diff.seconds) / 3600)
            value['duration'] = round(duration, 2)
        
        if date_type=='date_planned':
            value['date_scheduled'] = start_date
        if date_type=='date_scheduled':
            value['date_execution'] = start_date
            
        return {'value': value}
    
    _columns = {
        'asset_id': fields.many2one('asset.asset', 'Asset', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'asset_ids': fields.many2many('product.product', string='Assets', required=True),
        'partner_id': fields.many2one('res.partner','Client'),
        'subcontract': fields.boolean('Subcontract?'),
        'subcontractor_id': fields.many2one('res.partner','Subcontractor'),
        'contract_id': fields.many2one('account.analytic.account','Contract'),
        'technician': fields.many2one('hr.employee','Technician',required=True),
        'order_id': fields.many2one('sale.order','Order'),
        'place': fields.selection([('site','Site'),('workshop','Worskhop')],'Place'),
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True,
            help="When the maintenance order is created the status is set to 'Draft'.\n\
            If the order is confirmed the status is set to 'Waiting Parts'.\n\
            If any exceptions are there, the status is set to 'Picking Exception'.\n\
            If the stock is available then the status is set to 'Ready to Maintenance'.\n\
            When the maintenance order gets started then the status is set to 'In Progress'.\n\
            When the maintenance is over, the status is set to 'Done'."),
        'maintenance_type': fields.selection(MAINTENANCE_TYPE_SELECTION, 'Maintenance Type', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'tools_ids': fields.many2many('mro.tools',string='Tools'),
        'date_deadline': fields.datetime('End Date', readonly=True, states={'draft':[('readonly',False)],'released':[('readonly',False)],'ready':[('readonly',False)]}),
        'duration': fields.float('Duration', readonly=True, states={'draft':[('readonly',False)],'released':[('readonly',False)],'ready':[('readonly',False)]}),
        'allday': fields.boolean('All Day', readonly=True, states={'draft':[('readonly',False)],'released':[('readonly',False)],'ready':[('readonly',False)]}),
    }
    
    _defaults = {
        'date_planned': False,
        'date_scheduled': False,
        'date_execution': False,
        'maintenance_type': lambda *a: 'cm',
    }
    
    def action_meeting(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state': 'meeting'})
        return True
    
    def action_progress(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state': 'progress'})
        return True
    
    def _make_consume_parts_line(self, cr, uid, parts_line, context=None):
        stock_move = self.pool.get('stock.move')
        order = parts_line.maintenance_id
        # Internal shipment is created for Stockable and Consumer Products
        if parts_line.parts_id.type not in ('product', 'consu'):
            return False
        move_id = stock_move.create(cr, uid, {
            'name': order.name,
            'date': order.date_planned,
            'product_id': parts_line.parts_id.id,
            'product_qty': parts_line.parts_qty,
            'product_uom': parts_line.parts_uom.id,
            'location_id': order.parts_location_id.id,
            'location_dest_id': order.asset_ids[0].property_stock_asset.id,
            'state': 'waiting',
            'company_id': order.company_id.id,
        })
        order.write({'parts_move_lines': [(4, move_id)]}, context=context)
        return move_id
        

    
    
class mro_tools(osv.osv):
    """
    Tools
    """
    _name = 'mro.tools'
    _description = 'Tools'
    _inherit = ['mail.thread']
    
    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image, avoid_resize_medium=True)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)


    _columns = {
        'name': fields.char('Tool Name', size=128, required=True),
        'active': fields.boolean('Active'),
        'model': fields.char('Model', size=128),
        'manufacturer': fields.char('Manufacturer', size=128),
        'serial': fields.char('Serial no.', size=128),
        'data': fields.binary('File'),
        # image: all image fields are base64 encoded and PIL-supported
        'image': fields.binary("Image",
            help="This field holds the image used as image for the tool, limited to 1024x1024px."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized image", type="binary", multi="_get_image",
            store={
                'tool.tool': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized image of the tool. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved, "\
                 "only when the image exceeds one of those sizes. Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized image", type="binary", multi="_get_image",
            store={
                'tool.tool': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized image of the tool. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
        'date_validity_begin': fields.date('Validity date begin'),
        'date_validity_end': fields.date('Validity date end'),
    }
    
    _defaults = {
        'active': True,
    }
