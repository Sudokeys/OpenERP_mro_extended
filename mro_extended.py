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
from openerp import tools
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
        ('invoicing', 'Invoicing'),
        ('invoiced', 'Invoiced'),
        ('done', 'Done'),
        ('cancel', 'Canceled')
    ]
TOOLS_PLACE=[('fixed','Fixed'),('movable','Movable')]

class mro_order(osv.osv):
    """
    Maintenance Orders
    """
    _inherit = 'mro.order'
    
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
        if subcontract and subcontractor_id:
            subcontractor = self.pool.get('res.partner').browse(cr, uid, subcontractor_id)
            value['description']=_('%s [Subcontract: %s]') % (description.split(' [Subcontract') and description.split(' [Subcontract')[0] or '' +description.split('Subcontract]') and description.split('Subcontract]')[1] or '',subcontractor.name)
        else:
            value['description']='%s' % (description.split(' [Subcontract') and description.split(' [Subcontract')[0] or '' +description.split('Subcontract]') and description.split('Subcontract]')[1] or '')
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
        #~ 'asset_ids': fields.many2many('product.product', string='Assets', required=True),
        'asset_ids': fields.many2many('generic.assets', string='Assets', required=True),
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
        
    def action_invoicing(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state': 'invoicing'})
        return True

################################################################################
# DO invoice
################################################################################    
    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        """Prepare the dict of values to create the new invoice for a
           mro order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: mro.order record to invoice
           :return: dict of value to create() the invoice
        """
        if context is None:
            context = {}
        journal_ids = self.pool.get('account.journal').search(cr, uid,
            [('type', '=', 'sale'), ('company_id', '=', order.company_id.id)],
            limit=1)
        if not journal_ids:
            raise osv.except_osv(_('Error!'),
                _('Please define sales journal for this company: "%s" (id:%d).') % (order.company_id.name, order.company_id.id))
        invoice_vals = {
            'name': order.description or '',
            'origin': order.name,
            'type': 'out_invoice',
            'reference': order.name,
            'account_id': order.partner_id.property_account_receivable.id,
            'partner_id': order.partner_id.id,
            'journal_id': journal_ids[0],
            #'invoice_line': [(6, 0, lines)],
            'currency_id': order.company_id.currency_id.id,
            'comment': order.operations_description or '',
            'payment_term': False,
            'fiscal_position': order.partner_id.property_account_position and order.partner_id.property_account_position.id or False,
            #'date_invoice': context.get('date_invoice', False),
            'company_id': order.company_id.id,
            'user_id': uid,
        }
        return invoice_vals
    
    def _invoice_line(self, cr, uid,invoice_id, product_id, False, quantity, uom, type, partner_id, fpos_id, amount, context=None):
        invoice_line_obj = self.pool.get('account.invoice.line')
        line_value =  {
            'product_id': product_id,
        }

        line_dict = invoice_line_obj.product_id_change(cr, uid, {},
                        product_id, False, quantity, '', 'out_invoice', partner_id, fpos_id, amount, False, context, False)
                        #product, uom_id, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, currency_id=False, context=None, company_id=None):
        #print 'line_dict: ',line_dict
        line_value.update(line_dict['value'])

        line_value['price_unit'] = amount
        line_value['invoice_id']= invoice_id
        line_value['quantity']=quantity
        if line_value.get('invoice_line_tax_id', False):
            tax_tab = [(6, 0, line_value['invoice_line_tax_id'])]
            line_value['invoice_line_tax_id'] = tax_tab
        print 'line_value: ', line_value
        invoice_line_id = invoice_line_obj.create(cr, uid, line_value, context=context)
        return invoice_line_id
    
    def action_do_invoice(self, cr, uid, ids,context=False):
        inv_obj=self.pool.get('account.invoice')
        invline_obj=self.pool.get('account.invoice.line')
        #we search if there is an contrat first
        for interv in self.browse(cr,uid,ids,context):
            lines=[]
            # first product in contrat
            if interv.contract_id:
                for serv in interv.contract_id.service_ids:
                    if serv.service_id:
                        lines.append({
                            'product_id':serv.service_id.id,
                            'price':serv.price,
                            'qty':1,
                        })
            print 'lines: ',lines
            #second parts line
            for part in interv.parts_lines:
                lines.append({
                    'product_id':part.parts_id.id,
                    'price':part.parts_id.list_price,
                    'qty':part.parts_qty,
                })

            print 'lines: ',lines
            if len(lines)>0:
                #make invoice
                inv_vals=self._prepare_invoice(cr, uid, interv, False, context)
                if inv_vals:
                    inv_id=inv_obj.create(cr,uid,inv_vals)
                    if inv_id:
                        #invoice line
                        for line in lines:
                            self._invoice_line(cr,uid,inv_id, line['product_id'], False, line['qty'], '', 'out_invoice',
                            interv.partner_id.id, interv.partner_id.property_account_receivable,
                            line['price'],context=None)





        #raise osv.except_osv(_('Error!'),_('voulue'))

        self.write(cr, uid, ids, {'state': 'invoiced'})
        return True

    def _make_consume_parts_line(self, cr, uid, parts_line, context=None):
        stock_move = self.pool.get('stock.move')
        order = parts_line.maintenance_id
        # Internal shipment is created for Stockable and Consumer Products
        if parts_line.parts_id.type not in ('product', 'consu'):
            return False
        if not order.asset_ids[0].asset_id.property_stock_asset:
            raise osv.except_osv(
                _('Cannot consume parts!'),
                _('You must first assign a location for the parts in the asset.'))
        move_id = stock_move.create(cr, uid, {
            'name': order.name,
            'date': order.date_planned,
            'product_id': parts_line.parts_id.id,
            'product_qty': parts_line.parts_qty,
            'product_uom': parts_line.parts_uom.id,
            'location_id': order.parts_location_id.id,
            'location_dest_id': order.asset_ids[0].asset_id.property_stock_asset.id,
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
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        res = [(r['id'], r['name']+(r['model'] and ' '+r['model'] or '')  or r['name']  ) for r in self.read(cr, uid, ids, ['model','name'], context)]

        return res

    def name_search(self, cr, user, name='', args=None, operator='ilike',context=None, limit=100):
        if not args:
            args=[]
        if not context:
            context={}
        ids=[]
        ids = self.search(cr, user, ['|',('name', operator, name),('model', operator, name)] + args,limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context={}
        if 'order' in context and context['order']:
            order=context['order']

        return super(mro_tools, self).search(cr, uid, args, offset, limit, order, context, count)

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image, avoid_resize_medium=True)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    def _get_validity_3m(self,cr,uid,ids,field_name,arg,context=None):
        res={}
        for o in self.browse(cr,uid,ids,context):
            res[o.id]=False
            if o.date_validity_end and datetime.strptime(o.date_validity_end,'%Y-%m-%d')<=datetime.today()+relativedelta(months=3):
                res[o.id]=True
        return res

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
        'date_validity_3m':fields.function(_get_validity_3m,type='boolean',string='Validity end in 3 months'),
        'purchase_value':fields.float('Purchase value',digits_compute=dp.get_precision('Product Price')),
        'tools_place':fields.selection(selection=TOOLS_PLACE,string='Place'),
        'booking_ids':fields.one2many('mro.tools.booking','tools_id',string='Booking'),
        'inventory_num':fields.char(u'Inventory number')

    }

    _order='name asc'
    _defaults = {
        'active': True,
        'tools_place':'movable',
    }
    
class generic_assets(osv.osv):
    _name = 'generic.assets'
    _description = 'Generic Assets'
    
    def _get_date(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        done=[]
        other=[]
        for id in ids:
            res[id] = {'date_previous': False, 'date_next': False}
        if not ids:
            return res
        assets = self.browse(cr,uid,ids,context=context)
        for asset in assets:
            if asset.contract_id.mro_order_ids:
                for order in asset.contract_id.mro_order_ids:
                    if order.state == 'done':
                        done.append(order.date_execution)
                    else:
                        other.append(order.date_execution)
                if done:
                    res[asset.id]['date_previous'] = done[-1]
                if other:
                    res[asset.id]['date_next'] = other[0]
        return res
    
    _columns = {
        'name': fields.char('Description', size=128),
        'date_start': fields.date('Date start'),
        'date_end': fields.date('Date end'),
        'date_previous': fields.function(_get_date, string='Previous maintenance date', type='datetime',multi="previous_next_date"),
        'date_next': fields.function(_get_date, string='Next maintenance date', type='datetime',multi="previous_next_date"),
        'asset_id': fields.many2one('product.product', 'Asset', required=True, ondelete='set null'),
        'contract_id': fields.many2one('account.analytic.account', 'Contract', select=True, ondelete='set null'),
        'partner_id': fields.many2one('res.partner', 'Partner', select=True, ondelete='set null'),
        'service_id': fields.many2one('account.analytic.services', 'Contract service', select=True),
        'mro_id': fields.many2many('mro.order', string='MRO Order'),
        'serial_id': fields.many2one('product.serial', 'Serial #', select=True),
        'default_code': fields.related('asset_id','default_code',string='Reference',type='char',readonly=True),
        'loan': fields.boolean('Loan'),
    }
    
    _defaults = {
    }
    
    _sql_constraints = [
                     ('name_unique', 
                      'unique(asset_id,serial_id,partner_id)',
                      'Serial number must be unique per product and per partner')
    ]
    
    def _check_date(self, cr, uid, ids, context=None):
        
        for asset in self.browse(cr,uid,ids,context=context):
            if asset.serial_id and asset.date_start and asset.date_end:
                cr.execute('select id,partner_id,date_start,date_end from generic_assets \
                            where asset_id=%s \
                            and serial_id=%s \
                            and (%s between date_start and date_end or %s between date_start and date_end)',(asset.asset_id.id,asset.serial_id.id,asset.date_start,asset.date_end))
                fetchall = cr.fetchall()
                partner_ids = filter(None, map(lambda x:x[1], fetchall))
                dates = [(x[2], x[3]) for x in fetchall]
                if len(partner_ids)>1:
                    partner_name=self.pool.get('res.partner').read(cr,uid,partner_ids[0],['name'])
                    raise osv.except_osv(_('Error!'),
                        _("This asset already belongs to this partner for this period: %s. \n From %s to %s") % \
                            (partner_name['name'],dates[0][0],dates[0][1]) )
        return True

    _constraints = [
        (_check_date, 'Check assets dates.', ['date_start','date_end']),
    ]
    
    def onchange_asset(self, cr, uid, ids, product, context=None):
        context = context or {}
        result = {}
        product_obj = self.pool.get('product.product')
        prod = product_obj.browse(cr, uid, product, context=context)
        result['name'] = self.pool.get('product.product').name_get(cr, uid, [prod.id], context=context)[0][1]
        return {'value': result}
class mro_tools_booking(osv.osv):
    _name='mro.tools.booking'
    _description = 'Booking for tools'
    _inherit = ['mail.thread']



    def get_tech_name(self,cr,uid,ids,field_name,arg,context=None):
        res={}
        for o in self.browse(cr,uid,ids,context):
            res[o.id]='N/A'
            if o.calibration_booking:
                res[o.id]=_('IN CALIBRATION')
            elif o.technician_id:
                res[o.id]=o.technician_id.name
        return res

    _columns={
        'name':fields.function(get_tech_name,type='char',string='Name'),
        'tools_id':fields.many2one('mro.tools','Tool',select=True),
        'technician_id': fields.many2one('hr.employee','Technician',select=True),
        'calibration_booking':fields.boolean('Calibration booking'),
        'date_booking_begin':fields.date('Booking date begin'),
        'date_booking_end':fields.date('Booking date end'),
        'booking_comment':fields.text('Comment'),
    }
    def check_tools_available(self,cr,uid,id,tools_id,date_booking_begin,date_booking_end,context=None):
        if tools_id and date_booking_begin and date_booking_end:
            plus=''
            if id:
                plus="AND id<>%s" % (id[0])
            cr.execute("""
                SELECT id 
                FROM   mro_tools_booking
                WHERE tools_id=%s and (date_booking_begin, date_booking_end) OVERLAPS (TIMESTAMP '%s', TIMESTAMP '%s')
                 %s
            """ %(tools_id,date_booking_begin,date_booking_end,plus))
            res=cr.fetchall()
            if res and len(res)>0:
                return False
        return True
    ############################################################################
    # on_change
    ############################################################################
    def onchange_tools_id(self,cr,uid,id,tools_id,date_booking_begin,date_booking_end,context=None):
        value={}
        warning={}
        if tools_id and date_booking_begin and date_booking_end:
            #check if tools is available betwen date begin and date end
            res=self.check_tools_available(cr,uid,id,tools_id,date_booking_begin,date_booking_end,context)
            if not res:
                warning={'title':u'Warning !!','message':u'Tools not available for this dates'}
                value={'tools_id':False}

        return {'value':value,'warning':warning}
    def onchange_booking_begin(self,cr,uid,id,date_booking_begin,context=None):
        value={'date_booking_end':False}
        if date_booking_begin:
            dt=datetime.strptime(date_booking_begin, '%Y-%m-%d')+relativedelta(days=4)
            value['date_booking_end']=dt.strftime('%Y-%m-%d')
        return {'value':value}
    def onchange_booking(self,cr,uid,id,tools_id,date_booking_begin,date_booking_end,context=None):
        value={}
        warning={}
        if tools_id and date_booking_begin and date_booking_end:
            #check if tools is available betwen date begin and date end
            res=self.check_tools_available(cr,uid,id,tools_id,date_booking_begin,date_booking_end,context)
            if not res:
                warning={'title':u'Warning !!','message':u'Tools not available for this dates'}
                value={'date_booking_begin':False,'date_booking_end':False}

        return {'value':value,'warning':warning}
