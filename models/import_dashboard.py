from odoo import fields, models, api


class ImportDashboard(models.Model):
    _name = "import.dashboard"
    _description = "Import Dashboard"

    name = fields.Char("Import Dashboard")
<<<<<<< HEAD

    # 'state' define el tipo de importación que representa esta tarjeta
    state = fields.Selection([
        ("account.move", "Invoice / Bill"),
        ("import.attendance", "Attendance"),
        ("import.bill.of.material", "BOM"),
        ("import.invoice", "Invoice Import"),
        ("import.payment", "Payment Import"),
        ("import.task", "Task Import"),
        ("import.pos.order", "POS Order"),
        ("import.purchase.order", "Purchase Order"),
        ("wizard.producto", "Product Import"),
        ("import.contact.wizard", "Contact Import"),
    ], required=True)

    # Este campo se controla desde los ajustes
    show_account_move = fields.Boolean(string="Show Account Move", default=False)
    show_attendance = fields.Boolean(string="Show Attendance", default=False)
    show_bom = fields.Boolean(string="Show BOM", default=False)
    show_invoice = fields.Boolean(string="Show Invoice Import", default=False)
    show_payment = fields.Boolean(string="Show Payment Import", default=False)
    show_task = fields.Boolean(string="Show Task", default=False)
    show_pos = fields.Boolean(string="Show POS Order", default=False)
    show_purchase = fields.Boolean(string="Show Purchase", default=False)
    show_contact = fields.Boolean(string="Show Contact", default=False)
    show_product = fields.Boolean(string="Show Product Import", default=False)

    @api.model
    def toggle_task(self, enabled):
        """
        Activa o desactiva la visibilidad del módulo de importación de tareas en el dashboard
        según el estado del checkbox en los ajustes.
        """
        self.search([('state', '=', 'import.task')]).write({'show_task': enabled})

    @api.model
    def toggle_account_move(self, enabled):
        """
        Activa o desactiva la visibilidad del módulo en el dashboard
        según el estado del checkbox en los ajustes.
        """
        self.search([('state', '=', 'account.move')]).write({'show_account_move': enabled})

    @api.model
    def toggle_attendance(self, enabled):
        """
        Activa o desactiva la visibilidad del módulo en el dashboard
        según el estado del checkbox en los ajustes.
        """
        self.search([('state', '=', 'import.attendance')]).write({'show_attendance': enabled})

    @api.model
    def toggle_bom(self, enabled):
        """
        Activa o desactiva la visibilidad del módulo en el dashboard
        según el estado del checkbox en los ajustes.
        """
        self.search([('state', '=', 'import.bill.of.material')]).write({'show_bom': enabled})

    @api.model
    def toggle_invoice(self, enabled):
        """
        Activa o desactiva la visibilidad del módulo de importación de facturas en el dashboard
        según el estado del checkbox en los ajustes.
        """
        self.search([('state', '=', 'import.invoice')]).write({'show_invoice': enabled})

    @api.model
    def toggle_payment(self, enabled):
        """
        Activa o desactiva la visibilidad del módulo de importación de pagos en el dashboard
        según el estado del checkbox en los ajustes.
        """
        self.search([('state', '=', 'import.payment')]).write({'show_payment': enabled})

    @api.model
    def toggle_pos(self, enabled):
        """
        Activa o desactiva la visibilidad del módulo de importación POS en el dashboard
        según el estado del checkbox en los ajustes.
        """
        self.search([('state', '=', 'import.pos.order')]).write({'show_pos': enabled})

    @api.model
    def toggle_purchase(self, enabled):
        """
        Activa o desactiva la visibilidad del módulo de importación de órdenes de compra en el dashboard
        según el estado del checkbox en los ajustes.
        """
        self.search([('state', '=', 'import.purchase.order')]).write({'show_purchase': enabled})

    @api.model
    def toggle_contact(self, enabled):
        """
        Activa o desactiva la visibilidad del módulo de importación de contactos en el dashboard
        según el estado del checkbox en los ajustes.
        """
        self.search([('state', '=', 'import.contact.wizard')]).write({'show_contact': enabled})

    @api.model
    def toggle_product(self, enabled):
        """
        Activa o desactiva la visibilidad del módulo de importación de productos en el dashboard
        según el estado del checkbox en los ajustes.
        """
        self.search([('state', '=', 'wizard.producto')]).write({'show_product': enabled})

    def action_open_attendance_wizard(self):
        """
        Acción que abre el wizard de importación de asistencia
        desde la tarjeta del dashboard.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Import Attendance',
            'res_model': 'import.attendance',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_open_bom_wizard(self):
        """
        Acción que abre el wizard de importación de BOM
        desde la tarjeta del dashboard.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Import BOM',
            'res_model': 'import.bill.of.material',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_open_product_wizard(self):
        """
        Abre el wizard para importar productos
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Importar Productos',
            'res_model': 'wizard.producto',
            'view_mode': 'form',
            'target': 'new',
        }
=======
    state = fields.Selection([("account.move", "Invoice / Bill")])

    show_invoice_module = fields.Boolean(string="Show Invoice Module", default=False)

    @api.model
    def toggle_invoice_module(self, enabled):
        self.search([]).write({'show_invoice_module': enabled})
>>>>>>> 58ff627 (Actualización en account_move.py y account_move_view.xml)
