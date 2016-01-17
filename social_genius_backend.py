#! /Library/Frameworks/Python.framework/Versions/3.3/bin/python3.3

from flask import Flask
import json

app = Flask(__name__)

@app.route("/groups")
def get_groups():
    return(json.dumps(['groups', {'name': ('docker_randstad', 1565)}]))

if __name__ == '__main__':
    app.run(debug=True)
