-- Minimal synthetic data for SQL tests. No login is performed.
INSERT INTO core_user
 (id,password,is_superuser,username,first_name,last_name,email,
  is_staff,is_active,date_joined,role)
VALUES
 (1,'!test-only',FALSE,'olena','','','',FALSE,TRUE,NOW(),'teacher'),
 (2,'!test-only',FALSE,'taras','','','',FALSE,TRUE,NOW(),'manager');

INSERT INTO core_template
 (id,name,description,is_active,schema,version)
VALUES (1,'Заява','Навчальний шаблон',TRUE,'[]',1);

INSERT INTO core_document
 (id,title,template_snapshot,data,status,version,created_at,updated_at,
  completed_at,owner_id,template_id)
VALUES
 (1,'Заява Олени','{}','{"text":"Прошу надати відпустку"}',
  'draft',1,NOW(),NOW(),NULL,1,1);

INSERT INTO core_documentevent
 (id,document_id,actor_id,from_status,to_status,comment,created_at)
VALUES (1,1,1,'','draft','Створено',NOW());

SELECT setval(pg_get_serial_sequence('core_user','id'),2);
SELECT setval(pg_get_serial_sequence('core_template','id'),1);
SELECT setval(pg_get_serial_sequence('core_document','id'),1);
SELECT setval(pg_get_serial_sequence('core_documentevent','id'),1);
