# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Advance All in one Loyalty - POS & Website Rewards Redeem Program',
    'version': '15.0.0.4',
    'category': 'eCommerce',
    'summary': 'Website Loyalty rewards pos loyalty rewards pos club membership website Loyalty Program eCommerce Loyalty Program pos customer Loyalty and Rewards Program pos Bonus Gift website Referral website reward redeem on pos rewards All in one Loyalty management',
    'description' :"""

        All in one Loyalty Management Advance in odoo,
        All in one Loyalty and Rewards Program in Odoo,
        sale loyalty and rewarads program in odoo,
        website loyalty and rewarads program in odoo,
        pos loyalty and rewarads program in odoo,
        redeem and reward loyalty points in odoo,
        loyalty points in sale website and POS,
        discounts or loyalty in sale website and POS,
        Assign Manually Loyalty Points in odoo,
        Import Loyalty Points in odoo,
        Deactive Loyalty in odoo,
        Create Tiered Loyalty Program in odoo, 

    """,
    'author': 'BrowseInfo',
    "price": 70,
    "currency": 'EUR',
    'website': 'https://www.browseinfo.com',
    'depends': ['base','sale_management','point_of_sale','website','website_sale','delivery','website_sale_delivery','bi_loyalty_generic'],
    'data': [
        'security/ir.model.access.csv',
        'views/loyalty_view.xml',
        'views/loyalty_tier_view.xml',
        'views/res_config_view.xml',
        'views/template.xml',
        'wizard/import_functionality.xml',
        'wizard/manually_loyalty.xml',
    ],
    'assets': {
        'web.assets_backend': [
            ('replace', 'web/static/src/legacy/js/widgets/ribbon.js', 'bi_loyalty_generic_advance/static/src/js/ribbon.js'),
            'bi_loyalty_generic_advance/static/src/css/ribbon.css',
            "bi_loyalty_generic_advance/static/src/js/pos_final.js",
            'bi_loyalty_generic_advance/static/src/js/OrderWidgetExtendedAdvance.js',
            'bi_loyalty_generic_advance/static/src/js/LoyaltyPopupWidget.js'
        ],
        'web.assets_qweb': [
            'bi_loyalty_generic_advance/static/src/xml/**/*',
        ],
    },
    'license':'OPL-1',
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://youtu.be/kj1ltycy5Y0',
    "images":['static/description/Banner.png'],
}
