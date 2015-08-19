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
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import parser
from dateutil import rrule
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools, SUPERUSER_ID
import re
import logging

_logger = logging.getLogger(__name__)

months = {
    1: "January", 2: "February", 3: "March", 4: "April", \
    5: "May", 6: "June", 7: "July", 8: "August", 9: "September", \
    10: "October", 11: "November", 12: "December"
}

def get_recurrent_dates(rrulestring, exdate, startdate=None, exrule=None):
    """
    Get recurrent dates based on Rule string considering exdate and start date.
    @param rrulestring: rulestring
    @param exdate: list of exception dates for rrule
    @param startdate: startdate for computing recurrent dates
    @return: list of Recurrent dates
    """
    def todate(date):
        val = parser.parse(''.join((re.compile('\d')).findall(date)))
        return val

    if not startdate:
        startdate = datetime.now()

    if not exdate:
        exdate = []

    rset1 = rrule.rrulestr(str(rrulestring), dtstart=startdate, forceset=True)
    for date in exdate:
        datetime_obj = todate(date)
        rset1._exdate.append(datetime_obj)

    if exrule:
        rset1.exrule(rrule.rrulestr(str(exrule), dtstart=startdate))

    return list(rset1)

class account_analytic_account(osv.osv):
    _inherit = 'account.analytic.account'

    def create(self, cr, uid, vals, context=None):
        _logger.info("=======uid = %s =======" % uid)
        users = self.pool.get('res.users').browse(cr, uid, [uid], context)
        for user in users:
            if vals.get('name','Name')=='Name':
                if user.trigramme:
                    vals['name'] = user.trigramme
                else:
                    vals['name'] = user.name[:3]
                vals['name'] += self.pool.get('ir.sequence').get(cr,uid,'account.analytic.account.name') or 'Name'
                _logger.info("====vals['name'] = %s ====" % vals['name'])
        serial_id = super(account_analytic_account, self).create(cr, uid, vals, context)
        return serial_id

    def set_open(self, cr, uid, ids, context=None):
        states = self.browse(cr,uid,ids,context)
        for st in states:
            if st.state=='close':
                self.write(cr,uid,ids,{'state':'draft'},context=context)
            else:
                res = super(account_analytic_account, self).set_open(cr,uid,ids,context=context)

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        if context.get('show_ref'):
            rec_name = 'ref'
        else:
            rec_name = 'name'

        res = [(r['id'], r[rec_name]+(r['code'] and ' '+r['code'] or '')  or r[rec_name]  ) for r in self.read(cr, uid, ids, ['code',rec_name], context)]

        return res

    def _get_rulestring(self, cr, uid, ids, name, arg, context=None):
        """
        Gets Recurrence rule string according to value type RECUR of iCalendar from the values given.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param id: List of calendar event's ids.
        @param context: A standard dictionary for contextual values
        @return: dictionary of rrule value.
        """

        result = {}
        if not isinstance(ids, list):
            ids = [ids]

        for id in ids:
            #read these fields as SUPERUSER because if the record is private a normal search could return False and raise an error
            data = self.read(cr, SUPERUSER_ID, id, ['interval', 'count'], context=context)
            if data.get('interval', 0) < 0:
                raise osv.except_osv(_('Warning!'), _('Interval cannot be negative.'))
            if data.get('count', 0) <= 0:
                raise osv.except_osv(_('Warning!'), _('Count cannot be negative or 0.'))
            data = self.read(cr, uid, id, ['id','byday','recurrency', 'month_list','end_date', 'rrule_type', 'select1', 'interval', 'count', 'end_type', 'mo', 'tu', 'we', 'th', 'fr', 'sa', 'su', 'exrule', 'day', 'week_list' ], context=context)
            event = data['id']
            if data['recurrency']:
                result[event] = self.compute_rule_string(data)
            else:
                result[event] = ""
        return result

    def _rrule_write(self, obj, cr, uid, ids, field_name, field_value, args, context=None):
        data = self._get_empty_rrule_data()
        if field_value:
            data['recurrency'] = True
            for event in self.browse(cr, uid, ids, context=context):
                rdate = rule_date or event.date
                update_data = self._parse_rrule(field_value, dict(data), rdate)
                data.update(update_data)
                super(calendar_event, obj).write(cr, uid, ids, data, context=context)
        return True

    def _get_amendment(self, cr, uid, ids, name, arg, context=None):
        result = {}
        if not isinstance(ids, list):
            ids = [ids]

        for id in ids:
            #read these fields as SUPERUSER because if the record is private a normal search could return False and raise an error
            data = self.read(cr, SUPERUSER_ID, id, ['amendment_ids'], context=context)
            result[id]=False
            if data.get('amendment_ids', False):
                for amendment in data['amendment_ids']:
                    amend_data = self.pool.get('account.analytic.amendments').read(cr,uid,amendment,['state'],context=context)
                    if amend_data['state'] == 'draft':
                        result[id]=True
        return result

    def _get_amendment_search(self, cr, uid, obj, name, domain, context=None):
        res=[]
        ids=self.search(cr,uid,[],context=context)
        for contract in self.browse(cr,uid,ids,context=context):
            for amend in contract.amendment_ids:
                if amend.state=='draft':
                    res.append(contract.id)
        return [('id','in',res)]

    def _amount_service(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for contract in self.browse(cr, uid, ids, context=context):
            res[contract.id] = 0.0
            val = 0.0
            for line in contract.service_ids:
                val += line.price
            res[contract.id] = val
        return res

    def _get_contract(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.analytic.services').browse(cr, uid, ids, context=context):
            result[line.contract_id.id] = True
        return result.keys()

    def _amount_marge(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        _oproduct=self.pool.get('product.product')
        for contract in self.browse(cr, uid, ids, context=context):
            remise=contract.remise/100
            res[contract.id] = 0.0
            val = 0.0
            tpv=0.0
            tp=0.0
            i=0
            for line in contract.service_ids:
                #p=_oproduct.read(cr,uid,[line.service_id.id],['standard_price'])[0]['standard_price']
                p=line.standard_price
                if p>0 and line.price>0:
                    pv = line.price-(line.price*remise)
                    #if line.service_id.id==34054 : p=100.00
                    tpv +=pv
                    tp +=p
                    i+=1
            if i>0 :
                #val=(tpv-tp)/tp
                val=(tpv-tp)/tpv
                res[contract.id] = val*100
            else : 0.0
        return res

    _columns = {
        'mro_order_ids': fields.one2many('mro.order','contract_id','Maintenance Orders'),
        'asset_ids': fields.many2many('generic.assets',string='Assets',readonly=True),
        'service_ids': fields.one2many('account.analytic.services','contract_id','Contract services'),
        'amendment_ids': fields.one2many('account.analytic.amendments','contract_id','Amendments',readonly=True),
        'amendment': fields.function(_get_amendment, fnct_search=_get_amendment_search, type='boolean', string='Amendment not accepted'),
        'date_refused': fields.date('Refused Date'),
        'date_wished': fields.date('Wished Date'),
        'note_intern': fields.text('description'),
        'maintenance_date_start': fields.datetime('Maintenance date start'),
        'maintenance_date_end': fields.datetime('Maintenance date end'),
        'exdate': fields.text('Exception Date/Times', help="This property \
        defines the list of date/time exceptions for a recurring calendar component."),
        'exrule': fields.char('Exception Rule', size=352, help="Defines a \
        rule or repeating pattern of time to exclude from the recurring rule."),
        'rrule': fields.function(_get_rulestring, type='char', size=124, \
                    fnct_inv=_rrule_write, store=True, string='Recurrent Rule'),
        'rrule_type': fields.selection([
            ('daily', 'Day(s)'),
            ('weekly', 'Week(s)'),
            ('monthly', 'Month(s)'),
            ('yearly', 'Year(s)')
            ], 'Recurrency', states={'done': [('readonly', True)]},
            help="Let the event automatically repeat at that interval"),
        'end_type' : fields.selection([('count', 'Number of repetitions'), ('end_date','End date')], 'Recurrence Termination'),
        'interval': fields.integer('Repeat Every', help="Repeat every (Days/Week/Month/Year)"),
        'count': fields.integer('Repeat', help="Repeat x times"),
        'mo': fields.boolean('Mon'),
        'tu': fields.boolean('Tue'),
        'we': fields.boolean('Wed'),
        'th': fields.boolean('Thu'),
        'fr': fields.boolean('Fri'),
        'sa': fields.boolean('Sat'),
        'su': fields.boolean('Sun'),
        'select1': fields.selection([('date', 'Date of month'),
                                    ('day', 'Day of month')], 'Option'),
        'day': fields.integer('Date of month'),
        'week_list': fields.selection([
            ('MO', 'Monday'),
            ('TU', 'Tuesday'),
            ('WE', 'Wednesday'),
            ('TH', 'Thursday'),
            ('FR', 'Friday'),
            ('SA', 'Saturday'),
            ('SU', 'Sunday')], 'Weekday'),
        'byday': fields.selection([
            ('1', 'First'),
            ('2', 'Second'),
            ('3', 'Third'),
            ('4', 'Fourth'),
            ('5', 'Fifth'),
            ('-1', 'Last')], 'By day'),
        'month_list': fields.selection(months.items(), 'Month'),
        'end_date': fields.date('Repeat Until'),
        'recurrency': fields.boolean('Recurrency', help="Recurrency"),
        'loan': fields.boolean('Loan'),
        'amount_service': fields.function(_amount_service, digits_compute=dp.get_precision('Account'), string='Montant total',
            store={
                'account.analytic.account': (lambda self, cr, uid, ids, c={}: ids, ['service_ids'], 10),
               'account.analytic.services': (_get_contract, ['price'], 10),
            },
            type='float',track_visibility='always'),
        # 'state': fields.selection([('template', 'Template'),('draft','New'),('open','In Progress'),('pending','To Renew'),('close','Closed'),('cancelled', 'Cancelled')], 'Status', required=True, track_visibility='onchange'),
        'state': fields.selection([('draft','Draft'),('open','In Progress'),('pending','To Renew'),('refuse','Refused'),('close','Closed'),('cancelled', 'Cancelled')], 'Status', required=True, track_visibility='onchange'),

        'remise': fields.float('Remise en %'),
        'marge': fields.function(_amount_marge, digits_compute=dp.get_precision('Account'), string='Marge en %',
            type='float',track_visibility='always'),
        'order_number':fields.char(u'N° de commande'),
        'date_invoice': fields.date('Date de facture'),
        'invoice_number': fields.char(u'N° de facture'),

   }

    _defaults = {
        'state':'draft',
        'date': lambda *a: (datetime.strptime(time.strftime('%Y-%m-%d'),'%Y-%m-%d')+relativedelta(years=1)).strftime('%Y-%m-%d'),
        'end_date': lambda *a: (datetime.strptime(time.strftime('%Y-%m-%d'),'%Y-%m-%d')+relativedelta(years=1)).strftime('%Y-%m-%d'),
        'end_type': 'end_date',
        'count': 1,
        'rrule_type': 'yearly',
        'select1': 'date',
        'interval': 1,
        'recurrency': True,
        'name': 'Name',
    }

    def search(self,cr,uid, args, offset=0, limit=0, order=None, context=None, count=False):
        if context:
            if 'order' in context.keys():
                order=context.get('order')
        return super(account_analytic_account, self).search(cr, uid, args, offset, limit, order, context, count=False)

    def on_change_partner_id(self, cr, uid, ids,partner_id, name, context={}):
        res={}
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            if partner.user_id:
                res['manager_id'] = partner.user_id.id
            if not name:
                res['name'] = _('Contract: ') + partner.name
            res['asset_ids']=[]
            #~ for asset in partner.asset_ids:
                #~ if ids:
                    #~ exist_ids=self.pool.get('generic.assets').search(cr,uid,[('asset_id','=',asset.id),('contract_id','=',ids[0])])
                    #~ if exist_ids:
                        #~ continue
                #~ res['asset_ids'].append(self.pool.get('generic.assets').create(cr,uid,{'asset_id':asset.id}))

        return {'value': res}

    def on_change_end_date(self, cr, uid, ids,date, context={}):
        res={}
        if date:
            res['end_date']=date
        return {'value': res}

    def get_recurrency(self, cr, uid, ids, context=None):
        mro_obj = self.pool.get('mro.order')
        result=[]
        res={}
        contracts=self.browse(cr,uid,ids,context)
        #~ for data in self.read(cr, uid, ids, ['rrule', 'exdate', 'exrule', 'date_start'], context=context):
        for c in contracts:
            mro_obj.unlink(cr,uid,[x.id for x in c.mro_order_ids if x.state == 'draft'],context=context)

        for data in contracts:
            #Technician mandatory
            if not data.partner_id.technician:
                raise osv.except_osv(_('Error!'), _("Please link a technician in the partner."))

            if not data.rrule:
                result.append(data.id)
                continue
            if data.date_wished:
                event_date = datetime.strptime(data.date_wished, "%Y-%m-%d")
            else:
                event_date = datetime.strptime(data.date_start, "%Y-%m-%d")


            # TOCHECK: the start date should be replaced by event date; the event date will be changed by that of calendar code

            if not data.rrule:
                continue

            exdate = data.exdate and data.exdate.split(',') or []
            rrule_str = data.rrule
            new_rrule_str = []
            rrule_until_date = False
            is_until = False
            for rule in rrule_str.split(';'):
                name, value = rule.split('=')
                if name == "UNTIL":
                    is_until = True
                    value = parser.parse(value)
                    rrule_until_date = parser.parse(value.strftime("%Y-%m-%d 00:00:00"))
                    value = value.strftime("%Y%m%d000000")
                new_rule = '%s=%s' % (name, value)
                new_rrule_str.append(new_rule)
            new_rrule_str = ';'.join(new_rrule_str)
            rdates = get_recurrent_dates(str(new_rrule_str), exdate, event_date, data.exrule)
            for r_date in rdates:
                vals = {
                    #~ 'origin': sale.name,
                    #~ 'order_id': sale.id,
                    'contract_id': data.id,
                    'partner_id': data.partner_id.id,
                    'technician': data.partner_id.technician and data.partner_id.technician.id or False,
                    'description': '',
                    'origin': data.code,
                    'asset_ids': [(6,0,[x.id for x in data.asset_ids])],
                    'maintenance_type': 'm12',
                    'date_planned': r_date.strftime("%Y-%m-%d %H:%M:%S"),
                    'date_scheduled': r_date.strftime("%Y-%m-%d %H:%M:%S"),
                    'date_execution': r_date.strftime("%Y-%m-%d %H:%M:%S"),
                    #~ 'duration': make.duration,
                }
                mro_id=mro_obj.create(cr, uid, vals, context=context)
                mro_read=mro_obj.read(cr,uid,mro_id,['name'],context=context)
                mro_obj.write(cr,uid,mro_id,{'description': '%s - %s' % (data.name or '',mro_read['name'])},context=context)
        return res

    def compute_rule_string(self, data):
        """
        Compute rule string according to value type RECUR of iCalendar from the values given.
        @param self: the object pointer
        @param data: dictionary of freq and interval value
        @return: string containing recurring rule (empty if no rule)
        """
        def get_week_string(freq, data):
            weekdays = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
            if freq == 'weekly':
                byday = map(lambda x: x.upper(), filter(lambda x: data.get(x) and x in weekdays, data))
                if byday:
                    return ';BYDAY=' + ','.join(byday)
            return ''

        def get_month_string(freq, data):
            if freq == 'monthly':
                if data.get('select1')=='date' and (data.get('day') < 1 or data.get('day') > 31):
                    raise osv.except_osv(_('Error!'), ("Please select a proper day of the month."))

                if data.get('select1')=='day':
                    return ';BYDAY=' + data.get('byday') + data.get('week_list')
                elif data.get('select1')=='date':
                    return ';BYMONTHDAY=' + str(data.get('day'))
            return ''

        def get_end_date(data):
            if data.get('end_date'):
                data['end_date_new'] = ''.join((re.compile('\d')).findall(data.get('end_date'))) + 'T235959Z'

            return (data.get('end_type') == 'count' and (';COUNT=' + str(data.get('count'))) or '') +\
                             ((data.get('end_date_new') and data.get('end_type') == 'end_date' and (';UNTIL=' + data.get('end_date_new'))) or '')

        freq = data.get('rrule_type', False)
        res = ''
        if freq:
            interval_srting = data.get('interval') and (';INTERVAL=' + str(data.get('interval'))) or ''
            res = 'FREQ=' + freq.upper() + get_week_string(freq, data) + interval_srting + get_end_date(data) + get_month_string(freq, data)

        return res

    def _get_empty_rrule_data(self):
        return  {
            'byday' : False,
            'recurrency' : False,
            'end_date' : False,
            'rrule_type' : False,
            'select1' : False,
            'interval' : 0,
            'count' : False,
            'end_type' : False,
            'mo' : False,
            'tu' : False,
            'we' : False,
            'th' : False,
            'fr' : False,
            'sa' : False,
            'su' : False,
            'exrule' : False,
            'day' : False,
            'week_list' : False
        }

    def _parse_rrule(self, rule, data, date_start):
        day_list = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        rrule_type = ['yearly', 'monthly', 'weekly', 'daily']
        r = rrule.rrulestr(rule, dtstart=datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S"))

        if r._freq > 0 and r._freq < 4:
            data['rrule_type'] = rrule_type[r._freq]

        data['count'] = r._count
        data['interval'] = r._interval
        data['end_date'] = r._until and r._until.strftime("%Y-%m-%d %H:%M:%S")
        #repeat weekly
        if r._byweekday:
            for i in xrange(0,7):
                if i in r._byweekday:
                    data[day_list[i]] = True
            data['rrule_type'] = 'weekly'
        #repeat monthly by nweekday ((weekday, weeknumber), )
        if r._bynweekday:
            data['week_list'] = day_list[r._bynweekday[0][0]].upper()
            data['byday'] = r._bynweekday[0][1]
            data['select1'] = 'day'
            data['rrule_type'] = 'monthly'

        if r._bymonthday:
            data['day'] = r._bymonthday[0]
            data['select1'] = 'date'
            data['rrule_type'] = 'monthly'

        #repeat yearly but for openerp it's monthly, take same information as monthly but interval is 12 times
        if r._bymonth:
            data['interval'] = data['interval'] * 12

        #FIXEME handle forever case
        #end of recurrence
        #in case of repeat for ever that we do not support right now
        if not (data.get('count') or data.get('end_date')):
            data['count'] = 100
        if data.get('count'):
            data['end_type'] = 'count'
        else:
            data['end_type'] = 'end_date'
        return data

    def alert_fin_contrat(self, cr, uid, typedelai='days',delai=15):
        context = {}
        if typedelai=='days' : datem15= datetime.now() + timedelta(days=delai)
        if typedelai=='months' :
            delai = delai*30
            datem15= datetime.now() + timedelta(days=delai)
        datedeb=datetime.strftime(datem15, "%Y-%m-%d")+' 00:00:00'
        datefin=datetime.strftime(datem15, "%Y-%m-%d")+' 23:59:59'
        ids=self.pool.get('account.analytic.account').search(cr, uid, [('date','>=',datedeb),('date','<=',datefin),('date_start','!=',False),('partner_id','!=',False),('date','!=',False),('state','=','open')])
        self.pool.get('account.analytic.account').write(cr, uid,ids,{'state':'pending'},context)
        res=[]
        res1=[]
        for i in self.browse(cr, uid, ids, context):
            for j in i.message_follower_ids:
                res.append(j.id)
            for k in i.message_ids:
                res1.append(k.id)

            if not self.pool.get('mail.message').search(cr,uid,[
                                                            ('body','ilike','&lt;p&gt;Ce contrat sera expiré dans 2 semaines.&lt;/p&gt;'),
                                                            ('res_id','=',i.id)]):
                create_id=self.pool.get('mail.message').create(cr, uid, {
                                                                    'partner_ids':[i.manager_id.id],
                                                                    'body':u'Ce contrat sera expiré dans 2 semaines. Veuillez vous rapprocher du client afin de lui proposer un avenant de reconduction.',
                                                                    'res_id':i.id,
                                                                    'model':'account.analytic.account',
                                                                    'record_name':i.name},context)


class account_analytic_services(osv.osv):
    _name = 'account.analytic.services'
    _description = 'Contract services'

    _columns = {
        'name': fields.char('Description', size=128),
        'price': fields.float('Price'),
        'service_id': fields.many2one('product.product', 'Contract service', required=True),
        'contract_id': fields.many2one('account.analytic.account', 'Contract', select=True),
        'asset_id': fields.many2one('generic.assets','Asset', select=True),
        'standard_price': fields.float('Standard price'),
        'discount': fields.float('Discount %'),
        'quantity': fields.integer('Quantity'),
        'total': fields.float('Total'),
    }

    _defaults = {
        'quantity': 1,
    }

    def write(self, cr, uid, ids, vals, context=None):
        if 'quantity' in vals:
            if vals['quantity'] > 1:
                vals['asset_id'] = False
        write_id = super(account_analytic_services, self).write(cr, uid, ids, vals, context)
        return write_id


    def onchange_quantity(self, cr, uid, ids, standard_price, price, quantity, discount, asset_id, context=None):
        result = {}
        if quantity > 1:
            result['asset_id'] = False
        if discount and discount != 0:
            result['total'] = price * quantity
        else:
            result['total'] = standard_price * quantity
        return {'value': result}

    def onchange_discount(self, cr, uid, ids, discount, standard_price, context=None):
        result = {}
        remise =  (standard_price * discount) / 100
        result['price'] = standard_price - remise
        return {'value':result}

    def onchange_service(self, cr, uid, ids, product, context=None):
        context = context or {}
        result = {}
        product_obj = self.pool.get('product.product')
        product_obj = product_obj.browse(cr, uid, product, context=context)
        result['standard_price'] = product_obj.standard_price
        result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context)[0][1]
        return {'value': result}

    def create(self, cr, uid, vals, context=None):
        service_id = super(account_analytic_services, self).create(cr, uid, vals, context)
        if 'quantity' in vals:
            if vals['quantity'] > 1:
                vals['asset_id'] = False
        if 'asset_id' in vals:
            asset_obj = self.pool.get('generic.assets')
            if vals['asset_id']:
                asset_obj.write(cr,uid,vals['asset_id'],{'service_id':service_id})
            else:
                asset_ids = asset_obj.search(cr,uid,[('service_id','=',service_id)])
                for asset_id in asset_ids:
                    asset_obj.write(cr,uid,vals['asset_id'],{'service_id':False})
        return service_id

    def onchange_asset(self, cr, uid, ids, asset, context=None):
        context = context or {}
        result = {}
        asset_obj = self.pool.get('generic.assets')
        if ids:
            if asset:
                asset_obj.write(cr,uid,asset,{'service_id':ids[0]})
            else:
                asset_ids = asset_obj.search(cr,uid,[('service_id','=',ids[0])])
                for asset_id in asset_ids:
                    asset_obj.write(cr,uid,asset_id,{'service_id':False})
        return {'value': result}

class services_assets(osv.osv):

    _name = "services.assets"
    _description = "Contract services / Assets"



    _columns = {
        'service_id': fields.many2one('product.product', 'Contract service', required=True),
        'service_real_id': fields.many2one('account.analytic.services', 'Contract service real id'),
        'asset_id': fields.many2one('product.product', 'Asset', required=True),
        'serial_id': fields.many2one('product.serial', 'Serial #', select=True),
        'price': fields.float('Price'),
        'amendment_id': fields.many2one('account.analytic.amendments', 'Amendment'),
        'move_type': fields.selection([('add','Add'),('remove','Remove'),('remain','Remain')],'Move type'),
        'standard_price': fields.float('Standard price'),

    }



class account_analytic_amendments(osv.osv):
    _name = 'account.analytic.amendments'
    _description = 'Contract amendments'

    def _amount_service(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for amend in self.browse(cr, uid, ids, context=context):
            res[amend.id] = 0.0
            val = 0.0
            for line in amend.service_asset_ids:
                val += line.price
            res[amend.id] = val
        return res


    _columns = {
        'name': fields.char('Description', size=128),
        'date': fields.date('Date'),
        'new_date_begin': fields.date('Date',readonly=True),
        'new_date_end': fields.date('Date',readonly=True),
        'price_rise': fields.float('Price Rise (%)'),
        'state': fields.selection([('draft','Draft'),('accepted','Accepted'),('refused','Refused')],'Status'),
        'contract_id': fields.many2one('account.analytic.account', 'Contract', select=True),
        'service_asset_ids': fields.one2many('services.assets','amendment_id','Contract services / Assets',readonly=True),
        'amount_service': fields.function(_amount_service, digits_compute=dp.get_precision('Account'), string='Montant total',type='float'),
        'order_number':fields.char(u'N° de commande'),
        'date_invoice': fields.date('Date de facture'),
        'invoice_number': fields.char(u'N° de facture'),
        'total': fields.float('Total'),
        'quantity':fields.integer('Quantity'),

    }

    _defaults = {
        'state': 'draft',
        'date': fields.date.context_today,
    }

    _order = 'id desc'

    def onchange_quantity(self, cr, uid, ids, price_rise, quantity, context=None):
        result = {}
        result['total'] = price * quantity
        return {'value': result}

    def button_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def button_accepted(self, cr, uid, ids, context=None):
        print 'context',context,ids
        contract_obj = self.pool.get('account.analytic.account')
        amendment_obj = self.pool.get('account.analytic.amendments')
        service_asset_obj = self.pool.get('services.assets')
        service_obj = self.pool.get('account.analytic.services')
        asset_obj = self.pool.get('generic.assets')
        amendments=amendment_obj.browse(cr,uid,ids,context=context)
        for amend in amendments:
            if amend.new_date_begin and amend.new_date_end:
                contract_obj.write(cr,uid,amend.contract_id.id,{'date_start':amend.new_date_begin,'date':amend.new_date_end})
            for s in amend.contract_id.service_ids:
                service_obj.write(cr,uid,s.id,{'price':s.price + (s.price*amend.price_rise)/100})
            for sa in amend.service_asset_ids:
                if sa.move_type=='remove':
                    service_obj.unlink(cr,uid,sa.service_real_id.id)
                    asset_obj.unlink(cr,uid,sa.service_real_id.asset_id.id)
                if sa.move_type=='add':
                    service_id=service_obj.create(cr,uid,{'service_id':sa.service_id.id,
                                                'name':sa.service_id.name,
                                                'price':sa.price,
                                                'contract_id':amend.contract_id.id,
                                                })
                    asset_id=asset_obj.create(cr,uid,{'service_id':service_id,
                                                'asset_id':sa.asset_id.id,
                                                'name':sa.asset_id.name,
                                                'serial_id':sa.serial_id and sa.serial_id.id or False,
                                                'contract_id':amend.contract_id.id,
                                                })
                    service_obj.write(cr,uid,service_id,{'asset_id':asset_id})
        return self.write(cr, uid, ids, {'state': 'accepted'}, context=context)

