from flask import Flask
from flask import render_template
app = Flask(__name__)

app.config.from_object('fsvisualize.default_settings')

from . import image
from . import structure

@app.route('/')
def hello_world():
    return 'Hello, world'

@app.route('/visualize/', defaults={'path': ''})
@app.route('/visualize/<path:path>/')
def visualize(path):
    components = [part for part in path.split('/') if part]
    with image.Image(app.config['IMAGE_PATH']) as im:
        struct = structure.MBR(im, 0)
        structs = [struct.as_dict()]
        for component in components:
            struct = struct.sub_struct(component)
            structs.append(struct.as_dict())
        return render_template('visualize.html', structs=structs)
