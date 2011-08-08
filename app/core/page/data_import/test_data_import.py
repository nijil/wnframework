"""
Tests for data import.

TODO

- test for overwrite
- test for update
"""

import unittest
import webnotes
from core.page.data_import.data_import import ImportCSV

class TestDataImport(unittest.TestCase):
	def setUp(self):
		webnotes.conn.begin()

	def test_extract_columns(self):
		"extract columns"
		csv = ImportCSV(test_csv, 'Sandbox')
		self.assertEquals(csv.get_columns(), ['C1', 'C2', 'C3', 'C4'])
	
	def test_date_fields(self):
		"check if date fields are interpreted correctly"
		csv = ImportCSV(test_csv_date, 'Sandbox', mapper = test_map)
		csv.imp()
		self.assertEquals(csv.data[0].test_date, '2011-01-22')
	
	def test_with_custom_fields(self):
		"test if custom validations are done"
		csv = ImportCSV(test_csv_custom, 'Sandbox', mapper = test_map)
		self.assertRaises(csv.imp(), webnotes.OptionsError)
		
	def test_success(self):
		"test if the data is imported"
		from webnotes.model.model import DatabaseModel
		csv = ImportCSV(test_csv, 'Sandbox', mapper = test_map)
		d1 = DatabaseModel('Sandbox','test1')
		d2 = DatabaseModel('Sandobx','test2')
		self.assertTrue(d1.test_data=='A' and d1.test_date=='2011-01-22' and d1.test_link=='Administrator')
		self.assertTrue(d1.test_data=='B' and d1.test_date=='2011-01-23' and d2.test_link=='Guest')
		
	def tearDown(self):
		webnotes.conn.rollback()

test_map = [
	'Test Data',
	'Test Date',
	'Test Link',
	'Test Select'
]

test_csv = '''C1,C2,C3,C4
T1,2011-01-22,'Administrator','A'
T2,2011-01-23,'Guest','B'
'''

test_csv_link = '''C1,C2,C3,C4
T1,2011-01-22,'Administrator','A'
T2,2011-01-23,'xxx','B'
'''

test_csv_option = '''C1,C2,C3,C4
T1,2011-01-22,'Administrator','A'
T2,2011-01-23,'Guest','X'
'''

test_csv_option = '''C1,C2,C3,C4
T1,2011-01-22,'Administrator','A'
T2,2011-01-23,'Guest','X'
'''
