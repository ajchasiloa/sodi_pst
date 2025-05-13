# -*- coding: utf-8 -*-
import base64
import binascii
import csv
import io
import tempfile
import xlrd
import re
import xlsxwriter
from io import BytesIO
from odoo import fields, models
from odoo.exceptions import ValidationError
import datetime


class ImportPurchaseOrder(models.TransientModel):
    _name = 'import.purchase.order'
    _description = 'Purchase Order import'

    file_type = fields.Selection(
        selection=[('csv', 'CSV File'), ('xlsx', 'XLSX File')],
        string='Select File Type', default='csv',
        help="File type to import")
    file_upload = fields.Binary(string="File Upload",
                                help="Helps to upload your file")
    auto_confirm_quot = fields.Boolean(
        string='Confirm Quotation Automatically',
        help="Automatically confirm the quotation")
    order_number = fields.Selection(
        selection=[('from_system', 'From System'),
                ('from_file', 'From File')],
        string='Reference', default='from_file', help="reference")
    import_product_by = fields.Selection(
        selection=[('name', 'Name'), ('default_code', 'Internal Reference'),
                ('barcode', 'Barcode')],
        default="name", string="Import order by", help="import product")

    def action_test_import_purchase_order(self):
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
                if len(rows) <= 1:  # If only header is present
                    raise ValidationError("The CSV file is empty or missing data.")
            except Exception as e:
                raise ValidationError(f"Error reading the CSV file: {str(e)}")
        elif self.file_type == 'xlsx':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                if sheet.nrows <= 1:  # If only header is present
                    raise ValidationError("The XLSX file is empty or missing data.")
            except Exception as e:
                raise ValidationError(f"Error reading the XLSX file: {str(e)}")

        # Validate required fields
        if self.import_product_by not in ['name', 'default_code', 'barcode']:
            raise ValidationError("Invalid import product option. It should be 'name', 'default_code', or 'barcode'.")
        
        if not self.order_number:
            raise ValidationError("Order number reference must be selected.")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Test Success',
                'message': 'The file has passed validation.',
                'sticky': False,
            }
        }

    def action_generate_template(self):
        """Genera una plantilla Excel para importar órdenes de compra con los encabezados correctos"""

        field_labels = [
            "Referencia de Pedido",        # Order Reference
            "Proveedor",                   # Vendor
            "Referencia del Proveedor",    # Vendor Reference
            "Fecha Límite de Pedido",      # Order Deadline
            "Fecha de Recepción",          # Receipt Date
            "Representante de Compras",    # Purchase Representative
            "Producto",                    # Product
            "Referencia Interna",          # Internal Reference
            "Código de Barras",            # Barcode
            "Valores de Variante",         # Variant Values
            "Descripción",                 # Description
            "Cantidad",                    # Quantity
            "UoM",                         # Uom
            "Precio Unitario",             # Unit Price
            "Fecha de Entrega",            # Delivery Date
            "Impuestos"                    # Taxes
        ]

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Plantilla Importación OC")

        # Estilo del encabezado
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9'})
        for col, label in enumerate(field_labels):
            worksheet.write(0, col, label, header_format)

        # Añadir una fila de ejemplo
        example_data = [
            "PO12345",                # Order Reference
            "Proveedor A",            # Vendor
            "V12345",                 # Vendor Reference
            "31/12/2024",             # Order Deadline
            "15/01/2025",             # Receipt Date
            "Juan Pérez",             # Purchase Representative
            "Producto X",             # Product
            "12345",                  # Internal Reference
            "123456789012",           # Barcode
            "Color: Rojo",            # Variant Values
            "Descripción del Producto", # Description
            "100",                    # Quantity
            "Unidad",                 # UoM
            "50",                     # Unit Price
            "30/01/2025",             # Delivery Date
            "IVA 21%"                 # Taxes
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

        # Crear adjunto
        attachment = self.env['ir.attachment'].create({
            'name': 'plantilla_importación_orden_compras.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()).decode(),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_import_purchase_order(self):
        """Creating purchase record using uploaded xl/csv files"""
        purchase_order = self.env['purchase.order']
        res_partner = self.env['res.partner']
        res_users = self.env['res.users']
        product_product = self.env['product.product']
        product_attribute = self.env['product.attribute']
        product_attribute_value = self.env['product.attribute.value']
        product_template_attribute_value = self.env['product.template.attribute.value']
        account_tax = self.env['account.tax']
        uom_uom = self.env['uom.uom']

        # Mapeo de nombres de columnas flexibles
        column_mapping = {
            'order_reference': [
                'Order Reference', 
                'Referencia de Pedido', 
                'Número de Pedido', 
                'PO Number',
                'Reference',
                'Referencia'
            ],
            'vendor': [
                'Vendor', 
                'Proveedor', 
                'Supplier',
                'Nombre del Proveedor',
                'Vendor Name',
                'Supplier Name'
            ],
            'product': [
                'Product', 
                'Producto', 
                'Product Name',
                'Nombre del Producto',
                'Item',
                'Artículo'
            ],
            'quantity': [
                'Quantity', 
                'Cantidad', 
                'Cant.',
                'Qty',
                'Amount',
                'Monto'
            ],
            'unit_price': [
                'Unit Price', 
                'Precio Unitario', 
                'Precio',
                'Price',
                'Cost',
                'Costo'
            ],
            'vendor_reference': [
                'Vendor Reference',
                'Referencia del Proveedor',
                'Supplier Reference',
                'Reference Number'
            ],
            'order_deadline': [
                'Order Deadline',
                'Fecha Límite',
                'Deadline',
                'Due Date'
            ],
            'receipt_date': [
                'Receipt Date',
                'Fecha de Recepción',
                'Delivery Date',
                'Fecha de Entrega'
            ],
            'purchase_representative': [
                'Purchase Representative',
                'Representante de Compras',
                'Buyer',
                'Comprador'
            ],
            'internal_reference': [
                'Internal Reference',
                'Referencia Interna',
                'SKU',
                'Código Interno'
            ],
            'barcode': [
                'Barcode',
                'Código de Barras',
                'EAN13',
                'UPC'
            ],
            'variant_values': [
                'Variant Values',
                'Valores de Variante',
                'Attributes',
                'Atributos'
            ],
            'description': [
                'Description',
                'Descripción',
                'Product Description',
                'Descripción del Producto'
            ],
            'uom': [
                'UoM',
                'Unidad de Medida',
                'Unit',
                'Unidad'
            ],
            'taxes': [
                'Taxes',
                'Impuestos',
                'Tax',
                'VAT'
            ]
        }

        def find_column(item, column_options):
            """Buscar columna de manera flexible"""
            for option in column_options:
                for key in item.keys():
                    if option.lower() == key.lower().strip():
                        return key
            return None

        # Preparar archivo de importación
        if self.file_type == 'csv':
            try:
                csv_data = base64.b64decode(self.file_upload)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                csv_reader = csv.DictReader(data_file, delimiter=',')
                items = list(csv_reader)
            except Exception as e:
                raise ValidationError(f"Error reading CSV file: {str(e)}")

        elif self.file_type == 'xlsx':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file_upload))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                
                # Obtener encabezados
                headers = [str(sheet.cell_value(0, col)).strip() for col in range(sheet.ncols)]
                
                # Convertir datos
                items = []
                for row in range(1, sheet.nrows):
                    row_data = {}
                    for col, header in enumerate(headers):
                        value = str(sheet.cell_value(row, col)).strip()
                        row_data[header] = value
                    items.append(row_data)
            except Exception as e:
                raise ValidationError(f"Error reading XLSX file: {str(e)}")

        # Variables de seguimiento
        row = 0
        imported = 0
        confirmed = 0
        imported_purchaseorders = []
        error_msg = ""
        vendor_added_msg = ""
        warning_msg = ""

        # Procesar cada elemento
        for item in items:
            row += 1

            # Encontrar columnas flexiblemente
            order_ref_col = find_column(item, column_mapping['order_reference'])
            vendor_col = find_column(item, column_mapping['vendor'])
            product_col = find_column(item, column_mapping['product'])
            quantity_col = find_column(item, column_mapping['quantity'])
            price_col = find_column(item, column_mapping['unit_price'])
            vendor_ref_col = find_column(item, column_mapping['vendor_reference'])
            deadline_col = find_column(item, column_mapping['order_deadline'])
            receipt_col = find_column(item, column_mapping['receipt_date'])
            rep_col = find_column(item, column_mapping['purchase_representative'])

            # Validar campos requeridos
            if not order_ref_col or not vendor_col:
                error_msg += f"\n❌Fila {row} no importada. Faltan columnas requeridas (Referencia o Proveedor)."
                continue

            # Obtener valores
            order_reference = item.get(order_ref_col, '').strip()
            vendor_name = item.get(vendor_col, '').strip()
            vendor_reference = item.get(vendor_ref_col, '').strip() if vendor_ref_col else ''
            order_deadline = item.get(deadline_col, '').strip() if deadline_col else ''
            receipt_date = item.get(receipt_col, '').strip() if receipt_col else ''
            purchase_rep = item.get(rep_col, '').strip() if rep_col else ''

            # Validar que los campos no estén vacíos
            if not order_reference or not vendor_name:
                error_msg += f"\n❌Fila {row} no importada. Referencia de Pedido o Proveedor vacíos."
                continue

            # Procesar proveedor
            vendor = res_partner.search([
                '|', 
                ('name', '=', vendor_name),
                ('name', 'ilike', vendor_name)
            ], limit=1)

            if not vendor:
                try:
                    vendor = res_partner.create({
                        'name': vendor_name,
                        'supplier_rank': 1,  # Marcar como proveedor
                        'company_type': 'company'
                    })
                    vendor_added_msg += f"\n\t🆕 Nuevo proveedor creado: {vendor_name}"
                except Exception as e:
                    error_msg += f"\n❌Fila {row} no importada. Error creando proveedor: {str(e)}"
                    continue

            # Crear orden de compra
            try:
                vals = {
                    'partner_id': vendor.id,
                    'name': order_reference,
                    'partner_ref': vendor_reference,
                }

                # Agregar fecha límite si existe
                if order_deadline:
                    try:
                        vals['date_order'] = datetime.datetime.strptime(order_deadline, '%d/%m/%Y')
                    except ValueError:
                        warning_msg += f"\n⚠️ Fila {row}: Formato de fecha límite inválido, se usará la fecha actual."

                # Agregar fecha de recepción si existe
                if receipt_date:
                    try:
                        vals['date_planned'] = datetime.datetime.strptime(receipt_date, '%d/%m/%Y')
                    except ValueError:
                        warning_msg += f"\n⚠️ Fila {row}: Formato de fecha de recepción inválido, se usará la fecha actual."

                # Agregar representante de compras si existe
                if purchase_rep:
                    user = res_users.search([('name', 'ilike', purchase_rep)], limit=1)
                    if user:
                        vals['user_id'] = user.id
                    else:
                        warning_msg += f"\n⚠️ Fila {row}: Representante de compras no encontrado."

                # Buscar si ya existe una orden con esta referencia
                existing_po = purchase_order.search([('name', '=', order_reference)])
                
                if existing_po:
                    existing_po.write(vals)
                    purchaseorder = existing_po[0]
                else:
                    purchaseorder = purchase_order.create(vals)

                # Procesar las líneas de productos
                if not all([product_col, quantity_col, price_col]):
                    error_msg += f"\n❌Fila {row} no importada. Faltan columnas de producto."
                    continue

                product_name = item.get(product_col, '').strip()
                quantity = item.get(quantity_col, '').strip()
                unit_price = item.get(price_col, '').strip()

                # Validar que la cantidad y el precio sean números válidos
                try:
                    quantity = float(quantity)
                    unit_price = float(unit_price)
                except ValueError:
                    error_msg += f"\n❌Fila {row} no importada. La cantidad o el precio no son válidos."
                    continue

                # Buscar producto según el método de importación seleccionado
                domain = []
                if self.import_product_by == 'name':
                    domain = [('name', '=', product_name)]
                elif self.import_product_by == 'default_code':
                    domain = [('default_code', '=', product_name)]
                elif self.import_product_by == 'barcode':
                    domain = [('barcode', '=', product_name)]

                product = product_product.search(domain, limit=1)

                if not product:
                    try:
                        product = product_product.create({
                            'name': product_name,
                            'type': 'product',
                            'purchase_ok': True,
                        })
                        warning_msg += f"\n\t🆕 Nuevo producto creado: {product_name}"
                    except Exception as e:
                        error_msg += f"\n❌Fila {row} no importada. Error creando producto: {str(e)}"
                        continue

                # Crear la línea de la orden de compra
                self.env['purchase.order.line'].create({
                    'order_id': purchaseorder.id,
                    'product_id': product.id,
                    'product_qty': quantity,
                    'price_unit': unit_price,
                    'name': product.name,
                    'date_planned': vals.get('date_planned', fields.Datetime.now()),
                    'product_uom': product.uom_po_id.id or product.uom_id.id,
                })

                imported += 1
                imported_purchaseorders.append(purchaseorder)

            except Exception as e:
                error_msg += f"\n❌Fila {row} no importada. Error: {str(e)}"
                continue

        # Confirmación automática si está habilitada
        if self.auto_confirm_quot and imported_purchaseorders:
            for po in imported_purchaseorders:
                try:
                    po.button_confirm()
                    confirmed += 1
                except Exception as e:
                    warning_msg += f"\n⚠️ No se pudo confirmar la orden {po.name}: {str(e)}"

        # Generar mensaje de resultado
        if error_msg:
            error_msg = "\n\n⚠ ADVERTENCIA ⚠" + error_msg
            error_message = self.env['import.message'].create({'message': error_msg})
            return {
                'name': '¡Error!',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'import.message',
                'res_id': error_message.id,
                'target': 'new'
            }

        msg = (f"Se importaron {imported} registros.\nSe confirmaron {confirmed} registros" 
               + vendor_added_msg + warning_msg)
        message = self.env['import.message'].create({'message': msg})
        
        if message:
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': msg,
                    'type': 'rainbow_man',
                }
            }