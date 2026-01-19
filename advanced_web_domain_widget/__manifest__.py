# -*- coding: utf-8 -*-
#################################################################################
# Author      : Terabits Technolab (<www.terabits.xyz>)
# Copyright(c): 2023-25
# All Rights Reserved.
#
# This module is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
{
    "name": "Advanced Web Domain Widget",
    "version": "18.0.2.2.4",
    "summary": "Set all relational fields domain by selecting its records unsing `in, not in` operator.",
    "sequence": 10,
    "author": "Terabits Technolab",
    "license": "OPL-1",
    "website": "https://www.terabits.xyz/apps/18.0/advanced_web_domain_widget",
    "description": """
      
        """,
    "price": "5.00",
    "currency": "USD",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "advanced_web_domain_widget/static/src/tree_editor/*.js",
            "advanced_web_domain_widget/static/src/tree_editor/*.xml",
            "advanced_web_domain_widget/static/src/domain_selector/*.js",
            "advanced_web_domain_widget/static/src/domain_selector/*.xml",
            "advanced_web_domain_widget/static/src/domain_selector_dialog/*.js",
            "advanced_web_domain_widget/static/src/domain_selector_dialog/*.xml",
            "advanced_web_domain_widget/static/src/domain/*.js",
            "advanced_web_domain_widget/static/src/domain/*.xml",
            "advanced_web_domain_widget/static/src/model_field_selector/*.js", 
            "advanced_web_domain_widget/static/src/model_field_selector/*.xml", 
            "advanced_web_domain_widget/static/src/autocomplete/*",
            "advanced_web_domain_widget/static/src/record_selectors/*.js",
            "advanced_web_domain_widget/static/src/record_selectors/*.xml",
            "advanced_web_domain_widget/static/src/name_service.js"
        ],
    },
    "images": ["static/description/banner.png"],
    "application": True,
    "installable": True,
    "auto_install": False,
}
