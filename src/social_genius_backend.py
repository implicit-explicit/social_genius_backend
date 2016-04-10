import eventlet
eventlet.monkey_patch()

from flask import Flask, request
import requests
import json
import logging
from collections import defaultdict
import configparser
import click
from urllib.request import urlopen

app = Flask(__name__, static_folder='static')
config = None


@app.before_first_request
def setup_logging():
    if not app.debug:
        app.logger.addHandler(logging.StreamHandler())
        app.logger.setLevel(logging.DEBUG)


def fetch_api_endpoint(meetup_group):
    meetup_key = config['meetup']['api_key']
    request_string = 'https://api.meetup.com/{}/events?&key={}&page=200'.format(meetup_group, meetup_key)
    app.logger.info('Fetching events for {}'.format(meetup_group))
    #r = requests.get(request_string)
    body = urlopen(request_string).read()
    try:
        # results = json.loads(r.content.decode('utf-8'))
        results = json.loads(body.decode('utf-8'))
    except Exception as e:
        app.logger.info(e)
        return
    meetup_events = []
    app.logger.info('Found {} results for {}'.format(len(results), meetup_group))
    if len(results) > 0:
        for key in results:
            try:
                meetup_events.append(key['time'])
            except KeyError as e:
                app.logger.info("Time error for group {}".format(meetup_group))
    return meetup_group, meetup_events


@app.route("/city")
def city():

    meetup_group = request.args['meetup_group']
    meetup_key = config['meetup']['api_key']

    request_string = 'https://api.meetup.com/2/groups?&key={}&group_urlname={}&page=20'.format(
        meetup_key, meetup_group)

    results = None
    response = {}

    app.logger.info("Getting city for meetup group {}".format(meetup_group))
    r = requests.get(request_string)
    try:
        results = json.loads(r.content.decode('utf-8'))
    except Exception as e:
        app.logger.info(e)

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

    pool = eventlet.GreenPool(1)

    for group, events in pool.imap(fetch_api_endpoint, meetup_groups):
        meetup_events[group] = events

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
