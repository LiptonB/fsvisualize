import collections

class Field(object):
    def __init__(self, description, length, formatter, constructor):
        self.description = description
        self.length = length
        self.formatter = formatter
        self.constructor = constructor

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
                sub_path = '%s/%d' % (path, i)
            else:
                sub_path = str(i)
            subfields.append(field.as_dict(contents, sub_path))

        fg_dict = {
            'description': self.description,
            'subfields': subfields,
        }
        return fg_dict

    def field_contents(self, content_bytes, field_id):
        start = sum(field.length for field in self.fields[0:field_id])
        contents = content_bytes[start:start+self.fields[field_id].length]
        return contents

class Structure(object):
    FIELDS = FieldGroup('__unknown__', [])

    def __init__(self, image, offset):
        self.image = image
        self.offset = offset

    def as_dict(self):
        content = self.image[self.offset:self.offset+self.length()]
        struct_dict = self.FIELDS.as_dict(content, '')
        return struct_dict

    def __getitem__(self, item):
        pass

    def length(self):
        return self.FIELDS.length


def hexencode(s):
    enc = s.encode('hex')
    return enc


def hextrunc(s):
    enc = s.encode('hex')
    if len(enc) > 20:
        return enc[:6] + '...' + enc[-6:]
    else:
        return enc


class MBR(Structure):
    _PARTITION = FieldGroup('Partition Table Entry', [
        Field('status', 1, hextrunc, None),
        Field('start_chs', 3, hextrunc, True),
        Field('type', 1, hextrunc, None),
        Field('end_chs', 3, hextrunc, None),
        Field('start_lba', 4, hextrunc, None),
        Field('length', 4, hextrunc, None),
    ])
    FIELDS = FieldGroup('Master Boot Record', [
        Field('code', 446, hextrunc, None),
        _PARTITION,
        _PARTITION,
        _PARTITION,
        _PARTITION,
        Field('signature', 2, hextrunc, None),
    ])

    def partition(self, start_lba):
        start_byte = start_lba * 512 + 1024
        return Superblock(self.image, start_byte)

class Superblock(Structure):
    FIELDS = FieldGroup('Ext4 Superblock', [
        Field('stuff', 1024*4, hexencode, None)
    ])
