#!/usr/bin/env python

import os
import sys
import errno
import codecs

from fuse import FUSE, FuseOSError, Operations

class DigasFilesystem(Operations):
    def __init__(self, root):
        self.root = root
        self.fancy_filenames = {} # nice_path: original_path

    # ************
    # Utility functions
    # ************

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    def _listdir(self, full_path):
        # Get only the most recent 1000 files, for performance reasons
        original_filenames = sorted(os.listdir(full_path), key=lambda s: os.path.getmtime(os.path.join(full_path, s)), reverse=True)[0:1000]
        nice_filenames = []

        for fn in original_filenames:
            if os.path.isdir(os.path.join(full_path, fn)):
                nice_filenames.append(fn)

            _, extension = os.path.splitext(fn)
            if extension in (".wav", ".WAV", ".mp3", ".MP3"):
                try:
                    nice_name = self._nice_name(fn, full_path)
                    self.fancy_filenames[os.path.join(full_path, nice_name)] = os.path.join(full_path, fn)
                    nice_filenames.append(nice_name)
                except IOError:
                    print "No DBE file found for " + fn
                except IndexError:
                    print "Error while reading DBE file for " + fn

        return nice_filenames

    def _nice_name(self, file_path, folder):
        START_TAG = "[TITLE]"
        END_TAG = "[FILENAME]"

        name, extension = os.path.splitext(file_path)
        if extension not in (".wav", ".WAV", ".mp3", ".MP3"):
            raise IOError
        with codecs.open(os.path.join(folder, name + ".DBE"), 'r', 'latin1') as f:
            first_bytes = f.read(300)
            title = (first_bytes.split(START_TAG))[1].split(END_TAG)[0]

        return title.replace("/", "-").replace("\\", "_") + extension

    # ************
    # Filesystem methods
    # ************

    def access(self, path, mode):
        full_path = self._full_path(path)
        try:
            real_path = self.fancy_filenames[full_path]
            if not os.access(real_path, mode):
                raise FuseOSError(errno.EACCES)
        except KeyError:
            if not os.access(full_path, mode):
                raise FuseOSError(errno.EACCES)

    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        try:
            real_path = self.fancy_filenames[full_path]
            st = os.lstat(real_path)
        except KeyError:
            st = os.lstat(full_path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    def readdir(self, path, fh):
        full_path = self._full_path(path)

        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dirents.extend(self._listdir(full_path))
        for r in dirents:
            yield r

    def statfs(self, path):
        full_path = self._full_path(path)
        try:
            real_path = self.fancy_filenames[full_path]
            stv = os.statvfs(real_path)
        except KeyError:
            stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    # ************
    # File methods
    # ************

    def open(self, path, flags):
        full_path = self._full_path(path)
        try:
            real_path = self.fancy_filenames[full_path]
            return os.open(real_path, flags)
        except KeyError:
            return os.open(full_path, flags)

    def read(self, path, length, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def release(self, path, fh):
        return os.close(fh)

    # ***************
    # NOT IMPLEMENTED
    # ***************

    def create(self, path, mode, fi=None):
        return 0

    def write(self, path, buf, offset, fh):
        return 0

    def truncate(self, path, length, fh=None):
        return 0

    def flush(self, path, fh):
        return 0

    def fsync(self, path, fdatasync, fh):
        return 0

    def chmod(self, path, mode):
        return 0

    def chown(self, path, uid, gid):
        return 0

    def readlink(self, path):
        return 0

    def unlink(self, path):
        return 0

    def symlink(self, target, name):
        return 0

    def rename(self, old, new):
        return 0

    def link(self, target, name):
        return 0

    def utimens(self, path, times=None):
        return 0

    def mknod(self, path, mode, dev):
        return 0

    def rmdir(self, path):
        return 0

    def mkdir(self, path, mode):
        return 0

def main(mountpoint, root):
    FUSE(DigasFilesystem(root), mountpoint, foreground=False, allow_other=True, ro=True)

if __name__ == '__main__':
    main(sys.argv[2], sys.argv[1])
