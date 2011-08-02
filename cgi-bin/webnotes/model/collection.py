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
	def __init__(self, dt=None, dn=None, models = []):
		self.models = models
		self.obj = None
		self.to_docstatus = 0
		if models:
			self.objectify()

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

	def from_db(self, dt, dn):
		"""
			Load from database
		"""
		from webnotes.model import Document, getchildren

		doc = Document(dt, dn, prefix=prefix)

		# get all children types
		tablefields = webnotes.model.meta.get_table_fields(dt)

		# load chilren
		doclist = [doc,]
		for t in tablefields:
			doclist += getchildren(doc.name, t[0], t[1], dt, prefix=prefix)
		
		self.models = docs

	def from_compressed(self, data, docname):
		"""
			Expand called from client
		"""
		from webnotes.model.utils import expand
		self.models = expand(data)
		self.objectify(docname)
	
	def from_files(self, module):
		"""
			Load collection from files
		"""
		from webnotes.modules import Module
		self.models = Module(module).get_doc_file(self.dt, self.dn).get_collection()
		self.objectify()
	
	def objectify(self, docname=None):
		"""
			Converts self.models from a list of dicts to list of Documents
		"""
		from webnotes.model import get_model
		
		self.models = [get_model(attributes=d) for d in self.models]
		if not docname:
			self.doc, self.children = self.models[0], self.models[1:]

		else:
			self.children = []
			for d in self.models:
				if d.name == docname:
					self.doc = d
				else:
					self.children.append(d)

		# new style called model
		self.model = self.doc
	
	def make_obj(self):
		"""
			Create a DocType object
		"""
		if self.obj: return self.obj
		
		from webnotes.model.code import get_obj
		self.obj = get_obj(doc=self.doc, doclist=self.children)
		return self.obj

	def to_dict(self):
		"""
			return as a list of dictionaries
		"""
		return [d.fields for d in self.models]

	def check_if_latest(self):
		"""
			Raises exception if the modified time is not the same as in the database
		"""
		from webnotes.model.meta import is_single

		if (not is_single(self.doc.doctype)) and (not self.doc.fields.get('__islocal')):
			tmp = webnotes.conn.sql("""
				SELECT modified FROM `tab%s` WHERE name="%s" for update""" 
				% (self.doc.doctype, self.doc.name))

			if tmp and str(tmp[0][0]) != str(self.doc.modified):
				webnotes.msgprint("""
				Document has been modified after you have opened it. 
				To maintain the integrity of the data, you will not be able to save your changes. 
				Please refresh this document. [%s/%s]""" % (tmp[0][0], self.doc.modified), raise_exception=1)

	def check_permission(self):
		"""
			Raises exception if permission is not valid
		"""
		from webnotes.model.permissions import PermissionChecker
		if not PermissionChecker(self.parent).has_perm(verbose=1):
			webnotes.msgprint("Not enough permission to save %s" % self.doc.doctype, raise_exception=1)
		
	def prepare_for_save(self, check_links):
		"""
			Set owner, modified etc before saving
		"""
		self.check_if_latest()
		self.check_permission()

	def run_method(self, method):
		"""
		Run a method and custom_method
		"""
		self.make_obj()
		if hasattr(self.obj, method):
			getattr(self.obj, method)()
		if hasattr(self.obj, 'custom_' + method):
			getattr(self.obj, 'custom_' + method)()

		from webnotes.model.triggers import fire_event
		fire_event(self.doc, method)
				
	def save_main(self):
		"""
			Save the main doc
		"""
		try:
			self.doc.save(cint(self.doc.__islocal))
		except NameError, e:
			webnotes.msgprint('%s "%s" already exists' % (self.doc.doctype, self.doc.name))
			
			# prompt if cancelled
			if webnotes.conn.get_value(self.doc.doctype, self.doc.name, 'docstatus')==2:
				webnotes.msgprint('[%s "%s" has been cancelled]' % (self.doc.doctype, self.doc.name))
			webnotes.errprint(webnotes.utils.getTraceback())
			raise e

	def save_children(self):
		"""
			Save Children, with the new parent name
		"""
		for d in self.children:
			deleted, local = d.fields.get('__deleted',0), d.fields.get('__islocal',0)
	
			if cint(local) and cint(deleted):
				pass

			elif d.fields.has_key('parent'):
				if d.parent and (not d.parent.startswith('old_parent:')):
					d.parent = self.doc.name # rename if reqd
					d.parenttype = self.doc.doctype

				d.save(new = cint(local))		

	def save(self, check_links=1):
		"""
			Save the list
		"""
		self.prepare_for_save(check_links)
		self.run_method('validate')
		self.save_main()
		self.save_children()
		self.run_method('on_update')
		
	def submit(self):
		"""
			Save & Submit - set docstatus = 1, run "on_submit"
		"""
		if self.doc.docstatus != 0:
			msgprint("Only draft can be submitted", raise_exception=1)
		self.to_docstatus = 1
		self.save()
		self.run_method('on_submit')
		
	def cancel(self):
		"""
			Cancel - set docstatus 2, run "on_cancel"
		"""
		if self.doc.docstatus != 1:
			msgprint("Only submitted can be cancelled", raise_exception=1)
		self.to_docstatus = 2
		self.prepare_for_save(1)
		self.save_main()
		self.save_children()
		self.run_method('on_cancel')
		
	def update_after_submit(self):
		"""
			Update after submit - some values changed after submit
		"""
		self.to_docstatus = 1
		self.save_main()
		self.save_children()
		self.run_method('on_update_after_submit')


# for bc
def getlist(doclist, parentfield):
	"""
		Return child records of a particular type
	"""
	import webnotes.model.utils
	return webnotes.model.utils.getlist(doclist, parentfield)
	
def copy_doclist(doclist, no_copy = []):
	"""
		Make a copy of the doclist
	"""
	import webnotes.model.utils
	return webnotes.model.utils.copy_doclist(doclist, no_copy)
	
