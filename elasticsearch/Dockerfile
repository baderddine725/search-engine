FROM docker.elastic.co/elasticsearch/elasticsearch:7.17.9

# Plugin Elastiknn (la version doit correspondre exactement à celle d'Elasticsearch)
RUN elasticsearch-plugin install --batch \
    https://github.com/alexklibisz/elastiknn/releases/download/7.17.9.0/elastiknn-7.17.9.0.zip
