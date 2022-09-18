import os
import json
import functools

import functions_framework
from google.cloud import storage
import flask

from fafdata.fetch import construct_url, yield_pages
from fafdata.transform import process_page
from fafdata.utils import parse_date

DEFAULTS = {
    'page_size': (int, 10),
    'inter_page_sleep': (int, 1),
    'max_page': (int, 3),
    'start_date': (parse_date, '-2'),
    'end_date': (parse_date, '-1'),
}

def parse_request_args(request, specification):
    args = {}
    if set(request.args) - set(specification):
        flask.abort(400) 
    for parameter, (cast, default) in specification.items():
        args[parameter] = cast(request.args.get(parameter, default))
    return args


def log(msg, **kwargs):
    kwargs['msg'] = msg
    print(json.dumps(kwargs, default=repr))

@functions_framework.http
def scrape(request):
    ENTITY_TO_SCRAPE = 'game'
    INCLUDED_RELATIONS = ('playerStats', 'playerStats.ratingChanges')
    ENTITY_DATE_FIELD = 'endTime'
    bucket_name = os.environ['FAFGCP_BUCKET']
    args = parse_request_args(request, DEFAULTS)
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
    return flask.Response(f'{row_count} rows written to gs://{bucket_name}/{blob_name}', mimetype='text/plain')
