# Chai Project 0.1
# (c) 2011 Web Notes Technologies
# Chai Project may be freely distributed under MIT license
# Authors: Rushabh Mehta (@rushabh_mehta)

import webnotes

class HTMLPage:
	"""
		Builds the HTML page with
		1. linked .css and .js files
		2. page metadata
		3. bootstrap info (session, core)
		4. page content (if loaded using _escaped_fragment_)
	"""
	
	def __init__(self, template='Standard'):
		self.template = template
		self.html = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">\n<html>%s\n</html>'''
		self.title = 'App'
		self.boot_js = ''
		self.site_description = ''
		self.keywords = ''
		self.content = '\n<!-- Content to be generated by Javascript -->'
		
		# templates of HTML pages
		self.templates = {
			# test version
			'Standard': {
				'css': [
					'css/jquery-ui.css',
					'css/default.css'
				],
				'js': [
				'js/jquery/jquery.min.js',
				'js/jquery/jquery-ui.min.js',
				'js/tiny_mce_33/jquery.tinymce.js',
				'js/wnf.compressed.js',
				'js/form.compressed.js'
				]
			}
		}
	
	def get_render_page(self):
		"""
			Return the [doctype, name] of object to render
		"""
		
		page_url = webnotes.request._escaped_fragment_ or  webnotes.request.page or ''

		if page_url:
			import urllib
			if page_url.startswith('Page/'): 
				page_url = page_url[5:]
			page_url = ['Page', urllib.unquote(page_url)]
		else:
			page_url = ['Page', webnotes.user.get_home_page()]
		
		return page_url

	def load(self):
		"""
			Load the page on basis of given parameters
		"""

		page_url = self.get_render_page()
		if page_url[0] == 'Page':
			self.load_page(page_url[1])

		if not self.site_description:
			self.site_description = webnotes.conn.get_value('Control Panel',None,'site_description')

		if not self.keywords:
			self.keywords = webnotes.conn.get_value('Control Panel',None,'keywords')
	
	def get_page_content(self, doc):
		"""
			Get HTML page content, from template if set
		"""
		
		# content
		from webnotes.model.code import get_code, execute

		template = '%(content)s'
		if doc.template:
			template = get_code(webnotes.conn.get_value('Page Template', doc.template, 'module'), 'Page Template', doc.template, 'html', fieldname='template')

		self.content = get_code(doc.module, 'page', doc.name, 'html', fieldname='content') or ''

		# dynamic (scripted) content
		if self.content.startswith('#!python'):
			self.__dict__.update(webnotes.model.code.execute(self.content))

		self.content = scrub_ids(template % {'content': self.content})
			
	def load_page(self, page):
		"""
			Load page meta tags and content
		"""
		
		from webnotes.model.doc import Document

		if not page: return
		if '/' in page: page = page.split('/')[0]
		if page=='Form': return

		try:
			doc = Document('Page', page)
		except:
			return
		
		self.keywords = doc.keywords
		self.site_description = doc.site_description
		self.title = doc.title

		self.get_page_content()

	def load_session(self):
		"""
			Load session data
		"""
		import json
		import webnotes.session_cache

		try:
			sd = webnotes.session_cache.get()
		except:
			import webnotes.utils
			sd = {'exc':webnotes.utils.getTraceback()}
		
		# add debug messages
		sd['server_messages'] = '\n--------------\n'.join(webnotes.message_log)
		
		self.boot_js = webnotes.request.no_startup and '{}' or json.dumps(sd)

	def ele(self, tag_name, attributes, content):
		"""
			Render an html element
		"""
		
		al = []
		for key in attributes:
			al.append('%s="%s"' % (key, attributes[key]))
		out = '<%s %s>' % (tag_name, ' '.join(al))
		if content == None:
			content = ''
		return out + content + ('</%s>' % tag_name)
		
	def render(self):
		"""
			Render the page
		"""
		# load page info
		self.load()
		
		# load boot js
		self.load_session()
		
		# build the html
		return self.html % (self.get_head() + self.get_body())
		
		
	def get_head(self):
		"""
			Get <head>
		"""
		
		head = '\n<head>\n%s\n</head>'
		return head % (self.get_meta() + self.get_links() + self.get_scripts())

	def get_meta(self):
		"""
			Get <meta>
		"""
		
		ml = []
		ml.append(self.ele('meta', {'http-equiv':'Content-Type', 'content':'text/html; charset=UTF-8'}, None))
		
		# stuff for Search Engines
		ml.append(self.ele('meta', {'robots':'index, follow'}, None))
		
		# keywords
		if self.keywords:
			ml.append(self.ele('meta', {'keywords': self.keywords}, None))
		
		# description
		if self.site_description:
			ml.append(self.ele('meta', {'description': self.site_description}, None))
		
		# generator
		ml.append(self.ele('meta', {'generator':'wnframework: https://github.com/webnotes/wnframework'}, None))
		return '\n'.join(ml)

	def get_links(self):
		"""
			Get <links> for css
		"""
		
		css = self.templates[self.template].get('css')
		cl = []
		for i in css:
			cl.append(self.ele('link', {'type':'text/css', 'rel':'stylesheet', 'href':i}, None))
		
		return '\n\n<!-- style -->\n' + '\n'.join(cl)

	def get_scripts(self):
		"""
			Get <script> for js libraries
		"""
		scripts = self.templates[self.template].get('js')
		sl = []
		for i in scripts:
			sl.append(self.ele('script', {'language':'Javascript', 'type':'text/javascript', 'src':i}, ''))

		if self.boot_js:
			sl.append('\n<!-- bootstrap -->')
			sl.append(self.ele('script', {'language':'Javascript'}, 'var _startup_data = ' + self.boot_js))

		return '\n\n<!-- scripts -->\n' + '\n'.join(sl)

	def get_body(self):
		"""
			Get <body>
		"""
		return "\n<body>\n%s%s\n</body>" % (self.get_boot_eles() , self.content)
	
	def get_boot_eles(self):
		eles = []
		eles.append(self.ele('div', {'id' : 'dialog_back'}, None))
		eles.append(self.ele('div', { 'id' : 'startup_div'}, None))
		eles.append(self.ele('div', { 'id' : 'body_div'},
			'\n' + self.ele('div',{'class' : 'no_script'}, None)))
		return '\n'.join(eles)

def redirect():
	"""
		Redirect to self (to hide session id "sid" from the url)
	"""
	page = webnotes.request.page or ''
	return '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
	<html>
	<head>
	<title>Redirecting...</title>
	<meta http-equiv="REFRESH" content="0; url=%s"></HEAD>
	<BODY style="font-family: Arial; padding: 8px; font-size: 14px; margin: 0px;">
	Redirecting...
	</BODY>
	</HTML>''' % ('index.cgi' + (page and ('?page='+page) or ''))

def build(template = 'Standard'):
	"""
		Get the HTML content for "index.cgi". If a "sid" form property is set
		then it will return HTML to redirect to self without the sid, so that
		the sid remains hidden to the user
	"""
	
	webnotes.response.headers['Content-Type'] = 'text/html'

	if webnotes.request.sid: 
		webnotes.response.content = redirect()
		return
	webnotes.response.pagehtml= HTMLPage(template).render()
