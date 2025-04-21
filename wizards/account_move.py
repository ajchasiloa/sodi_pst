import base64
from datetime import datetime, timedelta
import xlrd
import os
from io import BytesIO
import xlsxwriter

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.TransientModel):
    _name = "import.account.move.wizard"
    _description = "Import account move wizard"

    move_type = fields.Selection(
        [("out_invoice", "Customer Invoice"), ("in_invoice", "Vendor Bill")],
        string="Move type",
        required=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain=[("type", "in", ("sale", "purchase"))],
    )
    xlsx_file = fields.Binary("File", required=True)
    search_product = fields.Selection(
        [("name", "Name"), ("default_code", "Internal Reference")],
        string="Search product by",
        required=True,
        default="name",
    )
    invoice_state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted")],
        string="Invoice state",
        required=True,
        default="draft",
    )

    def _get_journal_domain(self):
        if self.move_type == "out_invoice":
            return [("type", "=", "sale")]
        elif self.move_type == "in_invoice":
            return [("type", "=", "purchase")]
        else:
            return [("type", "in", ("sale", "purchase"))]

    @api.onchange("move_type")
    def _onchange_move_type(self):
        if self.move_type:
            return {"domain": {"journal_id": self._get_journal_domain()}}

    def parse_date(self, value):
        try:
            # Si es tipo float (fecha Excel)
            if isinstance(value, float):
                try:
                    return xlrd.xldate.xldate_as_datetime(value, 0).date()
                except Exception:
                    base_date = datetime(1899, 12, 30)
                    return (base_date + timedelta(days=int(value))).date()

            # Si es tipo string (texto en Excel)
            elif isinstance(value, str):
                value = value.strip()
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                    try:
                        return datetime.strptime(value, fmt).date()
                    except ValueError:
                        continue
                raise ValueError(f"Date string '{value}' does not match expected formats (dd/mm/yyyy, yyyy-mm-dd, etc)")

            raise ValueError(f"Unsupported date format: {value}")

        except Exception as e:
            raise ValueError(f"Error al procesar la fecha '{value}': {str(e)}")

    def action_import(self):
        if self.xlsx_file:
            try:
                data = base64.b64decode(self.xlsx_file)
                workbook = xlrd.open_workbook(file_contents=data)
                sheet = workbook.sheet_by_index(0)
            except Exception as e:
                raise ValidationError(f"Error al abrir el archivo: {str(e)}")

            invoices = []
            error_message = ""
            invoice = {}
            invoice_lines = []

            # Process the XLSX data and create the invoice
            # Skip header row, start from 2nd row
            for row_index in range(1, sheet.nrows):
                row = row_index + 1

                name = sheet.cell(row_index, 0).value
                support_document = sheet.cell(row_index, 1).value
                partner_name = sheet.cell(row_index, 2).value
                date_string = sheet.cell(row_index, 3).value
                end_date_string = sheet.cell(row_index, 4).value
                tax_support = sheet.cell(row_index, 6).value
                doc_type = sheet.cell(row_index, 7).value
                sales_partner = sheet.cell(row_index, 8).value
                account = sheet.cell(row_index, 9).value
                label = sheet.cell(row_index, 10).value
                quantity = sheet.cell(row_index, 11).value
                price = sheet.cell(row_index, 12).value

                if name:
                    name_id = self.env["account.move"].search([("name", "=", name)])
                    if name_id:
                        error_message += "Invoice '%s' already exists, on row %s \n" % (
                            name,
                            row,
                        )
                        continue

                if partner_name:
                    partner_id = self.env["res.partner"].search([("name", "=", partner_name)])

                    if not partner_id:
                        error_message += "Partner '%s' not found, on row %s \n" % (
                            partner_name,
                            row,
                        )
                        continue

                    try:
                        date = self.parse_date(date_string)
                    except ValueError as e:
                        error_message += str(e) + ", on row %s \n" % row
                        continue

                    try:
                        end_date = self.parse_date(end_date_string)
                    except ValueError as e:
                        error_message += str(e) + ", on row %s \n" % row
                        continue

                    # Omitimos la búsqueda de tax_support ya que el modelo no existe
                    tax_support_id = False

                    # Si no encontramos el modelo de tipo de documento, lo omitimos
                    doc_type_id = False
                    if doc_type:
                        try:
                            doc_type_id = self.env["account.voucher.type"].search([
                                ("name", "ilike", doc_type)
                            ], limit=1)
                        except Exception as e:
                            error_message += f"Error searching voucher type: {str(e)}, on row {row}\n"
                            doc_type_id = False

                    invoice = {
                        "move_type": self.move_type,
                        "journal_id": self.journal_id.id,
                        "partner_id": partner_id.id,
                        "invoice_date": date,
                        "invoice_date_due": end_date,
                        "tax_support": tax_support_id.id if tax_support_id else False,
                        "voucher_type_ats": doc_type_id.id if doc_type_id else False,
                        "is_imported": True,
                    }

                    if self.move_type == "in_invoice":
                        invoice["support_document"] = support_document

                    if self.search_product == "name":
                        product_id = self.env["product.product"].search([
                            ("name", "ilike", label),
                        ], limit=1)
                    else:
                        product_id = self.env["product.product"].search([
                            ("default_code", "=ilike", label),
                        ], limit=1)

                    if not product_id:
                        error_message += "Product '%s' not found, on row %s \n" % (
                            label,
                            row,
                        )
                        continue

                    if account:
                        # Intentamos buscar la cuenta por código
                        try:
                            # Convertimos el valor a un número entero
                            account_code = int(account)
                            # Buscamos la cuenta por código
                            account_id = self.env["account.account"].search([
                                ("code", "=ilike", str(account_code))
                            ], limit=1)
                        except ValueError:
                            # Si no es un número, intentamos buscar por nombre
                            account_id = self.env["account.account"].search([
                                ("name", "=ilike", account)
                            ], limit=1)
                        
                        if not account_id:
                            error_message += "Account code '%s' not found. Please check if the account exists in your chart of accounts, on row %s \n" % (
                                account,
                                row,
                            )
                            continue

                    invoice_lines.append(
                        (
                            0,
                            0,
                            {
                                "product_id": product_id.id,
                                "quantity": float(quantity),
                                "price_unit": float(price),
                                "name": str(label) if label else product_id.display_name,
                                "account_id": account_id.id if account_id else False,
                            },
                        )
                    )

                    if label:
                        invoice_lines[len(invoice_lines) - 1][2]["name"] = str(label)

                    if account:
                        invoice_lines[len(invoice_lines) - 1][2]["account_id"] = account_id.id

                if self.move_type == "out_invoice" and sales_partner:
                    sales_partner_id = self.env["res.partner"].search([
                        ("name", "ilike", sales_partner)
                    ], limit=1)
                    if not sales_partner_id:
                        error_message += "Sales partner '%s' not found, on row %s \n" % (
                            sales_partner,
                            row,
                        )
                        continue
                    invoice["invoice_user_id"] = sales_partner_id.id

            if invoice and invoice_lines:
                invoice["invoice_line_ids"] = invoice_lines
                invoices.append(invoice)

            if error_message:
                raise ValidationError(error_message)

            if invoices:
                res = self.env["account.move"].create(invoices)
                if self.invoice_state == "posted":
                    for record in res:
                        record.post()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Imported successfully'),
                        'sticky': False,
                    }
                }
            else:
                raise ValidationError("No valid invoices found in the file")

    def action_test(self):
        if self.xlsx_file:
            try:
                data = base64.b64decode(self.xlsx_file)
                workbook = xlrd.open_workbook(file_contents=data)
                sheet = workbook.sheet_by_index(0)
            except Exception as e:
                raise ValidationError(f"Error al abrir el archivo: {str(e)}")

            error_message = ""

            for row_index in range(1, sheet.nrows):
                row = row_index + 1
                date_string = sheet.cell(row_index, 3).value
                end_date_string = sheet.cell(row_index, 4).value

                try:
                    date = self.parse_date(date_string)
                    end_date = self.parse_date(end_date_string)
                except ValueError as e:
                    error_message += str(e) + ", on row %s \n" % row
                    continue

            if error_message:
                raise ValidationError(error_message)
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Everything looks correct'),
                        'sticky': False,
                    }
                }

    def action_download_template(self):
        import os

        # Ruta del archivo estático
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'static', 'src', 'data', 'plantilla.xlsx'
        )

        # Verifica existencia
        if not os.path.exists(template_path):
            raise UserError(_("El archivo de plantilla no se encuentra:\n%s") % template_path)

        try:
            with open(template_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            raise UserError(_("No se pudo leer el archivo de plantilla:\n%s") % str(e))

        # Crear attachment sin asignarlo a un registro
        try:
            attachment = self.env['ir.attachment'].create({
                'name': 'plantilla.xlsx',
                'type': 'binary',
                'datas': file_data,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'public': True,
            })
        except Exception as e:
            raise UserError(_("No se pudo crear el archivo de plantilla:\n%s") % str(e))

        # Retornar URL de descarga directaaaa
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
#Modificar en caso de nuevos camposs futurosss
    def action_generate_template(self):
        """Genera una plantilla Excel para importar facturas"""
        
        field_labels = [
            "Número",                  # name
            "Soporte Documento",       # support_document
            "Nombre",                  # partner_name
            "Fecha",                   # invoice_date
            "Fecha de vencimiento",    # invoice_date_due
            "",                        # columna vacía
            "Sustento tributario",     # tax_support
            "Tipo de documento",       # voucher_type_ats
            "Comercial",               # invoice_user_id
            "Cuenta",                  # account
            "Etiqueta",                # label
            "Cantidad",                # quantity
            "Precio",    
            "Prueba"              
        ]

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Import Template")

        # Escribir solo encabezados en la fila 0
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9'})
        for col, label in enumerate(field_labels):
            worksheet.write(0, col, label, header_format)

        workbook.close()
        output.seek(0)

        # Crear attachment y retornar como descarga
        attachment = self.env['ir.attachment'].create({
            'name': 'plantilla_importacion.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()).decode(),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }