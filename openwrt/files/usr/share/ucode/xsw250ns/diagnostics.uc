'use strict';

import * as fs from 'fs';
import { connect } from 'ubus';
import { cursor } from 'uci';
import { readStatus } from 'xsw250ns.state';

// The RPC accepts only a group name. It never accepts commands, paths or config.
const GROUPS = ['system', 'storage', 'ports', 'wireless', 'services', 'logs'];
const PORTS = ['eth0', 'eth1', 'lan1', 'lan2', 'lan3', 'lan4', 'lan2p5', 'br-lan'];
const SERVICES = ['network', 'firewall', 'dnsmasq', 'odhcpd', 'sysntpd', 'wpad',
	'dropbear', 'uhttpd', 'rpcd', 'sqm', 'pbr', 'samba4', 'blockd', 'openvpn', 'tailscale', 'zerotier'];

function read(path, limit) {
	// Reject FIFO/device inputs before open(); procfs symlinks are kernel-owned.
	let node = fs.lstat(path);
	if (node?.type == 'link' && index(path, '/proc/') == 0) node = fs.stat(path);
	if (node?.type != 'file') return null;
	const f = fs.open(path, 'r');
	if (!f) return null;
	const value = f.read(limit ?? 8192);
	f.close();
	return value == null ? null : trim(value);
}

function number(path) {
	const value = read(path, 128);
	return value != null && match(value, /^-?[0-9]+$/) ? +value : null;
}

function subset(value, names) {
	const out = {};
	for (let key in names) if (value?.[key] != null) out[key] = value[key];
	return out;
}

function call(bus, object, method, args) {
	try { return bus?.call(object, method, args ?? {}); }
	catch (e) { return null; }
}

function command(argv, limit, keep_tail) {
	// BusyBox timeout kills a stuck reader. No command is provided by the browser.
	const p = fs.popen(['/usr/bin/timeout', '-s', 'KILL', '2', '/bin/sh', '-c',
		'exec "$@" 2>&1', 'diagnostic', ...argv], 'r');
	if (!p) return { available: false, text: '', exit_code: null, truncated: false };
	const cap = limit ?? 12000;
	let text = '', total = 0, chunk;
	// Drain stdout even after reaching the bound, so a full pipe cannot deadlock.
	while (length(chunk = p.read(4096))) {
		total += length(chunk);
		if (keep_tail) {
			text += chunk;
			if (length(text) > cap) text = substr(text, length(text) - cap);
		} else if (length(text) < cap) text += substr(chunk, 0, cap - length(text));
	}
	const rc = p.close();
	return { available: rc == 0, text, exit_code: rc, truncated: total > cap };
}

function hiddenValues() {
	const hidden = [], u = cursor();
	// Read UCI solely to find values to mask; no config is returned or changed.
	for (let name in ['network', 'wireless', 'openvpn', 'ddns', 'system', 'rpcd']) {
		try {
			u.foreach(name, null, s => {
				for (let key, val in s)
					if (match(key, /(pass|secret|token|key|ssid|username|hostname|clientid)/i))
						for (let v in type(val) == 'array' ? val : [val])
							if (type(v) == 'string' && length(v) > 0) push(hidden, v);
			});
		} catch (e) { /* An absent optional package is not a collection failure. */ }
	}
	return hidden;
}

