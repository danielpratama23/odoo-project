# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _, tools
from datetime import date, time, datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError,Warning
import logging
_logger = logging.getLogger(__name__)

class pos_order(models.Model):
	_inherit = 'pos.order'

	@api.model
	def create_from_ui(self, orders, draft=False):

		order_ids = []
		for order in orders:
			existing_order = False
			if 'server_id' in order['data']:
				existing_order = self.env['pos.order'].search(['|', ('id', '=', order['data']['server_id']), ('pos_reference', '=', order['data']['name'])], limit=1)
			if (existing_order and existing_order.state == 'draft') or not existing_order:
				order_ids.append(self._process_order(order, draft, existing_order))
		
		loyalty_history_obj = self.env['all.loyalty.history']
		today_date = datetime.today().date() 
		config_loyalty_setting = self.env['all.loyalty.setting'].sudo().search([('active','=',True),('issue_date', '<=', today_date ),
							('expiry_date', '>=', today_date )])

		for loyalty_setting in config_loyalty_setting:
			if loyalty_setting:
				for order_id in order_ids:
					try:
						pos_order_id = self.browse(order_id)
						if loyalty_setting.loyalty_tier.min_range <= pos_order_id.partner_id.total_sales <= loyalty_setting.loyalty_tier.max_range:
							if pos_order_id:
								ref_order = [o['data'] for o in orders if o['data'].get('name') == pos_order_id.pos_reference]
								for order in ref_order:
									order_loyalty = order.get('loyalty')
									if order_loyalty > 0:
										vals = {
											'pos_order_id':pos_order_id.id,
											'partner_id': pos_order_id.partner_id.id,
											'date' : datetime.now(),
											'transaction_type' : 'credit',
											'generated_from' : 'pos',
											'points': order_loyalty,
											'state': 'done',
										}
										loyalty_history_obj.create(vals)
									pos_order_id.partner_id.write({'tier_id':loyalty_setting.loyalty_tier.id})		
					except Exception as e:
						_logger.error('Error in point of sale validation: %s', tools.ustr(e))
		if pos_order_id:
			ref_order = [o['data'] for o in orders if o['data'].get('name') == pos_order_id.pos_reference]
			for order in ref_order:
				redeemed = order.get('redeemed_points')
			if order.get('redeem_done') == True:
				vals = {
					'pos_order_id': pos_order_id.id,
					'partner_id': pos_order_id.partner_id.id,
					'date': datetime.now(),
					'transaction_type': 'debit',
					'generated_from': 'pos',
					'points': redeemed,
					'state': 'done',
				}
				loyalty_history_obj.create(vals)	
		return True

		
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:    
