# fafgcp

Some glue code to use my FAF analysis packages on GCP (i.e., [`fafdata`](https://github.com/yaniv-aknin/fafdata) and soon `fafdask`).

## fafdata scraper

Using the code in the `scraper/` directory, you can deploy a cloud function can be deployed by running:
```bash
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

## fafdask cluster

Using the files in `dask-cluster/`, you can create a [dask](http://dask.org) cluster running on a Managed Instance Group (MIG).

* Using the following environment variables:

    ```bash
    REGION=europe-west1
    ZONE=europe-west1-b
    PACKAGE=fafalytics/fafalytics/fafdask:latest
    REGISTRY=$REGION-docker.pkg.dev/$PACKAGE
    SERVICE_ACCOUNT=data-engineering@fafalytics.iam.gserviceaccount.com
    PROJECT=fafalytics
    WORKER_MACHINE=e2-medium
    MIG_SIZE=2
    ```

* Build a Docker image using the `Dockerfile`, possibly on Cloud Build by running:

    ```bash
    gcloud builds submit --region=$REGION --tag $REGISTRY
    ```

    You will then need to ensure `$SERVICE_ACCOUNT` can access the image.

* Create a MIG template to run dask workers using:

    ```bash
    gcloud compute instance-templates create-with-container \
        fafdask-w \
        --project=$PROJECT \
        --machine-type=$WORKER_MACHINE \
        --network-interface=subnet=default,no-address \
        --maintenance-policy=MIGRATE \
        --service-account=$SERVICE_ACCOUNT \
        --scopes=https://www.googleapis.com/auth/cloud-platform \
        --image=projects/cos-cloud/global/images/cos-stable-101-17162-40-56 \
        --boot-disk-size=10GB \
        --boot-disk-type=pd-balanced \
        --container-image=$REGISTRY \
        --container-restart-policy=always \
        --container-command=dask \
        --container-arg=worker \
        --container-arg=tcp://fafdask-s.c.$PROJECT.internal:8786 \
        --container-arg=--nworkers \
        --container-arg=auto \
        --container-mount-disk=mode=ro,mount-path=/DATA,name=faf-replays-1v1,partition=1 \
        --disk=boot=no,device-name=faf-replays-1v1,mode=ro,name=faf-replays-1v1
    ```

* Instantiate a worker MIG using:

    ```bash
    gcloud compute instance-groups managed create fafdask-ws \
        --zone=$ZONE \
        --template=fafdask-w \
        --size $MIG_SIZE
    ```

* Instantiate a scheduler instance using:

    ```bash
    gcloud compute instances create-with-container \
        fafdask-s \
        --project=$PROJECT \
        --zone=$ZONE \
        --machine-type=e2-medium \
        --network-interface=network-tier=PREMIUM,subnet=default \
        --maintenance-policy=MIGRATE \
        --provisioning-model=STANDARD \
        --service-account=$SERVICE_ACCOUNT \
        --scopes=https://www.googleapis.com/auth/cloud-platform \
        --image=projects/cos-cloud/global/images/cos-stable-101-17162-40-56 \
        --boot-disk-size=10GB \
        --boot-disk-type=pd-balanced \
        --container-image=$REGISTRY \
        --container-restart-policy=always \
        --container-command=dask \
        --container-arg=scheduler
    ```

* Finally, you can develop locally with the included `docker-compose.yml` file, after teaching your local `docker` to [authenticate](https://cloud.google.com/artifact-registry/docs/docker/authentication) with Artifact Registry.
