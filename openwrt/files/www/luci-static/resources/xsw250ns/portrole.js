'use strict';
'require baseclass';

const PORTS = ['lan2p5', 'lan1', 'lan2', 'lan3', 'lan4'];
const STATE = 'xsw250ns_port2p5';

function list(value) {
	return Array.isArray(value) ? value.slice() : String(value || '').trim().split(/\s+/).filter(Boolean);
}

function sections(config, type) {
	return Object.keys(config).filter(id => config[id]['.type'] == type);
}

function usesPort(device) {
	return PORTS.some(port => device == port || String(device || '').indexOf(port + '.') == 0);
}

return baseclass.extend({
	inspect(network, firewall, port = 'lan2p5') {
		const PORT = network.wan?.device || network.wan6?.device || 'lan2p5';
		const bridges = sections(network, 'device').filter(id => network[id].name == 'br-lan' && network[id].type == 'bridge');
		const zones = sections(firewall, 'zone').filter(id => firewall[id].name == 'wan');
		const fail = reason => ({ role: 'custom', supported: false, reason: reason });
		if (bridges.length != 1 || network.lan?.device != 'br-lan' || zones.length != 1)
			return fail('Cần cấu hình LAN br-lan và vùng tường lửa WAN tiêu chuẩn.');
		if (!PORTS.includes(port) || !PORTS.includes(PORT))
			return fail('WAN không dùng cổng vật lý tiêu chuẩn. Hãy dùng Mạng → Giao diện.');
		const bridge = bridges[0], ports = list(network[bridge].ports);
		if (network[bridge].vlan_filtering == '1' || sections(network, 'bridge-vlan').some(id => network[id].device == 'br-lan'))
			return fail('Mạng đang dùng VLAN trên bridge. Hãy đổi vai trò cổng trong Mạng → Giao diện.');
		if (network[STATE] && network[STATE]['.type'] != 'xsw250ns_port')
			return fail('Tên cấu hình cổng đã được sử dụng.');
		for (const id of sections(network, 'device')) {
			if (usesPort(network[id].name) && !PORTS.includes(network[id].name) || list(network[id].ports).some(p => usesPort(p) && !PORTS.includes(p)))
				return fail('Cổng mạng đang dùng VLAN. Hãy dùng Mạng → Giao diện.');
			if (id != bridge && list(network[id].ports).some(usesPort))
				return fail('Cổng mạng đang thuộc một bridge hoặc nhóm cổng khác.');
			if (usesPort(network[id].ifname))
				return fail('Cổng mạng đang dùng cấu hình VLAN hoặc thiết bị nâng cao.');
		}
		for (const id of sections(network, 'interface')) {
			const s = network[id];
			if (usesPort(s.device) && (id != 'wan' && id != 'wan6' || s.device != PORT))
				return fail('Cổng mạng đang dùng interface hoặc VLAN tùy chỉnh.');
			if (list(s.ifname).some(usesPort) || s.device == '@wan' && id != 'wan6')
				return fail('Cổng mạng có cấu hình phụ thuộc; hãy dùng Mạng → Giao diện.');
		}
		for (const id of ['wan', 'wan6']) {
			const s = network[id];
			if (s && (s['.type'] != 'interface' || s.device != PORT && !(id == 'wan6' && s.device == '@wan') || s.ifname || s.auto == '0'))
				return fail('WAN hiện tại dùng thiết bị khác hoặc cấu hình khởi động riêng. Hãy dùng Mạng → Giao diện.');
		}
		if (network.wan6?.device == '@wan' && !network.wan)
			return fail('Interface WAN6 đang thiếu interface WAN phụ thuộc.');
		for (const id of sections(firewall, 'zone')) {
			if (id != zones[0] && list(firewall[id].network).some(n => n == 'wan' || n == 'wan6'))
				return fail('Interface WAN đang thuộc vùng tường lửa khác. Hãy dùng Mạng → Giao diện.');
		}
		const inLAN = ports.includes(PORT);
		const activeWAN = ['wan', 'wan6'].some(id => network[id] && network[id].disabled != '1');
		if (inLAN && activeWAN)
			return fail('Cổng đang đồng thời gán vào LAN và WAN. Hãy kiểm tra Mạng → Giao diện.');
		return { supported: true, bridge: bridge, zone: zones[0], wanPort: PORT, role: ports.includes(port) ? 'lan' : activeWAN && port == PORT ? 'wan' : 'unused' };
	},

	plan(network, firewall, role, PORT = 'lan2p5') {
		if (role != 'lan' && role != 'wan')
			throw new Error('Vai trò cổng không hợp lệ.');
		const status = this.inspect(network, firewall, PORT);
		if (!status.supported)
			throw new Error(status.reason);
		if (status.role == role)
			return [];
		const ops = [];
		const set = (config, section, option, value) => ops.push({ config, section, option, value });
		const add = (config, section, type) => ops.push({ config, section, type });
		const ports = list(network[status.bridge].ports).filter(p => p != PORT);
		if (role == 'lan' && status.wanPort != PORT) {
			ports.push(PORT);
		} else if (role == 'lan') {
			const enabled = ['wan', 'wan6'].filter(id => network[id] && network[id].disabled != '1');
			if (!network[STATE])
				add('network', STATE, 'xsw250ns_port');
			set('network', STATE, 'disabled_interfaces', enabled);
			for (const id of enabled)
				set('network', id, 'disabled', '1');
			ports.push(PORT);
		} else {
			if (status.wanPort != PORT && !ports.includes(status.wanPort))
				ports.push(status.wanPort);
			if (!ports.some(p => PORTS.includes(p)))
				throw new Error('Phải giữ ít nhất một cổng LAN để quản trị.');
			const restore = list(network[STATE]?.disabled_interfaces);
			for (const id of ['wan', 'wan6']) {
				if (id == 'wan6' && !network[id])
					continue;
				if (!network[id]) {
					add('network', id, 'interface');
					set('network', id, 'proto', 'dhcp');
					set('network', id, 'device', PORT);
				}
				if (id == 'wan' || network[id]?.device != '@wan')
					set('network', id, 'device', PORT);
				if (id == 'wan' || restore.includes(id))
					set('network', id, 'disabled', null);
			}
			if (network[STATE])
				ops.push({ config: 'network', section: STATE, remove: true });
			const members = list(firewall[status.zone].network);
			for (const id of ['wan', 'wan6'])
				if ((network[id] || id == 'wan') && !members.includes(id)) members.push(id);
			set('firewall', status.zone, 'network', members);
		}
		set('network', status.bridge, 'ports', ports);
		return ops;
	}
});
