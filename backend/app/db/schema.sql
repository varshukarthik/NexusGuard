-- NovaTech Solutions — PostgreSQL 16 + pgvector schema (generated from app/db/models.py).
-- The app creates these tables automatically (SQLAlchemy create_all); this file documents the DDL.
-- Every business record carries a classification + department scope enforced by core/rbac.py.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE companies (
	id VARCHAR(40) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	domain VARCHAR(120) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (domain)
);

CREATE TABLE audit_logs (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE NOT NULL, 
	user_id VARCHAR(40), 
	user_name VARCHAR(200) NOT NULL, 
	session_id VARCHAR(60) NOT NULL, 
	ip VARCHAR(64) NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	query TEXT NOT NULL, 
	resource VARCHAR(300) NOT NULL, 
	resource_id VARCHAR(60) NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	permission_result VARCHAR(20) NOT NULL, 
	tool VARCHAR(60) NOT NULL, 
	result VARCHAR(40) NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	risk VARCHAR(20) NOT NULL, 
	request_id VARCHAR(60) NOT NULL, 
	details JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_audit_company_ts ON audit_logs (company_id, ts);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_company_id ON audit_logs (company_id);
CREATE INDEX ix_audit_logs_permission_result ON audit_logs (permission_result);
CREATE INDEX ix_audit_logs_risk ON audit_logs (risk);
CREATE INDEX ix_audit_logs_ts ON audit_logs (ts);
CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);

