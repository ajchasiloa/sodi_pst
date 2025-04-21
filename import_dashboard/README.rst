===========================
Odoo Import Dashboard v17.0
===========================

.. !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! This file has been generated based on the official Odoo    !!
   !! documentation structure for version 16, updated and        !!
   !! migrated to Odoo version 17 by FenixERP.                   !!
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

.. |badge1| image:: https://img.shields.io/badge/maturity-Stable-brightgreen.svg
    :target: https://fenixerp.com
    :alt: Stable
.. |badge2| image:: https://img.shields.io/badge/github-FenixERP%2Fimport--dashboard-lightgray.svg?logo=github
    :target: https://github.com/Fenix-ERP/l10n-ecuador
    :alt: GitHub Repository
.. |badge3| image:: https://img.shields.io/badge/license-OPL--1-blue.svg
    :target: https://www.odoo.com/documentation/17.0/legal/licenses.html#odoo-apps
    :alt: License: OPL-1

|badge1| |badge2| |badge3|

The **Import Dashboard** module for Odoo 17 provides a centralized interface for importing multiple types of business records using structured Excel or CSV files.

This module facilitates bulk data creation through intuitive wizards that offer field validation, live feedback, and error-handling messages.

**Supported Import Types:**

- ✅ Products  
- ✅ Contacts  
- ✅ Customers / Vendors  
- ✅ Invoices  
- ✅ Payments  
- ✅ Purchase Orders  
- ✅ POS Orders  
- ✅ Tasks  
- ✅ Attendances  
- ✅ Bill of Materials (BoMs)  

**Table of Contents**

.. contents::
   :local:

Installation
============

To install this module:

1. Copy this module folder into your Odoo `addons` path.
2. Restart the Odoo service.

   .. code-block:: bash

      sudo service odoo-server restart

3. Activate *Developer Mode*.
4. Go to *Apps* → *Update Apps List*.
5. Search for **Import Dashboard** and click *Install*.

Configuration
=============

No extra configuration is needed.

To customize what is shown on the dashboard:

- Navigate to **Settings** → **Import Dashboard**
- Enable or disable each import wizard (invoices, payments, tasks, etc.)

Usage
=====

1. Open **Import Dashboard** from the main menu.
2. Select the type of data to import (e.g. Products, Invoices).
3. Download the sample template provided.
4. Fill the Excel or CSV file with your data.
5. Upload the file via the wizard interface.
6. Use the *Test* button to validate before final import (optional).
7. Click *Import* to create the records in Odoo.

Each wizard provides guidance, inline validation, and meaningful error messages.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/Fenix-ERP/l10n-ecuador/issues>`_.

If you encounter an issue:

- Check if it’s already reported.
- If not, open a new issue with detailed steps to reproduce it.

**Do not contact maintainers directly for support.** Use GitHub issues instead.

Credits
=======

Authors
~~~~~~~

* Anderson Chasiloa

Maintainers
~~~~~~~~~~~

This module is maintained by **FenixERP**.

.. image:: https://fenixerp.com/assets/img/logo-dark.svg
   :alt: FenixERP
   :target: https://fenixerp.com

License
=======

This module is licensed under the Odoo Proprietary License (OPL-1).  
For more information, see: https://www.odoo.com/documentation/17.0/legal/licenses.html#odoo-apps

Repository
==========

GitHub: https://github.com/Fenix-ERP/l10n-ecuador

Pull requests and contributions are welcome 🚀

