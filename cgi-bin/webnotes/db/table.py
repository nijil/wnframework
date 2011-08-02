import webnotes

default_columns = ['name', 'creation', 'modified', 'modified_by', 'owner', 'docstatus', 'parent',\
	 'parentfield', 'parenttype', 'idx']


class DatabaseTable:
	def __init__(self, doctype, prefix = 'tab'):
		self.doctype = doctype
		self.name = prefix + doctype
		self.columns = {}
		self.current_columns = {}
		
		# lists for change
		self.add_column = []
		self.change_type = []
		self.add_index = []
		self.drop_index = []
		self.set_default = []
		
		# load
		self.get_columns_from_docfields()

	def create(self):
		add_text = ''
		
		# columns
		t = self.get_column_definitions()
		if t: add_text += ',\n'.join(t) + ',\n'
		
		# index
		t = self.get_index_definitions()
		if t: add_text += ',\n'.join(t) + ',\n'
	
		# create table
		webnotes.conn.sql("""create table `%s` (
			name varchar(120) not null primary key, 
			creation datetime,
			modified datetime,
			modified_by varchar(40), 
			owner varchar(40),
			docstatus int(1) default '0', 
			parent varchar(120),
			parentfield varchar(120), 
			parenttype varchar(120), 
			idx int(8),
			%sindex parent(parent)) ENGINE=InnoDB""" % (self.name, add_text))

	def get_columns_from_docfields(self):
		fl = webnotes.conn.sql("SELECT * FROM tabDocField WHERE parent = '%s'" % self.doctype, as_dict = 1)

		for f in fl:
			if not f.get('no_column'):
				self.columns[f['fieldname']] = DatabaseColumn(self, f['fieldname'], f['fieldtype'], f.get('length'), f['default'], f['search_index'], f['options'])
	
	def get_columns_from_db(self):
		self.show_columns = webnotes.conn.sql("desc `%s`" % self.name)
		for c in self.show_columns:
			self.current_columns[c[0]] = {'name': c[0], 'type':c[1], 'index':c[3], 'default':c[4]}
	
	def get_column_definitions(self):
		column_list = [] + default_columns
		ret = []
		for k in self.columns.keys():
			if k not in column_list:
				d = self.columns[k].get_definition()
				if d:
					ret.append('`'+ k+ '` ' + d)
					column_list.append(k)
		return ret
	
	def get_index_definitions(self):
		ret = []
		for k in self.columns.keys():
			if self.columns[k].has_index():
				ret.append(self.columns[k].get_index())
		return ret


	# GET foreign keys
	def get_foreign_keys(self):
		fk_list = []
		txt = webnotes.conn.sql("show create table `%s`" % self.name)[0][1]
		for line in txt.split('\n'):
			if line.strip().startswith('CONSTRAINT') and line.find('FOREIGN')!=-1:
				try:
					fk_list.append((line.split('`')[3], line.split('`')[1]))
				except IndexError, e:
					pass

		return fk_list

	# Drop foreign keys
	def drop_foreign_keys(self):
		if not self.drop_foreign_key:
			return

		fk_list = self.get_foreign_keys()
		
		# make dictionary of constraint names
		fk_dict = {}
		for f in fk_list:
			fk_dict[f[0]] = f[1]
			
		# drop
		for col in self.drop_foreign_key:
			webnotes.conn.sql("set foreign_key_checks=0")
			webnotes.conn.sql("alter table `%s` drop foreign key `%s`" % (self.name, fk_dict[col.fieldname]))
			webnotes.conn.sql("set foreign_key_checks=1")
		
	def sync(self):
		if not self.name in DbManager(webnotes.conn).get_tables_list(webnotes.conn.cur_db_name):
			self.create()
		else:
			self.alter()
	
	def alter(self):
		self.get_columns_from_db()
		for col in self.columns.values():
			col.check(self.current_columns.get(col.fieldname, None))

		for col in self.add_column:
			webnotes.conn.sql("alter table `%s` add column `%s` %s" % (self.name, col.fieldname, col.get_definition()))

		for col in self.change_type:
			webnotes.conn.sql("alter table `%s` change `%s` `%s` %s" % (self.name, col.fieldname, col.fieldname, col.get_definition()))

		for col in self.add_index:
			webnotes.conn.sql("alter table `%s` add index `%s`(`%s`)" % (self.name, col.fieldname, col.fieldname))

		for col in self.drop_index:
			if col.fieldname != 'name': # primary key
				webnotes.conn.sql("alter table `%s` drop index `%s`" % (self.name, col.fieldname))


		for col in self.set_default:
			webnotes.conn.sql("alter table `%s` alter column `%s` set default %s" % (self.name, col.fieldname, '%s'), col.default)