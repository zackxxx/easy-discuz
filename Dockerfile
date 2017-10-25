FROM vaultvulp/pipenv-alpine

COPY ./Pipfile /var/www/

RUN pipenv install

