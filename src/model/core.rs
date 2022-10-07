use serde::{Deserialize, Serialize};

pub type EntityKey = String;

#[derive(Debug, Serialize, Deserialize)]
pub struct EntityRef {
    #[serde(alias = "py/object")]
    py_object: String,
    #[serde(alias = "py/ref")]
    py_ref: String,
    key: EntityKey,
    klass: String,
    name: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Identity {
    #[serde(alias = "py/object")]
    py_object: String,
    private: String,
    public: String,
    signature: Option<String>, // TODO Why does this happen?
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Kind {
    #[serde(alias = "py/object")]
    py_object: String,
    identity: Identity,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct EntityClass {
    #[serde(alias = "py/type")]
    py_type: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AclRule {
    #[serde(alias = "py/object")]
    py_object: String,
    keys: Vec<String>,
    perm: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Acls {
    #[serde(alias = "py/object")]
    py_object: String,
    rules: Vec<AclRule>,
}
