import collections

class Error(Exception):
    pass


class UsageError(Exception):
    pass


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
        start = sum(field.length for field in self.fields[0:field_id])
        contents = content_bytes[start:start+self.fields[field_id].length]
        return contents

    def constructor(self, image, offset):
        return Structure(image, offset, self.fields)

    def __getitem__(self, key):
        return self.fields[key]


class Structure(object):
    FIELDS = None

    def __init__(self, image, offset, fields=None):
        self.image = image
        self.offset = offset
        if self.FIELDS is None:
            if fields is None:
                raise UsageError('No fields provided to plain Structure')
            else:
                self.fields = fields
        else:
            if fields is not None:
                raise UsageError(
                    'Fields should not be provided when instantiating Structure'
                    ' subclasses that define FIELDS')
            else:
                self.fields = self.FIELDS

    def content(self):
        content = self.image[self.offset:self.offset+self.length()]
        return content

    def as_dict(self):
        struct_dict = self.fields.as_dict(self.content(), '')
        return struct_dict

    #def sub_struct(self, descriptor):
    #    subfields = descriptor.split('.')
    #    field = self.fields
    #    for subfield_id in subfields:
    #        field = field.get_subfield(subfield_id)

    def __getitem__(self, key):
        constructor = self.fields[key].constructor
        subfield = constructor(self.image, self.offset)
        return subfield

    def sub_struct(self, descriptor):
        subfields = descriptor.split('.')
        struct = self
        for subfield_id in subfields:
            struct = struct[int(subfield_id)]
        return struct

    def length(self):
        return self.fields.length


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
        Field('stuff', 1024*4, hexencode, None)
    ])


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
