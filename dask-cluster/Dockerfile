FROM ghcr.io/dask/dask:2023.1.1-py3.10
RUN apt update && apt install -y git zstd
RUN git clone https://github.com/yaniv-aknin/fafdata.git
RUN pip install shapely orjson
RUN pip install /fafdata
