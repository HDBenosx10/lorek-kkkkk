import unittest, tempfile, threading, json, sys, csv
from pathlib import Path
from collections import Counter
from unittest.mock import patch
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, str(Path(__file__).parent))
import engine as e


class CoreTests(unittest.TestCase):
    def test_distribution(self):
        c = e.Config()
        rows = e.generate(103, list(c.options), "test", c)
        counts = Counter(r.segment for r in rows)
        self.assertEqual(len(set(r.email for r in rows)), 103)
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)
        self.assertTrue(
            all(
                r.firstname.startswith("TESTE ") and r.email.endswith("@example.com")
                for r in rows
            )
        )

    def test_invalid(self):
        for total, segments in [
            (0, ["Curioso"]),
            (5001, ["Curioso"]),
            (2, []),
            (2, ["invalid"]),
        ]:
            with self.assertRaises(ValueError):
                e.generate(total, segments, "test")

    def test_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "config.json"
            c = e.Config(mode="api", interval=2)
            e.save_config(c, p)
            self.assertEqual(e.load_config(p).mode, "api")
            self.assertEqual(e.load_config(p).interval, 2)

    def definition(self):
        return {
            "isPublished": True,
            "form": {
                "modules": [
                    {
                        "type": "step",
                        "modules": [
                            {
                                "type": "email",
                                "propertyReference": "0-1/email",
                                "required": True,
                            },
                            {
                                "type": "dropdownSelect",
                                "propertyReference": "0-1/origem_formulario_1",
                                "options": [
                                    {"label": "Novo segmento", "value": "new-key"}
                                ],
                            },
                        ],
                    }
                ]
            },
        }

    def test_sync_new_option(self):
        source = e.Config()
        c = e.sync_schema(source, lambda _: self.definition())
        self.assertEqual(c.options, {"Novo segmento": "new-key"})
        self.assertNotIn("Novo segmento", source.options)
        r = e.generate(1, ["Novo segmento"], "test", c)[0]
        self.assertEqual(e.payload(r, c)["fields"][-1]["value"], "new-key")

    def test_required_field_blocks_then_configures(self):
        d = self.definition()
        d["form"]["modules"].append(
            {"type": "text", "propertyReference": "0-1/company", "required": True}
        )
        c = e.sync_schema(e.Config(), lambda _: d)
        r = e.generate(1, ["Novo segmento"], "test", c)[0]
        with self.assertRaisesRegex(ValueError, "company"):
            e.payload(r, c)
        c.extra_values = {"company": "TESTE Empresa"}
        self.assertIn("company", [f["name"] for f in e.payload(r, c)["fields"]])

    def test_removed_fields_not_sent(self):
        c = e.sync_schema(e.Config(), lambda _: self.definition())
        r = e.generate(1, ["Novo segmento"], "test", c)[0]
        self.assertNotIn("firstname", [f["name"] for f in e.payload(r, c)["fields"]])

    def test_consent_and_rules_block(self):
        for module in [
            {"type": "legalConsent"},
            {"type": "recaptcha"},
            {"type": "file", "propertyReference": "0-1/attachment"},
        ]:
            d = self.definition()
            d["form"]["modules"].append(module)
            c = e.sync_schema(e.Config(), lambda _: d)
            with self.assertRaises(ValueError):
                c.validate()
        d = self.definition()
        d["form"]["logicRules"] = {"some": "rule"}
        c = e.sync_schema(e.Config(), lambda _: d)
        with self.assertRaises(ValueError):
            c.validate()

    def test_bad_static_option_blocks(self):
        c = e.Config(extra_values={"origem_formulario_1": "bad"})
        c.fields.append(
            {
                "property": "department",
                "type": "dropdownSelect",
                "objectTypeId": "0-1",
                "required": True,
                "options": {"A": "a"},
            }
        )
        c.extra_values["department"] = "not-a"
        with self.assertRaises(ValueError):
            e.payload(e.generate(1, ["Curioso"], "test", c)[0], c)

    def test_no_query_in_payload(self):
        c = e.Config(url="https://example.com/contact?private=x#foo")
        r = e.generate(1, ["Curioso"], "test", c)[0]
        self.assertEqual(
            e.payload(r, c)["context"]["pageUri"], "https://example.com/contact"
        )


