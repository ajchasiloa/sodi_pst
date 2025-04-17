import base64
import binascii
import csv
import io
import tempfile
import xlrd
from odoo import fields, models
from odoo.exceptions import ValidationError


class ImportPayment(models.TransientModel):
    _name = 'import.payment'
    _description = 'Payment Import'

    file_type = fields.Selection(
        selection=[('csv', 'CSV File'), ('xlsx', 'XLSX File')],
        string='Select File Type', default='xlsx',
        help='It helps to choose the file type'
    )
    file_upload = fields.Binary(string='File Upload', attachment=False, help='It helps to upload files')

    def action_import_payment(self):
        """ Method to import payments from .csv or .xlsx files. """
        # Validación del tipo de archivo
        if not self.file_upload:
            raise ValidationError("Por favor, sube un archivo válido antes de continuar.")
        
        if self.file_type == 'csv':
            try:
                # Intentamos leer como CSV
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                reader = csv.reader(data_file)
                rows = list(reader)
                if len(rows) <= 1:  # Si solo tiene una fila (cabecera), es un archivo vacío
                    raise ValidationError("The CSV file is empty or missing data.")
            except Exception as e:
                raise ValidationError(f"Error reading the file as CSV: {str(e)}")
        
        elif self.file_type == 'xlsx':
            try:
                # Intentamos leer como XLSX
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

        # 4. Validación de campos requeridos
        error_msg = ""
        for row_index, row in enumerate(rows, start=2):  # Empieza desde la fila 2 (excluyendo la cabecera)
            if not row or len(row) < 6:
                error_msg += f"Row {row_index} is empty or incomplete.\n"
                continue

            if not row[0]:  # Verificar que Amount esté presente
                error_msg += f"Amount is missing in row {row_index}\n"
            if not row[1]:  # Verificar que Date esté presente
                error_msg += f"Date is missing in row {row_index}\n"
            if not row[2]:  # Verificar que Journal esté presente
                error_msg += f"Journal is missing in row {row_index}\n"
            if not row[3]:  # Verificar que Customer/Vendor esté presente
                error_msg += f"Customer/Vendor is missing in row {row_index}\n"
            if not row[4]:  # Verificar que Payment Type esté presente
                error_msg += f"Payment Type is missing in row {row_index}\n"
            if not row[5]:  # Verificar que Number esté presente
                error_msg += f"Payment Number is missing in row {row_index}\n"

        if error_msg:
            raise ValidationError(f"Validation failed:\n{error_msg}")

        # 5. Validación del tipo de pago
        for row_index, row in enumerate(rows, start=2):
            if row[4] not in ['Send', 'Receive']:
                error_msg += f"Invalid Payment Type in row {row_index}\n"

        if error_msg:
            raise ValidationError(f"Validation failed:\n{error_msg}")

        # 6. Si todas las validaciones pasaron
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validation Success',
                'message': 'The file was validated successfully.',
                'sticky': False,
            }
        }

    def action_test_import_payment(self):
        # 1. Verificar si el archivo está vacío
        if not self.file_upload:
            raise ValidationError("Por favor, sube un archivo válido antes de continuar.")

        # 2. Validar que el archivo corresponda al tipo seleccionado
        if self.file_type == 'csv':
            try:
                # Intentamos leer como CSV
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                reader = csv.reader(data_file)
                rows = list(reader)
                if len(rows) <= 1:  # Si solo tiene una fila (cabecera), es un archivo vacío
                    raise ValidationError("The CSV file is empty or missing data.")
            except Exception as e:
                raise ValidationError(f"Error reading the file as CSV: {str(e)}")
        
        elif self.file_type == 'xlsx':
            try:
                # Intentamos leer como XLSX
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
        for row_index, row in enumerate(rows, start=2):  # Empieza desde la fila 2 (excluyendo la cabecera)
            if not row or len(row) < 6:
                error_msg += f"Row {row_index} is empty or incomplete.\n"
                continue

            if not row[0]:  # Verificar que Amount esté presente
                error_msg += f"Amount is missing in row {row_index}\n"
            if not row[1]:  # Verificar que Date esté presente
                error_msg += f"Date is missing in row {row_index}\n"
            if not row[2]:  # Verificar que Journal esté presente
                error_msg += f"Journal is missing in row {row_index}\n"
            if not row[3]:  # Verificar que Customer/Vendor esté presente
                error_msg += f"Customer/Vendor is missing in row {row_index}\n"
            if not row[4]:  # Verificar que Payment Type esté presente
                error_msg += f"Payment Type is missing in row {row_index}\n"
            if not row[5]:  # Verificar que Number esté presente
                error_msg += f"Payment Number is missing in row {row_index}\n"

        if error_msg:
            raise ValidationError(f"Validation failed:\n{error_msg}")

        # 4. Validación del tipo de pago
        for row_index, row in enumerate(rows, start=2):
            if row[4] not in ['Send', 'Receive']:
                error_msg += f"Invalid Payment Type in row {row_index}\n"

        if error_msg:
            raise ValidationError(f"Validation failed:\n{error_msg}")

        # 5. Si todas las validaciones pasaron
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validation Success',
                'message': 'The file was validated successfully.',
                'sticky': False,
            }
        }
