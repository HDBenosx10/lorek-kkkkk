"""Configurable fixture generation and submission; no GUI dependencies."""

from __future__ import annotations
import csv, json, random, re, threading, time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from urllib import error, request, parse
import ssl
import truststore


def open_url(url, timeout=25):
    # Use the Windows certificate store, preserving TLS verification.
    if isinstance(url, str):
        url = request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HubSpotLotes/1.1"
            },
        )
    return request.urlopen(
        url, timeout=timeout, context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    )


VERSION = "1.1.0"
DEFAULT_OPTIONS = {
    "Recrutador": "NC2ztwgcNJTilAoEroC9k",
    "Gestor(a) de Marketing": "LSTeQgnsDY0mVp-DQelPI",
    "Colega de área": "Colega de área",
    "Curioso": "Curioso",
}
MODES = {
    "Primeiro em tela + restantes via API": "mixed",
    "Todos em tela": "visible",
    "Todos via API": "api",
}
NAMES = [
    "Ana",
    "Bruno",
    "Clara",
    "Diego",
    "Elisa",
    "Felipe",
    "Gabriela",
    "Hugo",
    "Isabela",
    "João",
    "Laura",
    "Marcos",
    "Nina",
    "Pedro",
    "Rafaela",
    "Tiago",
]
SURNAMES = [
    "Almeida",
    "Barbosa",
    "Costa",
    "Dias",
    "Fernandes",
    "Gomes",
    "Lima",
    "Moreira",
    "Pereira",
    "Ribeiro",
    "Santos",
    "Vieira",
]
DEFAULT_FIELDS = [
    {"property": n, "objectTypeId": "0-1", "type": t, "required": r, "options": opts}
    for n, t, r, opts in [
        ("firstname", "text", False, {}),
        ("lastname", "text", False, {}),
        ("email", "email", True, {}),
        ("origem_formulario_1", "dropdownSelect", False, DEFAULT_OPTIONS),
    ]
]


@dataclass
class Config:
    url: str = "https://portifolio-leonardo-lagoa.pages.dev/beta#contato"
    portal_id: str = "51906766"
    form_id: str = "c2ff372a-85ba-40e0-8f90-18badde87196"
    mode: str = "mixed"
    interval: float = 1.0
    visual_pause: float = 0.5
    browser: str = "auto"
    sync_before: bool = True
    stop_on_error: bool = True
    segment_property: str = "origem_formulario_1"
    fields: list = field(default_factory=lambda: json.loads(json.dumps(DEFAULT_FIELDS)))
    extra_values: dict = field(default_factory=dict)
    selectors: dict = field(
        default_factory=lambda: {
            "frame": "",
            "form": "form",
            "firstname": "",
            "lastname": "",
            "email": "",
            "segment": "",
            "submit": 'button[type="submit"], input[type="submit"]',
            "success": "#contact-success",
            "status": "#native-status",
        }
    )
    synced_at: str = ""
    blockers: list = field(default_factory=list)

    @property
    def endpoint(self):
        return f"https://api.hsforms.com/submissions/v3/integration/submit/{self.portal_id}/{self.form_id}"

    @property
    def options(self):
        return next(
            (
                f["options"]
                for f in self.fields
                if f["property"] == self.segment_property
            ),
            {},
        )

    def validate(self, require_schema=True):
        url = parse.urlsplit(self.url)
        if (
            url.scheme not in ("https", "http")
            or not url.netloc
            or url.username
            or url.password
        ):
            raise ValueError("Use uma URL HTTP/HTTPS válida, sem credenciais.")
        if not self.portal_id.isdigit() or not re.fullmatch(
            r"[0-9a-fA-F-]{36}", self.form_id
        ):
            raise ValueError("Portal ID ou Form ID inválido.")
        if self.mode not in MODES.values() or self.browser not in (
            "auto",
            "msedge",
            "chrome",
        ):
            raise ValueError("Modo ou navegador inválido.")
        if not 1 <= self.interval <= 60 or not 0 <= self.visual_pause <= 10:
            raise ValueError("Intervalo: 1 a 60 s. Pausa visual: 0 a 10 s.")
        if require_schema and not self.options:
            raise ValueError(
                "O campo de segmento não tem opções. Sincronize e escolha uma propriedade de seleção."
            )
        if require_schema and self.blockers:
            raise ValueError(
                "Formulário exige suporte específico: " + "; ".join(self.blockers)
            )
        for key, value in self.extra_values.items():
            if not isinstance(key, str) or not isinstance(
                value, (str, int, float, bool)
            ):
                raise ValueError(
                    "Valores adicionais devem ser um objeto JSON de valores simples."
                )


