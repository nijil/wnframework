"""
Tests for database creation, schemas etc
"""

import webnotes
from webnotes.model.collection import FileCollection, DatabaseCollection
from webnotes.db.row import DatabaseRow

from webnotes.run_tests import TestCase
from webnotes.db.errors import *

test_model_def = FileCollection(models = [
		{
			'name': 'Temp Sandbox',
			'type': 'ModelDef',
			'path': 'core/temp_sandbox'
		},
		{
			'type':'ModelProperty',
			'fieldname':'test_data',
			'label':'Test Data',
			'fieldtype':'Data'
		},
		{
			'type':'ModelProperty',
			'fieldname':'test_link',
			'label':'Test Link',
			'fieldtype':'Link',
			'options': 'Profile'
		}
	]
)

test_collection = DatabaseCollection(models = [{
	'type': 'Temp Sandbox',
	'test_data': 'test',
	'test_link': 'Guest'
}])

from webnotes.db.table import DatabaseTable

# cleanup from failed tests
try: webnotes.conn.sql("drop table `tabTemp Sandbox`")
except: pass

class TestDbTable(TestCase):
	def setUp(self):
		test_model_def.update()

		self.tab = DatabaseTable(model_def = test_model_def)
		self.tab.create()
		
	def test_creation(self):
		# insert a record
		test_collection.insert()

		self.assertTrue(DatabaseRow('tabTemp Sandbox').read(test_data='test')['test_data']=='test')

	def test_db_add_column(self):
		test_model_def.add_model({
			'doctype':'DocField',
			'fieldname':'test_data``',
			'label':'Test Data``',
			'fieldtype':'Data'
		})
		self.tab.sync()
		test_collection.parent.test_data1 = 'test1'
		test_collection.insert()
		self.assertTrue(DatabaseRow('tabTemp Sandbox').read(test_data1='test1')['test_data1']=='test1')
	
	def test_db_add_index(self):
		test_model_def.get_children(fieldname='test_data')[0].index = 1
		self.tab.sync()
		self.assertTrue(tab.is_indexed('test_data'))
		
	def test_db_drop_index(self):
		test_model_def.get_children(fieldname='test_data')[0].index = 1
		self.tab.sync()
		self.assertTrue(self.tab.is_indexed('test_data'))

		test_model_def.get_children(fieldname='test_data')[0].index = 0
		self.tab.sync()
		self.assertFalse(self.tab.is_indexed('test_data'))
		
	def test_db_add_fkey(self):
		tmp = test_model_def.get_children(fieldname='test_data')[0]
		tmp.fieldtype = 'Link'
		tmp.options = 'Profile'
		self.tab.sync()
		self.assertRaises(test_collection.insert, webnotes.InvalidLinkError)
		self.assertTrue(self.tab.is_indexed('test_data'))
		
	def tearDown(self):
		test_model_def.delete()
		self.tab.drop()
		