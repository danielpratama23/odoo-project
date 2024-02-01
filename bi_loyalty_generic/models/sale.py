# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _, tools
from datetime import date, time, datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError,Warning
from collections import defaultdict
import logging
import math

_logger = logging.getLogger(__name__)

class web_category(models.Model):
	_inherit = 'product.category'

	Minimum_amount  = fields.Integer("Amount For loyalty Points")
	amount_footer = fields.Integer('Amount', related='Minimum_amount')

class SaleOrder(models.Model):
	_inherit = 'sale.order'

	order_credit_points = fields.Integer(string='Order Credit Points',copy=False)
	order_redeem_points = fields.Integer(string='Order Redeemed Points',copy=False)
	redeem_value = fields.Float(string='Redeem point value',copy=False)
	is_from_website = fields.Boolean("Is from Website",copy=False,readonly=True)
	loyalty_point_credit=fields.Float(string="Your Loyalty Balance:",readonly=True,copy=False)

	def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
		res = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)
		if res.get('quantity') != 0 :
			self.ensure_one()
			OrderLine = self.env['sale.order.line']
			line = OrderLine.sudo().browse(line_id)
			if line and line.discount_line :
				line.write({
					'price_unit' : - line.redeem_points * line.order_id.redeem_value
				})
		return res

	def action_confirm(self):		
		res = super(SaleOrder,self).action_confirm()
		loyalty_history_obj = self.env['all.loyalty.history']	
		today_date = datetime.today().date()
		config = self.env['all.loyalty.setting'].sudo().search([('active','=',True),('issue_date', '<=', today_date ),
								('expiry_date', '>=', today_date )])
		if config : 
			for rec in self:
				partner_id =rec.partner_id
				# plus_points = 0.0

				# company_currency = rec.company_id.currency_id
				# web_currency = rec.pricelist_id.currency_id		
				
				# if config.loyalty_basis_on == 'amount' :
				# 	if config.loyality_amount > 0 :
				# 		price = sum(rec.order_line.filtered(lambda x: not x.is_delivery).mapped('price_total'))	
				# 		if company_currency.id != web_currency.id:
				# 			new_rate = (price*company_currency.rate)/web_currency.rate
				# 		else:
				# 			new_rate = price
				# 		plus_points =  int( new_rate / config.loyality_amount)

				# if config.loyalty_basis_on == 'loyalty_category' :
				# 	for line in  rec.order_line:
				# 		if not line.discount_line or not line.is_delivery :
				# 			if rec.is_from_website :
				# 				prod_categs = line.product_id.public_categ_ids
				# 				for c in prod_categs :
				# 					if c.Minimum_amount > 0 :
				# 						if company_currency.id != web_currency.id:
				# 							price = line.price_total
				# 							new_rate = (price*company_currency.rate)/web_currency.rate
				# 						else:
				# 							new_rate = line.price_total
				# 						plus_points += int(new_rate / c.Minimum_amount)
				# 			else:
				# 				prod_categ = line.product_id.categ_id
				# 				if prod_categ.Minimum_amount > 0 :
				# 					if company_currency.id != web_currency.id:
				# 						price = line.price_total
				# 						new_rate = (price*company_currency.rate)/web_currency.rate
				# 					else:
				# 						new_rate = line.price_total
				# 					plus_points += int(new_rate / prod_categ.Minimum_amount)
				
				if rec.order_redeem_points > 0:
					is_debit = loyalty_history_obj.search([('order_id','=',rec.id),('transaction_type','=','debit')])
					if is_debit:
						is_debit.write({
							'points': rec.order_redeem_points,
							'state': 'done',
							'date' : datetime.now(),
							'partner_id': partner_id.id,
						})
					else:
						vals = {
							'order_id':rec.id,
							'partner_id': partner_id.id,
							'loyalty_config_id' : config.id,
							'date' : datetime.now(),
							'transaction_type' : 'debit',
							'generated_from' : 'sale',
							'points': rec.order_redeem_points,
							'state': 'done',
						}
						loyalty_history = loyalty_history_obj.sudo().create(vals)
		return res
	
	def action_cancel(self):		
		res = super(SaleOrder,self).action_cancel()
		loyalty_history_obj = self.env['all.loyalty.history']	
		for rec in self:
			loyalty = loyalty_history_obj.search([('order_id','=',rec.id)])
			for l in loyalty:
				l.write({
					'state' : 'cancel'
				})
		return res
		

class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	discount_line = fields.Boolean(string='Discount line',readonly=True,copy=False)
	redeem_points = fields.Integer(string='Redeem Points',copy=False)
	redeem_value = fields.Float(string='Redeem point value',copy=False)