def save_config(config: Config, path: Path):
    config.validate(require_schema=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temp.replace(path)


def load_config(path: Path):
    if not path.exists():
        return Config()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Configuração inválida.")
    known = Config.__dataclass_fields__
    config = Config(**{k: v for k, v in data.items() if k in known})
    config.selectors = {**Config().selectors, **config.selectors}
    return config


def get_json(url):
    with open_url(
        request.Request(url, headers={"User-Agent": "HubSpotLotes/1.1"}), timeout=25
    ) as response:
        return json.load(response)


def sync_schema(config: Config, getter=get_json):
    definition = getter(
        f"https://forms.hsforms.com/embed/v4/render-definition/{config.portal_id}/{config.form_id}"
    )
    if definition.get("isPublished") is False:
        raise ValueError("Formulário não está publicado.")
    fields = []
    blockers = []

    def visit(module):
        kind = module.get("type", "")
        if any(
            word in kind.lower() for word in ("consent", "captcha", "file", "payment")
        ):
            blockers.append(kind)
        reference = module.get("propertyReference")
        if reference:
            object_id, name = reference.split("/", 1)
            options = {
                o["label"]: str(o["value"])
                for o in module.get("options", [])
                if "label" in o and "value" in o
            }
            fields.append(
                {
                    "property": name,
                    "objectTypeId": object_id,
                    "type": kind,
                    "required": bool(module.get("required")),
                    "options": options,
                }
            )
        for child in module.get("modules", []):
            visit(child)

    form = definition.get("form", {})
    for module in form.get("modules", []):
        visit(module)
    if not fields:
        raise ValueError(
            "Não foi possível ler os campos deste formulário. Configuração preservada."
        )
    if form.get("logicRules"):
        blockers.append("regras condicionais")
    settings = definition.get("settings", {})
    if any(
        v
        for k, v in settings.items()
        if any(s in k.lower() for s in ("captcha", "consent"))
    ):
        blockers.append("consentimento/CAPTCHA")
    # Work with an independent snapshot; do not partially mutate UI settings.
    result = Config(**asdict(config))
    result.fields = fields
    result.blockers = list(dict.fromkeys(blockers))
    result.synced_at = time.strftime("%Y-%m-%d %H:%M:%S")
    if not result.options:
        candidates = [f["property"] for f in fields if f["options"]]
        if len(candidates) == 1:
            result.segment_property = candidates[0]
    return result


def detect_ids(url):
    parsed = parse.urlsplit(url)
    if (
        parsed.scheme not in ("https", "http")
        or not parsed.netloc
        or parsed.username
        or parsed.password
    ):
        raise ValueError("URL inválida.")
    with open_url(url, timeout=25) as response:
        html = response.read(2_000_000).decode("utf-8", errors="replace")
    portals = set(re.findall(r'(?:data-portal-id\s*=\s*["\']|forms/embed/)(\d+)', html))
    forms = set(re.findall(r'data-form-id\s*=\s*["\']([a-fA-F0-9-]{36})', html))
    # Native beta stores its public endpoint in an external script.
    scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html, re.I)
    for src in scripts[:15]:
        script_url = parse.urljoin(url, src)
        if parse.urlsplit(script_url).netloc != parsed.netloc:
            continue
        with open_url(script_url, timeout=15) as response:
            script = response.read(1_000_000).decode("utf-8", errors="replace")
        for portal, form in re.findall(
            r"api\.hsforms\.com/submissions/v3/integration/submit/(\d+)/([a-fA-F0-9-]{36})",
            script,
        ):
            portals.add(portal)
            forms.add(form)
    if len(portals) != 1 or len(forms) != 1:
        raise ValueError(
            "Não encontrei um único formulário. Informe Portal ID e Form ID na configuração."
        )
    return next(iter(portals)), next(iter(forms))


@dataclass(frozen=True)
class Contact:
    firstname: str
    lastname: str
    email: str
    segment: str
    value: str


def generate(total, segments, batch, config=None):
    config = config or Config()
    if (
        not 1 <= total <= 5000
        or not segments
        or any(s not in config.options for s in segments)
    ):
        raise ValueError(
            "Escolha segmentos disponíveis e de 1 a 5.000 contatos. Se as opções mudaram, sincronize novamente."
        )
    return [
        Contact(
            "TESTE " + random.choice(NAMES),
            random.choice(SURNAMES) + " LOTE-" + batch,
            f"teste.{batch}.{i+1:05d}@example.com",
            segments[i % len(segments)],
            config.options[segments[i % len(segments)]],
        )
        for i in range(total)
    ]


