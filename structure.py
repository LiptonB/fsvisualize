class MBR(object):
    fields = (
        ('code', 446, None),
        ('partition', 16, None),
        ('partition', 16, None),
        ('partition', 16, None),
        ('partition', 16, None),
        ('signature', 2, None),
    )

    def __init__(self, image, offset):
        self.image = image
        self.offset = offset

    def as_dict(self):
        return {'name': 'foo', 'contents': 'blah'}
