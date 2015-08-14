# -*- coding: utf-8 -*-

##############################################################################
#
#    Technician module for OpenERP, Description
#    Copyright (C) 200X Company (<http://website>) author
#
#    This file is a part of Technician
#
#    Technician is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Technician is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, fields


class HrEmployee(osv.osv):
    _inherit = 'hr.employee'

    _columns = {
        'date_start': fields.date(u'Date Début', help=u'Date de début'),
        'date_end': fields.date(u'Date de fin', help='Date de fin'),
        'preuve_ids': fields.one2many('ir.attachement', 'employee_id', 'Preuve'),
    }

HrEmployee()
