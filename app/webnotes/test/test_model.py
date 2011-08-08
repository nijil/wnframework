"""
Tests for model

TODO:

Model

x insert
x read
x update
* delete
* rename

x validate correct links
x validate correct options
x validate mandatory

Collection

x insert
x read
x update
* delete
* rename

* call methods

* validate before delete
* naming series

* tests with children

* submit
* cancel
* custom fields

* permissions
-----------------
* custom property patch (add fieldname)
x reimplement foreign keys
x methods

"""

import unittest
import webnotes

from webnotes.model.collection import DatabaseCollection, FileCollection
from webnotes.model.model import DatabaseModel
from webnotes.db.errors import *

class TestModel(unittest.TestCase):
	def setUp(self):
		from webnotes.model.model_index import get_model_path
		from webnotes.db.table import DatabaseTable

		# create the sandbox table
		sb = FileCollection(get_model_path('Sandbox'))
		self.tab = DatabaseTable(model_def = sb)
		self.tab.create()
		webnotes.conn.begin()

	def get_test_model(self):
		m = DatabaseModel('Sandbox', attributes = {
			'name': 'SB000x',
			'test_data': 'value',
			'test_date': '2011-01-22',
			'test_select': 'A',
			'garbage': 'x'
		})
		return m
		
	def test_insert_db(self):
		"""
			test model insertion
		"""
		m = self.get_test_model()
		m.insert()
		m2 = DatabaseModel('Sandbox',m.name)
		self.assertEquals(m2.test_data, 'value')
	
	def test_upate_db_model(self):

		m = self.get_test_model()
		m.insert()

		m2 = DatabaseModel('Sandbox',m.name)
		m2.test_data = 'new_value'
		m2.update()
		
		self.assertTrue(webnotes.conn.get_value('Sandbox',m.name,'test_data')=='new_value')
				

	def test_read_file_collection(self):
		from webnotes.model.collection import FileCollection
		from webnotes.model.model_index import get_model_path
		
		f = FileCollection(get_model_path('Sandbox'))
		self.assertTrue(f.parent.name=='Sandbox')
		
	def test_insert_db_collection(self):
		dc = DatabaseCollection('Sandbox', models=[self.get_test_model()])
		dc.insert()
		
		dc2 = DatabaseCollection('Sandbox', dc.parent.name)
		self.assertEquals(dc2.parent.test_data, 'value')
		
	def test_update_db_collection(self):

		dc = DatabaseCollection('Sandbox', models=[self.get_test_model()])
		dc.insert()
		
		dc2 = DatabaseCollection('Sandbox', dc.parent.name)
		dc2.parent.test_data = 'new_value'
		dc2.update()
		
		self.assertTrue(webnotes.conn.get_value('Sandbox', dc.parent.name, 'test_data')=='new_value')
		
	def test_validate_bad_link(self):
		dc = DatabaseCollection('Sandbox', models=[self.get_test_model()])
		dc.parent.test_link = 'xxx'
	
		import MySQLdb
		self.assertRaises(MySQLdb.IntegrityError, dc.insert)
			
	def test_validate_bad_options(self):
		dc = DatabaseCollection('Sandbox', models=[self.get_test_model()])
		dc.parent.test_select = 'xxx'
		self.assertRaises(webnotes.InvalidOptionError, dc.insert)

	def test_validate_mandatory(self):
		dc = DatabaseCollection('Sandbox', models=[self.get_test_model()])
		dc.parent.test_data = None
		
		from MySQLdb import OperationalError
		self.assertRaises(OperationalError, dc.insert)
		
	def tearDown(self):
		webnotes.conn.rollback()
		self.tab.drop()
		