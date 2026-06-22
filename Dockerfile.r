FROM rocker/geospatial:latest
RUN install2.r --error --skipinstalled osmdata RPostgres