def field_values(contact, config):
    values = {
        "firstname": contact.firstname,
        "lastname": contact.lastname,
        "email": contact.email,
        **{k: str(v) for k, v in config.extra_values.items()},
    }
    values[config.segment_property] = contact.value
    available = {f["property"]: f for f in config.fields}
    if "email" not in available:
        raise ValueError("Este gerador precisa de uma propriedade email no formulário.")
    for name, definition in available.items():
        value = values.get(name, "")
        if definition["required"] and not value:
            raise ValueError(
                f"Campo obrigatório novo: {name}. Configure um valor adicional antes de enviar."
            )
        if (
            value
            and definition["options"]
            and value not in definition["options"].values()
        ):
            raise ValueError(
                f"Valor inválido em {name}; confira as opções sincronizadas."
            )
    unknown = set(config.extra_values) - set(available)
    if unknown:
        raise ValueError(
            "Valores adicionais apontam para campos ausentes: "
            + ", ".join(sorted(unknown))
        )
    return {k: v for k, v in values.items() if k in available and v != ""}


def payload(contact, config=None):
    config = config or Config()
    definitions = {f["property"]: f for f in config.fields}
    url = parse.urlsplit(config.url)
    return {
        "fields": [
            {"objectTypeId": definitions[k]["objectTypeId"], "name": k, "value": v}
            for k, v in field_values(contact, config).items()
        ],
        "context": {
            "pageUri": parse.urlunsplit((url.scheme, url.netloc, url.path, "", "")),
            "pageName": "HubSpot Lotes — dados de teste",
        },
    }


def send_http(contact, config=None):
    config = config or Config()
    req = request.Request(
        config.endpoint,
        json.dumps(payload(contact, config), ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "HubSpotLotes/1.1"},
        method="POST",
    )
    try:
        with open_url(req, timeout=25) as response:
            return "aceito", f"HTTP {response.status}"
    except error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        exc.close()
        try:
            result = json.loads(body)
            detail = "; ".join(
                str(e.get("errorType") or e.get("message", ""))
                for e in result.get("errors", [])
            ) or str(result.get("message", "Envio recusado"))
        except ValueError:
            detail = "Envio recusado"
        return (
            "limite" if exc.code == 429 else "recusado"
        ), f"HTTP {exc.code}: {detail[:350]}"
    except (error.URLError, TimeoutError, OSError) as exc:
        return "incerto", "Envio sem confirmação: " + str(exc)[:250]


def scope_for(page, config):
    if config.selectors["frame"]:
        return page.frame_locator(config.selectors["frame"])
    if page.locator(config.selectors["form"]).count():
        return page
    if page.locator('iframe[title="Form"]').count() == 1:
        return page.frame_locator('iframe[title="Form"]')
    return page


def selector_for(name, config):
    role = "segment" if name == config.segment_property else name
    if config.selectors.get(role):
        return config.selectors[role]
    if not re.fullmatch(r"[\w-]+", name):
        raise ValueError("Propriedade exige seletor CSS explícito: " + name)
    definition = next(f for f in config.fields if f["property"] == name)
    return f'[name="{name}"], [name="{definition["objectTypeId"]}/{name}"]'


def fill_visible(page, contact, stop, config=None):
    config = config or Config()
    page.goto(config.url, wait_until="domcontentloaded", timeout=45000)
    scope = scope_for(page, config)
    form = scope.locator(config.selectors["form"])
    if form.count() != 1:
        raise ValueError(
            "Não encontrei um único formulário. Ajuste o seletor de formulário/iframe na aba Config."
        )
    form.wait_for(state="visible", timeout=25000)
    for name, value in field_values(contact, config).items():
        if stop.is_set():
            return False
        locator = form.locator(selector_for(name, config))
        if locator.count() != 1:
            raise ValueError(
                f"Campo {name} ausente ou ambíguo na página. Ajuste os seletores ou atualize o front-end."
            )
        tag = locator.evaluate("(e)=>e.tagName.toLowerCase()")
        kind = locator.get_attribute("type") or ""
        if tag == "select":
            locator.select_option(value)
        elif kind in ("checkbox", "radio"):
            raise ValueError(
                f"Campo {name} exige suporte específico; não marcamos consentimentos automaticamente."
            )
        elif locator.get_attribute("role") == "combobox":
            # New HubSpot embed: custom dropdown + hidden property input.
            label = next(
                (
                    k
                    for k, v in next(f for f in config.fields if f["property"] == name)[
                        "options"
                    ].items()
                    if v == value
                ),
                None,
            )
            locator.click()
            scope.get_by_role("option", name=label, exact=True).click()
        elif kind == "hidden":
            definition = next(f for f in config.fields if f["property"] == name)
            if not definition["options"]:
                raise ValueError(f"Campo oculto {name}: configure o front-end.")
            # Pair a hidden select value with the rendered control in its module.
            control = locator.locator("..").get_by_role("combobox")
            label = next(k for k, v in definition["options"].items() if v == value)
            control.click()
            scope.get_by_role("option", name=label, exact=True).click()
        else:
            locator.fill(value)
        if stop.wait(config.visual_pause):
            return False
    return not stop.wait(config.visual_pause)


