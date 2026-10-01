import sys, unittest, tempfile, threading, json, csv
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
sys.path.insert(0, str(Path(__file__).parent))
import app

class UnitTests(unittest.TestCase):
    def test_distribution_and_unique_fixtures(self):
        from collections import Counter
        rows = app.generate(103, list(app.SEGMENTS), 'unit-123')
        self.assertEqual(len(set(r.email for r in rows)), 103)
        counts=Counter(r.segment for r in rows)
        self.assertLessEqual(max(counts.values())-min(counts.values()),1)
        self.assertTrue(all(r.firstname.startswith('TESTE ') and r.email.endswith('@example.com') for r in rows))
        self.assertEqual(app.payload(rows[0])['fields'][-1]['value'], app.SEGMENTS['Recrutador'])
        rows=app.generate(5, ['Curioso'], 'one')
        self.assertEqual({r.segment for r in rows},{'Curioso'})
    def test_invalid(self):
        for total, segments in [(0,['Curioso']), (5001,['Curioso']), (2,[]), (2,['bad'])]:
            with self.assertRaises(ValueError): app.generate(total,segments,'test')

HTML='''<!doctype html><html><head><title>Fixture local</title></head><body><form id="contact-native"><input id="contact-firstname" name="firstname"><input id="contact-lastname" name="lastname"><input id="contact-email" name="email" type="email" required><select id="contact-profile" name="origem_formulario_1"><option value="NC2ztwgcNJTilAoEroC9k">Recrutador</option><option value="Curioso">Curioso</option></select><button type="submit">Enviar</button></form><p id="native-status"></p><div id="contact-success" hidden>Recebido</div><script>document.querySelector('form').addEventListener('submit',async e=>{e.preventDefault();const b=document.querySelector('button');b.disabled=true;try{const f=Object.fromEntries(new FormData(e.target));const r=await fetch('/submit',{method:'POST',body:JSON.stringify(f)});if(r.ok){document.querySelector('#contact-success').hidden=false}else{document.querySelector('#native-status').textContent='Recusado'}}finally{b.disabled=false}})</script></body></html>'''
class Handler(BaseHTTPRequestHandler):
    status=200
    bodies=[]
    def log_message(self,*args): pass
    def do_GET(self):
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(HTML.encode())
    def do_POST(self):
        self.bodies.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        self.send_response(self.status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b'{"errors":[{"errorType":"BLOCKED_EMAIL"}]}')

class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()
        app.SITE=f'http://127.0.0.1:{cls.server.server_port}/beta'
        app.ENDPOINT=f'http://127.0.0.1:{cls.server.server_port}/submit'
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def setUp(self):Handler.bodies=[];Handler.status=200
    def run_fixture(self,preview=False):
        events=[]
        with tempfile.TemporaryDirectory() as folder:
            app.run_batch(app.generate(3,['Recrutador','Curioso'],'local-test'),'local-test',preview,threading.Event(),lambda k,v:events.append((k,v)),folder=Path(folder))
            with open(Path(folder)/'lote-local-test.csv',encoding='utf-8-sig') as result:
                report=list(csv.DictReader(result,delimiter=';'))
        return events,report
    def test_visible_then_api(self):
        events,report=self.run_fixture()
        self.assertEqual(len(Handler.bodies),3)
        self.assertIn('firstname',Handler.bodies[0])
        self.assertIn('fields',Handler.bodies[1])
        self.assertEqual([r['status'] for r in report],['aceito']*3)
    def test_preview_has_no_requests(self):
        events,report=self.run_fixture(True)
        self.assertEqual(Handler.bodies,[])
        self.assertEqual([r['status'] for r in report],['prévia']*3)
    def test_first_failure_stops_batch(self):
        Handler.status=400
        events,report=self.run_fixture()
        self.assertEqual(len(Handler.bodies),1)
        self.assertEqual(report[0]['status'],'recusado')
    def test_http_failure_and_rate(self):
        for status, expected in [(400,'recusado'),(429,'limite')]:
            Handler.status=status
            self.assertEqual(app.send_http(app.generate(1,['Curioso'],'http')[0])[0], expected)

if __name__=='__main__':unittest.main(verbosity=2)
