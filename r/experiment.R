library(DBI)
library(RPostgres)
library(sf)

con <- dbConnect(
  Postgres(),
  host     = Sys.getenv("PGHOST", "host.docker.internal"),
  port     = as.integer(Sys.getenv("PGPORT", "54321")),
  dbname   = Sys.getenv("PGDATABASE"),
  user     = Sys.getenv("PGUSER"),
  password = Sys.getenv("PGPASSWORD")
)
on.exit(dbDisconnect(con))

cat("Connected. PostGIS:", dbGetQuery(con, "select postgis_version()")[[1]], "\n")

# General query -> plain data.frame. Use for aggregates, counts,
# attribute-only selects, or anything with no geometry column.
# Supports parameters via the `params` list to avoid string-pasting values.
run_query <- function(con, sql, params = NULL) {
  if (is.null(params)) dbGetQuery(con, sql)
  else                 dbGetQuery(con, sql, params = params)
}

# Spatial query -> sf data.frame. Use only when the select returns a
# geometry column you want parsed into real geometries.
run_query_sf <- function(con, sql, params = NULL, geom = "geom") {
  st_read(con, query = sql, geometry_column = geom, quiet = TRUE)
}


run_query(con, "
  select highway, count(*) as n
  from raw_data.evanston_osm_bike_network_edges
  where valid_to is null
  group by highway
  order by n desc
")

run_query(con, "
  select osm_id, name, surface
  from raw_data.evanston_osm_bike_network_edges
  where valid_to is null and highway = $1
  limit 20
", params = list("cycleway"))

run_query_sf(con, "
  select *
  from raw_data.evanston_osm_bike_network_edges
  where valid_to is null
  limit 5
")

edges <- run_query_sf(con, "
  select osm_id, highway, name, geom
  from raw_data.evanston_osm_bike_network_edges
  where valid_to is null
")