HTML = """<!doctype html><html><head><title>Fixture local</title></head><body><form id="contact-native"><input name="firstname"><input name="lastname"><input name="email" type="email" required><select name="origem_formulario_1"><option value="NC2ztwgcNJTilAoEroC9k">Recrutador</option><option value="Curioso">Curioso</option></select><button type="submit">Enviar</button></form><div id="contact-success" hidden>Recebido</div><p id="native-status"></p><script>document.querySelector('form').addEventListener('submit',async ev=>{ev.preventDefault();const b=document.querySelector('button');b.disabled=true;try{const r=await fetch('ENDPOINT',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(ev.target)))});if(r.ok){document.querySelector('#contact-success').hidden=false}else{document.querySelector('#native-status').textContent='Recusado'}}finally{b.disabled=false}})</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.replace("ENDPOINT", e.Config().endpoint).encode())


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def fixture(
        self, mode, preview=False, status=200, stop_on_error=True, different_ids=False
    ):
        config = e.Config(
            url=f"http://127.0.0.1:{self.server.server_port}/beta",
            mode=mode,
            visual_pause=0,
            sync_before=False,
            stop_on_error=stop_on_error,
        )
        if different_ids:
            config.form_id = "c2ff372a-85ba-40e0-8f90-18badde87197"
        sent = []
        filled = []
        events = []
        original_submit = e.submit_visible
        original_fill = e.fill_visible

        def fill(page, c, stop, config):
            result = original_fill(page, c, stop, config)
            filled.append(c.email)
            return result

        def submit(page, config):
            def fulfill(route):
                if route.request.method == "POST":
                    sent.append(("visible", route.request.post_data))
                route.fulfill(
                    status=status,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "content-type",
                    },
                    content_type="application/json",
                    body="{}",
                )

            page.route(e.Config().endpoint, fulfill)
            try:
                return original_submit(
                    page, config, timeout_ms=5000 if not different_ids else 500
                )
            finally:
                page.unroute(e.Config().endpoint, fulfill)

        def sender(c, config):
            sent.append(("api", e.payload(c, config)))
            return (
                ("aceito", "mock HTTP 200")
                if status == 200
                else ("recusado", "mock HTTP 400")
            )

        with tempfile.TemporaryDirectory() as folder, patch.object(
            e, "submit_visible", submit
        ), patch.object(e, "fill_visible", fill):
            e.run_batch(
                e.generate(3, ["Recrutador", "Curioso"], "local-test", config),
                "local-test",
                preview,
                threading.Event(),
                lambda k, v: events.append((k, v)),
                config,
                Path(folder),
                sender,
                browser_headless=True,
            )
            with open(Path(folder) / "lote-local-test.csv", encoding="utf-8-sig") as f:
                report = list(csv.DictReader(f, delimiter=";"))
        return sent, filled, report

    def test_mixed(self):
        sent, filled, report = self.fixture("mixed")
        self.assertEqual([s[0] for s in sent], ["visible", "api", "api"])
        self.assertEqual(len(filled), 1)
        self.assertEqual(len(report), 3)

    def test_all_visible(self):
        sent, filled, report = self.fixture("visible")
        self.assertEqual([s[0] for s in sent], ["visible"] * 3)
        self.assertEqual(len(filled), 3)

    def test_all_api_needs_no_browser(self):
        with patch(
            "playwright.sync_api.sync_playwright",
            side_effect=AssertionError("Browser must not open"),
        ):
            sent, filled, report = self.fixture("api")
            self.assertEqual([s[0] for s in sent], ["api"] * 3)
            self.assertEqual(filled, [])

    def test_preview_all_visible_no_submission(self):
        sent, filled, report = self.fixture("visible", True)
        self.assertEqual(sent, [])
        self.assertEqual(len(filled), 3)
        self.assertTrue(all(r["status"] == "prévia" for r in report))

    def test_preview_all_api_no_submission(self):
        sent, filled, report = self.fixture("api", True)
        self.assertEqual(sent, [])
        self.assertEqual(filled, [])
        self.assertEqual(len(report), 3)

    def test_wrong_visible_destination_blocks_post(self):
        sent, filled, report = self.fixture("mixed", different_ids=True)
        self.assertEqual(sent, [])
        self.assertEqual(report[0]["status"], "recusado")

    def test_stop_on_first_visible_failure(self):
        sent, filled, report = self.fixture("mixed", status=400, stop_on_error=False)
        self.assertEqual(len(sent), 1)
        self.assertEqual(len(report), 1)

    def test_optional_continue_api_validation_error(self):
        sent, filled, report = self.fixture("api", status=400, stop_on_error=False)
        self.assertEqual(len(sent), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
