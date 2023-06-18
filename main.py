from artist import *
from flask import Flask, jsonify
from flask_cors import CORS

app: Flask = Flask(__name__)
CORS(app)

@app.post("/")
def get_map():
    default_args = {
        'location': "Западный округ",
        'cars': 10,
        'duration': 10,
        'frames_per_second': 30,
        'interactive': False,
        'light_prescaling': 15,
        'mp4': False,
        'serialize': False
    }
    main(**default_args)
    return jsonify({"is_files_to_dir": True})


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6000)