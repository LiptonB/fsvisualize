import collections

class Field(object):
    def __init__(self, description, length, formatter, constructor):
        self.description = description
        self.length = length
        self.formatter = formatter
        self.constructor = constructor

    def as_dict(self, content_bytes):
        field_dict = {
            'description': self.description,
            'link?': self.constructor is not None,
            'contents': self.formatter(content_bytes)
        }

        return field_dict

class FieldGroup(object):
    def __init__(self, description, fields):
        self.description = description
        self.fields = fields
        self.length = sum(field.length for field in fields)
        
    def as_dict(self, content_bytes):
        subfields = []
        for i, field in enumerate(self.fields):
            contents = self.field_contents(content_bytes, i)
            subfields.append(field.as_dict(contents))

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
        struct_dict = self.FIELDS.as_dict(content)
        return struct_dict

    def __getitem__(self):
        pass

    def length(self):
        return self.FIELDS.length


def hexencode(s):
    enc = s.encode('hex')
    if len(enc) > 20:
        return enc[:6] + '...' + enc[-6:]
    else:
        return enc

class MBR(Structure):
    _PARTITION = FieldGroup('partition', [
        Field('status', 1, hexencode, None),
        Field('start_chs', 3, hexencode, True),
        Field('type', 1, hexencode, None),
        Field('end_chs', 3, hexencode, None),
        Field('start_lba', 4, hexencode, None),
        Field('length', 4, hexencode, None),
    ])
    FIELDS = FieldGroup('Master Boot Record', [
        Field('code', 446, hexencode, None),
        _PARTITION,
        _PARTITION,
        _PARTITION,
        _PARTITION,
        Field('signature', 2, hexencode, None),
    ])

class Partition(Structure):
    FIELDS = FieldGroup('Partition Table', [
        Field('status', 1, hexencode, None),
        Field('start_chs', 3, hexencode, None),
        Field('type', 1, hexencode, None),
        Field('end_chs', 3, hexencode, None),
        Field('start_lba', 4, hexencode, None),
        Field('length', 4, hexencode, None),
    ])
