# to generate sitemaps

frame_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s
</urlset>"""

link_xml = """\n<url><loc>%s</loc><lastmod>%s</lastmod></url>"""

# generate the sitemap XML
def generate_xml(conn, site_prefix):
	global frame_xml, link_xml
	import urllib

	# settings
	max_doctypes = 10
	max_items = 1000
	
	site_map = ''
	page_list = []
	
	if site_prefix:
		# list of all Records that are viewable by guests (Blogs, Articles etc)
		try:
			from startup.event_handlers import get_sitemap_items
			for i in get_sitemap_items(site_prefix):
				site_map += link_xml % (i[0], i[1])
				('/' in i[0]) and page_list.append(i[0].split('/')[1]) or i[0]
		except ImportError, e:
			pass

		# list of all Guest pages (static content)
		for r in conn.sql("SELECT name, modified FROM tabPage WHERE ifnull(publish,0)=1 ORDER BY modified DESC"):
			#check for double
			if r[0] not in page_list:
				page_url = site_prefix + '#!' + urllib.quote(r[0])
				site_map += link_xml % (page_url, r[1].strftime('%Y-%m-%d'))
		

	return frame_xml % site_map
