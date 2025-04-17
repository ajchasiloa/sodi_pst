# -*- coding: utf-8 -*-
import base64
import binascii
import csv
import io
import tempfile
import xlrd
import datetime
from odoo.exceptions import ValidationError
from odoo import fields, models

class ImportTask(models.TransientModel):
    """ Model for import project task. """
    _name = 'import.task'
    _description = 'Task Import'

    file_type = fields.Selection(
        selection=[('csv', 'CSV File'), ('xls', 'XLS File')], default='csv',
        string='Select File Type', help='File type')
    file_upload = fields.Binary(string="Upload File", help="Helps to upload your file")
    user_id = fields.Many2one(comodel_name='res.users', string='Assigned to', help="assigned to user")

    def action_test_import_task(self):
        """ Method to test the import file for tasks """
        # 1. Verificar si el archivo está vacío
        if not self.file_upload:
            raise ValidationError("Por favor, sube un archivo válido antes de continuar.")

        # 2. Validar el tipo de archivo
        if self.file_type == 'csv':
            try:
                # Verificar que el archivo CSV tenga contenido
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                reader = csv.reader(data_file)
                rows = list(reader)
                if len(rows) <= 1:  # Si solo tiene una fila (cabecera), es un archivo vacío
                    raise ValidationError("The CSV file is empty or missing data.")
            except Exception as e:
                raise ValidationError(f"Error reading the file as CSV: {str(e)}")
        
        elif self.file_type == 'xls':
            try: 
                # Verificar que el archivo XLSX tenga contenido
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                if sheet.nrows <= 1:  # Si solo tiene una fila (cabecera), es un archivo vacío
                    raise ValidationError("The XLSX file is empty or missing data.")
                rows = [sheet.row_values(row_idx) for row_idx in range(1, sheet.nrows)]
            except Exception as e:
                raise ValidationError(f"Error reading the file as XLSX: {str(e)}")
        
        else:
            raise ValidationError("Invalid file type. Only CSV and XLSX are allowed.")

        # 3. Validación de campos requeridos
        error_msg = ""
        for row_index, row in enumerate(rows, start=2):  # empieza desde la fila 2
            if not row or len(row) < 5:
                error_msg += f"Row {row_index} is empty or incomplete.\n"
                continue
            if not row[0]:  # Amount
                error_msg += f"Amount is missing in row {row_index}\n"
            if not row[1]:  # Date
                error_msg += f"Date is missing in row {row_index}\n"
            if not row[2]:  # Journal
                error_msg += f"Journal is missing in row {row_index}\n"
            if not row[3]:  # Customer
                error_msg += f"Customer is missing in row {row_index}\n"
            if not row[4]:  # Payment Type
                error_msg += f"Payment Type is missing in row {row_index}\n"
        
        if error_msg:
            raise ValidationError(f"Validation failed:\n{error_msg}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validation Success',
                'message': 'The file was validated successfully.',
                'sticky': False,
            }
        }

    def action_generate_template(self):
        """Genera una plantilla Excel para importar tareas de proyecto"""

        import base64
        from io import BytesIO
        import xlsxwriter

        # Columnas requeridas por el importador de tareas
        field_labels = [
            "Proyecto",           # Project
            "Título",             # Title
            "Cliente",            # Customer
            "Fecha Límite",       # Deadline
            "Tarea Padre"         # Parent Task
        ]

        # Crear archivo en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Task Import Template")

        # Estilo para encabezados
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9'})
        for col, label in enumerate(field_labels):
            worksheet.write(0, col, label, header_format)

        workbook.close()
        output.seek(0)

        # Crear adjunto en Odoo
        attachment = self.env['ir.attachment'].create({
            'name': 'task_import_template.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()).decode(),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_import_task(self):
        """ Method to import tasks from .csv or .xlsx files """
        res_partner = self.env['res.partner']
        project_project = self.env['project.project']
        project_task = self.env['project.task']
        items = False

        # Verificar si el archivo es CSV
        if self.file_type == 'csv':
            try:
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                csv_reader = csv.DictReader(data_file, delimiter=',')
            except:
                raise ValidationError("File not Valid.\n\nPlease check the type and format of the file and try again!")
            items = csv_reader
        
        # Verificar si el archivo es XLS
        if self.file_type == 'xls':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
            except:
                raise ValidationError("File not Valid.\n\nPlease check the type and format of the file and try again!")
            
            headers = sheet.row_values(0)
            data = []
            for row_index in range(1, sheet.nrows):
                row = sheet.row_values(row_index)
                data += [{k: v for k, v in zip(headers, row)}]
            items = data

        imported = 0
        info_msg = ""
        error_msg = ""

        for item in items:
            vals = {}
            if item.get('Project'):
                project = project_project.search([('name', '=', item.get('Project'))])
                if not project:
                    project = project_project.create({'name': item.get('Project')})
                    info_msg += f"\nCreated new project with name :{item.get('Project')}"
                vals['project_id'] = project.id
            
            if item.get('Title'):
                vals['name'] = item.get('Title')
            else:
                error_msg += "⚠Title missing in file!"
            
            if item.get('Customer'):
                partner = res_partner.search([['name', '=', item.get('Customer')]])
                if not partner:
                    partner = res_partner.create({'name': item.get('Customer')})
                    info_msg += f"\nCreated new partner with name :{item.get('Customer')}"
                vals['partner_id'] = partner.id
            
            if item.get('Deadline'):
                vals['date_deadline'] = datetime.datetime.strptime(item.get('Deadline'), '%m/%d/%Y')
            
            if item.get('Parent Task'):
                parent_task = project_task.search([('name', '=', item.get('Parent Task'))])
                if len(parent_task) > 1:
                    parent_task = parent_task[0]
                vals['parent_id'] = parent_task.id
            
            vals['user_ids'] = self.user_id

            if error_msg:
                error_msg = "\n\n🏮 ERROR 🏮" + error_msg
                error_message = self.env['import.message'].create({'message': error_msg})
                return {
                    'name': 'Error!',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'import.message',
                    'res_id': error_message.id,
                    'target': 'new'
                }

            task_id = project_task.create(vals)
            if task_id:
                imported += 1

            if info_msg:
                info_msg = f"\nInformation : {info_msg}"
            msg = (("Imported %d records." % imported) + info_msg)

            message = self.env['import.message'].create({'message': msg})
            if message:
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': msg,
                        'type': 'rainbow_man',
                    }
                }
