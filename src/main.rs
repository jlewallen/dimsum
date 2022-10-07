use std::collections::HashMap;

use anyhow::{Error, Result};

use tracing::{debug, info};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter, Registry};
use tracing_tree::HierarchicalLayer;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use rusqlite::Connection;

#[derive(Debug, Serialize, Deserialize)]
struct Version {
    #[serde(alias = "py/object")]
    py_object: String,
    i: u32,
}

#[derive(Debug, Serialize, Deserialize)]
struct EntityRef {
    #[serde(alias = "py/object")]
    py_object: String,
    #[serde(alias = "py/ref")]
    py_ref: String,
    key: String,
    klass: String,
    name: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct Identity {
    #[serde(alias = "py/object")]
    py_object: String,
    private: String,
    public: String,
    signature: Option<String>, // TODO Why does this happen?
}

#[derive(Debug, Serialize, Deserialize)]
struct EntityClass {
    #[serde(alias = "py/type")]
    py_type: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct AclRule {
    #[serde(alias = "py/object")]
    py_object: String,
    keys: Vec<String>,
    perm: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct Acls {
    #[serde(alias = "py/object")]
    py_object: String,
    rules: Vec<AclRule>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Property {
    value: serde_json::Value,
}

#[derive(Serialize, Deserialize)]
struct Props {
    map: HashMap<String, Property>,
}

#[derive(Serialize, Deserialize)]
struct Entity {
    #[serde(alias = "py/object")]
    py_object: String,
    key: String,
    version: Version,
    parent: Option<EntityRef>,
    creator: Option<EntityRef>,
    identity: Identity,
    #[serde(alias = "klass")]
    class: EntityClass,
    acls: Acls,
    props: Props,
    scopes: HashMap<String, serde_json::Value>,
}

#[derive(Debug)]
struct PersistedEntity {
    key: String,
    gid: u32,
    version: u32,
    serialized: String,
}

impl PersistedEntity {
    fn to_entity(&self) -> Result<Entity, Error> {
        let entity: Entity = serde_json::from_str(&self.serialized)?;

        info!(%entity.key, "parsed");

        return Ok(entity);
    }
}

fn main() -> Result<()> {
    /*
    https://fasterthanli.me/articles/request-coalescing-in-async-rust#a-simple-web-server

    let tracer = opentelemetry_jaeger::new_pipeline().install_batch(opentelemetry::runtime::Tokio)?;
    let telemetry = tracing_opentelemetry::layer().with_tracer(tracer);
    */

    Registry::default()
        .with(EnvFilter::from_default_env())
        .with(
            HierarchicalLayer::new(2)
                .with_targets(true)
                .with_bracketed_fields(true),
        )
        .init();

    let conn = Connection::open("world.sqlite3")?;

    let mut stmt = conn.prepare("SELECT key, gid, version, serialized FROM entities;")?;

    let entities = stmt.query_map([], |row| {
        Ok(PersistedEntity {
            key: row.get(0)?,
            gid: row.get(1)?,
            version: row.get(2)?,
            serialized: row.get(3)?,
        })
    })?;

    for maybe_entity in entities {
        let persisted = maybe_entity.unwrap();

        debug!(%persisted.key, %persisted.gid, %persisted.version, "loading");

        // let opaque: Value = serde_json::from_str(&persisted.serialized)?;
        // debug!("{}", serde_json::to_string_pretty(&opaque).unwrap());

        let entity = persisted.to_entity()?;

        info!(%entity.key, "parsed");
    }

    Ok(())
}
