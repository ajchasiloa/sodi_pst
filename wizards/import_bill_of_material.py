import base64
import binascii
import csv
import io
import tempfile
import xlrd
from odoo import fields, models
from odoo.exceptions import ValidationError


class ImportBillOfMaterial(models.TransientModel):
    _name = 'import.bill.of.material'
    _description = 'Importación de Listas de Materiales'

    file_type = fields.Selection(
        [('csv', 'Archivo CSV'), ('xls', 'Archivo XLS')],
        default='csv',
        string='Seleccionar Tipo de Archivo',
        help="Tipo de archivo para cargar"
    )
    file_upload = fields.Binary(
        string='Subir Archivo',
        help="Ayuda a subir el archivo",
        attachment=False
    )
    import_product_by = fields.Selection(
        [('default_code', 'Referencia Interna'), ('barcode', 'Código de Barras')],
        default='default_code',
        string="Importar Productos Por",
        help="Ayuda a importar el producto"
    )
    bom_type = fields.Selection(
        [('manufacture_this_product', 'Fabricar este Producto'),
         ('kit', 'Kit'), ('both', 'Ambos')],
        string="Tipo de BOM",
        default='both',
        help="Ayuda a elegir el tipo de BOM"
    )
    bom_component = fields.Selection(
        [('add', 'Agregar Componentes'), ('do_not', 'No agregar Componentes')],
        default='add',
        string="Componente BOM",
        help="Ayuda a elegir el comportamiento de los componentes BOM"
    )

    def action_import_bom(self):
        datas = {}
        if not self.file_upload:
            raise ValidationError("Por favor, sube un archivo válido antes de continuar.")

        if self.file_type == 'csv':
            try:
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                datas = csv.DictReader(data_file, delimiter=',')
            except Exception:
                raise ValidationError("Archivo CSV no válido.")
        elif self.file_type == 'xls':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xls")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                headers = sheet.row_values(0)
                datas = [
                    {k: v for k, v in zip(headers, sheet.row_values(i))}
                    for i in range(1, sheet.nrows)
                ]
            except Exception:
                raise ValidationError("Archivo XLS no válido.")

        row = 0
        imported = 0
        updated = 0
        error_msg = ""
        warning_msg = ""

        for item in datas:
            row += 1
            vals = {}
            product_tmpl = False

            if item.get('Producto'):
                if self.import_product_by == 'default_code' and item.get('Referencia Interna'):
                    product_tmpl = self.env['product.template'].search([
                        ('default_code', '=', item.get('Referencia Interna'))], limit=1)
                elif self.import_product_by == 'barcode' and item.get('Código de Barras'):
                    product_tmpl = self.env['product.template'].search([
                        ('barcode', '=', item.get('Código de Barras'))], limit=1)
                else:
                    product_tmpl = self.env['product.template'].search([
                        ('name', '=', item.get('Producto'))], limit=1)

                if not product_tmpl:
                    product_tmpl = self.env['product.template'].create({
                        'name': item.get('Producto'),
                        'default_code': item.get('Referencia Interna'),
                        'barcode': item.get('Código de Barras')
                    })
                    warning_msg += f"\n◼ Producto nuevo creado en la fila {row}"

                vals['product_tmpl_id'] = product_tmpl.id
            else:
                error_msg += f"\n⚠ Producto faltante en la fila {row}"

            try:
                vals['product_qty'] = float(item.get('Cantidad') or 1.0)
            except Exception:
                vals['product_qty'] = 1.0
            vals['code'] = item.get('Referencia') or ''

            bom_type = self.bom_type
            if bom_type == 'both' and item.get('Tipo de Lista de Materiales'):
                bom_type = 'manufacture_this_product' if item['Tipo de Lista de Materiales'] == 'Fabricar este Producto' else 'kit'
            vals['type'] = 'normal' if bom_type == 'manufacture_this_product' else 'phantom'

            components = {}
            if self.bom_component == 'add' and item.get('Componente de BoM'):
                product_component = False
                if item.get('Componente de BoM/Referencia Interna'):
                    product_component = self.env['product.product'].search([
                        ('default_code', '=', item.get('Componente de BoM/Referencia Interna'))], limit=1)
                elif item.get('Componente de BoM/Código de Barras'):
                    product_component = self.env['product.product'].search([
                        ('barcode', '=', item.get('Componente de BoM/Código de Barras'))], limit=1)
                else:
                    product_component = self.env['product.product'].search([
                        ('name', '=', item.get('Componente de BoM'))], limit=1)

                if not product_component:
                    product_component = self.env['product.product'].create({
                        'name': item.get('Componente de BoM'),
                        'default_code': item.get('Componente de BoM/Referencia Interna'),
                        'barcode': item.get('Componente de BoM/Código de Barras'),
                    })
                    warning_msg += f"\n◼ Componente nuevo creado en la fila {row}"

                try:
                    component_qty = float(item.get('Cantidad de Componente') or 1.0)
                except Exception:
                    component_qty = 1.0

                components = {
                    'product_id': product_component.id,
                    'product_qty': component_qty
                }
                vals['bom_line_ids'] = [(0, 0, components)]

            if product_tmpl:
                bom_id = self.env['mrp.bom'].search([
                    ('product_tmpl_id', '=', product_tmpl.id)
                ], limit=1)
                if bom_id and self.bom_component == 'add':
                    bom_id.write({'bom_line_ids': [(0, 0, components)]})
                    updated += 1
                else:
                    self.env['mrp.bom'].create(vals)
                    imported += 1

        if error_msg:
            raise ValidationError(error_msg)

        return {
            'effect': {
                'fadeout': 'slow',
                'message': f"✅ Importado: {imported}, Actualizado: {updated}{warning_msg}",
                'type': 'rainbow_man',
            }
        }

    def action_test_import_bom(self):
        if not self.file_upload:
            raise ValidationError("Por favor, sube un archivo válido antes de continuar.")

        datas = {}
        errors = ""

        if self.file_type == 'csv':
            try:
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                datas = csv.DictReader(data_file, delimiter=',')
            except Exception:
                raise ValidationError("Archivo CSV no válido.")
        elif self.file_type == 'xls':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xls")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                headers = sheet.row_values(0)
                datas = [
                    {k: v for k, v in zip(headers, sheet.row_values(i))}
                    for i in range(1, sheet.nrows)
                ]
            except Exception:
                raise ValidationError("Archivo XLS no válido.")

        row = 0

        for item in datas:
            row += 1

            if not item.get('Producto'):
                errors += f"Producto faltante en la fila {row}\n"

            quantity = item.get('Cantidad')
            if quantity is None or quantity == "":
                errors += f"Cantidad faltante o vacía en la fila {row}\n"
            else:
                try:
                    float(quantity)
                except ValueError:
                    errors += f"Cantidad inválida en la fila {row}: {quantity}\n"

            if self.bom_component == 'add' and item.get('Componente de BoM'):
                try:
                    component_quantity = item.get('Cantidad de Componente')
                    if component_quantity is None or component_quantity == "":
                        errors += f"Cantidad de componente faltante en la fila {row}\n"
                    else:
                        float(component_quantity)
                except ValueError:
                    errors += f"Cantidad de componente inválida en la fila {row}\n"

        if errors:
            raise ValidationError(errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validación Exitosa',
                'message': 'El archivo fue validado correctamente',
                'sticky': False,
            }
        }

    def action_generate_template(self):
        """Genera una plantilla Excel para importar estructuras de BOM con formato mejorado"""

        import base64
        from io import BytesIO
        import xlsxwriter

        # Encabezados
        field_labels = [
            "ID Externo",
            "Referencia",
            "Producto",
            "Cantidad",
            "Tipo de Lista de Materiales",
            "Componente de BoM",
            "Cantidad de Componente"
        ]

        # Filas de ejemplo (1 ejemplo)
        example_data = [
            ["bom_001", "BOM_MESA001", "Mesa de Madera", 1, "Fabricar este Producto", "Pata de Madera", 4],
            ["boom_002", "BOM_SC234", "[FURN_7800] D", 1, "Kit", "[FURN_2100] Drawer Black", 5]
        ]

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Plantilla de BOM")

        # Formato del encabezado
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9'})

        # Escribir encabezados y ajustar ancho
        for col, label in enumerate(field_labels):
            worksheet.write(0, col, label, header_format)
            worksheet.set_column(col, col, len(label) + 2)

        # Escribir filas de ejemplo
        for row_idx, row_data in enumerate(example_data, start=1):
            for col_idx, value in enumerate(row_data):
                worksheet.write(row_idx, col_idx, value)

        workbook.close()
        output.seek(0)

        # Crear adjunto en Odoo
        attachment = self.env['ir.attachment'].create({
            'name': 'plantilla_importacion_bom.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()).decode(),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }