odoo.define('bi_loyalty_generic_advance.pos_final', function(require) {
	"use strict";

	let models = require('point_of_sale.models');
	let parent_loyalty = require('bi_loyalty_generic.pos');
	let utils = require('web.utils');
	

	models.load_models({
		model: 'loyalty.tier.config',
		fields: [],
		domain: [],
		loaded: function(self, pos_loyalty_tiers) {
			self.pos_loyalty_tiers = pos_loyalty_tiers;
		},
	});
	models.load_fields('all.loyalty.setting', ['loyalty_tier']);
	models.load_fields('res.partner', ['tier_id','total_sales']);
		
	
	let OrderSuper = models.Order.prototype;
	models.Order = models.Order.extend({
		initialize: function(attributes, options) {
			OrderSuper.initialize.apply(this, arguments);
			let self = this;
			this.loyalty = this.loyalty  || 0;
			this.redeemed_points = this.redeemed_points || 0;
			this.redeem_done = this.redeem_done || false;
		},
		
		get_total_loyalty_final: function() {
			let final_loyalty = 0
			let order = this.pos.get_order();
			let orderlines = this.get_orderlines();
			let partner_id = this.get_client();
			var self=this;
			if(order){
				if(partner_id){
					if(partner_id.tier_id){
						if(this.pos.pos_loyalty_setting.length != 0){						
							let pos_loyalty_setting = this.pos.pos_loyalty_setting;
							pos_loyalty_setting.forEach(function(config){
								let pos_loyalty_tiers= self.pos.pos_loyalty_tiers;
								pos_loyalty_tiers.forEach(function(tier){
									if(partner_id.total_sales >= tier.min_range && partner_id.total_sales <= tier.max_range){
										if(config.active == true && config.loyalty_tier[0] == partner_id.tier_id[0]){
											if (config.loyalty_basis_on == 'loyalty_category') {
												if (partner_id){
													let loyalty = 0;
													for (let i = 0; i < orderlines.length; i++) {
														let lines = orderlines[i];
														let cat_ids = this.pos.db.get_category_by_id(lines.product.pos_categ_id[0])
														if(cat_ids){
															if (cat_ids['Minimum_amount']>0){
																final_loyalty += lines.get_price_with_tax() / cat_ids['Minimum_amount'];
															}
														}
													}
													return parseFloat(final_loyalty.toFixed(2));
												}
											}
											else if (config.loyalty_basis_on == 'amount') {
												let loyalty_total = 0;
												if (order && partner_id){
													let amount_total = order.get_total_with_tax();
													let subtotal = order.get_total_without_tax();
													let loyaly_points = config.loyality_amount;
													final_loyalty += (amount_total / loyaly_points);
													if(order.get_client()){
														loyalty_total = order.get_client().loyalty_points1 + final_loyalty;							
													}
													return parseFloat(final_loyalty.toFixed(2));
												}
											}
										}
									}
								});
							});			
						
						}
						return parseFloat(final_loyalty.toFixed(2));
					}	
					else{
						var self=this;
						if(self.pos.pos_loyalty_setting.length != 0){
							let pos_loyalty_setting = self.pos.pos_loyalty_setting;
							pos_loyalty_setting.forEach(function(config){
								let pos_loyalty_tiers= self.pos.pos_loyalty_tiers;
								pos_loyalty_tiers.forEach(function(tier){
									if(partner_id.total_sales >= tier.min_range && partner_id.total_sales <= tier.max_range){
										if(config.active == true && config.loyalty_tier[0] == tier.id){
											if (config.loyalty_basis_on == 'loyalty_category') {
												if (partner_id){
													let loyalty = 0;
													for (let i = 0; i < orderlines.length; i++) {
														let lines = orderlines[i];
														let cat_ids = this.pos.db.get_category_by_id(lines.product.pos_categ_id[0])
														if(cat_ids){
															if (cat_ids['Minimum_amount']>0){
																final_loyalty += lines.get_price_with_tax() / cat_ids['Minimum_amount'];
															}
														}
													}
													return parseFloat(final_loyalty.toFixed(2));
												}
											}
											else if (config.loyalty_basis_on == 'amount') {
												let loyalty_total = 0;
												if (order && partner_id){
													let amount_total = order.get_total_with_tax();
													let subtotal = order.get_total_without_tax();
													let loyaly_points = config.loyality_amount;
													final_loyalty += (amount_total / loyaly_points);
													if(order.get_client()){
														loyalty_total = order.get_client().loyalty_points1 + final_loyalty;							
													}
													return parseFloat(final_loyalty.toFixed(2));
												}
											}
										}
									}

								});

							});

						}
						return parseFloat(final_loyalty.toFixed(2));
					}				
				}
			}
		},

		export_as_JSON: function() {
			let json = OrderSuper.export_as_JSON.apply(this, arguments);
			json.redeemed_points = parseInt(this.redeemed_points);
			json.loyalty = this.get_total_loyalty_final();
			json.redeem_done = this.redeem_done;
			return json;
		},

		init_from_JSON: function(json){
			OrderSuper.init_from_JSON.apply(this,arguments);
			this.loyalty = json.loyalty;
			this.redeem_done = json.redeem_done;
			this.redeemed_points = json.redeemed_points;
		},
	
	});

});
