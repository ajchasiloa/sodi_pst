from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_account_move_import = fields.Boolean(
        string="Activar Importación de Facturas",
        config_parameter='import_dashboard.enable_account_move_import',
        default=False,  # Asegúrate de que el valor predeterminado sea False
    )

    enable_attendance_import = fields.Boolean(
        string="Activar Importación de Asistencia",
        config_parameter='import_dashboard.enable_attendance_import',
        default=False,
    )

    enable_bom_import = fields.Boolean(
        string="Activar Importación de BOM",
        config_parameter='import_dashboard.enable_bom_import',
        default=False,
    )

    enable_invoice_import = fields.Boolean(
        string="Activar Importación de Facturas",
        config_parameter='import_dashboard.enable_invoice_import',
        default=False,
    )

    enable_payment_import = fields.Boolean(
        string="Activar Importación de Pagos",
        config_parameter='import_dashboard.enable_payment_import',
        default=False,
    )

    enable_task_import = fields.Boolean(
        string="Activar Importación de Tareas",
        config_parameter='import_dashboard.enable_task_import',
        default=False,
    )

    enable_pos_import = fields.Boolean(
        string="Activar Importación POS",
        config_parameter='import_dashboard.enable_pos_import',
        default=False,
    )

    show_purchase = fields.Boolean(
        string="Activar Importación de Órdenes de Compra",
        config_parameter='import_dashboard.show_purchase',
        default=False,
    )

    enable_product_import = fields.Boolean(
        string="Activar importación de productos",
        config_parameter='import_dashboard.enable_product_import',
        default=False,
    )

    enable_contact_import = fields.Boolean(
        string="Activar Importación de Contactos",
        config_parameter='import_dashboard.enable_contact_import',
        default=False,
    )

    def set_values(self):
        super().set_values()
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

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        
        # Obtener el estado de los módulos
        import_dashboard = self.env['import.dashboard'].search([], limit=1)
        
        # Actualizar valores de configuración basados en el estado de los módulos
        res.update({
            'enable_account_move_import': import_dashboard.show_account_move and 
                self.env['ir.config_parameter'].sudo().get_param('import_dashboard.enable_account_move_import', default=False),
            'enable_attendance_import': import_dashboard.show_attendance and 
                self.env['ir.config_parameter'].sudo().get_param('import_dashboard.enable_attendance_import', default=False),
            'enable_bom_import': import_dashboard.show_bom and 
                self.env['ir.config_parameter'].sudo().get_param('import_dashboard.enable_bom_import', default=False),
            'enable_invoice_import': import_dashboard.show_invoice and 
                self.env['ir.config_parameter'].sudo().get_param('import_dashboard.enable_invoice_import', default=False),
            'enable_payment_import': import_dashboard.show_payment and 
                self.env['ir.config_parameter'].sudo().get_param('import_dashboard.enable_payment_import', default=False),
            'enable_task_import': import_dashboard.show_task and 
                self.env['ir.config_parameter'].sudo().get_param('import_dashboard.enable_task_import', default=False),
            'enable_pos_import': import_dashboard.show_pos and 
                self.env['ir.config_parameter'].sudo().get_param('import_dashboard.enable_pos_import', default=False),
            'show_purchase': import_dashboard.show_purchase and 
                self.env['ir.config_parameter'].sudo().get_param('import_dashboard.show_purchase', default=False),
            'enable_product_import': import_dashboard.show_product and 
                self.env['ir.config_parameter'].sudo().get_param('import_dashboard.enable_product_import', default=False),
            'enable_contact_import': import_dashboard.show_contact and 
                self.env['ir.config_parameter'].sudo().get_param('import_dashboard.enable_contact_import', default=False),
        })
        return res

    @api.model
    def _install_import_dashboard(self):
        """
        Este método solo se ejecuta en la instalación del módulo para asegurar
        que todas las tarjetas estén ocultas solo en la primera instalación.
        """
        if not self.env['ir.config_parameter'].sudo().get_param('import_dashboard.first_install', False):
            # Ocultar todas las tarjetas de importación
            self.env['import.dashboard'].write({
                'show_account_move': False,
                'show_attendance': False,
                'show_bom': False,
                'show_invoice': False,
                'show_payment': False,
                'show_task': False,
                'show_pos': False,
                'show_purchase': False,
                'show_product': False,
                'show_contact': False,
            })
            # Marcar como "ya instalado"
            self.env['ir.config_parameter'].sudo().set_param('import_dashboard.first_install', 'True')

    def _register_hook(self):
        """
        Este método se ejecuta al instalar el módulo, para asegurarse de que las tarjetas
        se oculten solo una vez en la primera instalación.
        """
        self._install_import_dashboard()
        return super()._register_hook()
