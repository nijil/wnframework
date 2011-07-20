# Chai Project 0.1
# (c) 2011 Web Notes Technologies
# Chai Project may be freely distributed under MIT license
# Authors: Rushabh Mehta (@rushabh_mehta)
import webnotes.handler.session
import webnotes
import webnotes.db
import webnotes.utils
import webnotes.profile
import webnotes.defs
class HTTPRequest:
	"""
	Wrapper around HTTPRequest

	- selects database
	- manages session
	- calls "cmd"

	"""
	def __init__(self,reqflds):
		self.cmd = None
		self.database = None
		self.set_env_variables()
		#TODO get rid of self.form, the members of form should be memebers of request itself
		self.form = reqflds
		self.connect_db()
		# write out cookies if sid is supplied (this is a pre-logged in redirect)
		# run login triggers
		#if self.form.get('cmd')=='login':
		#	webnotes.login_manager.run_trigger('on_login_post_session')
		webnotes.conn.commit()
	
	def setup_profile(self):
		"""
			Setup Profile
		"""
		webnotes.user = webnotes.profile.Profile()
		# load the profile data
		if webnotes.session['data'].get('profile'):
			webnotes.user.load_from_session(webnotes.session['data']['profile'])
		else:
			webnotes.user.load_profile()	

	def get_ac_name(self):
		"""
			try to hunt the account name from various places
		"""
		# login
		if webnotes.form_dict.get('acx'):
			return webnotes.form_dict.get('acx')
		
		# in form
		elif self.form.get('ac_name'):
			return webnotes.form_dict.get('ac_name')
			
		# in cookie
		elif webnotes.incoming_cookies.get('ac_name'):
			return webnotes.incoming_cookies.get('ac_name')
			
	def set_cookies(self):
		"""
		Builds cookies dictionary
		"""
		webnotes.cookie_manager = webnotes.handler.session.CookieManager()
		
	def connect_db(self):
		"""
		Selects db
		"""
		# select based on subdomain
		if getattr(webnotes.defs,'domain_name_map', {}).get(self.domain):
			db_name = webnotes.defs.domain_name_map[self.domain]

		# select based on ac_name
		else:
			ac_name = self.get_ac_name()
			if ac_name:
				db_name = getattr(webnotes.defs,'db_name_map',{}).\
					get(ac_name, ac_name)
			else:
				db_name = getattr(webnotes.defs,'default_db_name','')
	
		webnotes.conn = webnotes.db.Database(user = db_name,password = getattr(webnotes.defs,'db_password',''))
		webnotes.ac_name = ac_name
		
	def execute(self):
		"""
			Executes the request specified in "cmd". Action must be a direct
			method call and should be "whitelisted" in the module
		"""
		try:
			module = ''
			cmd = self.form.get('cmd')
			if '.' in cmd:
				module = '.'.join(cmd.split('.')[:-1])
				cmd = cmd.split('.')[-1]
				exec 'from %s import %s' % (module, cmd) in locals()
				ret = locals().get(cmd)()
				webnotes.response['message']=ret

		except webnotes.ValidationError:
			webnotes.conn.rollback()
		except:
			webnotes.errprint(webnotes.utils.getTraceback())
			webnotes.conn and webnotes.conn.rollback()
	def set_env_variables(self):
		"""
			Set environment variables like domain name and ip address
		"""
		self.domain = webnotes.get_env_vars('HTTP_HOST')
		if self.domain and self.domain.startswith('www.'):
			self.domain = self.domain[4:]
		webnotes.remote_ip = webnotes.get_env_vars('REMOTE_ADDR')
		
	def check_status(self):
		"""
			Check session status
		"""
		if webnotes.conn.get_global("__session_status")=='stop':
			webnotes.msgprint(webnotes.conn.get_global("__session_status_message"))
			raise Exception
	def load_session(self):
		"""
			Load the session object
		"""
		webnotes.session_obj = webnotes.handler.session.Session()
		webnotes.session = webnotes.session_obj.data
		webnotes.tenant_id = webnotes.session.get('tenant_id', 0)

	def set_form(self):
		self.form = webnotes.requestform
