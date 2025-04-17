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
    _description = 'Bill of Material Import'

    file_type = fields.Selection(
        [('csv', 'CSV File'), ('xls', 'XLS File')],
        default='csv',
        string='Select File Type',
        help="Uploading file Type"
    )
    file_upload = fields.Binary(
        string='Upload File',
        help="Helps to upload file",
        attachment=False
    )
    import_product_by = fields.Selection(
        [('default_code', 'Internal Reference'), ('barcode', 'Barcode')],
        default='default_code',
        string="Import Products By",
        help="Helps to import product"
    )
    bom_type = fields.Selection(
        [('manufacture_this_product', 'Manufacture this Product'),
         ('kit', 'Kit'), ('both', 'Both')],
        string="BOM Type",
        default='both',
        help="Helps to choose the BOM type"
    )
    bom_component = fields.Selection(
        [('add', 'Add Components'), ('do_not', 'Do not add Components')],
        default='add',
        string="BOM Component",
        help="Helps to choose the BOM component behavior"
    )

    def action_import_bom(self):
        datas = {}
        if not self.file_upload:
            raise ValidationError("Por favor, sube un archivo válido antes de continuar.")

        # Load CSV
        if self.file_type == 'csv':
            try:
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                datas = csv.DictReader(data_file, delimiter=',')
            except Exception:
                raise ValidationError("archivo CSV no válido.")

        # Load XLS
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
                raise ValidationError("Invalid XLS file.")

        row = 0
        imported = 0
        updated = 0
        error_msg = ""
        warning_msg = ""

        for item in datas:
            row += 1
            vals = {}
            product_tmpl = False

            # Buscar producto principal
            if item.get('Product'):
                if self.import_product_by == 'default_code' and item.get('Product/Internal Reference'):
                    product_tmpl = self.env['product.template'].search([
                        ('default_code', '=', item.get('Product/Internal Reference'))], limit=1)
                elif self.import_product_by == 'barcode' and item.get('Product/Barcode'):
                    product_tmpl = self.env['product.template'].search([
                        ('barcode', '=', item.get('Product/Barcode'))], limit=1)
                else:
                    product_tmpl = self.env['product.template'].search([
                        ('name', '=', item.get('Product'))], limit=1)

                if not product_tmpl:
                    product_tmpl = self.env['product.template'].create({
                        'name': item.get('Product'),
                        'default_code': item.get('Product/Internal Reference'),
                        'barcode': item.get('Product/Barcode')
                    })
                    warning_msg += f"\n◼ Created new product on row {row}"

                vals['product_tmpl_id'] = product_tmpl.id
            else:
                error_msg += f"\n⚠ Product missing on row {row}"

            # Otras propiedades
            vals['product_qty'] = item.get('Quantity') or 1.0
            vals['code'] = item.get('Reference') or ''

            bom_type = self.bom_type
            if bom_type == 'both' and item.get('BoM Type'):
                bom_type = 'manufacture_this_product' if item['BoM Type'] == 'Manufacture this product' else 'kit'
            vals['type'] = 'normal' if bom_type == 'manufacture_this_product' else 'phantom'

            # Componentes
            components = {}
            if self.bom_component == 'add' and item.get('Components'):
                product_component = False
                if item.get('Components/Internal Reference'):
                    product_component = self.env['product.product'].search([
                        ('default_code', '=', item.get('Components/Internal Reference'))], limit=1)
                elif item.get('Components/Barcode'):
                    product_component = self.env['product.product'].search([
                        ('barcode', '=', item.get('Components/Barcode'))], limit=1)
                else:
                    product_component = self.env['product.product'].search([
                        ('name', '=', item.get('Components'))], limit=1)

                if not product_component:
                    product_component = self.env['product.product'].create({
                        'name': item.get('Components'),
                        'default_code': item.get('Components/Internal Reference'),
                        'barcode': item.get('Components/Barcode'),
                    })
                    warning_msg += f"\n◼ Created new component on row {row}"

                components = {
                    'product_id': product_component.id,
                    'product_qty': item.get('BoM Lines/Quantity') or 1.0
                }
                vals['bom_line_ids'] = [(0, 0, components)]

            # Crear o actualizar BOM
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
                'message': f"✅ Imported: {imported}, Updated: {updated}{warning_msg}",
                'type': 'rainbow_man',
            }
        }

    def action_test_import_bom(self):
        if not self.file_upload:
            raise ValidationError("Por favor, sube un archivo válido antes de continuar.")

        datas = {}
        errors = ""

        # Load CSV
        if self.file_type == 'csv':
            try:
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                datas = csv.DictReader(data_file, delimiter=',')
            except Exception:
                raise ValidationError("Archivo CSV no válido.")

        # Load XLS
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
                raise ValidationError("Invalid XLS file.")

        row = 0

        for item in datas:
            row += 1

            # Verificar Producto
            if not item.get('Product'):
                errors += f"Product missing on row {row}\n"

            # Validación de cantidad
            quantity = item.get('Quantity')
            if quantity is None or quantity == "":
                errors += f"Quantity is missing or empty on row {row}\n"
            else:
                try:
                    # Verificar que la cantidad sea un número
                    float(quantity)
                except ValueError:
                    errors += f"Invalid quantity on row {row}: {quantity}\n"

            # Validación de componentes (si se añaden componentes)
            if self.bom_component == 'add' and item.get('Components'):
                component_error = False
                try:
                    # Verificar que la cantidad del componente sea un número
                    component_quantity = item.get('BoM Lines/Quantity')
                    if component_quantity is None or component_quantity == "":
                        errors += f"Component quantity missing on row {row}\n"
                    else:
                        float(component_quantity)  # Verificar que sea un número
                except ValueError:
                    component_error = True
                if component_error:
                    errors += f"Invalid component quantity on row {row}\n"

        # Si hay errores, lanzamos un mensaje de validación
        if errors:
            raise ValidationError(errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validation Success',
                'message': 'The file was validated successfully',
                'sticky': False,
            }
        }
