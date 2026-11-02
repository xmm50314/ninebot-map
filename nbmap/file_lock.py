"""Advisory file locks shared by local CLI, server, and worker processes."""
import errno
import os

if os.name == 'nt':
    import msvcrt
else:
    import fcntl


def _prepare_windows_region(stream):
    stream.seek(0, os.SEEK_END)
    if stream.tell() == 0:
        stream.write('\0')
        stream.flush()
    stream.seek(0)


def lock(stream, *, blocking=True):
    """Lock one byte from the start of an open lock file."""
    if os.name == 'nt':
        _prepare_windows_region(stream)
        mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
        try:
            msvcrt.locking(stream.fileno(), mode, 1)
        except OSError as exc:
            if not blocking and exc.errno in (errno.EACCES, errno.EDEADLK):
                raise BlockingIOError(exc.errno, exc.strerror) from exc
            raise
        return
    flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
    fcntl.flock(stream.fileno(), flags)


def unlock(stream):
    if os.name == 'nt':
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return
    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
