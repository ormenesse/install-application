# ubuntu
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND noninteractive
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY . /app

RUN apt-get update -y && apt-get -y install cron
RUN apt -y install apt-utils
RUN apt-get install -y python3 python3-pip python3-virtualenv nginx gunicorn3 supervisor

#python libraries
RUN pip3 install -r /app/app/requirements.txt

# Copy hello-cron file to the cron.d directory
COPY cron /etc/cron.d/cron
RUN chmod 0644 /etc/cron.d/cron
RUN crontab /etc/cron.d/cron

# Setup nginx
RUN rm /etc/nginx/sites-enabled/default
COPY nginx_sock.conf /etc/nginx/sites-available/
RUN ln -s /etc/nginx/sites-available/nginx_sock.conf /etc/nginx/sites-enabled/nginx_sock.conf
RUN echo "daemon off;" >> /etc/nginx/nginx.conf

# Setup supervisord
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY gunicorn.conf /etc/supervisor/conf.d/gunicorn.conf

RUN chmod 777 -R /app/app
EXPOSE 80
CMD cron
CMD ["cd /app/app/install_csv && python3 updateCSV.py"]
CMD ["/usr/bin/supervisord"]