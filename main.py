from artist import *
from flask import Flask
from flask_cors import CORS

app: Flask = Flask(__name__)
CORS(app)

@app.post("/")
def get_map():
    default_args = {
        'location': "Западный округ",
        'cars': 10,
        'duration': 10,
        'frames_per_second': 60,
        'interactive': False,
        'light_prescaling': 15,
        'mp4': False,
        'serialize': False
    }
    main(**default_args)
    return True


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)