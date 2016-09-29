import collections
import struct

class Error(Exception):
    pass


class UsageError(Error):
    pass


class IncorrectLevelError(Error):
    pass


class Field(object):
    def __init__(self, description, length, formatter, constructor, interpreter):
        self.description = description
        self.length = length
        self.formatter = formatter
        self.constructor = constructor
        self.interpreter = interpreter

    def as_dict(self, content_bytes, path):
        field_dict = {
            'description': self.description,
            'contents': self.formatter(content_bytes)
        }

        if self.constructor is not None:
            field_dict['link'] = path

        return field_dict


class FieldGroup(object):
    def __init__(self, description, fields):
        self.description = description
        self.fields = fields
        self.length = sum(field.length for field in fields)
        
    def as_dict(self, content_bytes, path):
        subfields = []
        for i, field in enumerate(self.fields):
            contents = self.field_contents(content_bytes, i)
            if path:
                sub_path = '%s.%d' % (path, i)
            else:
                sub_path = str(i)
            subfields.append(field.as_dict(contents, sub_path))

        fg_dict = {
            'description': self.description,
            'subfields': subfields,
        }
        return fg_dict

    def field_contents(self, content_bytes, field_id):
        start = self.field_offset(field_id)
        length = self.field_length(field_id)
        contents = content_bytes[start:start+length]
        return contents

    def field_offset(self, field_id):
        offset = sum(field.length for field in self.fields[0:field_id])
        return offset

    def field_length(self, field_id):
        length = self.fields[field_id].length
        return length

    def __getitem__(self, key):
        return self.fields[key]


class Structure(object):
    FIELDS = None

    def __init__(self, image, content):
        self.image = image
        self.content = content
        self.fields = self.FIELDS

    @classmethod
    def from_offset(cls, image, offset):
        content = image[offset:offset+cls.FIELDS.length]
        return cls(image, content)

    def as_dict(self):
        struct_dict = self.fields.as_dict(self.content, '')
        return struct_dict

    def __getitem__(self, key):
        start = self.fields.field_offset(key)
        length = self.fields.field_length(key)
        subfield_content = self.content[start:start+length]
        subfield = AnonymousStruct(self.image, subfield_content, self.fields[key])
        return subfield

    def sub_struct(self, descriptor):
        subfields = descriptor.split('.')
        struct = self
        for subfield_id in subfields:
            struct = struct[int(subfield_id)]
        return struct

    def length(self):
        return self.fields.length

    def dereference(self):
        subclass = self.fields.constructor
        interpreter = self.fields.interpreter
        offset = interpreter(self.content)
        print 'Instantiating %s at offset 0x%x' % (subclass.__name__, offset)
        return subclass.from_offset(self.image, offset)


class AnonymousStruct(Structure):
    def __init__(self, image, content, fields):
        super(AnonymousStruct, self).__init__(image, content)
        self.fields = fields


def hexencode(s):
    enc = s.encode('hex')
    return enc


def hextrunc(s):
    enc = s.encode('hex')
    if len(enc) > 20:
        enc = enc[:6] + '...' + enc[-6:]
    enc = '0x' + enc
    return enc


def bytes_to_int(s):
    missing = 4 - len(s)
    s = '\x00' * missing + s
    return struct.unpack('>I', s)[0]

def le_bytes_to_int(s):
    missing = 4 - len(s)
    s = s + '\x00' * missing
    return struct.unpack('<I', s)[0]


def block_offset(s):
    block_offset = le_bytes_to_int(s)
    byte_offset = block_offset * 512 + 1024
    return byte_offset


