"""
	`Model Index`
	-------------
	
	Discussion: All the models that define the application are stored in the "app" folder 
	and with an extension `.model`. The model index, walks through the app folder and 
	finds all the `.model` files and syncs them to the database. 
	
	`Model Index` maintains the timestamps of all the models and their paths in a table
	`__model_index`
"""

import webnotes

def get_model_path(name):
	return webnotes.conn.sql("""
		select path from __model_index
		where name=%s
	""", name)[0][0]

class ModelIndex:
	"""
		Model Indexer walks the app folder and indexes all models and
		keeps the list in a table __model_index (name, path, tstamp)
	"""	
	def index_all(self):
		"""
			Walk the app folder and find all .model files
		"""
		import os
		from webnotes.model.collection import FileCollection
		from webnotes.utils import get_file_timestamp
		
		for walk_tuple in os.walk(webnotes.app_path):
			for model_file in filter(lambda x: x.endswith('.model'), walk_tuple[2]):
				fpath = os.path.join(walk_tuple[0], model_file)
				
				# read the collection
				fc = FileCollection(fpath)
				
				self.insert(fc.parent.name, fpath, get_file_timestamp(fpath))
					
	def insert(self, name, path, tstamp):
		"""
			Insert a new ModelDef
		"""
		from webnotes.db.errors import NO_TABLE
		try:
			webnotes.conn.sql("""
				insert into __model_index(name, path, tstamp)
				values (%s, %s, %s)
				on duplicate key 
					update tstamp=%s
			""", (name, path, tstamp, tstamp))
			
		# create the table the first time
		# models are synced for this
		# database
		except Exception, e:
			if e.args[0]==NO_TABLE:
				self.create()
				self.insert(name, path, tstamp)
			else:
				raise e
	
	def create(self):
		webnotes.conn.sql("""
			create table __model_index (
				name varchar(180) primary key not null,
				path varchar(240) unique not null,
				tstamp varchar(20)
			)
		""")