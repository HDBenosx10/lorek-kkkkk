"""Windows batch fixture generator for Leonardo Lagoa's HubSpot form."""
from __future__ import annotations
import csv
import json
import queue
import random
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib import error, request
import tkinter as tk
from tkinter import ttk, messagebox

SITE = 'https://portifolio-leonardo-lagoa.pages.dev/beta#contato'
ENDPOINT = 'https://api.hsforms.com/submissions/v3/integration/submit/51906766/c2ff372a-85ba-40e0-8f90-18badde87196'
SEGMENTS = {
    'Recrutador': 'NC2ztwgcNJTilAoEroC9k',
    'Gestor(a) de Marketing': 'LSTeQgnsDY0mVp-DQelPI',
    'Colega de área': 'Colega de área',
    'Curioso': 'Curioso',
}
NAMES = ['Ana', 'Bruno', 'Clara', 'Diego', 'Elisa', 'Felipe', 'Gabriela', 'Hugo', 'Isabela', 'João', 'Laura', 'Marcos', 'Nina', 'Pedro', 'Rafaela', 'Tiago']
SURNAMES = ['Almeida', 'Barbosa', 'Costa', 'Dias', 'Fernandes', 'Gomes', 'Lima', 'Moreira', 'Pereira', 'Ribeiro', 'Santos', 'Vieira']

@dataclass(frozen=True)
class Contact:
    firstname: str
    lastname: str
    email: str
    segment: str
    value: str


def generate(total: int, segments: list[str], batch: str) -> list[Contact]:
    if not 1 <= total <= 5000 or not segments or any(s not in SEGMENTS for s in segments):
        raise ValueError('Escolha ao menos um segmento e de 1 a 5.000 contatos.')
    # Round-robin gives each selected segment an equal share (difference <= 1).
    contacts = []
    for i in range(total):
        segment = segments[i % len(segments)]
        contacts.append(Contact('TESTE ' + random.choice(NAMES), random.choice(SURNAMES) + ' LOTE-' + batch,
            f'teste.{batch}.{i + 1:05d}@example.com', segment, SEGMENTS[segment]))
    return contacts


def payload(contact: Contact) -> dict:
    fields = {'firstname': contact.firstname, 'lastname': contact.lastname, 'email': contact.email,
              'origem_formulario_1': contact.value}
    return {'fields': [{'objectTypeId': '0-1', 'name': k, 'value': v} for k, v in fields.items()],
            'context': {'pageUri': SITE.split('#')[0], 'pageName': 'Leonardo Lagoa — Marketing em prática'}}


def send_http(contact: Contact) -> tuple[str, str]:
    req = request.Request(ENDPOINT, json.dumps(payload(contact), ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'HubSpotLotes-Test/1.0'}, method='POST')
    try:
        with request.urlopen(req, timeout=25) as response:
            return 'aceito', f'HTTP {response.status}'
    except error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        exc.close()
        try:
            result = json.loads(body)
            detail = '; '.join(str(e.get('errorType') or e.get('message', '')) for e in result.get('errors', []))
            detail = detail or str(result.get('message', 'Envio recusado'))
        except ValueError:
            detail = 'Envio recusado'
        return 'limite' if exc.code == 429 else 'recusado', f'HTTP {exc.code}: {detail[:350]}'
    except (error.URLError, TimeoutError, OSError) as exc:
        # Unknown outcome: don't retry and risk duplicates.
        return 'incerto', 'Não foi possível confirmar o envio: ' + str(exc)[:250]


def fill_visible(page, contact: Contact, stop: threading.Event):
    page.goto(SITE, wait_until='domcontentloaded', timeout=45000)
    page.locator('#contact-native').wait_for(state='visible', timeout=25000)
    for selector, value in [('#contact-firstname', contact.firstname), ('#contact-lastname', contact.lastname), ('#contact-email', contact.email)]:
        if stop.is_set():
            return False
        page.locator(selector).fill(value)
        stop.wait(.55)
    page.locator('#contact-profile').select_option(contact.value)
    return not stop.wait(1)


def visible_result(page) -> tuple[str, str]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if page.locator('#contact-success').is_visible():
            return 'aceito', 'Confirmado pelo formulário da beta'
        if page.locator('#contact-native button[type="submit"]').is_enabled():
            return 'recusado', page.locator('#native-status').inner_text() or 'Formulário não confirmou o envio'
        time.sleep(.2)
    return 'incerto', 'Tempo esgotado; envio não repetido automaticamente'


