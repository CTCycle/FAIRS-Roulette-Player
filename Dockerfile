FROM python:3.10.12

WORKDIR /app

COPY ./ /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "FAIRS.py"]

# First create an image from the working directory (same as dockerfile and requirements)
# docker build -t hubname/appname .
# Then create a container and mount it using a volume 
# docker run -it --name containername --gpus all -v volumename:/app appname /bin/bash
# You can now run the python script using python FAIRS.py in the container and access
# the files uisng the volume (best to use Docker Desktop)