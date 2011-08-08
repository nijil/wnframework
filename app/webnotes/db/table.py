import webnotes

default_columns = ['name', 'creation', 'modified', 'modified_by', 'owner', 'docstatus', 'parent',\
	 'parentfield', 'parenttype', 'idx']


class DatabaseTable:

	columns = {}
	current_columns = {}

	foreign_keys = {}
	
	# lists for change
	add_column = []
	add_foreign_key = []
	drop_foreign_key = []
	change_type = []
	add_index = []
	drop_index = []
	set_default = []
	
	def __init__(self, mtype=None, prefix = 'tab', model_def = None):
		self.type = mtype
		
		if model_def:
			self.model_def = model_def
			self.type = model_def.parent.name

		self.name = prefix + self.type
		
	def create(self):
		"""
			Create table based on `ModelDef`
		"""
		
		self.get_columns_from_modeldef()
		add_text = ''
		
		# columns
		t = self.get_column_definitions()
		if t: add_text += ',\n'.join(t) + ',\n'
		
		# index
		t = self.get_index_definitions()
		if t: add_text += ',\n'.join(t) + ',\n'
	
		# create table
		webnotes.conn.sql("set foreign_key_checks=0")
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
		webnotes.conn.sql("set foreign_key_checks=1")


	def get_column_definitions(self):
		"""
			Get columns to add at time of creation
		"""
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
		"""
			Get index to add at time of creation
		"""
		ret = []
		for k in self.columns.keys():
			c = self.columns[k]
			if c.has_index():
				ret.append(c.get_index_def())
			if c.fieldtype=='Link' and c.options:
				ret.append(c.get_foreign_key_def())
		return ret

	def get_columns_from_modeldef(self):
		"""
			Load column definition from `ModelDef`
		"""
		# clear
		self.columns = {}
		
		from webnotes.db.column import DatabaseColumn
		for f in self.model_def.children:
			if f.type=='ModelProperty' and not f.no_column:
				self.columns[f.fieldname] = DatabaseColumn(self, f)
	
	def get_columns_from_db(self):
		"""
			Load columns from db schema
		"""
		self.show_columns = webnotes.conn.sql("desc `%s`" % self.name)
		for c in self.show_columns:
			self.current_columns[c[0]] = {'name': c[0], 'type':c[1], 'index':c[3], 'default':c[4]}
		return self.current_columns
	
	def is_indexed(self, column_name):
		"""
			returns true if column is indexed
		"""
		return self.get_columns_from_db()[column_name]['index']		
	
	def sync(self):
		"""
			Create / Update table as per the modeldef
		"""
		from webnotes.db.manager import DbManager

		# load columns 
		self.get_columns_from_modeldef()		

		if not self.name in DbManager(webnotes.conn).get_tables_list(webnotes.conn.cur_db_name):
			self.create()
		else:
			self.alter()
	
	def clear_diff(self):
		"""
			Clear all the diff lists
		"""
		# lists for change
		self.add_column = []
		self.add_foreign_key = []
		self.drop_foreign_key = []
		self.change_type = []
		self.add_index = []
		self.drop_index = []
		self.set_default = []

	def alter(self):
		"""
			Alter the table based on diff lists
		"""
		self.clear_diff()
		self.get_columns_from_db()
	
		webnotes.conn.sql("set foreign_key_checks=0")
		
		# diff the columns (get the difference)
		for col in self.columns.values():
			col.diff(self.current_columns.get(col.fieldname, None))

		for col in self.add_column:
			webnotes.conn.sql("alter table `%s` add column `%s` %s" % (self.name, col.fieldname, col.get_definition()))

		for col in self.change_type:
			webnotes.conn.sql("alter table `%s` change `%s` `%s` %s" % (self.name, col.fieldname, col.fieldname, col.get_definition()))

		self.set_foreign_keys()
		self.drop_foreign_keys()

		for col in self.add_index:
			webnotes.conn.sql("alter table `%s` add index `%s`(`%s`)" % (self.name, col.fieldname, col.fieldname))

		for col in self.drop_index:
			if col.fieldname != 'name': # primary key
				webnotes.conn.sql("alter table `%s` drop index `%s`" % (self.name, col.fieldname))

		for col in self.set_default:
			webnotes.conn.sql("alter table `%s` alter column `%s` set default %s" % (self.name, col.fieldname, '%s'), col.default)

		# clear table metadata cache
		if self.name in webnotes.conn.table_metadata:
			del webnotes.conn.table_metadata[self.name]

		webnotes.conn.sql("set foreign_key_checks=1")


	# SET foreign keys
	def set_foreign_keys(self):
		if self.add_foreign_key:
			from webnotes.db.manager import DbManager
			tab_list = DbManager(webnotes.conn).get_tables_list(webnotes.conn.cur_db_name)

			for col in self.add_foreign_key:
				if col.options:
					tab_name = "tab" + col.options
					if tab_name in tab_list:
						webnotes.conn.sql("alter table `%s` add foreign key (`%s`) references `%s`(name) on update cascade" % (self.name, col.fieldname, tab_name))


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
			webnotes.conn.sql("alter table `%s` drop foreign key `%s`" % (self.name, fk_dict[col.fieldname]))

	def drop(self):
		"""
			Drop the table
		"""
		webnotes.conn.sql("drop table `%s`" % self.name)
