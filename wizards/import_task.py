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
                    raise ValidationError("El archivo CSV está vacío o falta contenido.")
            except Exception as e:
                raise ValidationError(f"Error leyendo el archivo CSV: {str(e)}")
        
        elif self.file_type == 'xls':
            try: 
                # Verificar que el archivo XLSX tenga contenido
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                if sheet.nrows <= 1:  # Si solo tiene una fila (cabecera), es un archivo vacío
                    raise ValidationError("El archivo XLSX está vacío o falta contenido.")
                rows = [sheet.row_values(row_idx) for row_idx in range(1, sheet.nrows)]
            except Exception as e:
                raise ValidationError(f"Error leyendo el archivo XLSX: {str(e)}")
        
        else:
            raise ValidationError("Tipo de archivo no válido. Solo se permiten archivos CSV y XLSX.")

        # 3. Validación de campos requeridos
        error_msg = ""
        for row_index, row in enumerate(rows, start=2):  # empieza desde la fila 2
            if not row or len(row) < 5:
                error_msg += f"Fila {row_index} está vacía o incompleta.\n"
                continue
            if not row[0]:  # Proyecto
                error_msg += f"El proyecto falta en la fila {row_index}\n"
            if not row[1]:  # Título
                error_msg += f"El título falta en la fila {row_index}\n"
            if not row[3]:  # Fecha límite
                error_msg += f"La fecha límite falta en la fila {row_index}\n"
            if not row[4]:  # Tarea padre
                error_msg += f"La tarea padre falta en la fila {row_index}\n"
        
        if error_msg:
            raise ValidationError(f"Error de validación:\n{error_msg}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validación exitosa',
                'message': 'El archivo fue validado exitosamente.',
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
            "Fecha Límite",       # Deadline
            "Tarea Padre"         # Parent Task
        ]

        # Crear archivo en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Task Import Template")

        # Estilo para encabezados
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'align': 'center', 'valign': 'vcenter'})

        # Escribir encabezados en la primera fila
        for col, label in enumerate(field_labels):
            worksheet.write(0, col, label, header_format)

        # Añadir una fila de ejemplo
        example_data = [
            "Proyecto A",            # Project
            "Tarea 1",               # Title
            "2024-12-31",            # Deadline
            "Tarea Padre 1"          # Parent Task
        ]

        # Escribir los datos de ejemplo en la segunda fila
        for col, value in enumerate(example_data):
            worksheet.write(1, col, value)

        # Ajustar automáticamente el tamaño de las columnas para que todo el texto sea visible
        for col in range(len(field_labels)):
            column_width = max(len(field_labels[col]), max(len(str(example_data[col])) for example_data in [example_data]))
            worksheet.set_column(col, col, column_width)

        # Cerrar y preparar el archivo
        workbook.close()
        output.seek(0)

        # Crear adjunto en Odoo
        attachment = self.env['ir.attachment'].create({
            'name': 'plantilla_importación_tareas.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()).decode(),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Retornar archivo para descarga
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
            if item.get('Proyecto'):
                project = project_project.search([('name', '=', item.get('Proyecto'))])
                if not project:
                    project = project_project.create({'name': item.get('Proyecto')})
                    info_msg += f"\nCreated new project with name :{item.get('Proyecto')}"
                vals['project_id'] = project.id
            
            if item.get('Título'):
                vals['name'] = item.get('Título')
            else:
                error_msg += "⚠Title missing in file!"
            
            if item.get('Fecha Límite'):
                vals['date_deadline'] = datetime.datetime.strptime(item.get('Fecha Límite'), '%Y-%m-%d')
            
            if item.get('Tarea Padre'):
                parent_task = project_task.search([('name', '=', item.get('Tarea Padre'))])
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
