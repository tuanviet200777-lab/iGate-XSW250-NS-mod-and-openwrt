'use strict';

import * as fs from 'fs';

const DIR = '/var/run/xsw250ns';
const STATE = DIR + '/status.json';
const TEMP = DIR + '/status.json.new';

function directory(create) {
	if (create) fs.mkdir(DIR, 0o700);
	const st = fs.lstat(DIR);
	// /var/run is created by the OS and is not writable by unprivileged users.
	// Never follow a substituted directory symlink, including on service restart.
	if (st?.type != 'directory' || st.uid != 0) return false;
	if (create && !fs.chmod(DIR, 0o700)) return false;
	const now = fs.lstat(DIR);
	return now && !now.perm.group_write && !now.perm.other_write;
}

export function readStatus() {
	if (!directory(false)) return null;
	const st = fs.lstat(STATE);
	if (st?.type != 'file' || st.uid != 0 || st.perm.group_write || st.perm.other_write) return null;
	const f = fs.open(STATE, 'r');
	if (!f) return null;
	const text = f.read(4096);
	f.close();
	return text == null ? null : trim(text);
}

export function writeStatus(status) {
	if (!directory(true)) die('Unsafe runtime status directory.');
	const previous = fs.lstat(TEMP);
	if (previous && (previous.type != 'file' || previous.uid != 0)) die('Unsafe temporary status file.');
	const text = sprintf('%J\n', status);
	if (length(text) > 4096) die('Runtime status exceeds the size limit.');
	const f = fs.open(TEMP, 'w', 0o600);
	if (!f) die('Cannot open runtime status file.');
	const written = f.write(text);
	const flushed = f.flush();
	f.close();
	if (written != length(text) || !flushed || !fs.chmod(TEMP, 0o600) || !fs.rename(TEMP, STATE))
		die('Cannot publish runtime status.');
}

export function removeStatus() {
	if (directory(false)) {
		fs.unlink(STATE);
		fs.unlink(TEMP);
	}
}
