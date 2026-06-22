import os

from loci.db.core import DatabaseCredentials, PostgresEngine
from loci.collectors.osm.collector import OSMCollector
from loci.collectors.osm.spec import OSMDatasetSpec
from loci.collectors.osm.query import OverpassAPIQuery
from loci.geo import BBox
from loci.sources import dataset_specs


def get_engine() -> PostgresEngine:
    """Build a PostgresEngine from PG* environment variables."""
    creds = DatabaseCredentials(
        host=os.environ["PGHOST"],
        port=int(os.environ.get("PGPORT", "5432")),
        database=os.environ["PGDATABASE"],
        username=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )
    return PostgresEngine(creds)


def ensure_schema(engine: PostgresEngine, schema: str) -> None:
    """Create the target schema if it isn't already there."""
    engine.execute(f"create schema if not exists {schema}")


def ensure_table(engine: PostgresEngine, collector: OSMCollector, spec: OSMDatasetSpec) -> None:
    """
    Create the target table (and its constraint/indexes) if it doesn't exist.

    We gate on existence rather than relying on `create ... if not exists`
    because generate_ddl() also emits an `alter table ... add constraint`,
    which is not idempotent and would error on a second run.
    """
    df = engine.query(
        """
        select 1 from information_schema.tables
        where table_schema = %(schema)s and table_name = %(table)s
        limit 1
        """,
        {"schema": spec.target_schema, "table": spec.target_table},
    )
    if not df.empty:
        engine.logger.info("Table %s.%s exists; skipping DDL", spec.target_schema, spec.target_table)
        return

    engine.logger.info("Creating table %s.%s", spec.target_schema, spec.target_table)
    engine.execute(collector.generate_ddl(spec))

def setup_and_collect(specs: list[OSMDatasetSpec], force: bool = True) -> None:
    """Ensure schema + tables exist for each spec, then collect."""
    engine = get_engine()
    collector = OSMCollector(engine=engine)
    try:
        for spec in specs:
            ensure_schema(engine, spec.target_schema)
            ensure_table(engine, collector, spec)
            summary = collector.collect(spec, force=force)
            engine.logger.info("Collected %s: %s", spec.name, summary)
    finally:
        engine.close()

EVANSTON_BBOX = BBox(42.02, -87.74, 42.08, -87.66)
EVANSTON_EDGES_SPEC = dataset_specs.generate_osm_bike_network_edges_spec(
    city="evanston", bbox=EVANSTON_BBOX
)
EVANSTON_NODES_SPEC = dataset_specs.generate_osm_bike_network_nodes_spec(
    city="evanston", bbox=EVANSTON_BBOX
)

if __name__ == "__main__":
    setup_and_collect(specs=[EVANSTON_EDGES_SPEC, EVANSTON_NODES_SPEC])
