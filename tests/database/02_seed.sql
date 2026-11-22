-- Load once into the empty schema. Identity columns assign the fixture IDs.
INSERT INTO django_content_type (app_label, model)
VALUES ('core', 'document');

INSERT INTO auth_permission (name, content_type_id, codename)
VALUES ('Can view document', 1, 'view_document');

INSERT INTO django_migrations (app, name, applied)
VALUES ('core', '0001_initial', NOW());

INSERT INTO core_user
 (password,is_superuser,username,first_name,last_name,email,
  is_staff,is_active,date_joined,role)
VALUES
 ('!test-only',FALSE,'olena','','','',FALSE,TRUE,NOW(),'teacher'),
 ('!test-only',FALSE,'taras','','','',FALSE,TRUE,NOW(),'manager');

INSERT INTO core_template
 (name,description,is_active,schema,version)
VALUES ('Заява','Навчальний шаблон',TRUE,'[]',1);

INSERT INTO core_document
 (title,template_snapshot,data,status,version,created_at,updated_at,
  completed_at,owner_id,template_id)
VALUES
 ('Заява Олени','{}','{"text":"Прошу надати відпустку"}',
  'draft',1,NOW(),NOW(),NULL,1,1);

INSERT INTO core_documentevent
 (document_id,actor_id,from_status,to_status,comment,created_at)
VALUES (1,1,'','draft','Створено',NOW());
