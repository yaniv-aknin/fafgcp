import flask
import os
import json
import pytest
from unittest import mock

import responses
from google.cloud import storage

import main

@pytest.fixture(scope="module")
def app():
    return flask.Flask(__name__)

@mock.patch.dict(os.environ, {"FAFGCP_BUCKET": "testbucket"})
@responses.activate
def test_scrape(mocker, app):
    with open('games.json') as handle:
        data = json.load(handle)
    url = ('https://api.faforever.com/data/game?page%5Bsize%5D=10&page%5Bnumber%5D=1&page%5Btotals%5D='
           '&filter=endTime%3Dge%3D1970-01-01T00%3A00%3A00Z%3BendTime%3Dle%3D1970-01-02T00%3A00%3A00Z'
           '&include=playerStats%2CplayerStats.ratingChanges&sort=endTime')
    responses.add(method='GET', url=url, json=data)
    mocker.patch('google.cloud.storage.Client')
    mocker.patch('google.cloud.storage.fileio.BlobWriter')
    with app.test_request_context(json={'end_date': '1970-01-02', 'start_date': '1970-01-01', 'max_page': 1}):
        res = main.scrape(flask.request)
        assert res.data == b'10 rows written to gs://testbucket/game/dt=1970-01-02/data.ndjson\n'
    storage.Client.assert_called_once()
    assert storage.fileio.BlobWriter.return_value.write.call_count == 10
    last_row = json.loads(storage.fileio.BlobWriter.return_value.write.call_args[0][0])
    assert last_row['id'] == '18029705'
