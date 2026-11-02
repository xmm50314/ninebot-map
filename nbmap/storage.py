"""Private atomic persistence. Raw responses remain separate from derived exports."""
import csv
import io
import json
import os
import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .file_lock import lock, unlock

_WINDOWS_PRIVATE_DIRS = set()
_WINDOWS_PRIVATE_SID = None


def _windows_private_sid():
    global _WINDOWS_PRIVATE_SID
    if _WINDOWS_PRIVATE_SID:
        return _WINDOWS_PRIVATE_SID
    result = subprocess.run(['whoami', '/user'], capture_output=True, text=True, timeout=10)
    match = re.search(r'\b(S-1-[0-9-]+)\b', result.stdout)
    if result.returncode or not match:
        raise RuntimeError('无法确定当前 Windows 用户，不能保护私密目录。')
    _WINDOWS_PRIVATE_SID = match.group(1)
    return _WINDOWS_PRIVATE_SID


def _protect_windows_directory(path):
    resolved = str(path.resolve()).casefold()
    if resolved in _WINDOWS_PRIVATE_DIRS:
        return
    sid = _windows_private_sid()
    result = subprocess.run(
        ['icacls', str(path), '/inheritance:r', '/grant:r', f'*{sid}:(OI)(CI)F'],
        capture_output=True, timeout=15)
    if result.returncode:
        raise RuntimeError('无法限制 Windows 私密目录权限，请检查 NTFS 权限。')
    result = subprocess.run(
        ['icacls', str(path), '/remove:g', '*S-1-3-4', '/T', '/C'],
        capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError('无法清理 Windows 私密目录权限，请检查 NTFS 权限。')
    _WINDOWS_PRIVATE_DIRS.add(resolved)


def private_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    if os.name == 'nt':
        _protect_windows_directory(path)
    return path


@contextmanager
def sync_lock(root):
    """One writer per local archive directory; the OS releases locks after crashes."""
    path = private_dir(root) / 'sync.lock'
    with path.open('a') as stream:
        path.chmod(0o600)
        try:
            lock(stream, blocking=False)
        except BlockingIOError:
            raise RuntimeError('另一个同步或配置任务正在运行，请稍后重试。') from None
        try:
            yield
        finally:
            unlock(stream)


def write_text(path, text):
    path = Path(path)
    private_dir(path.parent)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".writing-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, value):
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_csv(path, rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        # Neutralize spreadsheet formulas in untrusted textual fields.
        writer.writerow({k: ("'" + v if isinstance(v, str) and v.lstrip().startswith(
            ("=", "+", "-", "@")) else v) for k, v in row.items()})
    write_text(path, "\ufeff" + stream.getvalue())
