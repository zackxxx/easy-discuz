FROM vaultvulp/pipenv-alpine

COPY ./Pipfile /var/www/

RUN pipenv install

CMD [pipenv run crawler ]