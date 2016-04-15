import time
from flask import Flask, request
import requests
import json
import logging
from collections import defaultdict
import configparser
import click
from py2neo import Graph, Node, Relationship

app = Flask(__name__, static_folder='static')
config = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.before_first_request
def setup_logging():
    if not app.debug:
        global logger
        logger = app.logger
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)


def get_group_events(meetup_group):
    meetup_key = config['meetup']['api_key']
    request_string = 'https://api.meetup.com/{}/events?&key={}&page=200'.format(meetup_group, meetup_key)
    logger.info('Fetching events for {}'.format(meetup_group))
    r = requests.get(request_string)
    try:
        results = json.loads(r.content.decode('utf-8'))
    except Exception as e:
        app.logger.info(e)
        return
    meetup_events = []
    logger.info('Found {} results for {}'.format(len(results), meetup_group))
    if len(results) > 0:
        for key in results:
            try:
                meetup_events.append(key)
            except KeyError as e:
                app.logger.info("Time error for group {}".format(meetup_group))
    return meetup_group, meetup_events


def get_group_location(meetup_group):

    meetup_key = config['meetup']['api_key']

    request_string = 'https://api.meetup.com/2/groups?&key={}&group_urlname={}&page=20'.format(
        meetup_key, meetup_group)

    results = None
    location = {}

    logger.info("Getting city for meetup group {}".format(meetup_group))
    r = requests.get(request_string)
    try:
        results = json.loads(r.content.decode('utf-8'))
    except Exception as e:
        app.logger.info(e)

    location['city'] = results['results'][0]['city']
    location['country'] = results['results'][0]['country']

    if location['country'] == 'US':
        location['state'] = results['results'][0]['state']
    else:
        location['state'] = None

    logger.info(
        'Found. City: {} State: {} Country: {}'.format(location['city'], location['state'], location['country']))

    return location


def get_groups_in_location(location, category=34):
    meetup_key = config['meetup']['api_key']
    logger.info('Finding tech meetup groups in {}...'.format(location['city']))
    request_string = 'https://api.meetup.com/2/groups?&key={}&category_id={}&country={}&city={}&state={}&page=200'.format(
        meetup_key, category,location['country'], location['city'], location['state'])

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

    logger.info('Found {} tech meetup groups near {}'.format(len(meetup_groups), location['city']))
    return meetup_groups


@app.route("/city")
def city():
    location = request.args['meetup_group']

    graph = Graph(host=config['neo4j']['host'], user=config['neo4j']['user'],
                  password=config['neo4j']['password'])

    logger.info('Finding upcoming meetup events in {}'.format(location))

    groups_data = defaultdict()

    groups = graph.find('Group')
    for group in groups:
        groups_data[group.properties['name']] = []
        for rel in graph.match(start_node=group, rel_type="HAS EVENT"):
            groups_data[group.properties['name']].append(rel.end_node().properties['time'])

    return json.dumps(groups_data)


@app.route('/<path:path>')
def send_static(path):
    return app.send_static_file(path)


@app.route('/')
def root():
    return app.send_static_file('index.html')


@click.group()
@click.option('-c', default='config', help='Config file. Defaults to "config"')
def cli(c):
    global config
    config = configparser.ConfigParser()
    logger.info('Reading configuration file {}'.format(c))
    config.read(c)


@click.command()
def webserver():
    app.run(host='0.0.0.0', debug=False)


@click.command(name='sync', help='Saves data from the Meetup API to the local database')
@click.argument('group')
def sync_meetup_data(group):
    graph = Graph(host=config['neo4j']['host'], user=config['neo4j']['user'],
                  password=config['neo4j']['password'])

    location = get_group_location(group)

    tx = graph.begin()
    location_node = Node('Location', city=location['city'], state=location['state'], country=location['country'])
    tx.create(location_node)
    tx.commit()

    meetup_groups = get_groups_in_location(location, category=34)

    logger.info('Finding upcoming meetup events at {} meetup groups'.format(len(meetup_groups)))

    for group in meetup_groups:
        time.sleep(2)
        group, events = get_group_events(group)
        tx = graph.begin()
        group_node = Node("Group", name=group)
        tx.create(group_node)
        location_relation = Relationship(location_node, 'HAS MEETUP', group_node)
        tx.create(location_relation)
        for event in events:
            event_node = Node('Event', name=event['name'], time=event['time'])
            tx.create(event_node)
            rel = Relationship(group_node, "HAS EVENT", event_node)
            tx.create(rel)
        tx.commit()
        logger.info('Transaction ({}) status: {}'.format(group, str(tx.finished())))


if __name__ == "__main__":
    cli.add_command(webserver)
    cli.add_command(sync_meetup_data)
    cli()
