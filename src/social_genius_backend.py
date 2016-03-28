from flask import Flask, request
import requests
import json
from collections import defaultdict
from neo4jrestclient.client import GraphDatabase
import configparser

app = Flask(__name__)
meetup_key = None

@app.route("/city")
def city():
    print("Getting city from meetup group")
    meetup_group = request.args['meetup_group']

    request_string = 'https://api.meetup.com/2/groups?&key={}&group_urlname={}&page=20'.format(
        meetup_key, meetup_group)

    results = None
    response = {}

    r = requests.get(request_string)
    try:
        results = json.loads(r.content.decode('utf-8'))
    except Exception as e:
        print(e)

    response['city'] = results['results'][0]['city']
    response['country'] = results['results'][0]['country']

    if response['country'] == 'US':
        response['state'] = results['results'][0]['state']
    else:
        response['state'] = None

    print('Found. City: {} State: {} Country: {}'.format(response['city'], response['state'], response['country']))

    print('Finding tech meetup groups in {}...'.format(response['city']))
    request_string = 'https://api.meetup.com/2/groups?&key={}&category_id=34&country={}&city={}&state={}&page=200'.format(meetup_key, response['country'], response['city'], response['state'])

    results = None
    meetup_groups = []

    while True:
        r = requests.get(request_string)

        try:
            results = json.loads(r.content.decode('utf-8'))
        except Exception as e:
            print(e)

        for key in results['results']:
            meetup_groups.append(key['urlname'])

        try:
            if len(results['meta']['next']) <= 0:
                break
        except Exception as e:
            print(e)
            break

        request_string = results['meta']['next']

    print('Found {} tech meetup groups near {}'.format(len(meetup_groups), response['city']))

    print('Finding upcoming meetup events at {} meetup groups'.format(len(meetup_groups)))

    meetup_events = defaultdict(list)

    for meetup_group in meetup_groups:
        request_string = 'https://api.meetup.com/{}/events?&key={}&page=200'.format(
            meetup_group, meetup_key)
        r = requests.get(request_string)
        try:
            results = json.loads(r.content.decode('utf-8'))
        except Exception as e:
            print(e)

        if len(results) > 0:
            for key in results:
                try:
                    meetup_events[meetup_group].append(key['time'])
                except KeyError as e:
                    print("Time error for group {}".format(meetup_group))

    print('Found {} upcoming meetup events in {}'.format(len(meetup_events), response['city']))

    return json.dumps(meetup_events)

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('keys')
    meetup_key = config['MEETUP KEY']['meetup_key']
    print(meetup_key)
    app.run(host='0.0.0.0', debug=True)