def submit_visible(page, config, timeout_ms=30000):
    scope = scope_for(page, config)
    form = scope.locator(config.selectors["form"])
    button = form.locator(config.selectors["submit"])
    if button.count() != 1:
        raise ValueError("Botão de envio ausente ou ambíguo. Ajuste o seletor.")
    paths = [
        f"/submissions/v3/integration/submit/{config.portal_id}/{config.form_id}",
        f"/submissions/v3/public/submit/formsnext/multipart/{config.portal_id}/{config.form_id}",
    ]
    blocked = []

    def matches(url):
        parsed = parse.urlsplit(url)
        return (
            parsed.hostname in ("api.hsforms.com", "forms.hsforms.com")
            and parsed.path in paths
        )

    def guard(route):
        if route.request.method == "POST" and not matches(route.request.url):
            blocked.append(route.request.url)
            route.abort()
        else:
            route.fallback()

    # Never submit to a different CRM just because the configured URL changed.
    page.route("**/*", guard)
    try:
        with page.expect_response(
            lambda r: matches(r.url) and r.request.method == "POST", timeout=timeout_ms
        ) as captured:
            button.click()
        response = captured.value
        if response.ok:
            return "aceito", f"Formulário: HTTP {response.status}"
        return (
            "limite" if response.status == 429 else "recusado"
        ), f"Formulário: HTTP {response.status}"
    except Exception as exc:
        if blocked:
            return (
                "recusado",
                "Envio bloqueado: a página aponta para um destino diferente dos IDs configurados.",
            )
        detail = ""
        if (
            config.selectors.get("status")
            and scope.locator(config.selectors["status"]).count()
        ):
            detail = scope.locator(config.selectors["status"]).inner_text()
        return (
            "incerto",
            detail
            or "Envio não confirmado. Não repetido automaticamente. " + str(exc)[:100],
        )
    finally:
        page.unroute("**/*", guard)


def run_batch(
    contacts,
    batch,
    preview,
    stop,
    emit,
    config=None,
    folder=None,
    sender=send_http,
    *,
    browser_headless=False,
):
    config = config or Config()
    config.validate()
    for contact in contacts:
        field_values(contact, config)
    folder = folder or Path.home() / "Documents" / "HubSpotLotes"
    folder.mkdir(parents=True, exist_ok=True)
    report = folder / f"lote-{batch}.csv"
    completed = 0
    browser = None
    engine = None
    page = None
    try:
        if config.mode != "api":
            from playwright.sync_api import sync_playwright

            engine = sync_playwright().start()
            for channel in (
                ["msedge", "chrome"] if config.browser == "auto" else [config.browser]
            ):
                try:
                    browser = engine.chromium.launch(
                        channel=channel, headless=browser_headless
                    )
                    break
                except Exception:
                    continue
            if not browser:
                raise RuntimeError(
                    "Edge/Chrome não encontrado. Use Todos via API ou instale o navegador escolhido."
                )
            page = browser.new_page(viewport={"width": 1100, "height": 800})
        with report.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(
                ["lote", "nome", "sobrenome", "email", "segmento", "status", "detalhe"]
            )
            for index, contact in enumerate(contacts, 1):
                if stop.is_set():
                    break
                if index > 1 and stop.wait(
                    config.interval if not preview else min(config.interval, 0.5)
                ):
                    break
                visible = config.mode == "visible" or (
                    config.mode == "mixed" and index == 1
                )
                if visible:
                    emit("log", f"{index}: preenchendo no navegador…")
                    if not fill_visible(page, contact, stop, config):
                        break
                if preview:
                    status, detail = "prévia", (
                        "Preenchido em tela; não enviado"
                        if visible
                        else "Payload validado; não enviado"
                    )
                    if visible and stop.wait(max(config.visual_pause, 1)):
                        break
                else:
                    status, detail = (
                        submit_visible(page, config)
                        if visible
                        else sender(contact, config)
                    )
                writer.writerow(
                    [
                        batch,
                        contact.firstname,
                        contact.lastname,
                        contact.email,
                        contact.segment,
                        status,
                        detail,
                    ]
                )
                handle.flush()
                completed += 1
                emit("result", (index, status, contact.segment, detail))
                if (
                    status != "aceito"
                    and not preview
                    and (
                        visible
                        and index == 1
                        or config.stop_on_error
                        or status in ("limite", "incerto")
                    )
                ):
                    emit(
                        "log",
                        "Lote interrompido após falha; nenhum reenvio automático.",
                    )
                    break
    finally:
        if browser:
            browser.close()
        if engine:
            engine.stop()
        if report.exists():
            emit("report", str(report))
        emit("log", f"{completed} contatos processados.")
