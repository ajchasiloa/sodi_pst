from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_import_dashboard = fields.Boolean(
        string="Activar Import Dashboard",
        config_parameter='import_dashboard.enable_import_dashboard'
    )

    def set_values(self):
        super().set_values()
        enabled = self.enable_import_dashboard
        # Activar solo la visibilidad interna del módulo Invoice
        self.env['import.dashboard'].toggle_invoice_module(enabled)
