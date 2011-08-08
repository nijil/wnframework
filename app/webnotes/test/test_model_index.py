"""
	Tests for model indexer.
"""

from webnotes.run_tests import TestCase
from webnotes.model.model_index import ModelIndex, get_model_path

from webnotes.model.collection import FileCollection
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

class TestModelIndex(TestCase):
	def setUp(self):
		# No begin
		pass
		
	def write_model(self):
		test_model_def.update()
		
	def test_add_model(self):
		# write a new model
		self.write_model()

		ModelIndex().index_all()
		
		# read it into collection
		from webnotes import app_path
		import os
		fc = FileCollection(os.path.join(app_path, 'core/temp_sandbox/temp_sandbox.model'))
		
		self.assertTrue(fc.path == get_model_path('Temp Sandbox'))
	
		# delete it
		test_model_def.delete()
		

