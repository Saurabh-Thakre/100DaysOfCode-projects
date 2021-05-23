"""
Utilities for reading and writing Mach-O headers
"""

from pkg_resources import require
require("altgraph")

import sys
import struct
from macholib.mach_o import *
from macholib.dyld import dyld_find, framework_info

from altgraph.compat import *

__all__ = ['MachO']

RELOCATABLE = set((
    # relocatable commands that should be used for dependency walking
    LC_LOAD_DYLIB,
    LC_LOAD_WEAK_DYLIB,
    LC_PREBOUND_DYLIB,
))

RELOCATABLE_NAMES = {
    LC_LOAD_DYLIB: 'load_dylib',
    LC_LOAD_WEAK_DYLIB: 'load_weak_dylib',
    LC_PREBOUND_DYLIB: 'prebound_dylib',
}

def shouldRelocateCommand(cmd):
    """Should this command id be investigated for relocation?"""
    return cmd in RELOCATABLE

class MachO(object):
    """Provides reading/writing the Mach-O header of a specific existing file"""
    #   filename   - the original filename of this mach-o
    #   sizediff   - the current deviation from the initial mach-o size
    #   header     - the mach-o header
    #   commands   - a list of (load_command, somecommand, data)
    #                data is either a str, or a list of segment structures
    #   total_size - the current mach-o header size (including header)
    #   low_offset - essentially, the maximum mach-o header size
    #   id_cmd     - the index of my id command, or None


    def __init__(self, filename):

        # supports the ObjectGraph protocol
        self.graphident = filename
        self.filename = filename
        
        # initialized by load
        self.fat = None
        self.headers = []
        self.load(file(filename, 'rb'))

    def __repr__(self):
        return "<MachO filename=%r>" % (self.filename,)

    def load(self, fh):
        header = struct.unpack('>I', fh.read(4))[0]
        fh.seek(-4, 1)
        if header == FAT_MAGIC:
            self.load_fat(fh)
        else:
            self.load_header(fh, 0)

    def load_fat(self, fh):
        self.fat = fat_header.from_fileobj(fh)
        archs = [fat_arch.from_fileobj(fh) for i in xrange(self.fat.nfat_arch)]
        for arch in archs:
            self.load_header(fh, arch.offset)

    def rewriteLoadCommands(self, *args, **kw):
        changed = False
        for header in self.headers:
            if header.rewriteLoadCommands(*args, **kw):
                changed = True
        return changed

    def load_header(self, fh, offset):
        fh.seek(offset)
        header = struct.unpack('>I', fh.read(4))[0]
        fh.seek(-4, 1)
        headers = {
            MH_MAGIC: (MachOHeader, '>'),
            MH_CIGAM: (MachOHeader, '<'),
            MH_MAGIC_64: (MachOHeader64, '>'),
            MH_CIGAM_64: (MachOHeader64, '<'),
        }
        try:
            cls, endian = headers[header]
        except KeyError:
            raise ValueError("Unknown Mach-O header: 0x%08x in %s @ %d" % (header, self.filename, offset))
        self.headers.append(cls(self, fh, offset, endian))

    def write(self, f):
        for header in self.headers:
            header.write(f)
    
