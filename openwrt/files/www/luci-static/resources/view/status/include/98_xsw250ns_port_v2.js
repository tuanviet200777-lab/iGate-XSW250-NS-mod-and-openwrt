'use strict';
'require baseclass';
'require rpc';
'require uci';
'require ui';
'require xsw250ns.portrole as portrole';

const board = rpc.declare({ object: 'system', method: 'board', expect: { '': {} } });
const portStatus = rpc.declare({ object: 'luci.xsw250ns-port', method: 'status', expect: { '': {} }, reject: true });
const access = rpc.declare({ object: 'session', method: 'access', params: ['scope', 'object', 'function'], expect: { access: false } });

function hasChanges(changes) {
	return Object.keys(changes).some(name => changes[name]?.length);
}

return baseclass.extend({
	title: 'LAN/WAN — 2.5G và LAN 1–4',

	async load() {
		const info = await board();
		if (info.board_name != 'vnpt,xsw250ns-ubi')
			return null;
		if (this.busy)
			return this.snapshot;
		const data = await Promise.all([portStatus(), L.resolveDefault(access('uci', 'network', 'write'), false), L.resolveDefault(access('uci', 'firewall', 'write'), false)]);
		if (data[0].error) throw new Error(data[0].error);
		this.snapshot = [data[0].network, data[0].firewall, data[1], data[2]];
		return this.snapshot;
	},

	async handleApply(role, port) {
		if (this.busy)
			return;
		this.busy = true;
		try {
			if (hasChanges(await uci.changes()))
				throw new Error('Đang có thay đổi chưa áp dụng. Hãy áp dụng hoặc hoàn tác các thay đổi đó trước.');
			if (!await access('uci', 'network', 'write') || !await access('uci', 'firewall', 'write'))
				throw new Error('Tài khoản không có quyền sửa cấu hình mạng.');
			// Use a separate cursor so polling and other status cards keep their state.
			const cursor = new uci.constructor();
			await cursor.load(['network', 'firewall']);
			const values = name => {
				const result = {};
				cursor.sections(name, null, s => { result[s['.name']] = s; });
				return result;
			};
			const ops = portrole.plan(values('network'), values('firewall'), role, port);
			if (!ops.length)
				return;
			for (const op of ops) {
				if (op.type) cursor.add(op.config, op.type, op.section);
				else if (op.remove) cursor.remove(op.config, op.section);
				else if (op.value == null) cursor.unset(op.config, op.section, op.option);
				else cursor.set(op.config, op.section, op.option, op.value);
			}
			if (hasChanges(await uci.changes()))
				throw new Error('Có thay đổi cấu hình mới từ phiên này. Hãy xử lý thay đổi đang chờ trước.');
			await cursor.save();
			await ui.changes.init();
			this.selectedRoles = {};
			ui.changes.apply(true);
		} catch (error) {
			ui.addNotification(null, E('p', {}, error.message || String(error)), 'error');
		} finally {
			this.busy = false;
		}
	},

	render(data) {
		if (!data)
			return null;
		this.selectedRoles ||= {};
		return E('div', {}, ['lan2p5', 'lan1', 'lan2', 'lan3', 'lan4'].map(port => {
		const status = portrole.inspect(data[0], data[1], port);
		const labels = { lan: 'LAN', wan: 'WAN — kết nối Internet', unused: 'Chưa gán vai trò', custom: 'Cấu hình tùy chỉnh' };
		const writable = data[2] && data[3];
		const selected = this.selectedRoles[port] || (status.role == 'lan' ? 'lan' : 'wan');
		const select = E('select', { 'class': 'cbi-input-select', 'disabled': this.busy || !writable || !status.supported ? true : null }, [
			E('option', { value: 'lan', selected: selected == 'lan' ? true : null }, 'LAN'),
			E('option', { value: 'wan', selected: selected == 'wan' ? true : null }, 'WAN')
		]);
		const button = E('button', {
			'class': 'cbi-button cbi-button-apply',
			'disabled': this.busy || !writable || !status.supported || selected == status.role ? true : null,
			'click': ui.createHandlerFn(this, () => this.handleApply(select.value, port))
		}, 'Lưu & áp dụng');
		select.addEventListener('change', () => {
			this.selectedRoles[port] = select.value;
			button.disabled = this.busy || !writable || !status.supported || select.value == status.role;
		});
		return E('div', {}, [
			E('p', {}, [port.toUpperCase() + ' — vai trò hiện tại: ', E('strong', {}, labels[status.role])]),
			E('div', { 'class': 'cbi-value' }, [select, ' ', button]),
			E('p', { 'class': 'cbi-value-description' }, status.reason || 'Chọn một cổng WAN; WAN cũ trở về LAN, giữ cấu hình DHCP/PPPoE. Quản trị qua cổng LAN khác khi chuyển. Không phải nhiều WAN đồng thời.'),
			!writable ? E('p', {}, 'Tài khoản hiện tại chỉ có quyền xem.') : null,
			E('a', { href: L.url('admin/network/network') }, 'Cấu hình mạng nâng cao')
		]);
		}));
	}
});
