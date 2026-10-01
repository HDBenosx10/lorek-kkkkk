"""HubSpot Lotes: Windows GUI with persistent configuration and schema sync."""

from __future__ import annotations
import json, os, queue, threading, uuid, sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from engine import (
    Config,
    MODES,
    VERSION,
    generate,
    load_config,
    save_config,
    sync_schema,
    detect_ids,
    run_batch,
)

CONFIG_PATH = (
    Path(os.environ.get("APPDATA", str(Path.home()))) / "HubSpotLotes" / "config.json"
)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"HubSpot Lotes {VERSION}")
        self.geometry("900x790")
        self.minsize(780, 700)
        self.configure(bg="#FAF7F5")
        self.messages = queue.Queue()
        self.stop = threading.Event()
        self.running = False
        self.report_path = None
        try:
            self.config_data = load_config(CONFIG_PATH)
            self.load_error = ""
        except Exception as exc:
            self.config_data = Config()
            self.load_error = "Configuração não carregada: " + str(exc)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            ".", font=("Segoe UI", 10), background="#FAF7F5", foreground="#4A1425"
        )
        style.configure(
            "Accent.TButton", background="#6B1F36", foreground="white", padding=10
        )
        style.map("Accent.TButton", background=[("active", "#4A1425")])
        root = ttk.Frame(self, padding=20)
        root.pack(fill="both", expand=True)
        ttk.Label(
            root, text="Contatos de teste, por segmento.", font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")
        self.destination = ttk.Label(root, wraplength=830, foreground="#8D6773")
        self.destination.pack(anchor="w", pady=(3, 12))
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True)
        self.batch_tab = ttk.Frame(self.tabs, padding=18)
        self.config_tab = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(self.batch_tab, text="Lotes")
        self.tabs.add(self.config_tab, text="Config")
        self.segment_box = ttk.LabelFrame(self.batch_tab, text="Segmentos", padding=10)
        self.segment_box.pack(fill="x")
        row = ttk.Frame(self.batch_tab)
        row.pack(fill="x", pady=14)
        ttk.Label(row, text="Total de contatos").pack(side="left")
        self.total = tk.StringVar(value="20")
        self.spin = ttk.Spinbox(row, from_=1, to=5000, textvariable=self.total, width=9)
        self.spin.pack(side="left", padx=12)
        self.distribution = ttk.Label(
            self.batch_tab, wraplength=780, foreground="#8D6773"
        )
        self.distribution.pack(anchor="w")
        self.total.trace_add("write", self.update_distribution)
        ttk.Label(
            self.batch_tab,
            text="TESTE + identificador de lote. E-mails únicos em example.com.\nPrévia nunca envia. Enviar lote cria contatos no destino configurado.",
            wraplength=770,
        ).pack(anchor="w", pady=12)
        buttons = ttk.Frame(self.batch_tab)
        buttons.pack(fill="x")
        self.preview_button = ttk.Button(
            buttons, text="Prévia sem enviar", command=lambda: self.start(True)
        )
        self.preview_button.pack(side="left", padx=(0, 10))
        self.send_button = ttk.Button(
            buttons,
            text="Enviar lote",
            style="Accent.TButton",
            command=lambda: self.start(False),
        )
        self.send_button.pack(side="left")
        self.cancel_button = ttk.Button(
            buttons, text="Parar", command=self.cancel, state="disabled"
        )
        self.cancel_button.pack(side="right")
        self.progress = ttk.Progressbar(self.batch_tab)
        self.progress.pack(fill="x", pady=(16, 5))
        self.summary = ttk.Label(self.batch_tab, text="Pronto.")
        self.summary.pack(anchor="w")
        self.log = tk.Text(
            self.batch_tab,
            height=8,
            bg="white",
            fg="#4A1425",
            font=("Consolas", 9),
            relief="flat",
            state="disabled",
            wrap="word",
        )
        self.log.pack(fill="both", expand=True, pady=12)
        self.report_button = ttk.Button(
            self.batch_tab,
            text="Abrir relatório CSV",
            state="disabled",
            command=self.open_report,
        )
        self.report_button.pack(anchor="w")
        self.make_config_tab()
        self.apply_config(self.config_data)
        self.append(self.load_error or "Configuração salva em " + str(CONFIG_PATH))
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(100, self.poll)

    def make_config_tab(self):
        # Scrolling keeps advanced selectors accessible on small Windows screens.
        canvas = tk.Canvas(self.config_tab, bg="#FAF7F5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            self.config_tab, orient="vertical", command=canvas.yview
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        panel = ttk.Frame(canvas, padding=8)
        window = canvas.create_window((0, 0), window=panel, anchor="nw")
        panel.bind(
            "<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>", lambda e: canvas.itemconfigure(window, width=e.width)
        )
        self.vars = {}
        self.edit_controls = []

        def entry(label, key):
            ttk.Label(panel, text=label).pack(anchor="w", pady=(9, 3))
            var = tk.StringVar()
            self.vars[key] = var
            control = ttk.Entry(panel, textvariable=var)
            control.pack(fill="x")
            self.edit_controls.append(control)

        entry("URL da página (usada nos envios em tela e como contexto da API)", "url")
        entry("Portal ID HubSpot", "portal_id")
        entry("Form ID HubSpot", "form_id")
        actions = ttk.Frame(panel)
        actions.pack(fill="x", pady=10)
        self.detect_button = ttk.Button(
            actions,
            text="Identificar IDs pela URL",
            command=lambda: self.synchronize(True),
        )
        self.detect_button.pack(side="left", padx=(0, 8))
        self.sync_button = ttk.Button(
            actions, text="Sincronizar campos e opções", command=self.synchronize
        )
        self.sync_button.pack(side="left")
        self.edit_controls += [self.detect_button, self.sync_button]
        ttk.Label(panel, text="Modo de execução").pack(anchor="w", pady=(8, 3))
        self.vars["mode"] = tk.StringVar()
        control = ttk.Combobox(
            panel, textvariable=self.vars["mode"], values=list(MODES), state="readonly"
        )
        control.pack(fill="x")
        self.edit_controls.append(control)
        ttk.Label(
            panel,
            text="Na prévia, Todos em tela preenche cada contato sem enviar.\nTodos via API apenas valida os dados e gera o CSV; não abre navegador.",
            wraplength=740,
            foreground="#8D6773",
        ).pack(anchor="w", pady=5)
        entry("Intervalo entre contatos (1 a 60 segundos)", "interval")
        entry("Pausa visual por campo (0 a 10 segundos)", "visual_pause")
        ttk.Label(panel, text="Navegador (modo em tela)").pack(anchor="w", pady=(8, 3))
        self.vars["browser"] = tk.StringVar()
        control = ttk.Combobox(
            panel,
            textvariable=self.vars["browser"],
            values=["auto", "msedge", "chrome"],
            state="readonly",
        )
        control.pack(fill="x")
        self.edit_controls.append(control)
        for key, label in [
            ("sync_before", "Sincronizar definição do HubSpot antes de cada lote"),
            ("stop_on_error", "Parar também em erros de validação HTTP 400"),
        ]:
            self.vars[key] = tk.BooleanVar()
            control = ttk.Checkbutton(panel, text=label, variable=self.vars[key])
            control.pack(anchor="w", pady=8)
            self.edit_controls.append(control)
        ttk.Label(
            panel,
            text="Limites HTTP 429 e envios sem confirmação sempre interrompem o lote; não há repetição automática.",
            wraplength=740,
            foreground="#8D6773",
        ).pack(anchor="w")
        entry(
            "Propriedade usada para segmentação (ex.: origem_formulario_1)",
            "segment_property",
        )
        ttk.Label(
            panel,
            text='Valores adicionais, JSON (nomes internos → valores). Ex.: {"company":"TESTE Empresa"}',
            wraplength=740,
        ).pack(anchor="w", pady=(10, 4))
        self.extra = tk.Text(panel, height=3, font=("Consolas", 10))
        self.extra.pack(fill="x")
        self.edit_controls.append(self.extra)
        ttk.Label(
            panel,
            text="Seletores CSS, JSON. Campos vazios usam o atributo name automaticamente.\nframe: iframe opcional; form: formulário; submit: botão; success/status: confirmação alternativa.",
            wraplength=740,
        ).pack(anchor="w", pady=(10, 4))
        self.selectors = tk.Text(panel, height=8, font=("Consolas", 10))
        self.selectors.pack(fill="x")
        self.edit_controls.append(self.selectors)
        self.schema_status = ttk.Label(panel, wraplength=740, foreground="#8D6773")
        self.schema_status.pack(anchor="w", pady=10)
        self.schema_view = tk.Text(
            panel, height=8, font=("Consolas", 9), state="disabled", wrap="word"
        )
        self.schema_view.pack(fill="x")
        ttk.Label(
            panel,
            text="Alterações de campos/opções são lidas do HubSpot. O app não altera o HTML do site.\nCampos obrigatórios novos exigem valores adicionais; consentimento, CAPTCHA, arquivos e regras condicionais interrompem o envio para revisão.",
            wraplength=740,
        ).pack(anchor="w", pady=8)
        self.save_button = ttk.Button(
            panel, text="Salvar configuração", style="Accent.TButton", command=self.save
        )
        self.save_button.pack(anchor="w", pady=10)
        self.edit_controls.append(self.save_button)

    def apply_config(self, config):
        self.config_data = config
        for key, var in self.vars.items():
            value = getattr(config, key)
            if key == "mode":
                value = next(k for k, v in MODES.items() if v == value)
            var.set(value)
        for widget, value in [
            (self.extra, config.extra_values),
            (self.selectors, config.selectors),
        ]:
            widget.delete("1.0", "end")
            widget.insert("1.0", json.dumps(value, ensure_ascii=False, indent=2))
        old = {k: v.get() for k, v in getattr(self, "segments", {}).items()}
        for child in self.segment_box.winfo_children():
            child.destroy()
        self.segments = {
            k: tk.BooleanVar(value=old.get(k, True)) for k in config.options
        }
        for i, (label, var) in enumerate(self.segments.items()):
            ttk.Checkbutton(
                self.segment_box,
                text=label,
                variable=var,
                command=self.update_distribution,
            ).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 25), pady=5)
        self.schema_status.configure(
            text=f'Última sincronização: {config.synced_at or "ainda não realizada"}. Campos: '
            + ", ".join(
                f["property"] + (" *" if f["required"] else "") for f in config.fields
            )
            + (
                ("\nBloqueios: " + ", ".join(config.blockers))
                if config.blockers
                else ""
            )
        )
        self.schema_view.configure(state="normal")
        self.schema_view.delete("1.0", "end")
        self.schema_view.insert(
            "1.0", json.dumps(config.fields, ensure_ascii=False, indent=2)
        )
        self.schema_view.configure(state="disabled")
        self.destination.configure(
            text=config.url
            + " · "
            + next(k for k, v in MODES.items() if v == config.mode)
        )
        self.update_distribution()

    def collect_config(self):
        config = Config(**asdict(self.config_data))
        for key, var in self.vars.items():
            value = var.get()
            if key == "mode":
                value = MODES[value]
            elif key in ("interval", "visual_pause"):
                value = float(value)
            elif isinstance(value, str):
                value = value.strip()
            setattr(config, key, value)
        config.extra_values = json.loads(self.extra.get("1.0", "end"))
        config.selectors = {
            **Config().selectors,
            **json.loads(self.selectors.get("1.0", "end")),
        }
        if not isinstance(config.extra_values, dict) or any(
            not isinstance(v, str) for v in config.selectors.values()
        ):
            raise ValueError("JSON de configuração inválido.")
        config.validate(require_schema=False)
        return config

    def save(self):
        try:
            config = self.collect_config()
            save_config(config, CONFIG_PATH)
            self.apply_config(config)
            self.append("Configuração salva.")
            self.tabs.select(self.batch_tab)
        except Exception as exc:
            messagebox.showerror("Configuração", str(exc))

    def synchronize(self, detect=False):
        if self.running:
            return
        try:
            config = self.collect_config()
        except Exception as exc:
            messagebox.showerror("Configuração", str(exc))
            return
        self.stop.clear()
        self.set_busy(True)
        self.append("Lendo definição pública do HubSpot…")

        def worker():
            try:
                if detect:
                    config.portal_id, config.form_id = detect_ids(config.url)
                updated = sync_schema(config)
                save_config(updated, CONFIG_PATH)
                self.messages.put(("config", updated))
                self.messages.put(
                    (
                        "log",
                        "Campos e opções atualizados. Revise os segmentos na aba Lotes.",
                    )
                )
            except Exception as exc:
                self.messages.put(
                    ("log", "Sincronização falhou; nada enviado: " + str(exc))
                )
            finally:
                self.messages.put(("done", None))

        threading.Thread(target=worker, daemon=True).start()

    def update_distribution(self, *_):
        selected = [k for k, v in getattr(self, "segments", {}).items() if v.get()]
        try:
            total = int(self.total.get())
            if not selected or not 1 <= total <= 5000:
                raise ValueError()
            base, extra = divmod(total, len(selected))
            self.distribution.configure(
                text=" · ".join(
                    f"{s}: {base+(i<extra)}" for i, s in enumerate(selected)
                )
            )
        except ValueError:
            self.distribution.configure(
                text="Escolha segmentos disponíveis e total de 1 a 5.000."
            )

    def set_busy(self, busy):
        self.running = busy
        for control in (
            self.edit_controls
            + [self.spin, self.preview_button, self.send_button]
            + list(self.segment_box.winfo_children())
        ):
            control.configure(
                state=(
                    "disabled"
                    if busy
                    else ("readonly" if isinstance(control, ttk.Combobox) else "normal")
                )
            )
        self.cancel_button.configure(state="normal" if busy else "disabled")

    def start(self, preview):
        if self.running:
            return
        try:
            config = self.collect_config()
            total = int(self.total.get())
            segments = [k for k, v in self.segments.items() if v.get()]
            if not segments or not 1 <= total <= 5000:
                raise ValueError("Escolha segmentos e um total de 1 a 5.000.")
            save_config(config, CONFIG_PATH)
        except Exception as exc:
            messagebox.showerror("Confira o lote", str(exc))
            return
        self.apply_config(config)
        self.set_busy(True)
        self.stop.clear()
        self.counts = {"aceito": 0, "prévia": 0, "erro": 0}
        self.batch_total = total
        self.progress.configure(maximum=total, value=0)
        self.report_button.configure(state="disabled")
        self.summary.configure(text="Preparando lote…")
        batch = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        self.append(
            f"Lote {batch} · "
            + ("PRÉVIA" if preview else "ENVIO")
            + " · "
            + config.mode
        )

        def worker():
            try:
                current = sync_schema(config) if config.sync_before else config
                if config.sync_before:
                    save_config(current, CONFIG_PATH)
                    self.messages.put(("config", current))
                current.validate()
                contacts = generate(total, segments, batch, current)
                if not self.stop.is_set():
                    run_batch(
                        contacts,
                        batch,
                        preview,
                        self.stop,
                        lambda k, v: self.messages.put((k, v)),
                        current,
                    )
            except Exception as exc:
                self.messages.put(("log", "Interrompido: " + str(exc)))
            finally:
                self.messages.put(("done", None))

        threading.Thread(target=worker, daemon=True).start()

    def append(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def poll(self):
        try:
            while True:
                kind, data = self.messages.get_nowait()
                if kind == "log":
                    self.append(data)
                elif kind == "config":
                    self.apply_config(data)
                    if self.running:
                        self.set_busy(True)
                elif kind == "result":
                    index, status, segment, detail = data
                    self.counts[status if status in self.counts else "erro"] += 1
                    self.progress.configure(value=index)
                    self.summary.configure(
                        text=f'{index}/{self.batch_total} · Aceitos: {self.counts["aceito"]} · Prévia: {self.counts["prévia"]} · Erros: {self.counts["erro"]}'
                    )
                    self.append(f"{index:04d} · {segment} · {status} · {detail}")
                elif kind == "report":
                    self.report_path = data
                    self.report_button.configure(state="normal")
                    self.append("CSV: " + data)
                elif kind == "done":
                    self.set_busy(False)
                    if float(self.progress["value"]) == 0:
                        self.summary.configure(text="Nenhum contato processado.")
                    self.append(
                        "Finalizado."
                        if not self.stop.is_set()
                        else "Interrompido após o envio atual."
                    )
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def cancel(self):
        self.stop.set()
        self.cancel_button.configure(state="disabled")
        self.append("Parando após a operação atual…")

    def open_report(self):
        if self.report_path:
            os.startfile(self.report_path)

    def close(self):
        if self.running:
            self.cancel()
            self.append("Aguarde concluir a operação atual antes de fechar.")
            return
        self.destroy()


if __name__ == "__main__":
    app = App()
    if "--smoke-test" in sys.argv:
        app.withdraw()
        app.update()
        app.tabs.select(app.config_tab)
        app.update()
        assert len(app.tabs.tabs()) == 2
        from playwright.sync_api import sync_playwright

        with sync_playwright() as engine:
            browser = engine.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            page.set_content("<title>Pacote validado</title>")
            assert page.title() == "Pacote validado"
            browser.close()
        app.destroy()
        if len(sys.argv) > 2:
            Path(sys.argv[2]).write_text(
                json.dumps(
                    {
                        "interface": "ok",
                        "config_tab": "ok",
                        "browser": "ok",
                        "external_requests": 0,
                    }
                ),
                encoding="utf-8",
            )
    else:
        app.mainloop()
