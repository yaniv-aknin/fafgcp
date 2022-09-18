# fafgcp

Some glue code to deploy [fafdata](https://github.com/yaniv-aknin/fafdata) as a GCP Cloud Function.

## Deployment
The cloud function can be deployed by running:
```
REGION=europe-west1
FAFGCP_BUCKET=fafalytics
SERVICE_ACCOUNT=data-engineering@fafalytics.iam.gserviceaccount.com
gcloud functions deploy faf-scraper \
    --gen2 \
    --runtime=python310 \
    --timeout=120 \   
    --region=$REGION \
    --source=. \
    --entry-point=scrape \
    --trigger-http \
    --update-env-vars=FAFGCP_BUCKET=$FAFGCP_BUCKET \
    --service-account=$SERVICE_ACCOUNT
```

It assumes this assumes you have a service account setup with access to the named bucket.
