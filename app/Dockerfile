# our base image
FROM python:3.11

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y \
    build-essential

# Install Python modules needed by the Python app
COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r /usr/src/app/requirements.txt

# Copy files required for the app to run
COPY main.py /usr/src/app/
COPY requirements.txt /usr/src/app/
COPY score_image.py /usr/src/app/
COPY tfmodel.py /usr/src/app/
COPY app.yaml /usr/src/app/
COPY key.json /usr/src/app/
COPY templates/* /usr/src/app/templates/
COPY static/* /usr/src/app/static/
COPY static/tflite/* /usr/src/app/static/tflite/

# Tell the port number the container should expose
EXPOSE 8080

# Run the application   
CMD ["python", "/usr/src/app/main.py"]
