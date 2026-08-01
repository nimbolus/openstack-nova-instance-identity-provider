FROM python:3.12-alpine

RUN apk add --no-cache gcc libc-dev libffi-dev linux-headers

COPY requirements.txt /vendordata/requirements.txt
RUN pip3 install -r /vendordata/requirements.txt

COPY *.py /app/

WORKDIR /app

ENV PYTHONUNBUFFERED="1"

CMD ["python3", "main.py"]
