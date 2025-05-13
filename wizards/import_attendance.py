from odoo import fields, models, _
from odoo.exceptions import ValidationError
import base64
import binascii
import csv
import io
import tempfile
import xlrd
from datetime import datetime

class ImportAttendance(models.TransientModel):
    _name = 'import.attendance'
    _description = 'Attendance Import'

    file_type = fields.Selection(
        selection=[('csv', 'CSV File'), ('xls', 'XLS File')],
        string='Select File Type', default='csv',
        help="It helps to select File Type")
    file_upload = fields.Binary(string="Upload File", help="It helps to upload files")

    def _force_create_attendance(self, vals):
        """
        Crea un registro de asistencia ignorando todas las validaciones estándar de Odoo
        """
        attendance_obj = self.env['hr.attendance'].with_context(import_file=True)
        return attendance_obj.sudo().create(vals)

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
            except Exception as e:
                raise ValidationError(_("Invalid CSV file format. Error: %s" % str(e)))

        if self.file_type == 'xls':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
            except Exception as e:
                raise ValidationError(_("Invalid XLS file format. Error: %s" % str(e)))

            headers = sheet.row_values(0)
            data = []
            for row_index in range(1, sheet.nrows):
                row = sheet.row_values(row_index)
                data += [{k: v for k, v in zip(headers, row)}]
            datas = data

        # Proceso para verificar si los empleados existen y crear asistencia
        for item in datas:
            vals = {}
            employee_name = item.get('Employee')

            # Búsqueda flexible de empleados (por nombre e identificación)
            employee = hr_employee.search([
                '&',
                '|', 
                ('name', 'ilike', employee_name),
                ('identification_id', '=', employee_name),
                ('active', '=', True)
            ], limit=1)

            if not employee:
                # Si no encuentra el empleado, mostrar error
                raise ValidationError(_("No employee found with the name or identification: %s" % employee_name))

            vals['employee_id'] = employee.id

            # Procesar fechas
            date_formats = [
                '%Y-%m-%d %H:%M:%S',  # Formato estándar
                '%d/%m/%Y %H:%M:%S',  # Formato día/mes/año
                '%m/%d/%Y %H:%M:%S',  # Formato mes/día/año
                '%Y-%m-%d %H:%M',     # Sin segundos
                '%d/%m/%Y %H:%M',     # Sin segundos
            ]

            # Procesar check_in
            if item.get('Check In'):
                check_in_str = item.get('Check In')
                for date_format in date_formats:
                    try:
                        vals['check_in'] = datetime.strptime(check_in_str, date_format)
                        break
                    except ValueError:
                        continue
                if 'check_in' not in vals:
                    raise ValidationError(_("Invalid date format for 'Check In' for employee %s") % employee_name)

            # Procesar check_out
            if item.get('Check Out'):
                check_out_str = item.get('Check Out')
                for date_format in date_formats:
                    try:
                        vals['check_out'] = datetime.strptime(check_out_str, date_format)
                        break
                    except ValueError:
                        continue
                if 'check_out' not in vals and item.get('Check Out'):
                    raise ValidationError(_("Invalid date format for 'Check Out' for employee %s") % employee_name)

            # Validación de horas trabajadas
            if item.get('Worked Hours'):
                try:
                    vals['worked_hours'] = float(item.get('Worked Hours'))
                except ValueError:
                    raise ValidationError(_("Worked Hours must be a valid number for employee %s") % employee_name)

            # Crear registro de asistencia forzando la creación
            self._force_create_attendance(vals)

        return {
            'effect': {
                'fadeout': 'slow',
                'message': _('Imported Successfully'),
                'type': 'rainbow_man',
            }
        }

    def action_test_attendance(self):
        """Test the file before import"""
        if not self.file_upload:
            raise ValidationError(_("Please upload a valid file before continuing."))

        # Validate file type
        if self.file_type == 'csv':
            try:
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                csv_reader = csv.DictReader(data_file, delimiter=',')
                rows = list(csv_reader)
                if not rows:
                    raise ValidationError(_("The CSV file is empty."))
            except Exception as e:
                raise ValidationError(_("Error reading the CSV file: %s" % str(e)))
        
        elif self.file_type == 'xls':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                if sheet.nrows <= 1:  # If there's no data except header
                    raise ValidationError(_("The XLSX file is empty."))
            except Exception as e:
                raise ValidationError(_("Error reading the XLSX file: %s" % str(e)))
        
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
        """Genera una plantilla de Excel para importar asistencias de empleados"""

        import base64
        from io import BytesIO
        import xlsxwriter
        from datetime import datetime

        # Encabezados que debe contener el archivo
        field_labels = [
            "Empleado",           # Nombre del empleado
            "Entrada",            # Fecha/hora de entrada
            "Salida",             # Fecha/hora de salida
            "Horas Trabajadas"    # Horas trabajadas
        ]

        # Crear un archivo Excel en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Plantilla de Asistencia")

        # Formatos para el archivo
        header_format = workbook.add_format({
            'bold': True, 
            'bg_color': '#D9D9D9', 
            'align': 'center', 
            'valign': 'vcenter',
            'border': 1
        })

        date_format = workbook.add_format({
            'num_format': 'yyyy-mm-dd hh:mm:ss',
            'align': 'center'
        })

        number_format = workbook.add_format({
            'num_format': '0.00',
            'align': 'center'
        })

        # Escribir encabezados en la primera fila
        for col, label in enumerate(field_labels):
            worksheet.write(0, col, label, header_format)

        # Obtener fecha actual para el ejemplo
        now = datetime.now()
        entrada = now.replace(hour=8, minute=0, second=0)
        salida = now.replace(hour=17, minute=0, second=0)
        horas_trabajadas = (salida - entrada).total_seconds() / 3600

        # Datos de ejemplo
        example_data = [
            "ANDERSON JAIR CHASILOA NACATA",  # Empleado
            entrada,                           # Entrada
            salida,                            # Salida
            horas_trabajadas                   # Horas trabajadas
        ]

        # Escribir los datos de ejemplo en la segunda fila
        for col, value in enumerate(example_data):
            if col == 0:  # Nombre del empleado
                worksheet.write(1, col, value)
            elif col in [1, 2]:  # Fechas de entrada y salida
                worksheet.write(1, col, value, date_format)
            elif col == 3:  # Horas trabajadas
                worksheet.write(1, col, value, number_format)

        # Ajustar el ancho de las columnas
        column_widths = [30, 20, 20, 15]
        for col, width in enumerate(column_widths):
            worksheet.set_column(col, col, width)

        # Agregar validación de datos para la columna de empleados
        worksheet.data_validation(f'A2:A{1000}', {
            'validate': 'list',
            'source': ['Ingrese nombres de empleados']
        })

        # Cerrar y preparar el archivo
        workbook.close()
        output.seek(0)

        # Crear un archivo adjunto en Odoo
        attachment = self.env['ir.attachment'].create({
            'name': 'plantilla_asistencia.xlsx',  # Nombre del archivo en español
            'type': 'binary',
            'datas': base64.b64encode(output.read()).decode(),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Devolver la URL de descarga
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }