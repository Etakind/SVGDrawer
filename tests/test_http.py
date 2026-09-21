"""Real HTTP boundary tests, including loopback-only access and PNG dimensions."""
import json
from pathlib import Path
import struct
import sys
import threading
import unittest
import urllib.request
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from http.server import ThreadingHTTPServer
from server import Handler, cairosvg
from build import build

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build();cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def fetch(self,path,payload=None,headers=None):
        h={'Content-Type':'application/json'};h.update(headers or {})
        request=urllib.request.Request(self.url+path,data=None if payload is None else json.dumps(payload).encode(),headers=h)
        try:
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request,timeout=15) as r:return r.status,r.headers,r.read()
        except urllib.error.HTTPError as e:return e.code,e.headers,e.read()
    def test_health_and_html(self):
        code,headers,body=self.fetch('/api/health');self.assertEqual(code,200);self.assertEqual(json.loads(body)['app'],'svgdrawer')
        code,headers,body=self.fetch('/');self.assertEqual(code,200);self.assertIn(b'Find your next',body);self.assertIn(b'bootData',body)
        self.assertNotIn(b'__BOOT_DATA__',body)
    def test_svg(self):
        code,headers,body=self.fetch('/api/render',{'action':'export','asset':{'type':'chip'}})
        self.assertEqual(code,200);self.assertIn('<svg',json.loads(body)['svg'])
    def test_error_responses(self):
        self.assertEqual(self.fetch('/missing')[0],404)
        self.assertEqual(self.fetch('/api/render',[])[0],400)
        self.assertEqual(self.fetch('/api/render',{'asset':{'type':'missing'}})[0],400)
        self.assertEqual(self.fetch('/api/render',{},headers={'Content-Type':'text/plain'})[0],415)
    def test_remote_origins_and_hosts_rejected(self):
        self.assertEqual(self.fetch('/api/health',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.fetch('/api/render',{'asset':{'type':'chip'}},headers={'Origin':'https://evil.example'})[0],403)
    @unittest.skipIf(cairosvg is None,'Optional CairoSVG is not installed')
    def test_python_png(self):
        code,headers,body=self.fetch('/api/png',{'asset':{'type':'chip'},'options':{'width':300,'height':200},'scale':2})
        self.assertEqual(code,200);self.assertEqual(body[:8],b'\x89PNG\r\n\x1a\n');self.assertEqual(struct.unpack('>II',body[16:24]),(600,400))
        self.assertEqual(self.fetch('/api/png',{'asset':{'type':'chip'},'options':{'width':4096,'height':4096},'scale':4})[0],400)

if __name__=='__main__':unittest.main()
