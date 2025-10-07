FROM python:3.10

WORKDIR /python-docker

COPY . /python-docker
RUN pip3 install --trusted-host pypi.python.org -r requirements.txt


CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]