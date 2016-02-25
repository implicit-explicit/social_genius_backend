from flask import Flask, request
from flask_restful import Resource, Api

import config

import json
import requests

app = Flask(__name__, static_folder=config.STATIC_FILES)
api = Api(app)
logger = app.logger


class StaticAssets(Resource):
    @classmethod
    def get(self, path):
        return app.send_static_file(path)


class Index(Resource):
    @classmethod
    def get(self):
        return app.send_static_file('index.html')


class Meetup(Resource):

    def get_members(self, api_key, group_urlname, page_size=200):

        logger.info('Retrieving users for {}'.format(group_urlname))

        results = None
        users = []

        request_string = '{}{}?key={}&group_urlname={}&page={}'.format(config.API_URL, config.QUERY, api_key,
                                                                       group_urlname, page_size)

        while True:

            # print(request_string)

            r = requests.get(request_string)
            try:
                results = json.loads(r.content.decode('utf-8'))
            except Exception as e:
                print(e)


            num = len(results['results'])
            users += results['results']

            try:
                if len(results['meta']['next']) <= 0:
                    break
            except e:
                print(e)
                break

            request_string = results['meta']['next']

        logger.info('Retrieved {} users'.format(len(users)))

        return users

    def get(self, group_name):
        return self.get_members(config.API_KEY, group_name)

# Meetup
api.add_resource(Meetup, '/meetup/<string:group_name>')

# Static assets
api.add_resource(StaticAssets, '/<path:path>')
api.add_resource(Index, '/')

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