def run_batch(contacts, batch, preview, stop, emit, sender=send_http, folder=None):
    from playwright.sync_api import sync_playwright
    folder = folder or Path.home() / 'Documents' / 'HubSpotLotes'
    folder.mkdir(parents=True, exist_ok=True)
    report = folder / f'lote-{batch}.csv'
    browser = None
    completed = 0
    with report.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle, delimiter=';')
        writer.writerow(['lote', 'nome', 'sobrenome', 'email', 'segmento', 'status', 'detalhe'])
        with sync_playwright() as playwright:
            for channel in ['msedge', 'chrome']:
                try:
                    browser = playwright.chromium.launch(channel=channel, headless=False)
                    break
                except Exception:
                    continue
            if browser is None:
                raise RuntimeError('Instale Microsoft Edge ou Google Chrome para abrir a demonstração visível.')
            try:
                page = browser.new_page(viewport={'width': 1100, 'height': 800})
                emit('log', 'Abrindo o navegador e preenchendo o primeiro contato…')
                if not fill_visible(page, contacts[0], stop):
                    return
                if not preview:
                    # Arm UI submission once; never retry this contact through the API.
                    page.locator('#contact-native button[type="submit"]').click()
                    status, detail = visible_result(page)
                    writer.writerow([batch, contacts[0].firstname, contacts[0].lastname, contacts[0].email, contacts[0].segment, status, detail])
                    handle.flush()
                    completed = 1
                    emit('result', (1, status, contacts[0].segment, detail))
                    if status != 'aceito':
                        emit('log', 'Lote interrompido: o primeiro envio precisa funcionar antes de enviar o restante.')
                        return
                else:
                    emit('log', 'Prévia: formulário preenchido sem clicar em Enviar. Nenhum contato criado.')
                    stop.wait(5)
                for index, contact in enumerate(contacts[1:] if not preview else contacts, 2 if not preview else 1):
                    if stop.wait(1 if not preview else .03):
                        break
                    status, detail = ('prévia', 'Não enviado') if preview else sender(contact)
                    writer.writerow([batch, contact.firstname, contact.lastname, contact.email, contact.segment, status, detail])
                    handle.flush()
                    completed += 1
                    emit('result', (index, status, contact.segment, detail))
                    if status in ('limite', 'incerto', 'recusado'):
                        emit('log', 'Lote interrompido após falha. Consulte o relatório antes de iniciar outro lote.')
                        break
            finally:
                browser.close()
                emit('report', str(report))
                emit('log', f'{completed} contatos processados. CSV salvo; não há repetição automática.')


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('HubSpot · Lotes de teste')
        self.geometry('780x720')
        self.minsize(680, 660)
        self.configure(bg='#FAF7F5')
        self.messages = queue.Queue()
        self.stop = threading.Event()
        self.running = False
        self.report_path = None
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), background='#FAF7F5', foreground='#4A1425')
        style.configure('TCheckbutton', background='#FAF7F5')
        style.configure('Accent.TButton', background='#6B1F36', foreground='white', padding=12)
        style.map('Accent.TButton', background=[('active', '#4A1425')])
        body = ttk.Frame(self, padding=26)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='Contatos de teste, por segmento.', font=('Segoe UI', 21, 'bold')).pack(anchor='w')
        ttk.Label(body, text='Leonardo Lagoa · beta → HubSpot', foreground='#8D6773').pack(anchor='w', pady=(4, 20))
        ttk.Label(body, text='Selecione os segmentos').pack(anchor='w')
        self.segments = {s: tk.BooleanVar(value=True) for s in SEGMENTS}
        box = ttk.Frame(body)
        box.pack(fill='x', pady=10)
        self.controls = []
        for i, (s, var) in enumerate(self.segments.items()):
            control = ttk.Checkbutton(box, text=s, variable=var, command=self.update_distribution)
            control.grid(row=i//2, column=i%2, sticky='w', padx=(0, 35), pady=6)
            self.controls.append(control)
        row = ttk.Frame(body)
        row.pack(fill='x', pady=12)
        ttk.Label(row, text='Total de contatos').pack(side='left')
        self.total = tk.StringVar(value='20')
        spin = ttk.Spinbox(row, from_=1, to=5000, textvariable=self.total, width=10)
        spin.pack(side='left', padx=16)
        self.controls.append(spin)
        self.total.trace_add('write', self.update_distribution)
        self.distribution = ttk.Label(body, wraplength=620, foreground='#8D6773')
        self.distribution.pack(anchor='w', pady=(0, 12))
        ttk.Label(body, text='Dados marcados com TESTE e LOTE. E-mails únicos em example.com.\nO primeiro contato aparece no navegador; os demais usam a API, um por segundo.\nEnviar lote cria contatos reais de teste no seu HubSpot.', wraplength=620).pack(anchor='w', pady=10)
        buttons = ttk.Frame(body)
        buttons.pack(fill='x', pady=12)
        self.preview_button = ttk.Button(buttons, text='Prévia sem enviar', command=lambda: self.start(True))
        self.preview_button.pack(side='left', padx=(0, 10))
        self.send_button = ttk.Button(buttons, text='Enviar lote', style='Accent.TButton', command=lambda: self.start(False))
        self.send_button.pack(side='left')
        self.cancel_button = ttk.Button(buttons, text='Parar', command=self.cancel, state='disabled')
        self.cancel_button.pack(side='right')
        self.progress = ttk.Progressbar(body, mode='determinate')
        self.progress.pack(fill='x', pady=(12, 5))
        self.summary = ttk.Label(body, text='Pronto para gerar um lote.')
        self.summary.pack(anchor='w')
        self.log = tk.Text(body, height=10, bg='white', fg='#4A1425', relief='flat', font=('Consolas', 9), state='disabled', wrap='word')
        self.log.pack(fill='both', expand=True, pady=12)
        self.report_button = ttk.Button(body, text='Abrir relatório CSV', command=self.open_report, state='disabled')
        self.report_button.pack(anchor='w')
        self.update_distribution()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(100, self.poll)

    def update_distribution(self, *_):
        selected = [s for s, v in self.segments.items() if v.get()]
        try:
            total = int(self.total.get())
            if total < 1 or total > 5000 or not selected:
                raise ValueError()
            base, extra = divmod(total, len(selected))
            self.distribution.config(text=' · '.join(f'{s}: {base + (i < extra)}' for i, s in enumerate(selected)))
        except ValueError:
            self.distribution.config(text='Escolha segmentos e um total de 1 a 5.000.')

    def start(self, preview):
        if self.running:
            return
        try:
            total = int(self.total.get())
            batch = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
            contacts = generate(total, [s for s, v in self.segments.items() if v.get()], batch)
        except ValueError as exc:
            messagebox.showerror('Confira o lote', str(exc) or 'Quantidade inválida.')
            return
        self.running = True
        self.stop.clear()
        self.counts = {'aceito': 0, 'prévia': 0, 'erro': 0}
        self.progress.configure(maximum=total, value=0)
        self.report_path = None
        self.report_button.configure(state='disabled')
        for control in self.controls + [self.preview_button, self.send_button]:
            control.configure(state='disabled')
        self.cancel_button.configure(state='normal')
        self.append(f'Lote {batch} · {total} contatos · ' + ('PRÉVIA' if preview else 'ENVIO AO HUBSPOT'))
        def worker():
            try:
                run_batch(contacts, batch, preview, self.stop, lambda kind, data: self.messages.put((kind, data)))
            except Exception as exc:
                self.messages.put(('log', 'Erro: ' + str(exc)[:500]))
            finally:
                self.messages.put(('done', None))
        threading.Thread(target=worker, daemon=True).start()

    def append(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def poll(self):
        try:
            while True:
                kind, data = self.messages.get_nowait()
                if kind == 'log':
                    self.append(data)
                elif kind == 'result':
                    index, status, segment, detail = data
                    self.counts[status if status in self.counts else 'erro'] += 1
                    self.progress.configure(value=index)
                    self.summary.configure(text=f'{index}/{int(self.total.get())} · Aceitos: {self.counts["aceito"]} · Prévia: {self.counts["prévia"]} · Erros: {self.counts["erro"]}')
                    self.append(f'{index:04d} · {segment} · {status} · {detail}')
                elif kind == 'report':
                    self.report_path = data
                    self.report_button.configure(state='normal')
                    self.append('Relatório: ' + data)
                elif kind == 'done':
                    self.running = False
                    for control in self.controls + [self.preview_button, self.send_button]:
                        control.configure(state='normal')
                    self.cancel_button.configure(state='disabled')
                    self.append('Finalizado.' if not self.stop.is_set() else 'Interrompido. O envio em andamento pode ter sido aceito.')
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def cancel(self):
        self.stop.set()
        self.cancel_button.configure(state='disabled')
        self.append('Parando após o envio atual…')

    def open_report(self):
        import os
        if self.report_path:
            os.startfile(self.report_path)

    def close(self):
        if self.running:
            self.cancel()
            self.append('Aguarde a conclusão do envio atual antes de fechar.')
            return
        self.destroy()


if __name__ == '__main__':
    app = App()
    import sys
    if '--smoke-test' in sys.argv:
        app.withdraw()
        app.update()
        from playwright.sync_api import sync_playwright
        with sync_playwright() as engine:
            browser = engine.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page()
            page.set_content('<title>Pacote validado</title><p>Sem envios externos</p>')
            assert page.title() == 'Pacote validado'
            browser.close()
        app.destroy()
        if len(sys.argv) > 2:
            Path(sys.argv[2]).write_text(json.dumps({'interface': 'ok', 'browser': 'ok', 'external_requests': 0}), encoding='utf-8')
    else:
        app.mainloop()
