import os
import json
import functools

import functions_framework
from google.cloud import storage
import flask
from marshmallow import Schema, fields
import marshmallow

from fafdata.fetch import construct_url, yield_pages
from fafdata.transform import process_page
from fafdata.utils import parse_date

class Arguments(Schema):
    page_size = fields.Integer(load_default=10)
    inter_page_sleep = fields.Integer(load_default=1)
    max_page = fields.Integer(load_default=3)
    start_date = fields.Date(load_default=lambda: parse_date('-2'))
    end_date = fields.Date(load_default=lambda: parse_date('-1'))

def log(msg, **kwargs):
    kwargs['msg'] = msg
    print(json.dumps(kwargs, default=repr))

def load_request_args(func):
    @functools.wraps(func)
    def wrapper(request):
        try:
            return func(Arguments().load(request.json))
        except marshmallow.exceptions.ValidationError as error:
            return flask.jsonify(error.messages), 400
    return wrapper

@functions_framework.http
@load_request_args
def scrape(args):
    ENTITY_TO_SCRAPE = 'game'
    INCLUDED_RELATIONS = ('playerStats', 'playerStats.ratingChanges')
    ENTITY_DATE_FIELD = 'endTime'
    bucket_name = os.environ['FAFGCP_BUCKET']
    blob_name = f'{ENTITY_TO_SCRAPE}/dt={args["end_date"].strftime("%Y-%m-%d")}/data.ndjson'
    log('processing request', bucket_name=bucket_name, blob_name=blob_name, **args)

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(blob_name)
    writer = storage.fileio.BlobWriter(blob)
    url_constructor = functools.partial(construct_url, ENTITY_TO_SCRAPE, INCLUDED_RELATIONS, ENTITY_DATE_FIELD,
                                        args['page_size'], args['start_date'], args['end_date'])
    row_count = 0
    for page in yield_pages(url_constructor, max_page=args['max_page'], inter_page_sleep=args['inter_page_sleep']):
        for row in process_page(page, INCLUDED_RELATIONS):
            writer.write((json.dumps(row) + '\n').encode())
            row_count += 1
    writer.close()
    log('request complete', row_count=row_count)
    return flask.Response(f'{row_count} rows written to gs://{bucket_name}/{blob_name}\n', mimetype='text/plain')
