from odoo import fields, models, api


class ImportDashboard(models.Model):
    _name = "import.dashboard"
    _description = "Import Dashboard"

    name = fields.Char("Import Dashboard")
    state = fields.Selection([("account.move", "Invoice / Bill")])

    show_invoice_module = fields.Boolean(string="Show Invoice Module", default=False)

    @api.model
    def toggle_invoice_module(self, enabled):
        self.search([]).write({'show_invoice_module': enabled})
