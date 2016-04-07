from flask import Flask, request, send_from_directory
import requests
import json
import logging
import sys
from collections import defaultdict
import configparser
import click

app = Flask(__name__, static_folder='static')
app.logger.setLevel(logging.DEBUG)
config = None


@app.route("/city")
def city():
    app.logger.info("Getting city from meetup group")
    meetup_group = request.args['meetup_group']
    meetup_key = config['meetup']['api_key']

    request_string = 'https://api.meetup.com/2/groups?&key={}&group_urlname={}&page=20'.format(
        meetup_key, meetup_group)

    results = None
    response = {}

    r = requests.get(request_string)
    try:
        results = json.loads(r.content.decode('utf-8'))
    except Exception as e:
        app.logger.info(e)

    app.logger.info(results)

    response['city'] = results['results'][0]['city']
    response['country'] = results['results'][0]['country']

    if response['country'] == 'US':
        response['state'] = results['results'][0]['state']
    else:
        response['state'] = None

    app.logger.info('Found. City: {} State: {} Country: {}'.format(response['city'], response['state'], response['country']))

    app.logger.info('Finding tech meetup groups in {}...'.format(response['city']))
    request_string = 'https://api.meetup.com/2/groups?&key={}&category_id=34&country={}&city={}&state={}&page=200'.format(meetup_key, response['country'], response['city'], response['state'])

    results = None
    meetup_groups = []

    while True:
        r = requests.get(request_string)

        try:
            results = json.loads(r.content.decode('utf-8'))
        except Exception as e:
            app.logger.info(e)

        for key in results['results']:
            meetup_groups.append(key['urlname'])

        try:
            if len(results['meta']['next']) <= 0:
                break
        except Exception as e:
            app.logger.info(e)
            break

        request_string = results['meta']['next']

    app.logger.info('Found {} tech meetup groups near {}'.format(len(meetup_groups), response['city']))

    app.logger.info('Finding upcoming meetup events at {} meetup groups'.format(len(meetup_groups)))

    meetup_events = defaultdict(list)

    for meetup_group in meetup_groups:
        request_string = 'https://api.meetup.com/{}/events?&key={}&page=200'.format(
            meetup_group, meetup_key)
        r = requests.get(request_string)
        try:
            results = json.loads(r.content.decode('utf-8'))
        except Exception as e:
            app.logger.info(e)

        if len(results) > 0:
            for key in results:
                try:
                    meetup_events[meetup_group].append(key['time'])
                except KeyError as e:
                    app.logger.info("Time error for group {}".format(meetup_group))
        break

    app.logger.info('Found {} upcoming meetup events in {}'.format(len(meetup_events), response['city']))

    return json.dumps(meetup_events)


@app.route('/<path:path>')
def send_static(path):
    return app.send_static_file(path)


@app.route('/')
def root():
    return app.send_static_file('index.html')


@click.command()
@click.option('-c', default='config', help='Config file. Defaults to "config"')
def main(c):
    global config
    config = configparser.ConfigParser()
    app.logger.warning('Reading configuration file {}'.format(c))
    config.read(c)
    app.run(host='0.0.0.0', debug=False)

if __name__ == "__main__":
    main()
