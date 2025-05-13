# -*- coding: utf-8 -*-
import base64
import binascii
import csv
import datetime
import io
import tempfile
import xlrd
from odoo.exceptions import ValidationError
from odoo import fields, models, _


class ImportPosOrder(models.TransientModel):
    """ Model for import POS Orders """
    _name = 'import.pos.order'
    _description = 'Pos Orders Import'

    file_type = fields.Selection(
        selection=[('csv', 'CSV File'), ('xlsx', 'XLSX File')],
        string='Select File Type', default='xlsx',
        help='It helps to choose the file type')
    file_upload = fields.Binary(string='File Upload',
                                help="It helps to upload file")
    import_product_by = fields.Selection(
        selection=[('name', 'Name'), ('default_code', 'Internal Reference'),
                ('barcode', 'Barcode')], string="Import order by",
        help="Import product", default="name")

    def action_test_import_pos_order(self):
        """ Validate POS Order File Upload """
        if not self.file_upload:
            raise ValidationError("Por favor, sube un archivo válido antes de continuar.")

        if self.file_type == 'csv':
            try:
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                csv_reader = csv.DictReader(data_file, delimiter=',')
                rows = list(csv_reader)
                if not rows:
                    raise ValidationError("El archivo CSV está vacío.")
            except Exception as e:
                raise ValidationError(f"Error leyendo el archivo CSV: {str(e)}")
        
        elif self.file_type == 'xlsx':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                if sheet.nrows <= 1:  # Si no hay datos excepto la cabecera
                    raise ValidationError("El archivo XLSX está vacío.")
                rows = [sheet.row_values(row_idx) for row_idx in range(1, sheet.nrows)]
            except Exception as e:
                raise ValidationError(f"Error leyendo el archivo XLSX: {str(e)}")

        else:
            raise ValidationError("Tipo de archivo no válido. Solo se permiten archivos CSV y XLSX.")

        # Validación de campos requeridos
        error_msg = ""
        for row_index, row in enumerate(rows, start=2):  # empieza desde la fila 2
            if not row or len(row) < 5:
                error_msg += f"Fila {row_index} está vacía o incompleta.\n"
                continue
            if not row[0]:  # Order Reference
                error_msg += f"Falta la referencia de pedido en la fila {row_index}\n"
            if not row[1]:  # Customer (partner_id)
                error_msg += f"Falta el cliente en la fila {row_index}\n"
            if not row[2]:  # Order Date
                error_msg += f"Falta la fecha de pedido en la fila {row_index}\n"
            if not row[3]:  # Total Amount
                error_msg += f"Falta el total del pedido en la fila {row_index}\n"
            if not row[4]:  # Line items (productos)
                error_msg += f"Faltan líneas de pedido en la fila {row_index}\n"

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

    def action_import_pos_order(self):
        """ Creating POS Order record using uploaded xl/csv files """
        datas = {}

        if self.file_type == 'csv':
            try:
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                datas = list(csv.DictReader(data_file, delimiter=','))
            except Exception as e:
                raise ValidationError(f"Error leyendo el archivo CSV: {str(e)}")
        
        elif self.file_type == 'xlsx':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                
                headers = sheet.row_values(0)
                datas = []
                for row_index in range(1, sheet.nrows):
                    row = sheet.row_values(row_index)
                    datas.append({k: v for k, v in zip(headers, row)})
            except Exception as e:
                raise ValidationError(f"Error leyendo el archivo XLSX: {str(e)}")

        imported_count = 0
        for item in datas:
            try:
                vals = {}

                # Mapeo de Sesión a session_id
                if not item.get('Sesión'):
                    raise ValidationError("El campo 'Sesión' es obligatorio para cada pedido.")
                
                # Buscar la sesión por nombre
                session = self.env['pos.session'].search([('name', '=', item.get('Sesión'))], limit=1)
                if not session:
                    # Si no existe la sesión, intentar crear una nueva
                    pos_config = self.env['pos.config'].search([], limit=1)
                    if not pos_config:
                        raise ValidationError("No hay configuraciones de Punto de Venta disponibles. Cree una configuración de POS primero.")
                    
                    try:
                        session = self.env['pos.session'].create({
                            'name': item.get('Sesión'),
                            'config_id': pos_config.id,
                            'user_id': self.env.user.id
                        })
                    except Exception as e:
                        raise ValidationError(f"No se pudo crear la sesión '{item.get('Sesión')}': {str(e)}")
                
                # Asignar session_id
                vals['session_id'] = session.id

                # Referencia de Pedido
                if item.get('Referencia de Pedido'):
                    order_ref_search = self.env['pos.order'].search([('pos_reference', '=', item.get('Referencia de Pedido'))])
                    if order_ref_search:
                        raise ValidationError(f"El pedido con la referencia '{item.get('Referencia de Pedido')}' ya existe.")
                    vals['pos_reference'] = item.get('Referencia de Pedido')
                
                # Cliente
                if item.get('Cliente'):
                    partner = self.env['res.partner'].search([('name', '=', item.get('Cliente'))])
                    if not partner:
                        partner = self.env['res.partner'].create({'name': item.get('Cliente')})
                    vals['partner_id'] = partner.id
                
                # Fecha de Pedido
                if item.get('Fecha de Pedido'):
                    try:
                        vals['date_order'] = datetime.datetime.strptime(str(item.get('Fecha de Pedido')), '%Y-%m-%d')
                    except ValueError:
                        raise ValidationError(f"Formato de fecha inválido: {item.get('Fecha de Pedido')}. Use YYYY-MM-DD")
                
                # Total del Pedido
                if item.get('Total'):
                    try:
                        vals['amount_total'] = float(item.get('Total'))
                    except ValueError:
                        raise ValidationError(f"Total inválido: {item.get('Total')}")
                
                # Líneas de Producto
                lines = []
                if item.get('Producto'):
                    product = self.env['product.product'].search([('name', '=', item.get('Producto'))])
                    if not product:
                        product = self.env['product.product'].create({'name': item.get('Producto')})
                    
                    try:
                        qty = float(item.get('Cantidad', 0))
                        price_unit = float(item.get('Precio Unitario', 0))
                    except ValueError:
                        raise ValidationError(f"Cantidad o Precio Unitario inválido para producto '{item.get('Producto')}'")
                    
                    lines.append((0, 0, {
                        'product_id': product.id,
                        'qty': qty,
                        'price_unit': price_unit,
                    }))
                
                vals['lines'] = lines

                # Crear pedido de POS
                pos_order = self.env['pos.order'].create(vals)
                imported_count += 1

            except Exception as e:
                # Log the specific error for this item without stopping the entire import
                error_message = self.env['import.message'].create({
                    'message': f"Error importando pedido: {str(e)}"
                })
                return {
                    'name': 'Error de Importación',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'import.message',
                    'res_id': error_message.id,
                    'target': 'new'
                }
        
        return {
            'effect': {
                'fadeout': 'slow',
                'message': f'{imported_count} Pedidos importados con éxito.',
                'type': 'rainbow_man',
            }
        }

    def action_generate_template(self):
        """Genera una plantilla Excel para importar pedidos POS"""

        import base64
        from io import BytesIO
        import xlsxwriter

        field_labels = [
            "Referencia de Pedido",    # Order Ref
            "Fecha de Pedido",         # Order Date
            "Cliente",                 # Customer
            "Número de Recibo",        # Receipt Number
            "Responsable",             # Responsible
            "Sesión",                  # Session
            "Producto",                # Product
            "Cantidad",                # Quantity
            "Precio Unitario",         # Unit Price
            "Descuento %",             # Discount %
            "Subtotal",                # Sub Total
            "Importe de Impuestos",    # Tax Amount
            "Total",                   # Total
            "Monto Pagado",            # Paid Amount
            "Monto Devuelto"           # Amount Returned
        ]

        example_data = [
            "POS1234",            # Order Ref
            "2024-12-31",         # Order Date
            "Proveedor ABC",      # Customer
            "RC12345",            # Receipt Number
            "Juan Perez",         # Responsible
            "Sesion1",            # Session
            "Producto A",         # Product
            2,                    # Quantity
            10.00,                # Unit Price
            5,                    # Discount %
            20.00,                # Sub Total
            4.00,                 # Tax Amount
            24.00,                # Total
            20.00,                # Paid Amount
            4.00                  # Amount Returned
        ]

        # Crear archivo en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("POS Order Import Template")

        # Formato de encabezado
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'align': 'center', 'valign': 'vcenter'})
        
        # Escribir encabezados en la primera fila
        for col, label in enumerate(field_labels):
            worksheet.write(0, col, label, header_format)

        # Escribir una fila de ejemplo en la segunda fila
        for col, value in enumerate(example_data):
            worksheet.write(1, col, value)

        # Ajuste automático del tamaño de las columnas para que todo el texto sea visible
        for col in range(len(field_labels)):
            # Obtener la longitud máxima entre el encabezado y el valor de ejemplo
            column_width = max(len(field_labels[col]), len(str(example_data[col])))
            worksheet.set_column(col, col, column_width)

        # Cerrar el archivo
        workbook.close()
        output.seek(0)

        # Crear archivo adjunto en Odoo
        attachment = self.env['ir.attachment'].create({
            'name': 'plantilla_importación_pedidos_pos.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()).decode(),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }