# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 ADN France (<http://adn-france.com>).
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
#import datetime
import calendar
from datetime import date,datetime,timedelta
from calendar import Calendar
from openerp.osv import fields, osv
from openerp.tools.translate import _
from report import report_sxw
import logging
_logger = logging.getLogger(__name__)



def get_week_month(days,year,month):
    cal = calendar.Calendar(calendar.MONDAY)
    mfirst_day="%s-%s-01" % (year,month)
    dt=datetime.strptime(mfirst_day,'%Y-%m-%d')
    dteweeks=cal.monthdatescalendar(dt.year, dt.month)
    weeks=[]
    for i in dteweeks:
        weeks.append([i[0].strftime('%Y-%m-%d'),i[6].strftime('%Y-%m-%d')])
    if len(weeks)<6:
        for i in range(len(weeks),6):
            weeks.append([False,False])
    return weeks

def get_week_days(year, week):
    d = date(year,1,1)
    if(d.weekday()>3):
        d = d+timedelta(7-d.weekday())
    else:
        d = d - timedelta(d.weekday())
    dlt = timedelta(days = (week-1)*7)
    return d + dlt,  d + dlt + timedelta(days=6)

class tools_planning_month_print(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(tools_planning_month_print, self).__init__(cr, uid, name, context)
        _logger.info(u'Start printing monthly planning of tools')
        self.months=[]
        self.var_month=False
        self.weeks=[]
        self.planning=[]
        self.localcontext.update({
            'time': time,
            'set_months':self.set_months,
            'get_months':self.get_months,
            'set_weeks':self.set_weeks,
            'get_weeks':self.get_weeks,
            'set_planning':self.set_planning,
            'get_planning':self.get_planning,
            'get_periode':self.get_periode,
        })

    def set_months(self,form):
        #print 'je passe dans set_months====================>'
        if form['type']=='annual':
            self.months=[]
            for i  in range(1,13):
                self.months.append(str(i).zfill(2))
        elif form['type']=='monthly' and form['months']:
            self.months.append(form['months'])
        #print 'self.month: ',self.months
        self.var_month=0
        return self.months

    def get_months(self):
        #print 'je passe dans get_months====================>'
        return self.months

    def get_periode(self):
        return str(self.var_month+1).zfill(2)
    def set_weeks(self,data):

        if data['year']:
            days=calendar.monthrange(int(data['year']),int(self.months[self.var_month]))
            self.weeks=get_week_month(days,data['year'],self.months[self.var_month])
        return ''
    def get_weeks(self):
        return self.weeks
    def set_planning(self,form):
        _mro_tools=self.pool.get('mro.tools')
        _tools_booking=self.pool.get('mro.tools.booking')
        rech=[]
        if form['tools_id']:
            rech=[('id','=',form['tools_id'][0])]
        tools_ids=_mro_tools.search(self.cr,self.uid,rech)
        planning=[]
        if tools_ids:
            for tools in _mro_tools.browse(self.cr,self.uid,tools_ids):
                tools_week=[tools,[]]
                for week in self.weeks:
                    book_week=False
                    booking_id=_tools_booking.search(self.cr,self.uid,[('tools_id','=',tools.id),
                                                                       ('date_booking_begin','>=',week[0]),
                                                                       ('date_booking_end','<=',week[1])])
                    for book in _tools_booking.browse(self.cr,self.uid,booking_id):
                        book_week=book
                    tools_week[1].append(book_week)
                planning.append(tools_week)
        #print 'planning: ', planning
        self.planning=planning
        return ''
    def get_planning(self,form):
        _logger.info(u'End printing monthly planning of tools periode %s' % (str(self.var_month+1).zfill(2)) )
        if self.var_month+1<len(self.months):
            self.var_month+=1

        return self.planning

report_sxw.report_sxw('report.tools_planning_month_print',
    'mro.tools.booking',
    'addons/sudokeys_mro_extended/report/tools_planning_month.rml',
    parser=tools_planning_month_print) #,header=''


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