class MachOHeader(object):
    """Provides reading/writing the Mach-O header of a specific existing file"""
    #   filename   - the original filename of this mach-o
    #   sizediff   - the current deviation from the initial mach-o size
    #   header     - the mach-o header
    #   commands   - a list of (load_command, somecommand, data)
    #                data is either a str, or a list of segment structures
    #   total_size - the current mach-o header size (including header)
    #   low_offset - essentially, the maximum mach-o header size
    #   id_cmd     - the index of my id command, or None


    MH_MAGIC = MH_MAGIC
    mach_header = mach_header

    def __init__(self, parent, fh, offset, endian):

        # These are all initialized by self.load()
        self.parent = parent
        self.offset = offset

        self.endian = endian
        self.header = None
        self.commands = None
        self.id_cmd = None
        self.sizediff = None
        self.total_size = None
        self.low_offset = None
        self.filetype = None
        self.headers = []

        self.load(fh)

    def __repr__(self):
        return "<%s filename=%r offset=%d endian=%r>" % (type(self).__name__, self.parent.filename, self.offset, self.endian)

    def load(self, fh):
        self.sizediff = 0
        fh.seek(self.offset)
        kw = {'_endian_': self.endian}
        header = self.mach_header.from_fileobj(fh, **kw)
        self.header = header
        if header.magic != self.MH_MAGIC:
            raise ValueError("header has magic %08x, expecting %08x" % (header.magic, self.MH_MAGIC))

        cmd = self.commands = []

        self.filetype = MH_FILETYPE_SHORTNAMES[header.filetype]

        read_bytes = 0
        low_offset = sys.maxint
        for i in xrange(header.ncmds):
            # read the load command
            cmd_load = load_command.from_fileobj(fh, **kw)

            # read the specific command
            klass = LC_REGISTRY.get(cmd_load.cmd, None)
            if klass is None:
                raise ValueError("Unknown load command: %d" % (cmd_load.cmd,))
            cmd_cmd = klass.from_fileobj(fh, **kw)

            if cmd_load.cmd == LC_ID_DYLIB:
                # remember where this command was
                if self.id_cmd is not None:
                    raise ValueError("This dylib already has an id")
                self.id_cmd = i

            if cmd_load.cmd in (LC_SEGMENT, LC_SEGMENT_64):
                # for segment commands, read the list of segments
                segs = []
                # assert that the size makes sense
                if cmd_load.cmd == LC_SEGMENT:
                    section_cls = section
                else:
                    section_cls = section_64
                    
                expected_size = (
                    sizeof(klass) + sizeof(load_command) +
                    (sizeof(section_cls) * cmd_cmd.nsects)
                )
                if cmd_load.cmdsize != expected_size:
                    raise ValueError("Segment size mismatch")
                # this is a zero block or something
                # so the beginning is wherever the fileoff of this command is
                if cmd_cmd.nsects == 0:
                    if cmd_cmd.filesize != 0:
                        low_offset = min(low_offset, cmd_cmd.fileoff)
                else:
                    # this one has multiple segments
                    for j in xrange(cmd_cmd.nsects):
                        # read the segment
                        seg = section_cls.from_fileobj(fh, **kw)
                        # if the segment has a size and is not zero filled
                        # then its beginning is the offset of this segment
                        if seg.offset > 0 and seg.size > 0 and ((seg.flags & S_ZEROFILL) != S_ZEROFILL):
                            low_offset = min(low_offset, seg.offset)
                        segs.append(seg)
                # data is a list of segments
                cmd_data = segs
            else:
                # data is a raw str
                data_size = (
                    cmd_load.cmdsize - sizeof(klass) - sizeof(load_command)
                )
                cmd_data = fh.read(data_size)
            cmd.append((cmd_load, cmd_cmd, cmd_data))
            read_bytes += cmd_load.cmdsize

        # make sure the header made sense
        if read_bytes != header.sizeofcmds:
            raise ValueError("Read %d bytes, header reports %d bytes" % (read_bytes, header.sizeofcmds))
        self.total_size = sizeof(self.mach_header) + read_bytes
        self.low_offset = low_offset

        # this header overwrites a segment, what the heck?
        if self.total_size > low_offset:
            raise ValueError("total_size > low_offset (%d > %d)" % (self.total_size, low_offset))


    def walkRelocatables(self, shouldRelocateCommand=shouldRelocateCommand):
        """
        for all relocatable commands
        yield (command_index, command_name, filename)
        """
        for (idx, (lc, cmd, data)) in enumerate(self.commands):
            if shouldRelocateCommand(lc.cmd):
                name = RELOCATABLE_NAMES[lc.cmd]
                ofs = cmd.name - sizeof(lc.__class__) - sizeof(cmd.__class__)
                yield idx, name, data[ofs:data.find('\x00', ofs)]

    def rewriteInstallNameCommand(self, loadcmd):
        """Rewrite the load command of this dylib"""
        if self.id_cmd is not None:
            self.rewriteDataForCommand(self.id_cmd, loadcmd)
            return True
        return False

    def changedHeaderSizeBy(self, bytes):
        self.sizediff += bytes
        if (self.total_size + self.sizediff) > self.low_offset:
            print "WARNING: Mach-O header may be too large to relocate"

    def rewriteLoadCommands(self, changefunc):
        """
        Rewrite the load commands based upon a change dictionary
        """
        data = changefunc(self.parent.filename)
        changed = False
        if data is not None:
            if self.rewriteInstallNameCommand(data):
                changed = True
        for idx, name, filename in self.walkRelocatables():
            data = changefunc(filename)
            if data is not None:
                if self.rewriteDataForCommand(idx, data):
                    changed = True
        return changed

    def rewriteDataForCommand(self, idx, data):
        lc, cmd, old_data = self.commands[idx]
        hdrsize = sizeof(lc.__class__) + sizeof(cmd.__class__)
        data = data + ('\x00' * (4 - (len(data) % 4)))
        newsize = hdrsize + len(data)
        self.commands[idx] = (lc, cmd, data)
        self.changedHeaderSizeBy(newsize - lc.cmdsize)
        lc.cmdsize, cmd.name = newsize, hdrsize
        return True

    def synchronize_size(self):
        if (self.total_size + self.sizediff) > self.low_offset:
            raise ValueError("New Mach-O header is too large to relocate")
        self.header.sizeofcmds += self.sizediff
        self.total_size = sizeof(self.mach_header) + self.header.sizeofcmds
        self.sizediff = 0

    def write(self, fileobj):
        # serialize all the mach-o commands
        self.synchronize_size()
        # this should nearly always be 0, but we keep track anyway
        fileobj.seek(self.offset, 1)
        begin = fileobj.tell()
        self.header.to_fileobj(fileobj)
        for (lc, cmd, data) in self.commands:
            lc.to_fileobj(fileobj)
            cmd.to_fileobj(fileobj)
            if isinstance(data, unicode):
                data = data.encode('utf-8')
            if isinstance(data, str):
                fileobj.write(data)
            else:
                # segments..
                for obj in data:
                    obj.to_fileobj(fileobj)

        # zero out the unused space, doubt this is strictly necessary
        # and is generally probably already the case
        fileobj.write('\x00' * (self.low_offset - (fileobj.tell() - begin)))

    def getSymbolTableCommand(self):
        for (lc, cmd, data) in self.commands:
            if lc.cmd == LC_SYMTAB:
                return cmd
        return None

    def getDynamicSymbolTableCommand(self):
        for (lc, cmd, data) in self.commands:
            if lc.cmd == LC_DYSYMTAB:
                return cmd
        return None

class MachOHeader64(MachOHeader):
    MH_MAGIC = MH_MAGIC_64
    mach_header = mach_header_64

def main(fn):
    m = MachO(fn)
    seen = set()
    for header in m.headers:
        #print '[%s endian=%r]' % (header.__class__.__name__, header.endian)
        #seen = set()
        for idx, name, other in header.walkRelocatables():
            if other not in seen:
                seen.add(other)
                print '\t'+other

if __name__ == '__main__':
    import sys
    files = sys.argv[1:] or ['/bin/ls']
    for fn in files:
        print fn
        main(fn)
