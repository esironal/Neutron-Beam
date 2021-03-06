import os
import re
import base64
import json

from tornado.web import RequestHandler, StaticFileHandler, HTTPError
from tornado.escape import json_encode, json_decode

from .SimpleAES import SimpleAES
from .views  import list_dir, open_file, save_file, rename_file, delete, new_file, new_dir, upload_file, new_url, token, token_valid, create_realtime, stop_realtime
from .views_search import start_search, start_replace, job_status, cancel_job
from .version import VERSION_STRING

class StaticHandler (StaticFileHandler):
  def get (self, path, include_body=True):
    reobj = re.search('/(\S+)/public/(.*)', self.request.path)
    token = reobj.group(1)
    if token_valid(token):
      return super(StaticHandler, self).get(path, include_body)
      
    raise HTTPError(404)
    
class MainHandler (RequestHandler):
  def __init__ (self, *args, **kwargs):
    self.config = args[0].config
    self.aes = SimpleAES(args[0].config['key'])
    self.ALLOWED_TASKS = {
      'list': list_dir,
      'open': open_file,
      'save': save_file,
      'rename': rename_file,
      'delete': delete,
      'newfile': new_file,
      'newdir': new_dir,
      'upload': upload_file,
      'newurl': new_url,
      'search': start_search,
      'replace': start_replace,
      'jobstatus': job_status,
      'canceljob': cancel_job,
      'token': token,
      'createRealtime': create_realtime,
      'stopRealtime': stop_realtime,
    }
    
    super(MainHandler, self).__init__(*args, **kwargs)
    
  def valid_request (self, rdata):
    if rdata['task'] in self.ALLOWED_TASKS:
      if rdata['email'].lower() == self.config['email'].lower():
        path = None
        if 'file' in rdata:
          path = rdata['file']
          
        elif 'dir' in rdata:
          path = rdata['dir']
          
        if path:
          path = os.path.normpath(self.config['dir'] + path)
          if path.startswith(self.config['dir']):
            return True
            
        return True
        
    return False
    
  def options (self):
    self.set_header('Access-Control-Allow-Origin', '*')
    self.set_header('Access-Control-Allow-Headers', 'X-CSRFToken')
    self.set_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
    
  def post (self):
    data = {'status': 'Invalid Request'}
    self.set_header('Content-Type', 'application/json')
    self.set_header('Access-Control-Allow-Origin', '*')
    
    rdata = self.get_argument("request", '')
    try:
      test = base64.decodestring(rdata)
      rdata = self.aes.decrypt(rdata)
      rdata = json_decode(rdata)
      
    except:
      pass
    
    else:
      if self.valid_request(rdata):
        rdata['REMOTE_IP'] = self.request.remote_ip
        response_data = self.ALLOWED_TASKS[rdata['task']](self.config, rdata)
        
        data = {
          'response': response_data,
          'email': self.config['email'],
        }
        
        j = json_encode(data)
        data = {
          'encrypted': self.aes.encrypt(j),
          'beam': rdata['beam'],
          'status': 'ok',
          'version': VERSION_STRING,
        }
        
    j = json_encode(data)
    self.write(j)
    self.finish()
    