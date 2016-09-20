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
        return enc[:6] + '...' + enc[-6:]
    else:
        return enc


class Superblock(Structure):
    FIELDS = FieldGroup('Ext4 Superblock', [
        Field('stuff', 1024*4, hexencode, None, None)
    ])


def bytes_to_int(s):
    missing = 4 - len(s)
    s = '\x00' * missing + s
    return struct.unpack('>I', s)[0]


class MBR(Structure):
    _PARTITION = FieldGroup('Partition Table Entry', [
        Field('status', 1, hextrunc, None, None),
        Field('start_chs', 3, hextrunc, None, None),
        Field('type', 1, hextrunc, None, None),
        Field('end_chs', 3, hextrunc, None, None),
        Field('start_lba', 4, hextrunc, Superblock, bytes_to_int),
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
