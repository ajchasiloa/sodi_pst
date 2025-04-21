from odoo import _, models, fields, api
from odoo.exceptions import UserError, ValidationError
import io
import base64
import xlsxwriter
import xlrd
import csv


class WizardProducto(models.TransientModel):
    _name = "wizard.producto"
    _description = "Importar Productos"

    # === CAMPOS DEL WIZARD ===
    uom = fields.Many2one("uom.uom", string="Unidad de Medida", help="Unidad de medida estándar para el producto")
    uom_purchase = fields.Many2one("uom.uom", string="Unidad de Medida de Compra", help="Unidad de medida utilizada para la compra")
    can_sell = fields.Boolean(string="Se puede vender", default=True)
    can_purchase = fields.Boolean(string="Se puede comprar", default=True)
    internal_notes = fields.Text(string="Notas internas")
    file = fields.Binary(string="Archivo")
    file_name = fields.Char(string="Nombre del Archivo")

    # === ACCIÓN PRINCIPAL: IMPORTAR PRODUCTOS ===
    def action_import(self):
        productos_creados = 0
        error_message = ""

        if not self.file_name:
            raise UserError("Debe seleccionar un archivo.")

        # Archivos Excel
        if self.file_name.lower().endswith(".xlsx"):
            try:
                data = base64.b64decode(self.file)
                workbook = xlrd.open_workbook(file_contents=data)
                sheet = workbook.sheet_by_index(0)
            except Exception as e:
                raise UserError(f"Error al leer el archivo Excel: {str(e)}")

            if sheet.nrows <= 1:
                raise ValidationError("El archivo Excel está vacío. Debe contener al menos un producto para importar.")

            for row_index in range(1, sheet.nrows):
                row_msg = row_index + 1
                row_data = [str(sheet.cell_value(row_index, col)).strip() for col in range(sheet.ncols)]
                try:
                    self.importar_xlsx_productos(row_data, row_msg)
                    productos_creados += 1
                except Exception as e:
                    error_message += f"Fila {row_msg}: {str(e)}\n"

        # Archivos CSV
        elif self.file_name.lower().endswith(".csv"):
            try:
                data = base64.b64decode(self.file)
                csv_file = io.StringIO(data.decode("utf-8"))
                reader = csv.reader(csv_file, delimiter=",")
                next(reader)
                for idx, row_data in enumerate(reader, start=2):
                    self.importar_xlsx_productos(row_data, idx)
                    productos_creados += 1
            except Exception as e:
                raise UserError(f"Error al leer el archivo CSV: {str(e)}")

        # Mostrar errores o mensaje de éxito
        if error_message:
            raise ValidationError(error_message)
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Importación completada",
                    "message": f"Se importaron correctamente {productos_creados} productos.",
                    "type": "success",
                    "sticky": False,
                },
            }

    # === ACCIÓN: EXPORTAR PLANTILLA XLSX ===
    def action_export_template(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        # Hoja 1: Plantilla
        worksheet1 = workbook.add_worksheet("Plantilla Productos")
        header_format = workbook.add_format({
            "bold": True,
            "text_wrap": True,
            "valign": "vcenter",
            "align": "center",
            "border": 1,
            "bg_color": "#D9E1F2",
        })

        headers = [
            "Nombre del Producto", "Unidad de Medida", "Unidad de Medida de Compra", "Se puede Vender",
            "Se puede Comprar", "Notas Internas", "Tipo de Producto", "Política de Facturación",
            "Precio de Venta", "Impuesto al Cliente (15%)", "Costo", "Categoría del Producto",
            "Referencia Interna", "Lista de Precios", "Cantidad Mínima", "Precio", "Atributos", "Valores"
        ]
        for col_num, header in enumerate(headers):
            worksheet1.write(0, col_num, header, header_format)
        worksheet1.set_column(0, len(headers) - 1, 25)

        # Hoja 2: Observaciones
        worksheet2 = workbook.add_worksheet("Observaciones")
        obs_header_format = workbook.add_format({
            "bold": True,
            "text_wrap": True,
            "valign": "vcenter",
            "align": "center",
            "border": 1,
            "bg_color": "#FFD966",
        })

        worksheet2.write("A1", "Observaciones", obs_header_format)
        observaciones = [
            "Nombre del Producto: Escribir el nombre comercial del producto, ejemplo: Camiseta Polo.",
            "Unidad de Medida: Especificar la unidad (mm, g, cm, en, oz, fl oz, etc.).",
            "Unidad de Medida de Compra: Especificar la unidad utilizada en compras.",
            'Se puede Vender: Escribir "True" o "False si no se puede vender".',
            'Se puede Comprar: Escribir "True" o "False si no se puede comprar".',
            "Notas Internas: Escribir cualquier nota interna sobre el producto.",
            "Tipo de Producto: Comestible, Servicio o Producto almacenable.",
            "Política de Facturación: Cantidad ordenada o Cantidades entregadas.",
            "Precio de Venta: Número positivo.",
            'Impuesto al Cliente (15%): Escribir "15%".',
            "Costo: Número positivo.",
            "Categoría del Producto: All, All/Expenses, All/Saleable.",
            "Referencia Interna: Código único interno.",
            'Lista de Precios: Ej. "Lista de precios USD predeterminada o Mayorista".',
            "Cantidad Mínima: Número entero positivo.",
            "Precio: Precio correspondiente a la cantidad mínima.",
            "Atributos: Nombre del atributo, ej. Color.",
            "Valores: Valor del atributo, ej. Rojo.",
        ]
        for idx, obs in enumerate(observaciones, start=1):
            worksheet2.write(idx, 0, obs)
        worksheet2.set_column(0, 0, 80)

        # Guardar archivo y adjuntarlo
        workbook.close()
        file_data = base64.b64encode(output.getvalue())
        output.close()

        attachment = self.env["ir.attachment"].create({
            "name": "plantilla_productos.xlsx",
            "type": "binary",
            "datas": file_data,
            "res_model": "wizard.producto",
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    # === ACCIÓN: VALIDAR DATOS SIN IMPORTAR ===
    def action_test(self):
        if not self.file or not self.file_name:
            raise UserError("¡Debe subir un archivo válido con nombre!")

        error_message = ""

        if self.file_name.lower().endswith(".xlsx"):
            try:
                data = base64.b64decode(self.file)
                workbook = xlrd.open_workbook(file_contents=data)
                sheet = workbook.sheet_by_index(0)
            except Exception as e:
                raise UserError(f"Error al leer el archivo Excel: {str(e)}")

            if sheet.nrows <= 1:
                raise ValidationError(_("El archivo Excel está vacío. Debe contener al menos un producto para validar."))

            for row_index in range(1, sheet.nrows):
                row = row_index + 1
                row_data = [str(sheet.cell_value(row_index, col)).strip() for col in range(sheet.ncols)]
                error_message += self._validate_row(row_data, row)

        elif self.file_name.lower().endswith(".csv"):
            try:
                data = base64.b64decode(self.file)
                data_decoded = data.decode("utf-8")
                reader = csv.reader(io.StringIO(data_decoded))
                rows = list(reader)
            except Exception as e:
                raise UserError(f"Error al leer el archivo CSV: {str(e)}")

            if len(rows) <= 1:
                raise ValidationError(_("El archivo CSV está vacío."))

            for row_index, row_data in enumerate(rows[1:], start=2):
                if len(row_data) < 16:
                    error_message += f"Fila {row_index}: Datos incompletos.\n"
                    continue
                error_message += self._validate_row(row_data, row_index)

        else:
            raise UserError("Formato de archivo no soportado. Solo .xlsx o .csv.")

        if error_message:
            raise ValidationError(error_message)
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Validación exitosa",
                    "message": "¡Todo parece correcto en el archivo de productos!",
                    "type": "success",
                    "sticky": False,
                },
            }

    # === VALIDACIÓN DE CADA FILA ===
    def _validate_row(self, row_data, row):
        error_message = ""

        try:
            nombre_producto = row_data[0]
            uom = row_data[1]
            uom_purchase = row_data[2]
            can_sell = row_data[3].strip().lower() in ["true", "1"]
            can_purchase = row_data[4].strip().lower() in ["true", "1"]
            internal_notes = row_data[5]
            tipo_producto = row_data[6]
            politica_facturacion = row_data[7]
            precio_venta = row_data[8]
            impuesto_cliente = row_data[9]
            costo = row_data[10]
            categoria_producto = row_data[11]
            referencia_interna = row_data[12]
            lista_precios = row_data[13]
            cantidad_minima = row_data[14]
            precio_lista = row_data[15]
            nombre_atributo = row_data[16].strip()
            valor_atributo = row_data[17].strip()

            if nombre_atributo and valor_atributo:
                atributo = self.env["product.attribute"].search([("name", "=", nombre_atributo)], limit=1)
                if not atributo:
                    pass 

                else:
                    valor = self.env["product.attribute.value"].search([
                        ("name", "=", valor_atributo),
                        ("attribute_id", "=", atributo.id)
                    ], limit=1)
                    if not valor:
                        error_message += (
                            f"Fila {row}: El valor '{valor_atributo}' no existe para el atributo '{nombre_atributo}'. Será creado en la importación.\n"
                        )
        except IndexError:
            error_message += f"Fila {row}: Atributo o valor de atributo faltante.\n"

        except IndexError:
            return f"Fila {row}: Datos incompletos en la fila."

        if not nombre_producto:
            error_message += f"Fila {row}: Nombre del Producto vacío.\n"

        unidad = self.env["uom.uom"].search([("name", "=", uom)], limit=1)
        if not unidad:
            error_message += f"Fila {row}: Unidad de Medida inválida ('{uom}').\n"

        unidad_compra = self.env["uom.uom"].search(
            [("name", "=", uom_purchase)], limit=1
        )
        if not unidad_compra:
            error_message += (
                f"Fila {row}: Unidad de Medida de Compra inválida ('{uom_purchase}').\n"
            )

        if tipo_producto not in ["Comestible", "Servicio", "Producto almacenable"]:
            error_message += (
                f"Fila {row}: Tipo de Producto inválido ('{tipo_producto}').\n"
            )

        if politica_facturacion not in ["Cantidad ordenada", "Cantidades entregadas"]:
            error_message += f"Fila {row}: Política de Facturación inválida ('{politica_facturacion}').\n"

        try:
            precio = float(str(precio_venta).replace(",", "."))
            if precio < 0:
                error_message += (
                    f"Fila {row}: Precio de Venta negativo ('{precio_venta}').\n"
                )
        except Exception:
            error_message += (
                f"Fila {row}: Precio de Venta inválido ('{precio_venta}').\n"
            )

        try:
            impuesto_str = str(impuesto_cliente).replace("%", "").strip()
            impuesto_float = float(impuesto_str)
            if not (
                abs(impuesto_float - 15.0) < 0.01 or abs(impuesto_float - 0.15) < 0.001
            ):
                raise ValueError
        except Exception:
            error_message += (
                f"Fila {row}: Impuesto al Cliente inválido ('{impuesto_cliente}').\n"
            )

        nombre_atributo = row_data[16].strip()
        valor_atributo = row_data[17].strip()

        if nombre_atributo and valor_atributo:
            atributo = self.env["product.attribute"].search([("name", "=", nombre_atributo)], limit=1)
            if not atributo:
                pass 

            else:
                valor = self.env["product.attribute.value"].search([
                    ("name", "=", valor_atributo),
                    ("attribute_id", "=", atributo.id)
                ], limit=1)
                if not valor:
                    error_message += (
                            f"Fila {row}: El valor '{valor_atributo}' no existe para el atributo '{nombre_atributo}'. Será creado en la importación.\n"
                        )
            
        try:
            costo_valor = float(str(costo).replace(",", "."))
            if costo_valor < 0:
                error_message += f"Fila {row}: Costo negativo ('{costo}').\n"
        except Exception:
            error_message += f"Fila {row}: Costo inválido ('{costo}').\n"

        if categoria_producto not in ["All", "All/Expenses", "All/Saleable"]:
            error_message += f"Fila {row}: Categoría del Producto inválida ('{categoria_producto}').\n"

        if not referencia_interna:
            error_message += f"Fila {row}: Referencia Interna vacía.\n"

        if not lista_precios:
            error_message += f"Fila {row}: Lista de Precios vacía.\n"

        try:
            cantidad_min = float(str(cantidad_minima).replace(",", "."))
            if cantidad_min < 0:
                error_message += (
                    f"Fila {row}: Cantidad Mínima negativa ('{cantidad_minima}').\n"
                )
        except Exception:
            error_message += (
                f"Fila {row}: Cantidad Mínima inválida ('{cantidad_minima}').\n"
            )

        try:
            precio_lis = float(str(precio_lista).replace(",", "."))
            if precio_lis < 0:
                error_message += (
                    f"Fila {row}: Precio de Lista negativo ('{precio_lista}').\n"
                )
        except Exception:
            error_message += (
                f"Fila {row}: Precio de Lista inválido ('{precio_lista}').\n"
            )

        return error_message

    # === IMPORTACIÓN FINAL DE CADA FILA XLSX/CSV ===
    def importar_xlsx_productos(self, row_data, row):
        try:
            name = row_data[0]
            unidad = row_data[1]
            unidad_compra = row_data[2]
            sale_ok = row_data[3].strip().lower() in ["true", "1"]
            purchase_ok = row_data[4].strip().lower() in ["true", "1"]
            internal_notes = row_data[5]
            tipo_producto = row_data[6].strip().lower()
            if tipo_producto == "producto almacenable":
                detailed_type = "product"
            elif tipo_producto == "consumible":
                detailed_type = "consu"
            elif tipo_producto == "servicio":
                detailed_type = "service"
            else:
                raise UserError(f"Tipo de producto no válido: {tipo_producto}")
            politica = row_data[7].strip().lower()
            politicas_validas = {
                "cantidad ordenada": "order",
                "cantidades entregadas": "delivery",
            }
            invoice_policy = politicas_validas.get(politica)
            if not invoice_policy:
                raise UserError(f"Política inválida: {politica}")

            print(invoice_policy)

            list_price = float(row_data[8].replace(",", "."))
            costo = float(row_data[10].replace(",", "."))
            categoria_nombre = row_data[11]
            default_code = row_data[12]
            lista_precios_nombre = row_data[13]
            cantidad_minima = float(row_data[14])
            precio_fijo = float(row_data[15].replace(",", "."))

            producto_existente = self.env["product.template"].search(
                ["|", ("name", "=", name), ("default_code", "=", default_code)], limit=1
            )

            if producto_existente:
                raise UserError(
                    f"El producto '{name}' con referencia '{default_code}' ya existe."
                )

            uom = self.env["uom.uom"].search([("name", "ilike", unidad)], limit=1)
            uom_po = self.env["uom.uom"].search(
                [("name", "ilike", unidad_compra)], limit=1
            )
            categoria = self.env["product.category"].search(
                [("name", "ilike", categoria_nombre)], limit=1
            )
            if not categoria:
                categoria = self.env["product.category"].create(
                    {"name": categoria_nombre}
                )
            if not uom or not uom_po:
                raise Exception(
                    f"Unidad o unidad de compra no encontrada: {unidad} / {unidad_compra}"
                )

            producto = self.env["product.template"].create(
                {
                    "name": name,
                    "default_code": default_code,
                    "list_price": list_price,
                    "standard_price": costo,
                    "description": internal_notes,
                    "sale_ok": sale_ok,
                    "purchase_ok": purchase_ok,
                    "detailed_type": detailed_type,
                    "type": (
                        "product"
                        if tipo_producto == "producto almacenable"
                        else "service"
                    ),
                    "uom_id": uom.id,
                    "uom_po_id": uom_po.id,
                    "categ_id": categoria.id,
                    "invoice_policy": invoice_policy,
                }
            )
            lista_precios = self.env["product.pricelist"].search(
                [("name", "ilike", lista_precios_nombre.strip())], limit=1
            )

            if not lista_precios:
                raise UserError(_("Lista de precios no encontrada: '%s'") % lista_precios_nombre)

            self.env["product.pricelist.item"].create({
                "product_tmpl_id": producto.id,
                "pricelist_id": lista_precios.id,
                "min_quantity": cantidad_minima,
                "fixed_price": precio_fijo,
            })


            nombre_atributo = row_data[16].strip()
            valor_atributo = row_data[17].strip()

            if nombre_atributo and valor_atributo:
                atributo = self.env["product.attribute"].search([("name", "=", nombre_atributo)], limit=1)
                if not atributo:
                    atributo = self.env["product.attribute"].create({"name": nombre_atributo})
                valor = self.env["product.attribute.value"].search([
                    ("name", "=", valor_atributo),
                    ("attribute_id", "=", atributo.id)
                ], limit=1)
                if not valor:
                    valor = self.env["product.attribute.value"].create({
                        "name": valor_atributo,
                        "attribute_id": atributo.id
                    })
                self.env["product.template.attribute.line"].create({
                    "product_tmpl_id": producto.id,
                    "attribute_id": atributo.id,
                    "value_ids": [(6, 0, [valor.id])],
                })

        except Exception as e:
            raise Exception(f"Error al crear producto {name}: {str(e)}")

        return 1
    def importar_csv_productos(self):
        productos_creados = 0
        errores = ""
        
        data = base64.b64decode(self.file)
        csv_file = io.StringIO(data.decode("utf-8"))
        reader = csv.reader(csv_file, delimiter=",")
        next(reader)  

        if len(rows) <= 1:
            raise ValidationError("El archivo CSV está vacío.")

        for row_index, row_data in enumerate(reader, start=2):
            try:
                name = row_data[0]
                unidad = row_data[1]
                unidad_compra = row_data[2]
                sale_ok = row_data[3].strip().lower() in ["true", "1"]
                purchase_ok = row_data[4].strip().lower() in ["true", "1"]
                internal_notes = row_data[5]
                tipo_producto = row_data[6].strip().lower()
                if tipo_producto == "producto almacenable":
                    detailed_type = "product"
                elif tipo_producto == "consumible":
                    detailed_type = "consu"
                elif tipo_producto == "servicio":
                    detailed_type = "service"
                else:
                    raise UserError(f"Fila {row_index}: Tipo de producto no válido: {tipo_producto}")

                politica = row_data[7].strip().lower()
                politicas_validas = {
                    "cantidad ordenada": "order",
                    "cantidades entregadas": "delivery",
                }
                invoice_policy = politicas_validas.get(politica)
                if not invoice_policy:
                    raise UserError(f"Fila {row_index}: Política inválida: {politica}")

                list_price = float(row_data[8].replace(",", "."))
                costo = float(row_data[10].replace(",", "."))
                categoria_nombre = row_data[11]
                default_code = row_data[12]
                lista_precios_nombre = row_data[13]
                cantidad_minima = float(row_data[14])
                precio_fijo = float(row_data[15].replace(",", "."))

                producto_existente = self.env["product.template"].search(
                    ["|", ("name", "=", name), ("default_code", "=", default_code)], limit=1
                )
                if producto_existente:
                    raise UserError(f"Fila {row_index}: Producto '{name}' con referencia '{default_code}' ya existe.")

                uom = self.env["uom.uom"].search([("name", "ilike", unidad)], limit=1)
                uom_po = self.env["uom.uom"].search([("name", "ilike", unidad_compra)], limit=1)
                categoria = self.env["product.category"].search([("name", "ilike", categoria_nombre)], limit=1)
                if not categoria:
                    categoria = self.env["product.category"].create({"name": categoria_nombre})
                if not uom or not uom_po:
                    raise Exception(f"Fila {row_index}: Unidad o unidad de compra no encontrada: {unidad} / {unidad_compra}")

                producto = self.env["product.template"].create({
                    "name": name,
                    "default_code": default_code,
                    "list_price": list_price,
                    "standard_price": costo,
                    "description": internal_notes,
                    "sale_ok": sale_ok,
                    "purchase_ok": purchase_ok,
                    "detailed_type": detailed_type,
                    "type": "product" if tipo_producto == "producto almacenable" else "service",
                    "uom_id": uom.id,
                    "uom_po_id": uom_po.id,
                    "categ_id": categoria.id,
                    "invoice_policy": invoice_policy,
                })

                lista_precios = self.env["product.pricelist"].search(
                    [("name", "ilike", lista_precios_nombre.strip())], limit=1
                )
                if not lista_precios:
                    raise UserError(f"Fila {row_index}: Lista de precios no encontrada: '{lista_precios_nombre}'")

                self.env["product.pricelist.item"].create({
                    "product_tmpl_id": producto.id,
                    "pricelist_id": lista_precios.id,
                    "min_quantity": cantidad_minima,
                    "fixed_price": precio_fijo,
                })
                if len(row_data) >= 18:
                    nombre_atributo = row_data[16].strip()
                    valor_atributo = row_data[17].strip()
                    if nombre_atributo and valor_atributo:
                        atributo = self.env["product.attribute"].search([("name", "=", nombre_atributo)], limit=1)
                        if not atributo:
                            atributo = self.env["product.attribute"].create({"name": nombre_atributo})
                        valor = self.env["product.attribute.value"].search([
                            ("name", "=", valor_atributo),
                            ("attribute_id", "=", atributo.id)
                        ], limit=1)
                        if not valor:
                            valor = self.env["product.attribute.value"].create({
                                "name": valor_atributo,
                                "attribute_id": atributo.id
                            })
                        self.env["product.template.attribute.line"].create({
                            "product_tmpl_id": producto.id,
                            "attribute_id": atributo.id,
                            "value_ids": [(6, 0, [valor.id])],
                        })

                productos_creados += 1

            except Exception as e:
                errores += f"{str(e)}\n"

        if errores:
            raise ValidationError(_("Errores durante la importación:\n") + errores)

        return productos_creados
