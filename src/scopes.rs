use std::collections::HashMap;

use anyhow::{Error, Result};

use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};

use crate::model::core::{Acls, EntityKey, EntityRef, Kind};

pub trait Scope: std::fmt::Debug {}

pub fn parse<T: Scope + DeserializeOwned + 'static>(
    value: &serde_json::Value,
) -> Result<Box<dyn Scope>, Error> {
    // The call to serde_json::from_value requires owned data and we have a
    // reference to somebody else's. Presumuably so that we don't couple the
    // lifetime of the returned object to the lifetime of the data being
    // referenced? What's the right solution here?
    // Should the 'un-parsed' Scope also owned the parsed data?
    let owned_value = value.clone();
    let body: T = serde_json::from_value(owned_value)?;
    Ok(Box::new(body))
}

pub fn new_from_kv(key: &String, value: &serde_json::Value) -> Result<Box<dyn Scope>, Error> {
    match key.as_str() {
        "carryable" => parse::<Carryable>(value),
        "containing" => parse::<Containing>(value),
        "location" => parse::<Location>(value),
        "ownership" => parse::<Ownership>(value),
        "occupyable" => parse::<Occupyable>(value),
        "occupying" => parse::<Occupying>(value),
        "exit" => parse::<Exit>(value),
        "behaviors" => parse::<Behaviors>(value),
        "behaviorCollection" => parse::<BehaviorCollection>(value),
        "movement" => parse::<Movement>(value),
        "apparel" => parse::<Apparel>(value),
        "memory" => parse::<Memory>(value),
        "health" => parse::<Health>(value),
        "encyclopedia" => parse::<Encyclopedia>(value),
        "weather" => parse::<Weather>(value),
        "post" => parse::<Post>(value),
        "wellKnown" => parse::<WellKnown>(value),
        "auth" => parse::<Auth>(value),
        "usernames" => parse::<Usernames>(value),
        "identifiers" => parse::<Identifiers>(value),
        _ => Ok(Box::new(Unknown {})),
    }
}

pub fn from_map(
    map: &HashMap<String, serde_json::Value>,
) -> Result<HashMap<&String, Box<dyn Scope>>, Error> {
    map.iter()
        .map(|(k, v)| Ok((k, new_from_kv(k, v)?)))
        .collect()
}

// #[serde(alias = "py/object")]
// type PyObject = String;

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Unknown {}

impl Scope for Unknown {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Exit {
    acls: Acls,
    area: EntityRef,
}

impl Scope for Exit {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Location {
    acls: Acls,
    container: Option<EntityRef>,
}

impl Scope for Location {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Behaviors {
    behaviors: BehaviorsInner,
}

#[derive(Debug, Serialize, Deserialize)]
struct BehaviorMeta {
    #[serde(alias = "py/object")]
    py_object: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct BehaviorCollection {
    entities: HashMap<String, Vec<BehaviorMeta>>,
}

#[derive(Debug, Serialize, Deserialize)]
struct BehaviorsInner {
    #[serde(alias = "py/object")]
    py_object: String,
    map: HashMap<String, Behavior>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Behavior {
    #[serde(alias = "py/object")]
    py_object: String,
    acls: Acls,
    python: Option<String>,
    executable: bool,
    logs: Vec<BehaviorLog>,
}

#[derive(Debug, Serialize, Deserialize)]
struct BehaviorLog {
    context: HashMap<String, serde_json::Value>,
    logs: Vec<String>,
    exceptions: Option<serde_json::Value>,
    success: bool,
    time: f32,
    elapsed: f32,
}

impl Scope for Behaviors {}

impl Scope for BehaviorCollection {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Ownership {
    owner: EntityRef,
}

impl Scope for Ownership {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Occupyable {
    acls: Acls,
    occupancy: u32,
    occupied: Vec<EntityRef>,
}

impl Scope for Occupyable {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Openable {
    #[serde(alias = "py/object")]
    py_object: String,
}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Containing {
    acls: Acls,
    capacity: Option<u32>,
    holding: Vec<EntityRef>,
    locked: bool,
    openable: Option<Openable>,
    pattern: Option<String>,
    produces: serde_json::Value,
}

impl Scope for Containing {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Carryable {
    kind: Kind,
    loose: bool,
    quantity: f32,
}

impl Scope for Carryable {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Encyclopedia {
    acls: Option<Acls>,
    body: String,
}

impl Scope for Encyclopedia {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Memory {}

impl Scope for Memory {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Health {
    medical: Medical,
}

#[derive(Debug, Serialize, Deserialize)]
struct Medical {
    #[serde(alias = "py/object")]
    py_object: String,
    nutrition: Nutrition,
}

#[derive(Debug, Serialize, Deserialize)]
struct Nutrition {
    #[serde(alias = "py/object")]
    py_object: String,
    properties: HashMap<String, serde_json::Value>,
}

impl Scope for Health {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Auth {
    acls: Acls,
    password: Option<(String, String)>,
}

impl Scope for Auth {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct WellKnown {
    entities: HashMap<String, EntityKey>,
}

impl Scope for WellKnown {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Apparel {}

impl Scope for Apparel {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Movement {}

impl Scope for Movement {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Occupying {
    acls: Acls,
    area: EntityRef,
}

impl Scope for Occupying {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Post {
    queue: Vec<QueuedPost>,
}

#[derive(Debug, Serialize, Deserialize)]
struct QueuedTime {
    #[serde(alias = "py/object")]
    py_object: String,
    time: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct QueuedPost {
    #[serde(alias = "py/object")]
    py_object: String,
    when: QueuedTime,
    entity_key: String,
    message: String,
}

impl Scope for Post {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Weather {
    wind: Wind,
}

#[derive(Debug, Serialize, Deserialize)]
struct Wind {
    #[serde(alias = "py/object")]
    py_object: String,
    magnitude: u32,
}

impl Scope for Weather {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Identifiers {
    acls: Acls,
    gid: u32,
}

impl Scope for Identifiers {}

// scope
#[derive(Debug, Serialize, Deserialize)]
struct Usernames {
    acls: Acls,
    users: HashMap<String, EntityKey>,
}

impl Scope for Usernames {}
