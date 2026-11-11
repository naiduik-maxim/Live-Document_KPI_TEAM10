-- Synthetic data only. Apply to an empty test schema.
INSERT INTO core_user
 (id,password,last_login,is_superuser,username,first_name,last_name,email,
  is_staff,is_active,date_joined,role)
SELECT id,
 'pbkdf2_sha256$1000000$dbtestfixture$QCXKSKYYJQvVC5xifpHvHBcWAYiukH/D0YvX5w2OWqg=',
 NULL,FALSE,username,'','','',FALSE,TRUE,'2026-01-01 08:00:00+00',role
FROM (VALUES
 (101,'db_author','teacher'),(102,'db_other','teacher'),
 (103,'db_manager','manager'),(104,'db_admin','admin')
) AS fixture(id,username,role);

INSERT INTO core_template
 (id,name,description,is_active,schema,version)
VALUES
 (201,'DB report','Test only',TRUE,
 '[{"name":"text","label":"Текст","type":"textarea","required":true}]',1),
 (202,'DB inactive','Test only',FALSE,'[]',1);

INSERT INTO core_document
 (id,title,template_snapshot,data,status,version,created_at,updated_at,
  completed_at,owner_id,template_id)
SELECT 301,'DB draft',
 jsonb_build_object('name',name,'description',description,
                   'schema',schema,'version',version),
 '{"text":"Звіт"}','draft',1,'2026-01-01 08:00:00+00',
 '2026-01-01 08:00:00+00',NULL,101,id
FROM core_template WHERE id=201;

INSERT INTO core_document
 (id,title,template_snapshot,data,status,version,created_at,updated_at,
  completed_at,owner_id,template_id)
SELECT 302,'DB completed',
 jsonb_build_object('name',name,'description',description,
                   'schema',schema,'version',version),
 '{"text":"Готовий звіт"}','completed',4,'2026-01-01 08:00:00+00',
 '2026-01-01 10:00:00+00','2026-01-01 10:00:00+00',102,id
FROM core_template WHERE id=201;

INSERT INTO core_documentevent
 (id,document_id,actor_id,from_status,to_status,comment,created_at)
VALUES
 (401,301,101,'','draft','Created','2026-01-01 08:00:00+00'),
 (402,302,102,'','draft','Created','2026-01-01 08:00:00+00'),
 (403,302,102,'draft','submitted','','2026-01-01 08:30:00+00'),
 (404,302,103,'submitted','approved','','2026-01-01 09:00:00+00'),
 (405,302,102,'approved','completed','','2026-01-01 10:00:00+00');

SELECT setval(pg_get_serial_sequence('core_user','id'),104);
SELECT setval(pg_get_serial_sequence('core_template','id'),202);
SELECT setval(pg_get_serial_sequence('core_document','id'),302);
SELECT setval(pg_get_serial_sequence('core_documentevent','id'),405);
