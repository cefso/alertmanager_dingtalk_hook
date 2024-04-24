FROM python:3.10

WORKDIR /src

# add app
COPY app.py /src
COPY requirements.txt /src

# install requirements
RUN pip install -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

EXPOSE 5000

# run server
CMD python app.py
