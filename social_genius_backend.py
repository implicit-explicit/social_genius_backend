#! /Library/Frameworks/Python.framework/Versions/3.3/bin/python3.3

from flask import Flask, request

import json
from neo4jrestclient.client import GraphDatabase

app = Flask(__name__)
gdb = GraphDatabase("http://localhost:7474/db/data/")

@app.route('/groups/<group_name>', methods=['GET'])
def get_groups(group_name=None):
    q = """MATCH (group:Group) WHERE group.name = '%s' RETURN group""" % (group_name)
    results = gdb.query(q=q)
    if len(results) == 0:
        return 'Group name not found!\n', 404
    else:
        return(str(results[0]) + '\n'), 200

if __name__ == '__main__':
    app.run(debug=True)