class AccountMoveInherit(models.Model):
	_inherit = 'account.move'

	loyalty_genrate = fields.Boolean("Loyalty Genrated")
	genrated_points = fields.Integer("Loyalty Genrated")

	def button_draft(self):		
		res = super(AccountMoveInherit,self).button_draft()
		loyalty_history_obj = self.env['all.loyalty.history']
		sale_order = self.env['sale.order'].search([('name','=',self.invoice_origin)],limit=1)
		if sale_order:
			for rec in sale_order:
				loyalty = loyalty_history_obj.search([('order_id','=',rec.id)])
				for l in loyalty:
					l.write({
						'state' : 'cancel'
					})
		return res

	def _reverse_moves(self, default_values_list=None, cancel=False):
		''' Reverse a recordset of account.move.
		If cancel parameter is true, the reconcilable or liquidity lines
		of each original move will be reconciled with its reverse's.

		:param default_values_list: A list of default values to consider per move.
									('type' & 'reversed_entry_id' are computed in the method).
		:return:                    An account.move recordset, reverse of the current self.
		'''
		if not default_values_list:
			default_values_list = [{} for move in self]

		if cancel:
			lines = self.mapped('line_ids')
			# Avoid maximum recursion depth.
			if lines:
				lines.remove_move_reconcile()

		reverse_type_map = {
			'entry': 'entry',
			'out_invoice': 'out_refund',
			'out_refund': 'entry',
			'in_invoice': 'in_refund',
			'in_refund': 'entry',
			'out_receipt': 'entry',
			'in_receipt': 'entry',
		}

		move_vals_list = []
		for move, default_values in zip(self, default_values_list):
			default_values.update({
				'move_type': reverse_type_map[move.move_type],
				'reversed_entry_id': move.id,
			})
			move_vals_list.append(move.with_context(move_reverse_cancel=cancel)._reverse_move_vals(default_values, cancel=cancel))

		reverse_moves = self.env['account.move'].create(move_vals_list)
		

		if reverse_moves.genrated_points > reverse_moves.partner_id.loyalty_pts:
			today_date = datetime.today().date()
			config = self.env['all.loyalty.setting'].sudo().search([('active','=',True),('issue_date', '<=', today_date ),
									('expiry_date', '>=', today_date )])
			inv_lines = []
			if config :
				redeem_prod_id = config.product_id
				inv_lines.append({
						'product_id': config.product_id.id,
						'name': config.product_id.name,
						'price_unit': -(reverse_moves.genrated_points * config.loyality_amount),
						'move_id': reverse_moves.id,
					})

				reverse_moves.write({
					'invoice_line_ids': [(0, 0, l) for l in inv_lines],
				})
		for move, reverse_move in zip(self, reverse_moves.with_context(check_move_validity=False, move_reverse_cancel=cancel)):
			# Update amount_currency if the date has changed.
			if move.date != reverse_move.date:
				for line in reverse_move.line_ids:
					if line.currency_id:
						line._onchange_currency()
			reverse_move._recompute_dynamic_lines(recompute_all_taxes=False)
		reverse_moves._check_balanced()

		# Reconcile moves together to cancel the previous one.
		if cancel:
			reverse_moves.with_context(move_reverse_cancel=cancel)._post(soft=False)
			for move, reverse_move in zip(self, reverse_moves):
				group = defaultdict(list)
				for line in (move.line_ids + reverse_move.line_ids).filtered(lambda l: not l.reconciled):
					group[(line.account_id, line.currency_id)].append(line.id)

				
				for (account, dummy), line_ids in group.items():
					if account.reconcile or account.internal_type == 'liquidity':
						self.env['account.move.line'].browse(line_ids).with_context(move_reverse_cancel=cancel).reconcile()

		return reverse_moves

	
	def generate_loyalty_points(self,move):
		sale_order = self.env['sale.order'].search(['|',('name','=',move.invoice_origin),('name','=',move.ref)],limit=1)
		loyalty_history_obj = self.env['all.loyalty.history']   
		today_date = datetime.today().date()
		config = self.env['all.loyalty.setting'].sudo().search([('active','=',True),('issue_date', '<=', today_date ),
									('expiry_date', '>=', today_date )])
		flag = False
		if sale_order and config :
			if sale_order.website_id :
				if  sale_order.website_id.allow_to_loyalty :
					flag = True
			else:
		
				flag = True
				
		if flag:
			if move.move_type == 'out_invoice' or move.move_type == 'entry':
				for rec in sale_order:
					partner_id =rec.partner_id
					plus_points = 0.0

					company_currency = rec.company_id.currency_id
					web_currency = rec.pricelist_id.currency_id     
					
					if config.loyalty_basis_on == 'amount' :
						if config.loyality_amount > 0 :
							price = sum(rec.order_line.filtered(lambda x: not x.is_delivery).mapped('price_total'))
							if company_currency.id != web_currency.id:
								new_rate = (price*company_currency.rate)/web_currency.rate
							else:
								new_rate = price
							plus_points =  int( new_rate / config.loyality_amount)

					if config.loyalty_basis_on == 'loyalty_category' :
						for line in  rec.order_line:
							if not line.discount_line or not line.is_delivery :
								if rec.is_from_website :
									prod_categs = line.product_id.public_categ_ids
									for c in prod_categs :
										if c.Minimum_amount > 0 :
											price = sum(rec.order_line.filtered(lambda x: not x.is_delivery).mapped('price_total'))
											if company_currency.id != web_currency.id:
												new_rate = (price*company_currency.rate)/web_currency.rate
											else:
												new_rate = price
											plus_points += int(new_rate / c.Minimum_amount)
								else:
									prod_categ = line.product_id.categ_id
									if prod_categ.Minimum_amount > 0 :
										price = sum(rec.order_line.filtered(lambda x: not x.is_delivery).mapped('price_total'))
										if company_currency.id != web_currency.id:
											new_rate = (price*company_currency.rate)/web_currency.rate
										else:
											new_rate = price
										plus_points += int(new_rate / prod_categ.Minimum_amount)
					
					
					if plus_points > 0 :
						is_credit = loyalty_history_obj.search([('order_id','=',rec.id),('transaction_type','=','credit')])
						if is_credit:
							is_credit.write({
								'points': (plus_points),
								'state': 'done',
								'date' : datetime.now(),
								'partner_id': partner_id.id,
							})

							move.write({'loyalty_genrate':True ,'genrated_points':(move.genrated_points + plus_points)})

						else:
							vals = {
								'order_id':rec.id,
								'partner_id': partner_id.id,
								'loyalty_config_id' : config.id,
								'date' : datetime.now(),
								'transaction_type' : 'credit',
								'generated_from' : 'sale',
								'points': plus_points,
								'state': 'done',
							}
							loyalty_history = loyalty_history_obj.sudo().create(vals)
							move.write({'loyalty_genrate':True ,'genrated_points':plus_points})
							self.write({'loyalty_genrate':True ,'genrated_points':plus_points})
						rec.write({'order_credit_points':plus_points})

			if move.move_type == 'out_refund':
				for rec in sale_order:
					if move.genrated_points <= rec.partner_id.loyalty_pts:
						partner_id =rec.partner_id
						plus_points = 0.0

						company_currency = rec.company_id.currency_id
						web_currency = rec.pricelist_id.currency_id     
						
						if config.loyalty_basis_on == 'amount' :
							if config.loyality_amount > 0 :
								price = sum(rec.order_line.filtered(lambda x: not x.is_delivery).mapped('price_total'))
								if company_currency.id != web_currency.id:
									new_rate = (price*company_currency.rate)/web_currency.rate
								else:
									new_rate = price
								plus_points =  int( new_rate / config.loyality_amount)

						if config.loyalty_basis_on == 'loyalty_category' :
							for line in  rec.order_line:
								if not line.discount_line or not line.is_delivery :
									if rec.is_from_website :
										prod_categs = line.product_id.public_categ_ids
										for c in prod_categs :
											if c.Minimum_amount > 0 :
												price = sum(rec.order_line.filtered(lambda x: not x.is_delivery).mapped('price_total'))
												if company_currency.id != web_currency.id:
													new_rate = (price*company_currency.rate)/web_currency.rate
												else:
													new_rate = price
												plus_points += int(new_rate / c.Minimum_amount)
									else:
										prod_categ = line.product_id.categ_id
										if prod_categ.Minimum_amount > 0 :
											price = sum(rec.order_line.filtered(lambda x: not x.is_delivery).mapped('price_total'))
											if company_currency.id != web_currency.id:
												new_rate = (price*company_currency.rate)/web_currency.rate
											else:
												new_rate = price
											plus_points += int(new_rate / prod_categ.Minimum_amount)
						
						if plus_points > 0 :
							is_credit = loyalty_history_obj.search([('order_id','=',rec.id),('transaction_type','=','credit')])
							if is_credit:
								is_credit.write({
									'points': - plus_points,
									'state': 'done',
									'date' : datetime.now(),
									'partner_id': partner_id.id,
								})
								move.write({'loyalty_genrate':False ,'genrated_points':move.genrated_points - plus_points})
							else:
								vals = {
									'order_id':rec.id,
									'partner_id': partner_id.id,
									'loyalty_config_id' : config.id,
									'date' : datetime.now(),
									'transaction_type' : 'credit',
									'generated_from' : 'sale',
									'points': -plus_points,
									'state': 'done',
								}
								loyalty_history = loyalty_history_obj.sudo().create(vals)
								move.write({'loyalty_genrate':True ,'genrated_points':plus_points})
								self.write({'loyalty_genrate':True ,'genrated_points':plus_points})
							rec.write({'order_credit_points':plus_points})

							

	@api.depends(
		'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
		'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
		'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
		'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
		'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
		'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
		'line_ids.debit',
		'line_ids.credit',
		'line_ids.currency_id',
		'line_ids.amount_currency',
		'line_ids.amount_residual',
		'line_ids.amount_residual_currency',
		'line_ids.payment_id.state',
		'line_ids.full_reconcile_id')
	def _compute_amount(self):
		for move in self:
			if move.payment_state == 'invoicing_legacy':
				# invoicing_legacy state is set via SQL when setting setting field
				# invoicing_switch_threshold (defined in account_accountant).
				# The only way of going out of this state is through this setting,
				# so we don't recompute it here.
				move.payment_state = move.payment_state
				continue

			total_untaxed = 0.0
			total_untaxed_currency = 0.0
			total_tax = 0.0
			total_tax_currency = 0.0
			total_to_pay = 0.0
			total_residual = 0.0
			total_residual_currency = 0.0
			total = 0.0
			total_currency = 0.0
			currencies = move._get_lines_onchange_currency().currency_id

			for line in move.line_ids:
				if move._payment_state_matters():
					# === Invoices ===

					if not line.exclude_from_invoice_tab:
						# Untaxed amount.
						total_untaxed += line.balance
						total_untaxed_currency += line.amount_currency
						total += line.balance
						total_currency += line.amount_currency
					elif line.tax_line_id:
						# Tax amount.
						total_tax += line.balance
						total_tax_currency += line.amount_currency
						total += line.balance
						total_currency += line.amount_currency
					elif line.account_id.user_type_id.type in ('receivable', 'payable'):
						# Residual amount.
						total_to_pay += line.balance
						total_residual += line.amount_residual
						total_residual_currency += line.amount_residual_currency
				else:
					# === Miscellaneous journal entry ===
					if line.debit:
						total += line.balance
						total_currency += line.amount_currency

			if move.move_type == 'entry' or move.is_outbound():
				sign = 1
			else:
				sign = -1
			move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
			move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
			move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
			move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
			move.amount_untaxed_signed = -total_untaxed
			move.amount_tax_signed = -total_tax
			move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
			move.amount_residual_signed = total_residual
			move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)

			currency = currencies if len(currencies) == 1 else move.company_id.currency_id

			# Compute 'payment_state'.
			new_pmt_state = 'not_paid' if move.move_type != 'entry' else False


			
			if (move._payment_state_matters() or move.move_type == 'entry') and move.state == 'posted':
				if currency.is_zero(move.amount_residual):
					reconciled_payments = move._get_reconciled_payments()
					if not reconciled_payments or all(payment.is_matched for payment in reconciled_payments):
						new_pmt_state = 'paid'
						move.generate_loyalty_points(move)
					else:
						new_pmt_state = move._get_invoice_in_payment_state()
						move.generate_loyalty_points(move)
						

				elif currency.compare_amounts(total_to_pay, total_residual) != 0:
					new_pmt_state = 'partial'

			if new_pmt_state == 'paid' and move.move_type in ('in_invoice', 'out_invoice', 'entry'):
				reverse_type = move.move_type == 'in_invoice' and 'in_refund' or move.move_type == 'out_invoice' and 'out_refund' or 'entry'
				reverse_moves = self.env['account.move'].search([('reversed_entry_id', '=', move.id), ('state', '=', 'posted'), ('move_type', '=', reverse_type)])

				# We only set 'reversed' state in cas of 1 to 1 full reconciliation with a reverse entry; otherwise, we use the regular 'paid' state
				reverse_moves_full_recs = reverse_moves.mapped('line_ids.full_reconcile_id')
				if reverse_moves_full_recs.mapped('reconciled_line_ids.move_id').filtered(lambda x: x not in (reverse_moves + reverse_moves_full_recs.mapped('exchange_move_id'))) == move:
					new_pmt_state = 'reversed'

			move.payment_state = new_pmt_state