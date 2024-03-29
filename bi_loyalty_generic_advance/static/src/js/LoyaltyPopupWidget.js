odoo.define('bi_loyalty_generic_advance.LoyaltyPopupWidget', function(require){
	'use strict';

	const { useExternalListener } = owl.hooks;
	const PosComponent = require('point_of_sale.PosComponent');
	const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
	const Registries = require('point_of_sale.Registries');
	const { useListener } = require('web.custom_hooks');
	const { useState } = owl.hooks;
	let redeem;
	

	const LoyaltyPopupWidget = require('bi_loyalty_generic.LoyaltyPopupWidget');

	const BiLoyaltyPopupWidget = (LoyaltyPopupWidget) =>
		class extends LoyaltyPopupWidget {
			constructor() {
				super(...arguments);
			}

			calculate_loyalty_pts(){
				let self = this;
				let order = this.env.pos.get_order();
				let orderlines = order.get_orderlines();
				let partner = this.props.partner;
				let loyalty_settings = this.env.pos.pos_loyalty_setting;
				
				self.partner = partner || {};
				self.loyalty = partner.loyalty_pts;
				if(loyalty_settings.length != 0)
				{
					let product_id = loyalty_settings[0].product_id[0];
					let product = this.env.pos.db.get_product_by_id(product_id);
					self.product = product;
					for (var i=0; i<loyalty_settings.length; i++){
						var loyalty_setting = loyalty_settings[i]
						if(partner.tier_id[1] == loyalty_setting.loyalty_tier[1]){
							if(loyalty_setting.redeem_ids.length != 0)
							{
								let redeem_arr = []
								for (let i = 0; i < loyalty_setting.redeem_ids.length; i++) {
									for (let j = 0; j < this.env.pos.pos_redeem_rule.length; j++) {
										if(loyalty_setting.redeem_ids[i] == this.env.pos.pos_redeem_rule[j].id)
										{
											redeem_arr.push(this.env.pos.pos_redeem_rule[j]);
										}
									}
								}

								for (let j = 0; j < redeem_arr.length; j++) {
									if( parseInt(redeem_arr[j].min_amt) <= parseInt(partner.loyalty_pts) && parseInt(partner.loyalty_pts) <= parseInt(redeem_arr[j].max_amt))
									{
										redeem = redeem_arr[j];
										break;
									}
								}
								if(redeem)
								{
									let point_value = parseInt(redeem.reward_amt) * parseInt(self.loyalty);
									if (partner){
										self.loyalty_amount = point_value;
										partner.loyalty_amount = point_value;
									}
								}
								
							}
						}
					}	
				}
			}

			redeemPoints() {
				let self = this;
				let order = this.env.pos.get_order();
				let orderlines = order.orderlines;
				let update_orderline_loyalty = 0 ;
				let entered_code = $("#entered_item_qty").val();
				let point_value = 0;
				let remove_line;	
				let loyalty = self.loyalty;

				if(entered_code<0){
					alert('Please enter valid amount.');
					return
				}

				if(redeem && redeem.min_amt <= loyalty &&  loyalty<= redeem.max_amt)
				{
					if(parseInt(entered_code) <= loyalty)
					{
						let total = order.get_total_with_tax();
						let redeem_value = parseInt(redeem.reward_amt) * parseInt(entered_code)
						if (redeem_value > total) {
							alert('Please enter valid amountss.')
						}
						if (redeem_value <= total) {
							order.add_product(self.product, {
								price: -redeem_value
							});

							update_orderline_loyalty = loyalty - parseInt(entered_code)
							remove_line = orderlines.models[orderlines.length-1].id
							order.redeemed_points = parseInt(entered_code);
							order.set('update_after_redeem',update_orderline_loyalty)
							order.redeem_done = true;
							order.set("redeem_point",parseInt(entered_code));
							order.set('remove_line', remove_line);
							self.trigger('close-popup')
							self.showScreen('ProductScreen');
						}
					}
					else{
						alert('Please enter valid amount.');
					}
				}
				else{
					alert("limit exceeded");
				}	
				          
			}
		};
	
	Registries.Component.extend(LoyaltyPopupWidget, BiLoyaltyPopupWidget);
	return BiLoyaltyPopupWidget;

});