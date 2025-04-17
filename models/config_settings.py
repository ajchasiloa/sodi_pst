from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

<<<<<<< HEAD
    enable_account_move_import = fields.Boolean(
        string="Activar Importación de Facturas",
        config_parameter='import_dashboard.enable_account_move_import'
    )

    enable_attendance_import = fields.Boolean(
        string="Activar Importación de Asistencia",
        config_parameter='import_dashboard.enable_attendance_import'
    )

    enable_bom_import = fields.Boolean(
        string="Activar Importación de BOM",
        config_parameter='import_dashboard.enable_bom_import'
    )

    enable_invoice_import = fields.Boolean(
        string="Activar Importación de Facturas",
        config_parameter='import_dashboard.enable_invoice_import'
    )

    enable_payment_import = fields.Boolean(
        string="Activar Importación de Pagos",
        config_parameter='import_dashboard.enable_payment_import'
    )

    enable_task_import = fields.Boolean(
        string="Activar Importación de Tareas",
        config_parameter='import_dashboard.enable_task_import'
    )

    enable_pos_import = fields.Boolean(
        string="Activar Importación POS",
        config_parameter='import_dashboard.enable_pos_import'
    )

    show_purchase = fields.Boolean(
        string="Activar Importación de Órdenes de Compra",
        config_parameter='import_dashboard.show_purchase'
    )

    enable_product_import = fields.Boolean(
        string="Activar importación de productos",
        config_parameter='import_dashboard.enable_product_import'
    )

    enable_contact_import = fields.Boolean(
        string="Activar Importación de Contactos",
        config_parameter='import_dashboard.enable_contact_import'
=======
    enable_import_dashboard = fields.Boolean(
        string="Activar Import Dashboard",
        config_parameter='import_dashboard.enable_import_dashboard'
>>>>>>> 58ff627 (Actualización en account_move.py y account_move_view.xml)
    )

    def set_values(self):
        super().set_values()
<<<<<<< HEAD
        self.env['import.dashboard'].toggle_account_move(self.enable_account_move_import)
        self.env['import.dashboard'].toggle_attendance(self.enable_attendance_import)
        self.env['import.dashboard'].toggle_bom(self.enable_bom_import)
        self.env['import.dashboard'].toggle_invoice(self.enable_invoice_import)
        self.env['import.dashboard'].toggle_payment(self.enable_payment_import)
        self.env['import.dashboard'].toggle_task(self.enable_task_import)
        self.env['import.dashboard'].toggle_pos(self.enable_pos_import)
        self.env['import.dashboard'].toggle_purchase(self.show_purchase)
        self.env['import.dashboard'].toggle_product(self.enable_product_import)
        self.env['import.dashboard'].toggle_contact(self.enable_contact_import)
=======
        enabled = self.enable_import_dashboard
        # Activar solo la visibilidad interna del módulo Invoice
        self.env['import.dashboard'].toggle_invoice_module(enabled)
>>>>>>> 58ff627 (Actualización en account_move.py y account_move_view.xml)