export function redact(text, hidden) {
	let out = '' + (text ?? '');
	// Never include a kernel command line: OEM bootargs can contain passwords.
	out = join('\n', filter(split(out, '\n'), line => !match(line, /kernel command line:|bootargs=/i)));
	out = replace(out, /(sk-|github_pat_|ghp_|AIza)[A-Za-z0-9_-]{8,}/g, '[TOKEN]');
	const private_header = match(out, /-----BEGIN[^\n]*PRIVATE KEY-----/);
	if (private_header) out = substr(out, 0, index(out, private_header[0])) + '[PRIVATE KEY REMOVED]';
	out = replace(out, /((password|passwd|secret|token|psk|ssid|username|serial|authorization|bearer|api[_-]?key)["' \t]*[:= ]+)[^\r\n]*/gi, '$1[HIDDEN]');
	out = replace(out, /([a-z][a-z0-9+.-]*:\/\/)[^[:space:]\/@]+@/gi, '$1[URL-CREDENTIALS]@');
	const secrets = sort(filter(hidden ?? [], v => type(v) == 'string' && length(v) > 0),
		(a, b) => length(b) - length(a));
	let masked = '', pos = 0;
	while (pos < length(out)) {
		let found = null;
		for (let secret in secrets)
			if (substr(out, pos, length(secret)) == secret) { found = secret; break; }
		if (found != null) { masked += '[HIDDEN]'; pos += length(found); }
		else { masked += substr(out, pos, 1); pos++; }
	}
	out = masked;
	return out;
}

function sanitize(value, hidden) {
	if (type(value) == 'string') return redact(value, hidden);
	if (type(value) == 'array') return map(value, v => sanitize(v, hidden));
	if (type(value) == 'object') {
		const out = {};
		for (let k, v in value) out[k] = sanitize(v, hidden);
		return out;
	}
	return value;
}

function thermal() {
	const rows = [];
	for (let path in fs.glob('/sys/class/thermal/thermal_zone[0-9]*'))
		push(rows, { zone: fs.basename(path), type: read(path + '/type', 128),
			temperature_millic: number(path + '/temp') });
	return rows;
}

function system(bus) {
	const b = call(bus, 'system', 'board'), info = call(bus, 'system', 'info');
	const cpu = [];
	for (let path in fs.glob('/sys/devices/system/cpu/cpufreq/policy[0-9]*'))
		push(cpu, { policy: fs.basename(path), driver: read(path + '/scaling_driver', 128),
			governor: read(path + '/scaling_governor', 128),
			current_khz: number(path + '/scaling_cur_freq'),
			minimum_khz: number(path + '/scaling_min_freq'), maximum_khz: number(path + '/scaling_max_freq') });
	return {
		board: subset(b, ['system', 'model', 'board_name', 'kernel']),
		release: subset(b?.release, ['distribution', 'version', 'revision', 'target', 'description']),
		info: subset(info, ['uptime', 'localtime', 'load', 'memory', 'swap']),
		cpu_online: read('/sys/devices/system/cpu/online', 128), cpu_frequency: cpu,
		thermal: thermal(), memory_detail: read('/proc/meminfo', 6000),
		load_average: read('/proc/loadavg', 256), kernel_tainted: number('/proc/sys/kernel/tainted'),
		clock: command(['/bin/date', '-Iseconds'], 128),
		led_status: readStatus()
	};
}

export function validMac(mac) {
	return type(mac) == 'string' && !!match(mac, /^[0-9a-fA-F][02468aAcCeE](:[0-9a-fA-F]{2}){5}$/)
		&& lc(mac) != '00:00:00:00:00:00';
}

export function readerPatternValid(reader) {
	if (type(reader) != 'string') return false;
	const lines = split(trim(reader), '\n');
	if (length(lines) != 2) return false;
	for (let line in lines) if (!match(line, /^\/dev\/ubi[0-9]+_[0-9]+ 0x0 0x1f000 0x1f000 1$/)) return false;
	const a = split(lines[0], ' ')[0], b = split(lines[1], ' ')[0];
	return a != b && split(a, '_')[0] == split(b, '_')[0];
}

function storage() {
	const devices = [], volumes = [], mtd = [];
	for (let path in fs.glob('/sys/class/mtd/mtd[0-9]*')) {
		const name = fs.basename(path);
		if (!match(name, /^mtd[0-9]+$/)) continue;
		const row = { device: name, name: read(path + '/name', 128), type: read(path + '/type', 128) };
		for (let attr in ['size', 'erasesize', 'writesize', 'oobsize', 'ecc_strength', 'ecc_step_size',
			'bitflip_threshold', 'corrected_bits', 'ecc_failures', 'bad_blocks', 'bbt_blocks']) row[attr] = number(path + '/' + attr);
		push(mtd, row);
	}
	for (let path in fs.glob('/sys/class/ubi/ubi[0-9]*')) {
		const name = fs.basename(path);
		if (match(name, /^ubi[0-9]+$/)) {
			const row = { device: name };
			for (let attr in ['mtd_num', 'eraseblock_size', 'total_eraseblocks', 'avail_eraseblocks',
				'bad_peb_count', 'reserved_for_bad', 'max_ec', 'mean_ec', 'volumes_count']) row[attr] = number(path + '/' + attr);
			push(devices, row);
		} else if (match(name, /^ubi[0-9]+_[0-9]+$/)) {
			const row = { volume: name, name: read(path + '/name', 128), type: read(path + '/type', 128) };
			for (let attr in ['usable_eb_size', 'reserved_ebs', 'data_bytes', 'corrupted', 'upd_marker']) row[attr] = number(path + '/' + attr);
			push(volumes, row);
		}
	}
	const reader = read('/tmp/xsw250ns-fw_env.config', 512);
	const env = command(['/usr/sbin/fw_printenv', '-n', 'ethaddr'], 256);
	// Only expose a valid MAC, never raw output from an environment reader.
	const mac = trim(env.text);
	return { mtd: read('/proc/mtd', 6000), mounts: read('/proc/mounts', 12000),
		space: command(['/bin/df', '-k', '/', '/rom', '/overlay', '/tmp'], 5000),
		mtd_statistics: mtd, ubi_devices: devices, ubi_volumes: volumes,
		usb_devices: command(['/usr/bin/lsusb'], 6000),
		block_devices: command(['/sbin/block', 'info'], 6000),
		rom_build: read('/rom/etc/xsw250ns-build-id', 256),
		runtime_build: read('/etc/xsw250ns-build-id', 256),
		reader_link: fs.readlink('/etc/fw_env.config'), rom_reader_link: fs.readlink('/rom/etc/fw_env.config'),
		runtime_reader_valid: readerPatternValid(reader),
		environment_mac: env.exit_code == 0 && match(mac, /^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$/) ? mac : null,
		environment_mac_valid: env.exit_code == 0 && validMac(mac),
		environment_read_exit: env.exit_code
	};
}

function ports(bus) {
	const devices = [];
	for (let name in PORTS) {
		const path = '/sys/class/net/' + name, stat = fs.stat(path);
		if (!stat) { push(devices, { name, present: false }); continue; }
		const counters = {};
		for (let key in ['rx_bytes', 'tx_bytes', 'rx_packets', 'tx_packets', 'rx_errors', 'tx_errors',
			'rx_dropped', 'tx_dropped', 'collisions', 'rx_crc_errors']) counters[key] = number(path + '/statistics/' + key);
		push(devices, { name, present: true, mac: read(path + '/address', 64),
			address_assignment_type: number(path + '/addr_assign_type'),
			operstate: read(path + '/operstate', 64), carrier: number(path + '/carrier'),
			speed_mbps: number(path + '/speed'), duplex: read(path + '/duplex', 64),
			mtu: number(path + '/mtu'), carrier_changes: number(path + '/carrier_changes'), counters });
	}
	const interfaces = [], dump = call(bus, 'network.interface', 'dump');
	for (let iface in dump?.interface ?? []) {
		const row = subset(iface, ['interface', 'up', 'pending', 'available', 'autostart', 'uptime', 'proto',
			'device', 'l3_device', 'metric', 'delegation', 'errors', 'inactive']);
		delete row.inactive; // nested inactive data is not an allowlisted schema
		for (let key in ['ipv4-address', 'ipv6-address', 'ipv6-prefix', 'route', 'dns-server'])
			if (iface[key] != null) row[key] = iface[key];
		push(interfaces, row);
	}
	return { devices, interfaces,
		phy_2p5: command(['/usr/sbin/ethtool', 'lan2p5'], 7000),
		phy_2p5_driver: command(['/usr/sbin/ethtool', '-i', 'lan2p5'], 2000),
		phy_2p5_eee: command(['/usr/sbin/ethtool', '--show-eee', 'lan2p5'], 2000),
		phy_2p5_statistics: command(['/usr/sbin/ethtool', '-S', 'lan2p5'], 8000),
		routes: command(['/sbin/ip', 'route', 'show', 'table', 'all'], 6000),
		ipv6_routes: command(['/sbin/ip', '-6', 'route', 'show', 'table', 'all'], 6000)
	};
}

function wireless(bus) {
	const status = call(bus, 'network.wireless', 'status'), radios = [];
	for (let name, radio in status ?? {}) {
		const config = subset(radio.config, ['band', 'channel', 'htmode', 'country', 'txpower', 'disabled']);
		const interfaces = [];
		for (let i in radio.interfaces ?? []) push(interfaces, { section: i.section, ifname: i.ifname,
			config: subset(i.config, ['mode', 'network', 'disabled', 'isolate', 'encryption']) });
		push(radios, { name, ...subset(radio, ['up', 'pending', 'autostart', 'disabled', 'retry_setup_failed']), config, interfaces });
	}
	return { status_available: status != null, radios,
		devices: command(['/usr/sbin/iw', 'dev'], 8000),
		capabilities: command(['/usr/sbin/iw', 'phy'], 16000),
		driver_modules: join('\n', filter(split(read('/proc/modules', 30000) ?? '', '\n'),
			line => !!match(line, /^(mt76|mt79|mac80211|cfg80211)/))) };
}

function services(bus) {
	const list = call(bus, 'service', 'list'), rows = [];
	for (let name in SERVICES) {
		const instances = [];
		for (let id, instance in list?.[name]?.instances ?? {})
			push(instances, { id, ...subset(instance, ['running', 'pid', 'exit_code', 'respawn']) });
		// registered=false does not imply a fault or even an installed package.
		push(rows, { name, registered: list?.[name] != null, instances });
	}
	return { status_available: list != null, services: rows,
		dns_resolvers: read('/tmp/resolv.conf.d/resolv.conf.auto', 3000),
		firewall_tables: command(['/usr/sbin/nft', 'list', 'tables'], 4000),
		connection_tracking: { count: number('/proc/sys/net/netfilter/nf_conntrack_count'),
			maximum: number('/proc/sys/net/netfilter/nf_conntrack_max') },
		time_sync: 'Xem trạng thái sysntpd và sự kiện đồng bộ giờ trong log; đồng hồ hợp lý chưa chứng minh đã đồng bộ NTP.',
		note: 'Không gửi ping, truy vấn DNS, gọi API hoặc kết nối ra Internet. Có default route chưa chứng minh Internet hoạt động.' };
}

function logs() {
	const kernel = command(['/bin/dmesg'], 96000, true), systemlog = command(['/sbin/logread', '-l', '180'], 64000, true);
	const pattern = /(error|fail|warn|timeout|thermal|watchdog|panic|out of memory|oom|rcu.*stall|ubi|ubifs|squashfs|nand|nvmem|mt79|mt76|airoha|en8811|pcs|serdes|link is|link down|link up|segfault|firmware)/i;
	const lines = filter(split(kernel.text, '\n'), line => !!match(line, pattern));
	return { kernel: { ...kernel, text: join('\n', slice(lines, -160)), matched_lines: length(lines),
			filtered: true, event_limit: 160 }, system: systemlog,
		note: 'Log chỉ thuộc bộ đệm hiện tại; sự kiện cũ có thể đã xoay vòng. Một dòng lỗi lịch sử không chứng minh lỗi đang tiếp diễn.' };
}

export function assess(group, data) {
	const findings = [];
	const add = (level, title, evidence, advice) => push(findings, { level, title, evidence, advice });
	if (group == 'system') {
		const m = data.info?.memory;
		if (m?.total > 0 && m?.available != null && m.available * 100 < m.total * 8)
			add('warning', 'RAM khả dụng thấp', `${m.available}/${m.total} byte`, 'Đối chiếu OOM và tiến trình dùng RAM; một ảnh chụp không xác định được nguyên nhân.');
		for (let t in data.thermal ?? []) if (t.temperature_millic != null && t.temperature_millic >= 95000)
			add('warning', 'Nhiệt độ cao', `${t.zone}: ${t.temperature_millic / 1000} °C`, 'Kiểm tra thông gió và tải; ngưỡng bảo vệ thực tế thuộc kernel.');
		if (!length(data.cpu_frequency ?? [])) add('info', 'Chưa có số liệu cpufreq', 'Không có policy trong sysfs', 'Không đồng nghĩa CPU ngừng hoạt động hoặc chạy sai tần số.');
	} else if (group == 'storage') {
		const mounts = data.mounts ?? '';
		if (match(mounts, /\S+ \/overlay ubifs rw[, ]/))
			add('info', 'Overlay UBIFS đã mount đọc/ghi', '/overlay: ubifs rw', 'Cần thử lưu cấu hình rồi reboot để xác minh tính bền vững; trang này không tự ghi thử.');
		else add('warning', 'Chưa xác nhận overlay UBIFS đọc/ghi', 'Không thấy /overlay ubifs rw trong /proc/mounts', 'Recovery chạy RAM có thể không có overlay. Nếu đang boot từ NAND, kiểm tra mount và log UBI.');
		if (match(mounts, /\S+ \/rom squashfs ro[, ]/)) add('info', 'SquashFS chỉ đọc là bình thường', '/rom: squashfs ro', 'Cấu hình cần được lưu qua overlay.');
		if (!data.runtime_reader_valid) add('warning', 'Reader U-Boot chưa đúng mẫu dự kiến', 'Thiếu hoặc sai /tmp/xsw250ns-fw_env.config', 'Đối chiếu hook preinit và hai volume ubootenv/ubootenv2; không ghi lại bootloader.');
		if (data.rom_build != null && data.runtime_build != data.rom_build)
			add('warning', 'Build ID runtime khác lower image', 'Marker trong /etc khác /rom', 'Có thể overlay còn tệp từ bản cũ. Kiểm tra đúng firmware và hook trong /rom.');
		if (data.environment_read_exit == 0 && data.environment_mac_valid === false)
			add('warning', 'MAC trong environment không hợp lệ', data.environment_mac ?? 'Không có MAC Ethernet unicast hợp lệ', 'Đối chiếu MAC gốc trong backup riêng; không gán MAC mặc định dùng chung cho nhiều thiết bị.');
		for (let m in data.mtd_statistics ?? []) if (m.ecc_failures > 0)
			add('warning', 'MTD có bộ đếm ECC thất bại', `${m.device}: ecc_failures=${m.ecc_failures}`, 'Đây là bộ đếm tích lũy. Đối chiếu thời điểm/log đọc NAND và theo dõi tăng trước khi kết luận nguyên nhân.');
		for (let d in data.ubi_devices ?? []) {
			if (d.avail_eraseblocks == 0) add('info', 'UBI đã phân bổ hết PEB khả dụng', d.device + ': avail_eraseblocks=0', 'Không tự chứng minh filesystem đầy hoặc NAND hỏng; xem df và trạng thái volume.');
			if (d.bad_peb_count > 0) add('warning', 'UBI có bad PEB', `${d.device}: ${d.bad_peb_count}`, 'NAND có thể có bad block từ nhà máy. Theo dõi số lượng tăng và lỗi ECC/UBIFS trước khi kết luận hỏng.');
		}
		for (let v in data.ubi_volumes ?? []) if (v.corrupted == 1 || v.upd_marker == 1)
			add('warning', 'Volume cần kiểm tra', v.volume + ': corrupted/upd_marker được đánh dấu', 'Đối chiếu log UBI và tiến trình cập nhật; không tự format hoặc xóa volume.');
	} else if (group == 'ports') {
		for (let d in data.devices ?? []) {
			if (d.present && match(d.name, /^eth[01]$/) && d.address_assignment_type == 1)
				add('warning', 'Ethernet đang dùng MAC ngẫu nhiên', d.name + ': addr_assign_type=1', 'Firmware chưa nhận MAC cố định ở giao diện này; kiểm tra nguồn MAC và đối chiếu sau reboot.');
			if (d.present && d.name == 'lan2p5' && d.carrier == 0)
				add('info', 'Cổng 2.5G chưa có carrier', 'lan2p5: carrier=0', 'Có thể chưa cắm dây. Nếu đã cắm, kiểm tra dây, cổng đối diện và log; chưa đủ để quy lỗi PHY.');
			if (d.counters?.rx_errors > 0 || d.counters?.tx_errors > 0)
				add('warning', 'Có bộ đếm lỗi Ethernet', `${d.name}: RX=${d.counters.rx_errors ?? 0}, TX=${d.counters.tx_errors ?? 0}`, 'So sánh hai lần thu thập để biết lỗi có tăng; bộ đếm tích lũy không xác định thời điểm lỗi.');
		}
	} else if (group == 'wireless') {
		if (!data.status_available) add('warning', 'Chưa đọc được trạng thái radio', 'network.wireless status không trả dữ liệu', 'Có thể dịch vụ đang khởi động hoặc RPC không sẵn sàng; xem log và module.');
		for (let r in data.radios ?? []) if (r.retry_setup_failed)
			add('warning', 'Radio khởi tạo thất bại', r.name + ': retry_setup_failed', 'Đối chiếu log mt76/MT7916, firmware và EEPROM; không tự thay calibration.');
	} else if (group == 'services') {
		if (!data.status_available) add('warning', 'Chưa đọc được trạng thái dịch vụ', 'service list không trả dữ liệu', 'Không coi dịch vụ không quan sát được là đã dừng.');
		const c = data.connection_tracking;
		if (c?.maximum > 0 && c.count != null && c.count * 100 > c.maximum * 90)
			add('warning', 'Bảng conntrack gần đầy', `${c.count}/${c.maximum}`, 'Kiểm tra lưu lượng và số kết nối trước khi điều chỉnh giới hạn.');
	} else if (group == 'logs') {
		if (match(data.kernel?.text ?? '', /kernel panic|out of memory|oom-kill|rcu.*stall/i))
			add('warning', 'Log có sự kiện hệ thống nghiêm trọng', 'Có panic/OOM/RCU stall trong bộ đệm', 'Đọc timestamp và ngữ cảnh; chưa xác định nguyên nhân chỉ bằng từ khóa.');
	}
	return findings;
}

export function collect(group) {
	if (index(GROUPS, group) < 0) die('Nhóm chẩn đoán không hợp lệ.');
	const board = read('/tmp/sysinfo/board_name', 256);
	if (board != 'vnpt,xsw250ns-ubi') die('Chỉ hỗ trợ XSW250-NS UBI.');
	const bus = connect(null, 1);
	let data;
	try {
		if (group == 'system') data = system(bus);
		else if (group == 'storage') data = storage();
		else if (group == 'ports') data = ports(bus);
		else if (group == 'wireless') data = wireless(bus);
		else if (group == 'services') data = services(bus);
		else data = logs();
	} catch (e) { bus?.disconnect(); die(e); }
	bus?.disconnect();
	const hidden = hiddenValues();
	return sanitize({ schema: 2, group, board, build: read('/etc/xsw250ns-build-id', 256),
		uptime: read('/proc/uptime', 128), findings: assess(group, data), data,
		limitations: ['PON/TEL chưa được hỗ trợ.', 'Chỉ quan sát, không tự sửa cấu hình, reboot hoặc ghi flash.',
			'Không kiểm tra hỏng phần cứng bằng số liệu phần mềm đơn lẻ.',
			'Báo cáo có MAC/IP, trạng thái mạng và log đã lọc; xem lại trước khi chia sẻ.'] }, hidden);
}
