'use strict';
'require view';
'require form';
'require rpc';
'require poll';
'require uci';

const status = rpc.declare({ object: 'luci.xsw250ns-status', method: 'status', expect: { data: '' }, reject: true });

return view.extend({
	load() { return uci.load('xsw250ns_status'); },

	async render() {
		const current = E('p', {}, 'Đang đọc trạng thái…');
		const refresh = async () => {
			try {
				const s = JSON.parse(await status());
				current.textContent = 'CPU: ' + (s.temperature_millic == null ? 'không đọc được cảm biến' : (s.temperature_millic / 1000).toFixed(1) + '°C') +
					' · TEL1: ' + (!s.tel1_present ? 'chưa có LED GPIO' : s.temperature_millic == null ? 'lỗi cảm biến' : s.overheat ? 'cảnh báo nóng' : 'bình thường') +
					' · TEL2: ' + (!s.tel2_present ? 'chưa có LED GPIO' : s.tel2_mode == 'off' ? 'tắt' : s.online === true ? 'kết nối được' : s.online === false ? 'không kết nối được' : 'đang kiểm tra');
			} catch (e) { current.textContent = 'Chưa có trạng thái: dịch vụ đang tắt hoặc chưa khởi động. LED vật lý cần DTB của ITB r3.'; }
		};
		await refresh(); poll.add(refresh, 5);
		const m = new form.Map('xsw250ns_status', 'LED & Kết nối — XSW250-NS', 'Wi-Fi 2.4G/5G dùng GPIO từ bảng 7581ptled.conf của firmware gốc; sáng khi radio bật. Có thể đổi trigger tại Hệ thống → LED. TEL1/TEL2 dưới đây do dịch vụ trạng thái quản lý.');
		// Use the page permission already supplied by LuCI, including read-only logins.
		m.readonly = !L.hasViewPermission();
		const s = m.section(form.NamedSection, 'main', 'status', 'Đèn TEL dùng làm trạng thái');
		s.addremove = false;
		let o = s.option(form.Flag, 'enabled', 'Bật dịch vụ LED trạng thái'); o.rmempty = false;
		o = s.option(form.Flag, 'tel1_enabled', 'TEL1: cảnh báo nhiệt CPU'); o.rmempty = false;
		o = s.option(form.Value, 'temp_on', 'Sáng từ nhiệt độ (°C)'); o.datatype = 'range(60,115)'; o.rmempty = false;
		o = s.option(form.Value, 'temp_off', 'Tắt khi thấp hơn (°C)'); o.datatype = 'range(40,114)'; o.rmempty = false;
		o.validate = function(section, value) {
			const on = this.map.lookupOption('temp_on', section)[0]?.formvalue(section);
			return +value < +on ? true : 'Ngưỡng tắt phải thấp hơn ngưỡng sáng.';
		};
		o = s.option(form.ListValue, 'tel2_mode', 'TEL2');
		o.value('internet', 'Kiểm tra Internet qua ICMP');
		o.value('link', 'Có interface với đường mặc định');
		o.value('off', 'Tắt'); o.rmempty = false;
		o = s.option(form.Value, 'interval', 'Chu kỳ kiểm tra (giây)'); o.datatype = 'range(10,300)'; o.rmempty = false;
		for (const key of ['target1', 'target2']) {
			o = s.option(form.Value, key, key == 'target1' ? 'Đích ICMP thứ nhất' : 'Đích ICMP dự phòng');
			o.datatype = 'or(hostname,ip4addr)'; o.rmempty = false; o.depends('tel2_mode', 'internet');
		}
		return E('div', {}, [E('h2', {}, 'Trạng thái LED'), current,
			E('p', {}, 'TEL1 mặc định sáng từ 100°C, tắt dưới 95°C; nhấp nháy nếu không đọc được cảm biến. Không thay đổi cơ chế bảo vệ nhiệt của kernel. Không cần làm nóng router để thử đèn.'),
			E('p', {}, 'TEL2 sáng khi kiểm tra thành công hai lần liên tiếp; nhấp nháy sau ba lần thất bại. Trong lúc chưa có kết quả cũng nhấp nháy. ICMP bị chặn có thể báo mất mạng dù web vẫn vào được; khi đó dùng chế độ đường mặc định. Dịch vụ không tự khởi động lại router hoặc interface.'),
			await m.render()]);
	}
});
