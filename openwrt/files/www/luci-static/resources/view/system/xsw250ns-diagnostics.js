'use strict';
'require view';
'require rpc';

const collect = rpc.declare({
	object: 'luci.xsw250ns-diagnostics', method: 'collect',
	params: ['group'], expect: { '': {} }, timeout: 30000
});

const groups = [
	['system', 'Hệ thống, CPU, RAM & nhiệt độ'],
	['storage', 'NAND, UBI, overlay & U-Boot'],
	['ports', 'MAC, LAN/WAN, PHY 2.5G & định tuyến'],
	['wireless', 'Wi-Fi, radio & driver'],
	['services', 'Dịch vụ, DNS, firewall & VPN'],
	['logs', 'Sự kiện kernel & nhật ký hệ thống']
];

function pretty(value) { return JSON.stringify(value, null, 2); }
function show(value) { return value == null ? 'Chưa có dữ liệu' : String(value); }
function cell(value) { return E('td', {}, show(value)); }
function table(headers, rows) {
	return E('div', { style: 'overflow-x:auto' }, [E('table', { 'class': 'table' }, [
		E('tr', { 'class': 'tr table-titles' }, headers.map(h => E('th', { 'class': 'th' }, h))),
		...rows.map(row => E('tr', { 'class': 'tr' }, row.map(cell)))
	])]);
}
function evidence(title, value) {
	return E('details', { style: 'margin:0.8em 0' }, [
		E('summary', { style: 'cursor:pointer;font-weight:bold' }, title),
		E('pre', { style: 'white-space:pre-wrap;overflow-wrap:anywhere;max-height:38em;overflow:auto' },
			typeof value === 'string' ? value : pretty(value))
	]);
}
function findings(report) {
	const items = report.findings || [];
	if (!items.length) return E('p', {}, 'Chưa phát hiện cảnh báo theo các điều kiện đã kiểm tra. Không phải chứng nhận toàn bộ phần cứng hoạt động tốt.');
	return E('div', {}, items.map(f => E('div', {
		'class': 'alert-message ' + (f.level === 'warning' ? 'warning' : 'notice'),
		style: 'margin-bottom:0.6em'
	}, [E('strong', {}, f.title), E('p', {}, f.evidence), E('p', {}, f.advice)])));
}
function content(report) {
	const d = report.data || {}, nodes = [findings(report)];
	if (report.group === 'system') {
		const m = d.info?.memory || {};
		nodes.push(table(['Thông số', 'Giá trị'], [
			['Model', d.board?.model], ['Kernel', d.board?.kernel],
			['Firmware', report.build], ['Uptime (giây)', d.info?.uptime],
			['RAM tổng (byte)', m.total], ['RAM khả dụng (byte)', m.available],
			['CPU online', d.cpu_online], ['Load', d.load_average],
			['Thời gian router', d.clock?.text?.trim()]
		]));
		nodes.push(table(['Cảm biến', 'Loại', 'Nhiệt độ °C'], (d.thermal || []).map(t =>
			[t.zone, t.type, t.temperature_millic == null ? null : (t.temperature_millic / 1000).toFixed(1)])));
	} else if (report.group === 'ports') {
		nodes.push(table(['Cổng', 'Hiện diện', 'Link', 'Mbps', 'Duplex', 'MAC', 'Kiểu gán MAC', 'RX/TX lỗi'],
			(d.devices || []).map(p => [p.name, p.present ? 'Có' : 'Không',
				p.carrier == null ? null : p.carrier ? 'Có' : 'Không', p.speed_mbps, p.duplex, p.mac,
				({ 0: 'Cố định', 1: 'Ngẫu nhiên', 2: 'Lấy từ thiết bị khác', 3: 'Đã gán bằng phần mềm' })[p.address_assignment_type],
				p.counters ? show(p.counters.rx_errors) + '/' + show(p.counters.tx_errors) : null])));
		nodes.push(E('p', {}, 'Bộ đếm lỗi và carrier_changes là số tích lũy. Thu thập lại để so sánh; link 1G trên cổng 2.5G có thể là thương lượng bình thường với thiết bị 1G.'));
	} else if (report.group === 'wireless') {
		nodes.push(table(['Radio', 'Đang lên', 'Đã tắt', 'Đang chờ', 'Khởi tạo lỗi', 'Kênh', 'Chế độ'],
			(d.radios || []).map(r => [r.name, r.up, r.disabled, r.pending, r.retry_setup_failed, r.config?.channel, r.config?.htmode])));
	} else if (report.group === 'services') {
		nodes.push(table(['Dịch vụ', 'Đăng ký với procd', 'Instance đang chạy'],
			(d.services || []).map(s => [s.name, s.registered ? 'Có' : 'Chưa thấy',
				s.registered ? s.instances.filter(i => i.running).length + '/' + s.instances.length : 'Có thể chưa cài hoặc không chạy qua procd'])));
	}
	for (const key of Object.keys(d)) nodes.push(evidence(key, d[key]));
	return E('div', {}, nodes);
}

