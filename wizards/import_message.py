# -*- coding: utf-8 -*-
from odoo import fields, models


class ImportMessage(models.TransientModel):
    _name = 'import.message'
    _description = 'Message Import'

    message = fields.Text(string="Message", readonly=True, help="Message")

    def action_import_message(self):
        """For returning the corresponding window"""
        return {'type': 'ir.actions.act_window_close'}
