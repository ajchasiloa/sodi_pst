from odoo import models, api, _
from odoo.exceptions import UserError

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """Sobreescribir la validación estándar para permitir importaciones sin restricciones"""
        if self.env.context.get('import_file'):
            return True
        
        return super(HrAttendance, self)._check_validity()

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity_check_in_check_out(self):
        """Sobreescribir la validación de check_in/check_out para permitir importaciones sin restricciones"""
        if self.env.context.get('import_file'):
            return True
            
        return super(HrAttendance, self)._check_validity_check_in_check_out()

    def _check_open_attendance(self):
        if self.env.context.get('import_file'):
            return True
        return super(HrAttendance, self)._check_open_attendance()
