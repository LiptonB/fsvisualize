import mmap

class Image(object):
    def __init__(self, filename):
        self.filename = filename
        self.file = open(self.filename, 'rb')
        self.map = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)

    def close(self):
        self.map.close()
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __getitem__(self, key):
        return self.map[key]
