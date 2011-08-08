"""
Transactions are defined as collection of classes, a Collection represents collection of Document
objects for a transaction with main and children.

Group actions like save, etc are performed on collections
"""

import webnotes
from webnotes.utils import cint

class Collection:
	"""
	Collection of Documents with one parent and multiple children
	"""
	models = []
	children = []
	to_docstatus = 0
	obj = None
	
	def __init__(self, mtype=None, name=None, models=[]):
		self.type = mtype
		self.name = name
		if models:
			if type(models[0])==dict:
				models = self.objectify(models)

			self.set_models(models)

	def __iter__(self):
		"""
			Make this iterable
		"""
		return self.models.__iter__()

	def next(self):
		"""
			Next doc
		"""
		return self.models.next()


	def from_compressed(self, data, docname):
		"""
			Expand called from client
		"""
		from webnotes.model.utils import expand
		self.models = expand(data)
		
	def set_models(self, models, docname=None):
		"""
			Split models into parent and children
		"""
		self.models = models
		if not docname:
			self.parent = self.models[0]
			self.children = self.models[1:]

		else:
			self.children = []
			for d in self.models:
				if d.name == docname:
					self.parent = d
				else:
					self.children.append(d)

	def get_models(self, **args):
		"""
			Return models filtered by args
		"""
		# copy the children list
		fl = [c for c in self.models]
		
		# filter for each argument
		if args:
			for key in args:
				fl = filter(lambda x: x.get(key)==args[key], fl)
		
		return fl
	
	def add_model(self, m):
		"""
			Objectify and add a new child model to `models` and `children`
		"""
		if type(m)==dict:
			m = self.objectify([m])[0]
		self.children.append(m)
		self.models.append(m)
	
	def delete_model(self, **args):
		"""
			Remove models from the list
		"""
		cl = []
		for c in self.children:
			for key in args:
				if c.get(key) != args[key]:
					cl.append(c)
				elif getattr(c, 'delete'):
					c.delete()
		
		self.children = cl
		self.models = [self.parent] + cl


	def rename_parent_in_children(self):
		"""
			parent may have a new name after insert
		"""
		for c in self.children:
			if c.parent and (not c.parent.startswith('old_parent:')):
				c.parent = self.parent.name
				c.parenmtype = self.parent.type

	def to_dict(self, with_type=None):
		"""
			return as a list of dictionaries
		"""
		return [d.get_values(with_type) for d in self.models]

	def set_name(self):
		"""
			Set name (id) for this record
		"""

		from webnotes.model.naming import NamingControl
		self.parent.load_def()
		NamingControl(self).set_name()
		self.rename_parent_in_children()

	def check_if_latest(self):
		"""
			Raises exception if the modified time is not the same as in the database
		"""
		tmp = webnotes.conn.get_value(self.parent.type, self.parent.name, 'modified')

		if str(tmp) != str(self.parent.modified):
			webnotes.msgprint("""
			This Document has been modified after you have opened it. 
			To maintain the integrity of the data, you will not be able to save your changes. 
			Please refresh this document. [%s/%s]""" % (tmp, self.parent.modified), raise_exception=1)

	def check_permission(self):
		"""
			Raises exception if permission is not valid
		"""
		from webnotes.model.permissions import PermissionChecker
		if not PermissionChecker(self.parent).has_perm(verbose=1):
			webnotes.msgprint("Not enough permission to save %s" % self.parent.type, raise_exception=1)
	
	def update_docstatus(self):
		"""
			Update docstatus before update
		"""
		for m in self.models:
			if m.docstatus != 2: m.docstatus = self.to_docstatus

	def remove_local_and_deleted(self):
		"""
			remove local and deleted children
		"""
		for i in range(len(self.children)):
			c = self.children[i]
			if cint(c.__islocal) and cint(c.__deleted):
				del self.children[i]

	def load_controller(self):
		"""
			Add the controller object
		"""
		if hasattr(self, 'controller'):
			return
			
		# load parent ModelDef (so that we can get the controller path)
		self.parent.load_def()
			
		from webnotes.model.controller import ControllerFactory
		ControllerFactory(self).set()

	def run_method(self, method):
		"""
			Run a method and fire triggers
		"""
		self.load_controller()
		
		ret = None
		if hasattr(self, 'controller'):
			if hasattr(self.controller, method): 
				ret = getattr(self.controller, method)()
				
		from webnotes.model.triggers import fire_event
		fire_event(self.parent, method)
		
		return ret
	
	def pre_insert(self):
		"""
			Check permission
		"""
		if not self.parent.name:
			self.set_name()
		self.check_permission()
		self.run_method('validate')
		self.remove_local_and_deleted()

	def post_insert(self):
		"""
			Run on_update after insert
		"""
		self.run_method('on_update')

	def pre_update(self):
		"""
			Run update
		"""
		self.check_if_latest()
		self.check_permission()
		self.run_method('validate')
		self.update_docstatus()
		self.remove_local_and_deleted()

	def post_update(self):
		"""
			Run on_udpate
		"""
		self.run_method('on_update')

	def save(self):
		if self.parent.__islocal:
			self.insert()
		else:
			self.update()

	def submit(self):
		"""
			Save & Submit - set docstatus = 1, run "on_submit"
		"""
		if self.doc.docstatus != 0:
			msgprint("Only draft can be submitted", raise_exception=1)
		self.to_docstatus = 1
		self.update()
		self.run_method('on_submit')
		
	def cancel(self):
		"""
			Cancel - set docstatus 2, run "on_cancel"
		"""
		if self.doc.docstatus != 1:
			msgprint("Only submitted can be cancelled", raise_exception=1)
		self.to_docstatus = 2
		self.update()
		self.run_method('on_cancel')
		
	def update_after_submit(self):
		"""
			Update after submit - some values changed after submit
		"""
		self.to_docstatus = 1
		self.update()
		self.run_method('on_update_after_submit')


