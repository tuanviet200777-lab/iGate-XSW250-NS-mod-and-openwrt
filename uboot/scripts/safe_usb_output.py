"""Write backup files under a pinned USB directory without following links."""
import os
import stat


def stage_files(destination, files):
    # The caller supplies a trusted, existing USB mount/staging root.
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = os.open(destination, flags)
    directory = None
    try:
        try:
            os.mkdir('XSW250NS-STOCK', mode=0o700, dir_fd=root)
        except FileExistsError:
            pass
        directory = os.open('XSW250NS-STOCK', flags, dir_fd=root)
        for name, content in files.items():
            if not name or name in ('.', '..') or '/' in name or '\\' in name:
                raise ValueError('Invalid output basename')
            try:
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=directory)
            except FileExistsError:
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                with os.fdopen(fd, 'rb') as existing:
                    st = os.fstat(existing.fileno())
                    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size != len(content):
                        raise ValueError('Unsafe or different existing file: ' + name)
                    if existing.read(len(content) + 1) != content:
                        raise ValueError('Refuse to replace different file: ' + name)
            else:
                with os.fdopen(fd, 'wb') as output:
                    output.write(content)
                    output.flush()
                    os.fsync(output.fileno())
        os.fsync(directory)
    finally:
        if directory is not None:
            os.close(directory)
        os.close(root)
