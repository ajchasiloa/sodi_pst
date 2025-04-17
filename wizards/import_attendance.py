import base64
import binascii
import csv
import io
import tempfile
import xlrd
from odoo import fields, models
from odoo.exceptions import ValidationError


class ImportAttendance(models.TransientModel):
    _name = 'import.attendance'
    _description = 'Attendance Import'

    file_type = fields.Selection(
        selection=[('csv', 'CSV File'), ('xls', 'XLS File')],
        string='Select File Type', default='csv',
        help="It helps to select File Type")
    file_upload = fields.Binary(string="Upload File", help="It helps to upload files")

    def action_import_attendance(self):
        hr_employee = self.env['hr.employee']
        hr_attendance = self.env['hr.attendance']
        datas = {}

        if self.file_type == 'csv':
            try:
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                datas = csv.DictReader(data_file, delimiter=',')
            except:
                raise ValidationError("Invalid CSV file format.")

        if self.file_type == 'xls':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
            except:
                raise ValidationError("Invalid XLS file format.")

            headers = sheet.row_values(0)
            data = []
            for row_index in range(1, sheet.nrows):
                row = sheet.row_values(row_index)
                data += [{k: v for k, v in zip(headers, row)}]
            datas = data

        for item in datas:
            vals = {}
            employee = hr_employee.search([('name', '=', item.get('Employee'))])
            if not employee:
                raise ValidationError("No employee found: {}".format(item.get('Employee')))
            vals['employee_id'] = employee.id

            if item.get('Check In'):
                vals['check_in'] = item.get('Check In') if self.file_type == 'csv' else xlrd.xldate_as_datetime(item.get('Check In'), 0)
            if item.get('Check Out'):
                vals['check_out'] = item.get('Check Out') if self.file_type == 'csv' else xlrd.xldate_as_datetime(item.get('Check Out'), 0)
            if item.get('Worked Hours'):
                vals['worked_hours'] = item.get('Worked Hours')

            hr_attendance.create(vals)

        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Imported Successfully',
                'type': 'rainbow_man',
            }
        }

    def action_test_attendance(self):
        if not self.file_upload:
            raise ValidationError("Por favor carga un archivo primero.")

        datas = {}

        if self.file_type == 'csv':
            try:
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                datas = csv.DictReader(data_file, delimiter=',')
            except:
                raise ValidationError("Formato de CSV inválido.")

        elif self.file_type == 'xls':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
            except:
                raise ValidationError("Formato de XLS inválido.")

            headers = sheet.row_values(0)
            data = []
            for row_index in range(1, sheet.nrows):
                row = sheet.row_values(row_index)
                data += [{k: v for k, v in zip(headers, row)}]
            datas = data

        # Validación de contenido
        hr_employee = self.env['hr.employee']
        errors = ""
        for idx, item in enumerate(datas):
            row = idx + 2  # la fila 1 es encabezado

            employee_name = item.get('Employee')
            if not employee_name:
                errors += f"Falta el nombre del empleado en fila {row}\n"
            else:
                employee = hr_employee.search([('name', '=', employee_name)])
                if not employee:
                    errors += f"Empleado '{employee_name}' no encontrado (fila {row})\n"

            for campo_fecha in ['Check In', 'Check Out']:
                valor = item.get(campo_fecha)
                if valor:
                    if self.file_type == 'csv':
                        try:
                            fields.Datetime.from_string(valor)
                        except:
                            errors += f"'{campo_fecha}' inválido en fila {row}: {valor}\n"
                    else:
                        try:
                            xlrd.xldate_as_datetime(valor, 0)
                        except:
                            errors += f"'{campo_fecha}' inválido en fila {row}: {valor}\n"

        if errors:
            raise ValidationError(errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validación exitosa',
                'message': 'El archivo fue validado correctamente',
                'sticky': False,
            }
        }
