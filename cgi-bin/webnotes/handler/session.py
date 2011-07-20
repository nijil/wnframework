import webnotes
import webnotes.db
import webnotes.utils
import webnotes.profile
import webnotes.defs
#TODO Put Docsrtings here
class LoginManager:
	def __init__(self,request,response):
		self.cp = None
		self.request = request
		if request.cmd = 'login':
			# clear cache
			from webnotes.session_cache import clear_cache
			clear_cache(request.usr)				

			self.authenticate()
			self.post_login()
			response['message'] = 'Logged In'

	
	def post_login(self):
	"""
	run triggers, write cookies
	"""
		self.validate_ip_address()
		self.run_trigger()
	
	
	def authenticate(self, user=None, pwd=None):
		"""
		check password
		"""
		if not (user and pwd):	
			user, pwd = self.request.usr, self.request.pwd

		if not (user and pwd):
			webnotes.msgprint('Incomplete Login Details', raise_exception=1)
		
		# custom authentication (for single-sign on)
		self.load_control_panel()
		if hasattr(self.cp, 'authenticate'):
			self.user = self.cp.authenticate()
		
		# check the password
		if user=='Administrator':
			p = webnotes.conn.sql("select name from tabProfile where name=%s and (`password`=%s OR `password`=PASSWORD(%s))", (user, pwd, pwd))
		else:
			p = webnotes.conn.sql("select name from tabProfile where name=%s and (`password`=%s  OR `password`=PASSWORD(%s)) and IFNULL(enabled,0)=1", (user, pwd, pwd))
			
		if not p:
			webnotes.msgprint('Authentication Failed', raise_exception=1)
			
		self.user = p[0][0]
	
	
	def load_control_panel(self):
		import webnotes.model.code
		try:
			if not self.cp:
				self.cp = webnotes.model.code.get_obj('Control Panel')
		except Exception, e:
			self.response['Control Panel Exception'] = webnotes.utils.getTraceback()
	
	def run_trigger(self, method='on_login'):
		"""
		triggers
		"""
		try:
			from startup import event_handlers
			if hasattr(event_handlers, method):
				getattr(event_handlers, method)(self)
			return
		except ImportError, e:
			pass
	
		# deprecated
		self.load_control_panel()
		if self.cp and hasattr(self.cp, method):
			getattr(self.cp, method)(self)

	
	def validate_ip_address(self):
		"""
		ip validation
		"""
		try:
			ip = webnotes.conn.sql("select ip_address from tabProfile where name = '%s'" % self.user)[0][0] or ''
		except: return
			
		ip = ip.replace(",", "\n").split('\n')
		ip = [i.strip() for i in ip]
			
		if ret and ip:
			if not (webnotes.remote_ip.startswith(ip[0]) or (webnotes.remote_ip in ip)):
				raise Exception, 'Not allowed from this IP Address'	
	
	def login_as_guest(self):
		"""
		login as guest
		"""

		res = webnotes.conn.sql("select name from tabProfile where name='Guest' and ifnull(enabled,0)=1")
		if not res:
			raise Exception, "No Guest Access"
		self.user = 'Guest'
		self.post_login()

	def call_on_logout_event(self):
		import webnotes.model.code
		cp = webnotes.model.code.get_obj('Control Panel', 'Control Panel')
		if hasattr(cp, 'on_logout'):
			cp.on_logout(self)

	def logout(self, arg=''):
		self.run_trigger('on_logout')
		webnotes.conn.sql('update tabSessions set status="Logged Out" where sid="%s"' % webnotes.session['sid'])
		

class CookieManager:
	def __init__(self,request):
		import Cookie
		self.cookies = Cookie.SimpleCookie()
		self.get_incoming_cookies()
		self.request = request

	def get_incoming_cookies(self):
		import os
		cookies = {}
		if 'HTTP_COOKIE' in os.environ:
			c = os.environ['HTTP_COOKIE']
			self.cookies.load(c)
			for c in self.cookies.values():
				cookies[c.key] = c.value
					
		webnotes.incoming_cookies = cookies
		
	
	def set_cookies(self):
		if webnotes.conn.cur_db_name:
			self.cookies['account_id'] = webnotes.conn.cur_db_name
		
		# ac_name	
		self.cookies['ac_name'] = webnotes.ac_name or ''
		
		#FIXME
		if webnotes.session.get('sid'): 
			self.cookies['sid'] = webnotes.session['sid']

			# sid expires in 3 days
			import datetime
			expires = datetime.datetime.now() + datetime.timedelta(days=3)

			self.cookies['sid']['expires'] = expires.strftime('%a, %d %b %Y %H:%M:%S')		


	def set_remember_me(self):
		if webnotes.utils.cint(self.request.remember_me):
			remember_days = webnotes.conn.get_value('Control Panel',None,'remember_for_days') or 7
			self.cookies['remember_me'] = 1

			import datetime
			expires = datetime.datetime.now() + datetime.timedelta(days=remember_days)

			for k in self.cookies.keys():
				self.cookies[k]['expires'] = expires.strftime('%a, %d %b %Y %H:%M:%S')	


