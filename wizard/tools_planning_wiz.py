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
import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from mro_extended import analytic

class tools_planning_wiz(osv.osv_memory):
    _name='tools.planning.wiz'
    _description='Wizard for printing tools booking planning '
    def _get_year(self,cr,uid,context={}):
        today = datetime.date.today()
        annee = int(today.year);
        retour=[]
        retour.append( ('%s' % (annee-1),'%s' % (annee-1)) )
        retour.append( ('%s' % (annee),'%s' % (annee)) )
        retour.append( ('%s' % (annee+1),'%s' % (annee+1)) )
        return retour
    def _get_months(self,cr,uid,context=None):
        retour=[('01','january'),('02','february'),('03','march'),('04','april'),
        ('05','may'),('06','june'),('07','july'),('08','august'),('09','september'),
        ('10','october'),('11','november'),('12','december')]
        return retour
    _columns={
        'type':fields.selection([('annual','Annual'),('monthly','Monthly')],u'Type',required=True),
        #'months':fields.selection(_get_months,u'Month'),
        'months': fields.selection(analytic.months.items(), 'Month'),
        'year':fields.selection(_get_year,'Year',required=True),
        'tools_id':fields.many2one('mro.tools',u'Tools'),
    }

    _defaults={
        'type':'monthly',
        'year':str(int(datetime.date.today().year)),
    }




    def do_print(self,cr,uid,ids,context=None):
        data=self.read(cr,uid,ids,[],context)[0]
        mois=False
        if data['type']=='monthly' and data['months']:
            data['months']=str(data['months']).zfill(2)

        datas={
        'form':data

        }
        if data['type']=='annual':
            report={
                'type': 'ir.actions.report.xml',
                'report_name': 'tools_planning_month_print',
                'datas': datas
            }
        else:
            report={
                'type': 'ir.actions.report.xml',
                'report_name': 'tools_planning_month_print',
                'datas': datas
            }
        print 'report: ', report
        return report
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
