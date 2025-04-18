{
    "name": "Import Dashboard",
    "version": "17.0.1.0.0",
    "summary": "Import data into odoo",
    "category": "Extra Tools",
    "author": "Joseph Armas / FenixERP",
    "license": "OPL-1",
    "website": "https://github.com/Fenix-ERP/l10n-ecuador",
    "depends": [
        "base",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "wizards/account_move_view.xml",
<<<<<<< HEAD
        "wizards/import_attendance_view.xml",
        "wizards/import_bill_of_material_views.xml",
        "wizards/import_invoice_view.xml",
        "wizards/import_pos_order_views.xml",
        "wizards/import_payment_view.xml",
        "wizards/import_purchase_order_views.xml",
        "wizards/import_task_views.xml",
        "wizards/contact_import_wizard_view.xml",
        "wizards/wizard_product_view.xml",
        "views/import_dashboard.xml",
        "data/import_dashboard_settings_menu.xml",
        "views/import_dashboard_settings.xml",

=======
        "views/import_dashboard.xml",
        "data/import_dashboard_settings_menu.xml",
        "views/import_dashboard_settings.xml",
>>>>>>> 58ff627 (Actualización en account_move.py y account_move_view.xml)
    ],
    "controllers": [
        "controllers/main.py",
    ],
    "external_dependencies": {"python": ["xlrd"]},
    "installable": True,
    "application": False,
}