class Session:
	def __init__(self, request, user=None):
		self.user = user
		self.request = request
		self.sid = request.sid or webnotes.incoming_cookies.get('sid')
		self.data = {'user':user,'data':{}}

		if request.cmd='login':
			self.start()
			return
			
		self.load()
	
	# start a session
	# ---------------
	def load(self):
		import webnotes
		
		r=None
		try:
			r = webnotes.conn.sql("select user, sessiondata, status from tabSessions where sid='%s'" % self.sid)
		except Exception, e:
			if e.args[0]==1054:
				self.add_status_column()
			else:
				raise e
	
		if r:
			r=r[0]
			
			# ExipredSession
			if r[2]=='Expired' and (self.request.cmd=='resume_session'):
				if r[0]=='Guest' or (not self.request.cmd or self.request.cmd=='logout':
					webnotes.login_manager.login_as_guest()
					self.start()
				else:
					webnotes.response['session_status'] = 'Session Expired'
					raise Exception, 'Session Expired'
			elif r[2]=='Logged Out':
				webnotes.login_manager.login_as_guest()
				self.start()
				# allow refresh or logout
				if self.request.cmd and self.request.cmd!='logout':
					webnotes.response['session_status'] = 'Logged Out'
					raise Exception, 'Logged Out'
			else:
				self.data = {'data':eval(r[1]), 'user':r[0], 'sid': self.sid}
		else:				
			webnotes.login_manager.login_as_guest()
			self.start()
			

	# start a session
	# ---------------
	def start(self):
		import os
		import webnotes
		import webnotes.utils
		
		# generate sid
		self.data['user'] = webnotes.login_manager.user
		self.data['sid'] = webnotes.utils.generate_hash()
		self.data['data']['session_ip'] = os.environ.get('REMOTE_ADDR');
		self.data['data']['tenant_id'] = self.request.tenant_id

		# get ipinfo
		if webnotes.conn.get_global('get_ip_info'):
			self.get_ipinfo()
		
		# insert session
		try:
			self.insert_session_record()
		except Exception, e:
			if e.args[0]==1054:
				self.add_status_column()
				self.insert_session_record()
			else:
				raise e

		# update profile
		webnotes.conn.sql("UPDATE tabProfile SET last_login = '%s', last_ip = '%s' where name='%s'" % (webnotes.utils.now(), webnotes.remote_ip, self.data['user']))

		# set cookies to write
		webnotes.session = self.data
		webnotes.cookie_manager.set_cookies()


	# resume session
	# --------------
	def resume(self):
		pwd = self.request.pwd
		webnotes.login_manager.authenticate(self.data['user'], pwd)
		webnotes.conn.sql("update tabSessions set status='Active' where sid=%s", self.data['sid'])
		return 'Logged In'
	
	# update session
	# --------------
	def update(self):
		# update session
		webnotes.conn.sql("update tabSessions set sessiondata=%s, user=%s, lastupdate=NOW() where sid=%s" , (str(self.data['data']), self.data['user'], self.data['sid']))	

		self.check_expired()

	# check expired
	# -------------
	def check_expired(self):
		# in control panel?
		exp_sec = webnotes.conn.get_value('Control Panel', None, 'session_expiry') or '6:00:00'
		
		# set sessions as expired
		try:
			webnotes.conn.sql("update from tabSessions where TIMEDIFF(NOW(), lastupdate) > %s SET `status`='Expired'", exp_sec)
		except Exception, e:
			if e.args[0]==1054:
				self.add_status_column()
		
		# clear out old sessions
		webnotes.conn.sql("delete from tabSessions where TIMEDIFF(NOW(), lastupdate) > '72:00:00'")

	# -----------------------------
	def add_status_column(self):
		webnotes.conn.commit()
		webnotes.conn.sql("alter table tabSessions add column `status` varchar(20)")
		webnotes.conn.begin()


	# Get IP Info from ipinfodb.com
	# -----------------------------
	def get_ipinfo(self):
		import os
		
		try:
			import pygeoip
		except:
			return
		
		gi = pygeoip.GeoIP('data/GeoIP.dat')
		self.data['data']['ipinfo'] = {'countryName': gi.country_name_by_addr(os.environ.get('REMOTE_ADDR'))}
			
	# -----------------------------
	def insert_session_record(self):
		webnotes.conn.sql("insert into tabSessions (sessiondata, user, lastupdate, sid, status) values (%s , %s, NOW(), %s, 'Active')", (str(self.data['data']), self.data['user'], self.data['sid']))
		