class DatabaseCollection(Collection):
	"""
		Collection stored in files
	"""
	def __init__(self, mtype=None, name=None, models=[]):
		Collection.__init__(self, mtype, name, models)

		# autoread
		if mtype and name and not models:
			self.read()
			
		# only mtype supplied, set as new
		elif mtype and not name and not models:
			from webnotes.model.model import DatabaseModel
			self.parent = DatabaseModel(mtype)

	def objectify(self, models):
		"""
			Convert dicts to `DatabaseModel`
		"""
		from webnotes.model.model import DatabaseModel
		return [DatabaseModel(attributes=d) for d in models]

	def read(self):
		"""
			Read from db
		"""
		from webnotes.model.model import DatabaseModel
		
		# read parent
		parent = DatabaseModel(self.type, self.name)
		parent.read()
		models = [parent]

		# read children
		tables = parent.get_properties(fieldtype='Table')

		for t in tables:
			data = webnotes.conn.sql("select * from `tab%s` where parent=%s and parenmtype=%s and parentfield=%s" \
				% (t.options, '%s', '%s', '%s'), (parent.name, parent.type, t.fieldname), as_dict=1)
			for d in data:
				models.append(DatabaseModel(t.options, d.name, attributes=d))
		
		self.set_models(models)
		
	def insert(self):
		"""
			Insert collection
		"""
		self.pre_insert()
		self.parent.insert()
		for c in self.children:
			c.insert()
		self.post_insert()

	def update(self):
		"""
			Insert collection
		"""
		self.pre_update()
		self.parent.update()
		for c in self.children:
			c.update()
		self.post_update()

class FileCollection(Collection):
	"""
		Collection stored in files
	"""
	def __init__(self, path=None, mtype=None, name=None, models= None):
		self.path = path

		# load from given dict type models
		Collection.__init__(self, mtype=mtype, name=name, models=models)

		# autoread
		if path and not models:
			self.read()

	def objectify(self, models):
		"""
			Convert dicts to `Model`
		"""
		from webnotes.model.model import Model
		return [Model(attributes=d) for d in models]
		
	def read(self):
		"""
			Load collection from files
		"""
		from webnotes.model.model import Model
		from webnotes.model.utils import peval_collection
		
		if self.path:
			f = file(self.path, 'r')
			self.set_models([Model(attributes=m) for m in peval_collection(f.read())])
			f.close()
	
	def get_parent_folder(self):
		"""
			Returns the folder of the parent model
		"""
		import os
		from webnotes import app_path
		return os.path.join(app_path, self.parent.path)
	
	def get_parent_path(self):
		"""
			returns the full path of the collection (via parent model)
		"""
		import os
		from webnotes.utils import scrub
		
		return os.path.join(self.get_parent_folder(), scrub(self.parent.name) + '.model')
		
	def insert(self):
		"""
			Export the file collection
		"""
		from webnotes.model.utils import pprint_collection
		from webnotes.utils import create_folder
		
		create_folder(self.get_parent_folder())
		
		f = file(self.get_parent_path(), 'w')
		f.write(pprint_collection(self.to_dict(with_type=1)))
		f.close()
		
	def update(self):
		"""
			Export to file collection
		"""
		self.insert()
		
	def delete(self):
		"""
			Delete file
		"""
		import os
		os.remove(self.path or self.get_parent_path())

