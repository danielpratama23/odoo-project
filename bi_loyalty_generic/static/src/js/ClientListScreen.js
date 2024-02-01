odoo.define('bi_loyalty_generic.ClientListScreen', function(require) {
	'use strict';

	const ClientListScreen = require('point_of_sale.ClientListScreen');
	const Registries = require('point_of_sale.Registries');
	const session = require('web.session');
	const core = require('web.core');
	const _t = core._t;

	const BiClientListScreen = (ClientListScreen) =>
		class extends ClientListScreen {
			constructor() {
				super(...arguments);
				var self = this;
				this.searchClient();
			}
		}

	Registries.Component.extend(ClientListScreen, BiClientListScreen);
	return ClientListScreen;

});