CREATE TABLE budgets (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	department VARCHAR(120) NOT NULL, 
	cost_center VARCHAR(40) NOT NULL, 
	fiscal_year VARCHAR(10) NOT NULL, 
	quarter VARCHAR(4) NOT NULL, 
	category VARCHAR(60) NOT NULL, 
	allocated FLOAT NOT NULL, 
	spent FLOAT NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_budgets_classification ON budgets (classification);
CREATE INDEX ix_budgets_company_id ON budgets (company_id);
CREATE INDEX ix_budgets_department ON budgets (department);
CREATE INDEX ix_budgets_fiscal_year ON budgets (fiscal_year);

CREATE TABLE business_units (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	description TEXT NOT NULL, 
	head_id VARCHAR(40), 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_business_units_company_id ON business_units (company_id);

CREATE TABLE cost_centers (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	department VARCHAR(120) NOT NULL, 
	owner_id VARCHAR(40), 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_cost_centers_classification ON cost_centers (classification);
CREATE INDEX ix_cost_centers_company_id ON cost_centers (company_id);
CREATE INDEX ix_cost_centers_department ON cost_centers (department);

CREATE TABLE customers (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	industry VARCHAR(80) NOT NULL, 
	region VARCHAR(60) NOT NULL, 
	tier VARCHAR(20) NOT NULL, 
	account_owner_id VARCHAR(40), 
	customer_since DATE, 
	is_reference BOOLEAN NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_customers_classification ON customers (classification);
CREATE INDEX ix_customers_company_id ON customers (company_id);
CREATE INDEX ix_customers_name ON customers (name);
CREATE INDEX ix_customers_region ON customers (region);

CREATE TABLE departments (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	code VARCHAR(20) NOT NULL, 
	description TEXT NOT NULL, 
	business_unit VARCHAR(120) NOT NULL, 
	head_id VARCHAR(40), 
	location VARCHAR(120) NOT NULL, 
	is_public BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (company_id, name), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_departments_company_id ON departments (company_id);

CREATE TABLE locations (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	city VARCHAR(80) NOT NULL, 
	country VARCHAR(80) NOT NULL, 
	kind VARCHAR(40) NOT NULL, 
	address VARCHAR(300) NOT NULL, 
	timezone VARCHAR(60) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_locations_company_id ON locations (company_id);

CREATE TABLE permissions (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	code VARCHAR(80) NOT NULL, 
	description VARCHAR(300) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (company_id, code), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_permissions_company_id ON permissions (company_id);

CREATE TABLE products (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	description TEXT NOT NULL, 
	list_price FLOAT NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_products_classification ON products (classification);
CREATE INDEX ix_products_company_id ON products (company_id);

CREATE TABLE projects (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	department VARCHAR(120) NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	allowed_roles JSON NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	health VARCHAR(20) NOT NULL, 
	progress INTEGER NOT NULL, 
	owner_name VARCHAR(120) NOT NULL, 
	summary TEXT NOT NULL, 
	milestones JSON NOT NULL, 
	updated_on DATE NOT NULL, 
	manager_id VARCHAR(40), 
	priority VARCHAR(20) NOT NULL, 
	start_date DATE, 
	deadline DATE, 
	budget_category VARCHAR(40) NOT NULL, 
	budget_amount FLOAT NOT NULL, 
	risks JSON NOT NULL, 
	technologies JSON NOT NULL, 
	business_unit VARCHAR(120) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_projects_company_id ON projects (company_id);
CREATE INDEX ix_projects_company_status ON projects (company_id, status);
CREATE INDEX ix_projects_deadline ON projects (deadline);
CREATE INDEX ix_projects_manager_id ON projects (manager_id);

CREATE TABLE roles (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	code VARCHAR(60) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	description VARCHAR(300) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (company_id, code), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_roles_company_id ON roles (company_id);

CREATE TABLE security_alerts (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE NOT NULL, 
	user_id VARCHAR(40), 
	user_name VARCHAR(200) NOT NULL, 
	alert_type VARCHAR(60) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	pattern VARCHAR(400) NOT NULL, 
	risk VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	event_count INTEGER NOT NULL, 
	details JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_security_alerts_company_id ON security_alerts (company_id);
CREATE INDEX ix_security_alerts_ts ON security_alerts (ts);

CREATE TABLE software_catalog (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	vendor VARCHAR(120) NOT NULL, 
	license_type VARCHAR(60) NOT NULL, 
	approval_required BOOLEAN NOT NULL, 
	platforms JSON NOT NULL, 
	description VARCHAR(400) NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_software_catalog_classification ON software_catalog (classification);
CREATE INDEX ix_software_catalog_company_id ON software_catalog (company_id);
CREATE INDEX ix_software_catalog_name ON software_catalog (name);

CREATE TABLE vendors (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	country VARCHAR(60) NOT NULL, 
	rating FLOAT NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	onboarded_on DATE, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_vendors_category ON vendors (category);
CREATE INDEX ix_vendors_classification ON vendors (classification);
CREATE INDEX ix_vendors_company_id ON vendors (company_id);
CREATE INDEX ix_vendors_name ON vendors (name);

CREATE TABLE contracts (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	customer_id VARCHAR(40) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	value FLOAT NOT NULL, 
	start_date DATE NOT NULL, 
	end_date DATE NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id)
);
CREATE INDEX ix_contracts_classification ON contracts (classification);
CREATE INDEX ix_contracts_company_id ON contracts (company_id);
CREATE INDEX ix_contracts_customer_id ON contracts (customer_id);
CREATE INDEX ix_contracts_end_date ON contracts (end_date);
CREATE INDEX ix_contracts_status ON contracts (status);

CREATE TABLE opportunities (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	customer_id VARCHAR(40) NOT NULL, 
	product_id VARCHAR(40) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	stage VARCHAR(40) NOT NULL, 
	amount FLOAT NOT NULL, 
	probability INTEGER NOT NULL, 
	close_date DATE NOT NULL, 
	owner_id VARCHAR(40), 
	region VARCHAR(60) NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id)
);
CREATE INDEX ix_opportunities_classification ON opportunities (classification);
CREATE INDEX ix_opportunities_close_date ON opportunities (close_date);
CREATE INDEX ix_opportunities_company_id ON opportunities (company_id);
CREATE INDEX ix_opportunities_customer_id ON opportunities (customer_id);
CREATE INDEX ix_opportunities_owner_id ON opportunities (owner_id);
CREATE INDEX ix_opportunities_region ON opportunities (region);
CREATE INDEX ix_opportunities_stage ON opportunities (stage);

CREATE TABLE role_permissions (
	role_id VARCHAR(40) NOT NULL, 
	permission_id VARCHAR(40) NOT NULL, 
	PRIMARY KEY (role_id, permission_id), 
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
	FOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE
);

CREATE TABLE users (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	employee_code VARCHAR(30) NOT NULL, 
	email VARCHAR(200) NOT NULL, 
	full_name VARCHAR(200) NOT NULL, 
	password_hash VARCHAR(300) NOT NULL, 
	department_id VARCHAR(40) NOT NULL, 
	role_id VARCHAR(40) NOT NULL, 
	job_title VARCHAR(160) NOT NULL, 
	clearance VARCHAR(20) NOT NULL, 
	manager_id VARCHAR(40), 
	location VARCHAR(120) NOT NULL, 
	phone VARCHAR(40) NOT NULL, 
	pan_number VARCHAR(20) NOT NULL, 
	bank_account VARCHAR(30) NOT NULL, 
	joined_on DATE, 
	is_active BOOLEAN NOT NULL, 
	is_demo_persona BOOLEAN NOT NULL, 
	is_guest BOOLEAN NOT NULL, 
	employment_status VARCHAR(30) NOT NULL, 
	skills JSON NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (company_id, employee_code), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id), 
	FOREIGN KEY(role_id) REFERENCES roles (id), 
	FOREIGN KEY(manager_id) REFERENCES users (id)
);
CREATE INDEX ix_users_company_dept ON users (company_id, department_id);
CREATE INDEX ix_users_company_id ON users (company_id);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_is_guest ON users (is_guest);
CREATE INDEX ix_users_manager ON users (manager_id);

CREATE TABLE ai_actions (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	conversation_id VARCHAR(40), 
	message_id VARCHAR(40), 
	tool VARCHAR(60) NOT NULL, 
	args JSON NOT NULL, 
	preview JSON NOT NULL, 
	risk VARCHAR(20) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	result JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	decided_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_ai_actions_company_id ON ai_actions (company_id);
CREATE INDEX ix_ai_actions_user_id ON ai_actions (user_id);

CREATE TABLE approval_requests (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	type VARCHAR(40) NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	requester_id VARCHAR(40) NOT NULL, 
	approver_id VARCHAR(40), 
	approver_permission VARCHAR(80), 
	resource_id VARCHAR(60), 
	details JSON NOT NULL, 
	risk VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	decided_by VARCHAR(40), 
	decision_note VARCHAR(500) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	decided_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(requester_id) REFERENCES users (id), 
	FOREIGN KEY(approver_id) REFERENCES users (id), 
	FOREIGN KEY(decided_by) REFERENCES users (id)
);
CREATE INDEX ix_approval_requests_approver_id ON approval_requests (approver_id);
CREATE INDEX ix_approval_requests_company_id ON approval_requests (company_id);
CREATE INDEX ix_approval_requests_requester_id ON approval_requests (requester_id);
CREATE INDEX ix_approval_requests_status ON approval_requests (status);

CREATE TABLE compensation (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	band VARCHAR(20) NOT NULL, 
	base_salary FLOAT NOT NULL, 
	currency VARCHAR(8) NOT NULL, 
	effective_date DATE NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_compensation_classification ON compensation (classification);
CREATE INDEX ix_compensation_company_id ON compensation (company_id);
CREATE INDEX ix_compensation_user_id ON compensation (user_id);

CREATE TABLE conversations (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_conversations_company_id ON conversations (company_id);
CREATE INDEX ix_conversations_updated_at ON conversations (updated_at);
CREATE INDEX ix_conversations_user_id ON conversations (user_id);

CREATE TABLE documents (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	filename VARCHAR(300) NOT NULL, 
	doc_type VARCHAR(40) NOT NULL, 
	department VARCHAR(120) NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	allowed_roles JSON NOT NULL, 
	owner_id VARCHAR(40), 
	family_key VARCHAR(200) NOT NULL, 
	version VARCHAR(20) NOT NULL, 
	effective_date DATE NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	content TEXT NOT NULL, 
	summary TEXT NOT NULL, 
	ai_classification VARCHAR(20), 
	ai_classification_reason TEXT, 
	security_flags JSON NOT NULL, 
	source VARCHAR(20) NOT NULL, 
	tags JSON NOT NULL, 
	project_id VARCHAR(40), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);
CREATE INDEX ix_docs_company_status ON documents (company_id, status);
CREATE INDEX ix_docs_company_type ON documents (company_id, doc_type);
CREATE INDEX ix_documents_classification ON documents (classification);
CREATE INDEX ix_documents_company_id ON documents (company_id);
CREATE INDEX ix_documents_family_key ON documents (family_key);
CREATE INDEX ix_documents_project_id ON documents (project_id);
CREATE INDEX ix_documents_status ON documents (status);
CREATE INDEX ix_documents_updated_at ON documents (updated_at);

CREATE TABLE email_outbox (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	sender_id VARCHAR(40) NOT NULL, 
	recipient_email VARCHAR(200) NOT NULL, 
	recipient_name VARCHAR(200) NOT NULL, 
	subject VARCHAR(300) NOT NULL, 
	body TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(sender_id) REFERENCES users (id)
);
CREATE INDEX ix_email_outbox_company_id ON email_outbox (company_id);
CREATE INDEX ix_email_outbox_sender_id ON email_outbox (sender_id);

CREATE TABLE expenses (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	department VARCHAR(120) NOT NULL, 
	category VARCHAR(60) NOT NULL, 
	amount FLOAT NOT NULL, 
	spent_on DATE NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	description VARCHAR(300) NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_expenses_classification ON expenses (classification);
CREATE INDEX ix_expenses_company_id ON expenses (company_id);
CREATE INDEX ix_expenses_department ON expenses (department);
CREATE INDEX ix_expenses_spent_on ON expenses (spent_on);
CREATE INDEX ix_expenses_status ON expenses (status);
CREATE INDEX ix_expenses_user_id ON expenses (user_id);

CREATE TABLE it_assets (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	asset_type VARCHAR(40) NOT NULL, 
	model VARCHAR(120) NOT NULL, 
	assigned_to VARCHAR(40), 
	purchased_on DATE NOT NULL, 
	warranty_until DATE NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(assigned_to) REFERENCES users (id)
);
CREATE INDEX ix_it_assets_assigned_to ON it_assets (assigned_to);
CREATE INDEX ix_it_assets_company_id ON it_assets (company_id);

CREATE TABLE it_tickets (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	priority VARCHAR(10) NOT NULL, 
	category VARCHAR(40) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_it_tickets_company_id ON it_tickets (company_id);
CREATE INDEX ix_it_tickets_user_id ON it_tickets (user_id);
CREATE INDEX ix_tickets_user_status ON it_tickets (user_id, status);

CREATE TABLE leave_balances (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	year INTEGER NOT NULL, 
	casual_total FLOAT NOT NULL, 
	casual_used FLOAT NOT NULL, 
	sick_total FLOAT NOT NULL, 
	sick_used FLOAT NOT NULL, 
	earned_total FLOAT NOT NULL, 
	earned_used FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_leave_balances_company_id ON leave_balances (company_id);
CREATE INDEX ix_leave_balances_user_id ON leave_balances (user_id);

CREATE TABLE leave_requests (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	leave_type VARCHAR(20) NOT NULL, 
	start_date DATE NOT NULL, 
	end_date DATE NOT NULL, 
	days FLOAT NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_leave_requests_company_id ON leave_requests (company_id);
CREATE INDEX ix_leave_requests_user_id ON leave_requests (user_id);
CREATE INDEX ix_leave_user_status ON leave_requests (user_id, status);

CREATE TABLE meetings (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	organizer_id VARCHAR(40) NOT NULL, 
	project_id VARCHAR(40), 
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ends_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	location VARCHAR(120) NOT NULL, 
	agenda TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(organizer_id) REFERENCES users (id)
);
CREATE INDEX ix_meetings_company_id ON meetings (company_id);
CREATE INDEX ix_meetings_organizer_id ON meetings (organizer_id);
CREATE INDEX ix_meetings_starts_at ON meetings (starts_at);

CREATE TABLE performance_reviews (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	reviewer_id VARCHAR(40), 
	cycle VARCHAR(20) NOT NULL, 
	rating VARCHAR(30) NOT NULL, 
	summary TEXT NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_performance_reviews_classification ON performance_reviews (classification);
CREATE INDEX ix_performance_reviews_company_id ON performance_reviews (company_id);
CREATE INDEX ix_performance_reviews_user_id ON performance_reviews (user_id);

CREATE TABLE project_members (
	project_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	project_role VARCHAR(80) NOT NULL, 
	allocation_pct INTEGER NOT NULL, 
	PRIMARY KEY (project_id, user_id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);
CREATE INDEX ix_project_members_company_id ON project_members (company_id);
CREATE INDEX ix_project_members_user_id ON project_members (user_id);

CREATE TABLE purchase_orders (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	vendor_id VARCHAR(40) NOT NULL, 
	requester_id VARCHAR(40) NOT NULL, 
	department VARCHAR(120) NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	description VARCHAR(300) NOT NULL, 
	amount FLOAT NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_on DATE NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	allowed_departments JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(vendor_id) REFERENCES vendors (id), 
	FOREIGN KEY(requester_id) REFERENCES users (id)
);
CREATE INDEX ix_purchase_orders_classification ON purchase_orders (classification);
CREATE INDEX ix_purchase_orders_company_id ON purchase_orders (company_id);
CREATE INDEX ix_purchase_orders_created_on ON purchase_orders (created_on);
CREATE INDEX ix_purchase_orders_department ON purchase_orders (department);
CREATE INDEX ix_purchase_orders_requester_id ON purchase_orders (requester_id);
CREATE INDEX ix_purchase_orders_status ON purchase_orders (status);
CREATE INDEX ix_purchase_orders_vendor_id ON purchase_orders (vendor_id);

CREATE TABLE service_requests (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	requester_id VARCHAR(40) NOT NULL, 
	request_type VARCHAR(40) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	details JSON NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	approver_id VARCHAR(40), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(requester_id) REFERENCES users (id)
);
CREATE INDEX ix_service_requests_company_id ON service_requests (company_id);
CREATE INDEX ix_service_requests_request_type ON service_requests (request_type);
CREATE INDEX ix_service_requests_requester_id ON service_requests (requester_id);
CREATE INDEX ix_service_requests_status ON service_requests (status);

CREATE TABLE sessions (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	token_hash VARCHAR(128) NOT NULL, 
	auth_method VARCHAR(40) NOT NULL, 
	ip VARCHAR(64) NOT NULL, 
	user_agent VARCHAR(300) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_sessions_company_id ON sessions (company_id);
CREATE UNIQUE INDEX ix_sessions_token_hash ON sessions (token_hash);
CREATE INDEX ix_sessions_user_id ON sessions (user_id);

CREATE TABLE tasks (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	assignee_id VARCHAR(40) NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	project VARCHAR(120) NOT NULL, 
	priority VARCHAR(10) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	due_date DATE, 
	project_id VARCHAR(40), 
	description TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(assignee_id) REFERENCES users (id)
);
CREATE INDEX ix_tasks_assignee_id ON tasks (assignee_id);
CREATE INDEX ix_tasks_assignee_status ON tasks (assignee_id, status);
CREATE INDEX ix_tasks_company_id ON tasks (company_id);
CREATE INDEX ix_tasks_due_date ON tasks (due_date);
CREATE INDEX ix_tasks_project_id ON tasks (project_id);
CREATE INDEX ix_tasks_status ON tasks (status);

CREATE TABLE tool_executions (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	action_id VARCHAR(40), 
	tool VARCHAR(60) NOT NULL, 
	args JSON NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	result_summary TEXT NOT NULL, 
	duration_ms INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_tool_executions_company_id ON tool_executions (company_id);
CREATE INDEX ix_tool_executions_created_at ON tool_executions (created_at);
CREATE INDEX ix_tool_executions_tool ON tool_executions (tool);
CREATE INDEX ix_tool_executions_user_id ON tool_executions (user_id);

CREATE TABLE workflow_executions (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	conversation_id VARCHAR(40), 
	message_id VARCHAR(40), 
	intent VARCHAR(40) NOT NULL, 
	engine VARCHAR(40) NOT NULL, 
	agents JSON NOT NULL, 
	steps JSON NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	duration_ms INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_wf_company_created ON workflow_executions (company_id, created_at);
CREATE INDEX ix_workflow_executions_company_id ON workflow_executions (company_id);
CREATE INDEX ix_workflow_executions_user_id ON workflow_executions (user_id);

CREATE TABLE document_chunks (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	document_id VARCHAR(40) NOT NULL, 
	chunk_index INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	embedding VECTOR(384), 
	embedding_model VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
);
CREATE INDEX ix_chunks_company_doc ON document_chunks (company_id, document_id);
CREATE INDEX ix_document_chunks_company_id ON document_chunks (company_id);
CREATE INDEX ix_document_chunks_document_id ON document_chunks (document_id);

CREATE TABLE document_permissions (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	document_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	granted_by VARCHAR(40) NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(granted_by) REFERENCES users (id)
);
CREATE INDEX ix_document_permissions_company_id ON document_permissions (company_id);
CREATE INDEX ix_document_permissions_document_id ON document_permissions (document_id);
CREATE INDEX ix_document_permissions_user_id ON document_permissions (user_id);

CREATE TABLE meeting_attendees (
	meeting_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	PRIMARY KEY (meeting_id, user_id), 
	FOREIGN KEY(meeting_id) REFERENCES meetings (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_meeting_attendees_user_id ON meeting_attendees (user_id);

CREATE TABLE messages (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	conversation_id VARCHAR(40) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	content TEXT NOT NULL, 
	intent VARCHAR(40), 
	meta JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);
CREATE INDEX ix_messages_company_id ON messages (company_id);
CREATE INDEX ix_messages_conversation_id ON messages (conversation_id);

CREATE TABLE message_feedback (
	id VARCHAR(40) NOT NULL, 
	company_id VARCHAR(40) NOT NULL, 
	user_id VARCHAR(40) NOT NULL, 
	message_id VARCHAR(40) NOT NULL, 
	rating INTEGER NOT NULL, 
	comment VARCHAR(500) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, message_id), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(message_id) REFERENCES messages (id) ON DELETE CASCADE
);
CREATE INDEX ix_message_feedback_company_id ON message_feedback (company_id);
CREATE INDEX ix_message_feedback_message_id ON message_feedback (message_id);
CREATE INDEX ix_message_feedback_user_id ON message_feedback (user_id);

-- Approximate-nearest-neighbour index for permission-filtered semantic search
CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- Retrieval (authorization happens first; only authorized document ids are ever passed in):
--   SELECT id, document_id, 1 - (embedding <=> :q) AS score
--   FROM document_chunks WHERE company_id = :cid AND document_id = ANY(:authorized_ids)
--   ORDER BY embedding <=> :q LIMIT 60;

-- Optional defence-in-depth: Postgres row-level security for tenant isolation.
-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY tenant_isolation ON documents USING (company_id = current_setting('app.company_id'));
-- (repeat for document_chunks, conversations, messages, audit_logs, projects, …)

-- Audit log is append-only for the application role:
-- REVOKE UPDATE, DELETE ON audit_logs FROM novatech_app;
