CREATE TABLE sync_queue (
    id SERIAL PRIMARY KEY,
    assignmentid integer,
    new_responsible TEXT,
    old_responsible TEXT,
    status TEXT DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    message TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP,
	created_by varchar(50)
);