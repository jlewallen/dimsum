UPDATE entities SET
serialized = json_set(serialized, '$.scopes.post.queue', json('[]'))
WHERE json_extract(serialized, '$.scopes.post') IS NOT NULL
