"""Bound reads from untrusted backup media; never open FIFO or follow links."""
import os
import stat


def read_regular(path, maximum, exact=None):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError('Backup must be a bounded regular file')
        if exact is not None and info.st_size != exact:
            raise ValueError('Wrong backup size')
        content = source.read(maximum + 1)
        if len(content) != info.st_size or len(content) > maximum:
            raise ValueError('Backup changed size during read')
        return content
