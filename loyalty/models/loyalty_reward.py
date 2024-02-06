# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import _, api, fields, models
from odoo.osv import expression

class LoyaltyReward(models.Model):
    _name = 'loyalty.reward'
    _description = 'Loyalty Reward'
    _rec_name = 'description'
    _order = 'required_points asc'

    def _get_discount_mode_select(self):
        # The value is provided in the loyalty program's view since we may not have a program_id yet
        #  and makes sure to display the currency related to the program instead of the company's.
        symbol = self.env.context.get('currency_symbol', self.env.company.currency_id.symbol)
        return [
            ('percent', '%'),
            ('per_point', _('%s per point', symbol)),
            ('per_order', _('%s per order', symbol))
        ]

    def name_get(self):
        return [(reward.id, '%s - %s' % (reward.program_id.name, reward.description)) for reward in self]

    active = fields.Boolean(default=True)
    program_id = fields.Many2one('loyalty.program', required=True, ondelete='cascade')
    # Stored for security rules
    company_id = fields.Many2one(related='program_id.company_id', store=True)
    currency_id = fields.Many2one(related='program_id.currency_id')

    description = fields.Char(compute='_compute_description', readonly=False, store=True, translate=True)

    reward_type = fields.Selection([
        ('product', 'Free Product'),
        ('discount', 'Discount')],
        default='discount', required=True,
    )

    # Discount rewards
    discount = fields.Float('Discount', default=10)
    discount_mode = fields.Selection(selection=_get_discount_mode_select, required=True, default='percent')
    discount_applicability = fields.Selection([
        ('order', 'Order'),
        ('cheapest', 'Cheapest Product'),
        ('specific', 'Specific Products')], default='order',
    )
    discount_product_domain = fields.Char(default="[]")
    discount_product_ids = fields.Many2many('product.product', string="Discounted Products")
    discount_product_category_id = fields.Many2one('product.category', string="Discounted Prod. Categories")
    discount_product_tag_id = fields.Many2one('product.tag', string="Discounted Prod. Tag")
    all_discount_product_ids = fields.Many2many('product.product', compute='_compute_all_discount_product_ids')
    discount_max_amount = fields.Monetary('Max Discount', 'currency_id',
        help="This is the max amount this reward may discount, leave to 0 for no limit.")
    discount_line_product_id = fields.Many2one('product.product', copy=False, ondelete='restrict',
        help="Product used in the sales order to apply the discount. Each reward has its own product for reporting purpose")
    is_global_discount = fields.Boolean(compute='_compute_is_global_discount')

    # Product rewards
    reward_product_id = fields.Many2one('product.product', string='Product')
    reward_product_tag_id = fields.Many2one('product.tag', string='Product Tag')
    multi_product = fields.Boolean(compute='_compute_multi_product')
    reward_product_ids = fields.Many2many(
        'product.product', string="Reward Products", compute='_compute_multi_product',
        help="These are the products that can be claimed with this rule.")
    reward_product_qty = fields.Integer(default=1)
    reward_product_uom_id = fields.Many2one('uom.uom', compute='_compute_reward_product_uom_id')

    required_points = fields.Float('Points needed', default=1)
    point_name = fields.Char(related='program_id.portal_point_name', readonly=True)
    clear_wallet = fields.Boolean(default=False)

    _sql_constraints = [
        ('required_points_positive', 'CHECK (required_points > 0)',
            'The required points for a reward must be strictly positive.'),
        ('product_qty_positive', "CHECK (reward_type != 'product' OR reward_product_qty > 0)",
            'The reward product quantity must be strictly positive.'),
        ('discount_positive', "CHECK (reward_type != 'discount' OR discount > 0)",
            'The discount must be strictly positive.'),
    ]

    @api.depends('reward_product_id.product_tmpl_id.uom_id', 'reward_product_tag_id')
    def _compute_reward_product_uom_id(self):
        for reward in self:
            reward.reward_product_uom_id = reward.reward_product_ids.product_tmpl_id.uom_id[:1]

    def _get_discount_product_domain(self):
        self.ensure_one()
        domain = []
        if self.discount_product_ids:
            domain = [('id', 'in', self.discount_product_ids.ids)]
        if self.discount_product_category_id:
            domain = expression.OR([domain, [('categ_id', 'child_of', self.discount_product_category_id.id)]])
        if self.discount_product_tag_id:
            domain = expression.OR([domain, [('all_product_tag_ids', 'in', self.discount_product_tag_id.id)]])
        if self.discount_product_domain and self.discount_product_domain != '[]':
            domain = expression.AND([domain, ast.literal_eval(self.discount_product_domain)])
        return domain

    @api.depends('discount_product_ids', 'discount_product_category_id', 'discount_product_tag_id', 'discount_product_domain')
    def _compute_all_discount_product_ids(self):
        for reward in self:
            reward.all_discount_product_ids = self.env['product.product'].search(reward._get_discount_product_domain())

    @api.depends('reward_product_id', 'reward_product_tag_id', 'reward_type')
    def _compute_multi_product(self):
        for reward in self:
            products = reward.reward_product_id + reward.reward_product_tag_id.product_ids
            reward.multi_product = reward.reward_type == 'product' and len(products) > 1
            reward.reward_product_ids = reward.reward_type == 'product' and products or self.env['product.product']

    @api.depends('reward_type', 'reward_product_id', 'discount_mode',
                 'discount', 'currency_id', 'discount_applicability', 'all_discount_product_ids')
    def _compute_description(self):
        for reward in self:
            reward_string = ""
            if reward.reward_type == 'product':
                products = reward.reward_product_ids
                if len(products) == 1:
                    reward_string = _('Free Product - %s', reward.reward_product_id.name)
                else:
                    reward_string = _('Free Product - [%s]', ', '.join(products.mapped('name')))
            elif reward.reward_type == 'discount':
                format_string = '%(amount)g %(symbol)s'
                if reward.currency_id.position == 'before':
                    format_string = '%(symbol)s %(amount)g'
                formatted_amount = format_string % {'amount': reward.discount, 'symbol': reward.currency_id.symbol}
                if reward.discount_mode == 'percent':
                    reward_string = _('%g%% on ', reward.discount)
                elif reward.discount_mode == 'per_point':
                    reward_string = _('%s per point on ', formatted_amount)
                elif reward.discount_mode == 'per_order':
                    reward_string = _('%s per order on ', formatted_amount)
                if reward.discount_applicability == 'order':
                    reward_string += _('your order')
                elif reward.discount_applicability == 'cheapest':
                    reward_string += _('the cheapest product')
                elif reward.discount_applicability == 'specific':
                    if len(reward.all_discount_product_ids) == 1:
                        reward_string += reward.all_discount_product_ids.name
                    else:
                        reward_string += _('specific products')
                if reward.discount_max_amount:
                    format_string = '%(amount)g %(symbol)s'
                    if reward.currency_id.position == 'before':
                        format_string = '%(symbol)s %(amount)g'
                    formatted_amount = format_string % {'amount': reward.discount_max_amount, 'symbol': reward.currency_id.symbol}
                    reward_string += _(' (Max %s)', formatted_amount)
            reward.description = reward_string

    @api.depends('reward_type', 'discount_applicability', 'discount_mode')
    def _compute_is_global_discount(self):
        for reward in self:
            reward.is_global_discount = reward.reward_type == 'discount' and\
                                        reward.discount_applicability == 'order' and\
                                        reward.discount_mode == 'percent'

    def _create_missing_discount_line_products(self):
        # Make sure we create the product that will be used for our discounts
        rewards = self.filtered(lambda r: not r.discount_line_product_id)
        products = self.env['product.product'].create(rewards._get_discount_product_values())
        for reward, product in zip(rewards, products):
            reward.discount_line_product_id = product

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._create_missing_discount_line_products()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'description' in vals:
            self._create_missing_discount_line_products()
            # Keep the name of our discount product up to date
            for reward in self:
                reward.discount_line_product_id.write({'name': reward.description})
        return res

    def unlink(self):
        programs = self.program_id
        res = super().unlink()
        # Not guaranteed to trigger the constraint
        programs._constrains_reward_ids()
        return res

    def _get_discount_product_values(self):
        return [{
            'name': reward.description,
            'type': 'service',
            'sale_ok': False,
            'purchase_ok': False,
            'lst_price': 0,
        } for reward in self]