return view.extend({
	load() { return Promise.resolve(); },

	render() {
		let busy = false, snapshot = null;
		const reports = {}, sections = {}, errors = {};
		const message = E('p', { role: 'status', 'aria-live': 'polite' }, 'Chưa thu thập. Bấm nút để đọc trạng thái hiện tại.');
		const downloads = E('button', { 'class': 'cbi-button cbi-button-action', disabled: true }, 'Tải báo cáo JSON');
		const refresh = E('button', { 'class': 'cbi-button cbi-button-apply' }, 'Thu thập toàn bộ chẩn đoán');
		const collection = E('div', {}, groups.map(([id, title]) => {
			sections[id] = E('div', {}, 'Chưa thu thập.');
			return E('details', { open: id === 'system', style: 'margin:1em 0' }, [
				E('summary', { style: 'font-size:1.15em;font-weight:bold;cursor:pointer' }, title), sections[id]
			]);
		}));
		refresh.addEventListener('click', async () => {
			if (busy) return;
			busy = true; refresh.disabled = true; downloads.disabled = true;
			// Replace every group: a failed fresh request must never display old data.
			for (const [id] of groups) { delete reports[id]; delete errors[id]; sections[id].replaceChildren('Đang chờ…'); }
			snapshot = { schema: 2, started_at_browser: new Date().toISOString() };
			let failed = 0;
			try {
				for (const [id, title] of groups) {
					message.textContent = 'Đang đọc: ' + title + '…';
					try {
						const report = await collect(id);
						if (!report || report.error || report.group !== id || report.schema !== 2 || !report.data)
							throw new Error(report?.error || 'RPC trả dữ liệu không đúng nhóm.');
						reports[id] = report;
						sections[id].replaceChildren(content(report));
					} catch (e) {
						failed++; errors[id] = String(e.message || e);
						sections[id].replaceChildren(E('p', { 'class': 'alert-message warning' }, 'Không đọc được nhóm này: ' + errors[id]));
					}
				}
				snapshot.finished_at_browser = new Date().toISOString();
				message.textContent = 'Đã đọc ' + (groups.length - failed) + '/' + groups.length + ' nhóm. ' +
					(failed ? 'Báo cáo có nhóm thiếu dữ liệu; không coi là đạt kiểm tra.' : 'Xem cảnh báo và bằng chứng trong từng nhóm.') +
					' Thời điểm trình duyệt: ' + snapshot.finished_at_browser;
			} finally {
				busy = false; refresh.disabled = false;
				downloads.disabled = Object.keys(reports).length === 0;
			}
		});
		downloads.addEventListener('click', () => {
			if (busy || !snapshot || !Object.keys(reports).length) return;
			const data = { ...snapshot, groups: reports, collection_errors: errors,
				privacy: 'Contains MAC/IP, network status and filtered logs. Review before sharing.' };
			const url = URL.createObjectURL(new Blob([pretty(data) + '\n'], { type: 'application/json;charset=utf-8' }));
			const link = E('a', { href: url, download: 'xsw250ns-diagnostics-' + new Date().toISOString().replace(/[:.]/g, '-') + '.json' });
			document.body.appendChild(link); link.click(); link.remove();
			setTimeout(() => URL.revokeObjectURL(url), 1000);
		});
		return E('div', {}, [
			E('h2', {}, 'Chẩn đoán hệ thống — XSW250-NS'),
			E('p', {}, 'Đọc trạng thái thực tế và chỉ ra những dấu hiệu cần kiểm tra. Mở từng nhóm để xem đầy đủ số liệu, log và bằng chứng. Chưa có dữ liệu được ghi rõ; không tự kết luận hỏng linh kiện.'),
			E('p', {}, 'Thu thập khi bạn bấm nút; không tự sửa cấu hình, khởi động lại, ghi flash hoặc gửi dữ liệu ra Internet. MAC/IP có trong báo cáo. Đã lọc khóa, mật khẩu và dòng bootargs; hãy xem lại trước khi chia sẻ.'),
			E('p', {}, [refresh, ' ', downloads]), message, collection,
			E('p', { 'class': 'cbi-value-description' }, 'PON và chức năng điện thoại TEL chưa được hỗ trợ. Chẩn đoán phần mềm không thay thế kiểm tra router thực tế; tốc độ link, đèn và cảm biến còn phụ thuộc driver/phần cứng.')
		]);
	},
	handleSave: null, handleSaveApply: null, handleReset: null
});
