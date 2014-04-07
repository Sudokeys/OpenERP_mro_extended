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

{
    'name': 'MRO Extended',
    'version': '1.0',
    'summary': 'Asset Maintenance, Repair and Operation with added features',
    'description': """
Added Features
-------------
    

Required modules:
    * mro
    """,
    'author': 'ADN France',
    'website': 'http://adn-france.com',
    'category': 'Enterprise Asset Management',
    'sequence': 150,
    'depends': ['base','mro','mro_pm','hr','account_analytic_analysis','portal_project_issue'],
    'demo': [],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_make_mro_view.xml',
        'wizard/sale_make_contract_view.xml',
        'wizard/refuse_amendment_view.xml',
        'wizard/create_amendment_view.xml',
        'wizard/cancelled_contract_view.xml',
        'report/tools_planning_print.xml',
        'mro_extended_view.xml',
        'mro_extended_workflow.xml',
        'res_partner_view.xml',
        'sale_view.xml',
        'analytic_view.xml',
        'product_view.xml',
        'product_data.xml',
        'wizard/tools_planning_wiz_view.xml',
        'ir_cron_data.xml',

    ],
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