class Superblock(Structure):
    _SUPERBLOCK = FieldGroup('Ext4 Superblock', [
        Field('s_inodes_count', 4, le_bytes_to_int, None, None),
        Field('s_blocks_count_lo', 4, le_bytes_to_int, None, None),
        Field('s_r_blocks_count_lo', 4, le_bytes_to_int, None, None),
        Field('s_free_blocks_count_lo', 4, le_bytes_to_int, None, None),
        Field('s_free_inodes_count', 4, le_bytes_to_int, None, None),
        Field('s_first_data_block', 4, le_bytes_to_int, None, None),
        Field('s_log_block_size', 4, le_bytes_to_int, None, None),
        Field('s_log_cluster_size', 4, le_bytes_to_int, None, None),
        Field('s_blocks_per_group', 4, le_bytes_to_int, None, None),
        Field('s_clusters_per_group', 4, le_bytes_to_int, None, None),
        Field('s_inodes_per_group', 4, le_bytes_to_int, None, None),
        Field('s_mtime', 4, le_bytes_to_int, None, None),
        Field('s_wtime', 4, le_bytes_to_int, None, None),
        Field('s_mnt_count', 2, le_bytes_to_int, None, None),
        Field('s_max_mnt_count', 2, le_bytes_to_int, None, None),
        Field('s_magic', 2, hextrunc, None, None),
        Field('s_state', 2, hextrunc, None, None),
        Field('s_errors', 2, hextrunc, None, None),
        Field('s_minor_rev_level', 2, hextrunc, None, None),
        Field('s_lastcheck', 4, le_bytes_to_int, None, None),
        Field('s_checkinterval', 4, hextrunc, None, None),
        Field('s_creator_os', 4, hextrunc, None, None),
        Field('s_rev_level', 4, hextrunc, None, None),
        Field('s_def_resuid', 2, hextrunc, None, None),
        Field('s_def_resgid', 2, hextrunc, None, None),
        Field('s_first_ino', 4, hextrunc, None, None),
        Field('s_inode_size', 2, hextrunc, None, None),
        Field('s_block_group_nr', 2, hextrunc, None, None),
        Field('s_feature_compat', 4, hextrunc, None, None),
        Field('s_feature_incompat', 4, hextrunc, None, None),
        Field('s_feature_ro_compat', 4, hextrunc, None, None),
        Field('s_uuid', 16, hextrunc, None, None),
        Field('s_volume_name', 16, str, None, None),
        Field('s_last_mounted', 64, str, None, None),
        Field('s_algorithm_usage_bitmap', 4, hextrunc, None, None),
        Field('don\'t care', 1024-204, lambda x:'', None, None),
    ])
    _GROUP_DESCRIPTOR = FieldGroup('Ext4 Group Descriptor', [
        Field('bg_block_bitmap_lo', 4, hextrunc, None, None),
        Field('bg_inode_bitmap_lo', 4, hextrunc, None, None),
        Field('bg_inode_table_lo', 4, hextrunc, None, None),
        Field('bg_free_blocks_count_lo', 2, le_bytes_to_int, None, None),
        Field('bg_free_inodes_count_lo', 2, le_bytes_to_int, None, None),
        Field('bg_used_dirs_count_lo', 2, le_bytes_to_int, None, None),
        Field('bg_flags', 2, hextrunc, None, None),
        Field('don\'t care', 4, hextrunc, None, None),
        Field('don\'t care', 2, hextrunc, None, None),
        Field('don\'t care', 2, hextrunc, None, None),
        Field('don\'t care', 2, hextrunc, None, None),
        Field('don\'t care', 2, hextrunc, None, None),
        Field('don\'t care', 4, hextrunc, None, None),
        Field('don\'t care', 4, hextrunc, None, None),
        Field('don\'t care', 4, hextrunc, None, None),
        Field('don\'t care', 2, hextrunc, None, None),
        Field('don\'t care', 2, hextrunc, None, None),
        Field('don\'t care', 2, hextrunc, None, None),
        Field('don\'t care', 2, hextrunc, None, None),
        Field('don\'t care', 4, hextrunc, None, None),
        Field('don\'t care', 2, hextrunc, None, None),
        Field('don\'t care', 2, hextrunc, None, None),
        Field('padding', 4, hextrunc, None, None),
    ])
    FIELDS = FieldGroup('Ext4 Filesystem', [
        _SUPERBLOCK,
        _GROUP_DESCRIPTOR,
    ])


class MBR(Structure):
    _PARTITION = FieldGroup('Partition Table Entry', [
        Field('status', 1, hextrunc, None, None),
        Field('start_chs', 3, hextrunc, None, None),
        Field('type', 1, hextrunc, None, None),
        Field('end_chs', 3, hextrunc, None, None),
        Field('start_lba', 4, hextrunc, Superblock, block_offset),
        Field('length', 4, hextrunc, None, None),
    ])
    FIELDS = FieldGroup('Master Boot Record', [
        Field('code', 446, hextrunc, None, None),
        _PARTITION,
        _PARTITION,
        _PARTITION,
        _PARTITION,
        Field('signature', 2, hextrunc, None, None),
    ])
