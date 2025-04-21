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
        """Test the file before import"""
        if not self.file_upload:
            raise ValidationError("Por favor, sube un archivo válido antes de continuar.")

        # Validate file type
        if self.file_type == 'csv':
            try:
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                csv_reader = csv.DictReader(data_file, delimiter=',')
                rows = list(csv_reader)
                if not rows:
                    raise ValidationError("The CSV file is empty.")
            except Exception as e:
                raise ValidationError(f"Error reading the CSV file: {str(e)}")
        
        elif self.file_type == 'xls':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                if sheet.nrows <= 1:  # If there's no data except header
                    raise ValidationError("The XLSX file is empty.")
            except Exception as e:
                raise ValidationError(f"Error reading the XLSX file: {str(e)}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Validation Success'),
                'message': _('File validated successfully.'),
                'sticky': False,
            }
        }

    def action_generate_template(self):
        """Genera una plantilla Excel para importar asistencias de empleados"""

        import base64
        from io import BytesIO
        import xlsxwriter

        # Encabezados que el archivo debe contener
        field_labels = [
            "Empleado",       # Nombre del empleado
            "Entrada",       # Fecha/hora de entrada
            "Salida",        # Fecha/hora de salida
            "Horas Trabajadas"    # Horas trabajadas
        ]

        # Crear archivo Excel en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Attendance Template")

        # Formato del encabezado
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9'})

        # Escribir encabezados en la primera fila
        for col, label in enumerate(field_labels):
            worksheet.write(0, col, label, header_format)

        # Cerrar y preparar archivo
        workbook.close()
        output.seek(0)

        # Crear attachment en Odoo
        attachment = self.env['ir.attachment'].create({
            'name': 'attendance_import_template.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()).decode(),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Retornar URL de descarga
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
