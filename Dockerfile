FROM python:3

MAINTAINER "eric.mely@gmail.com"

WORKDIR /usr/src/app

RUN pip install Flask-QRcode
RUN pip install werkzeug 
RUN pip install fpdf
RUN pip install PyPDF2
RUN pip install requests
RUN apt-get update
RUN apt-get install -y pdftk

COPY /app/. .

EXPOSE 3000

CMD [ "python", "./qrapiv2.py" ]
