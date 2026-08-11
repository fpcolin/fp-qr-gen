"""Flooring Partners QR Code Generator.

Third-party requirements: qrcode, Pillow. Everything else is stdlib.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer

import updater

VENDOR = 'Flooring Partners'
APP_NAME = 'QR Code Generator'
VERSION = '2.1.0'

# Bumped only when the shape of the config file changes, never for an ordinary
# release. Keying the reset on VERSION would wipe everyone's saved folder and
# filename on every patch, which is exactly what they would not expect.
CONFIG_SCHEMA = 1

DEFAULT_LOGO = 'default-logo'
IMAGE_TYPES = [('Image files', '.png .jpg .jpeg .jfif .pjpeg .pjp')]
INVALID_FILENAME_CHARS = '<>:"/\\|?*'

DEFAULTS = {
    'schema': CONFIG_SCHEMA,
    'version': VERSION,
    'saveto_path': str(Path.home() / 'Downloads'),
    'saveto_name': 'qr_code',
    'option_open_image': True,
    'option_open_folder': False,
    'option_embed_logo': True,
    'option_round_edges': False,
    'embed_image': DEFAULT_LOGO,
}


def resource_path(name: str) -> Path:
    """Locate a bundled data file, whether frozen by PyInstaller or run from source."""
    base = getattr(sys, '_MEIPASS', None) or os.path.dirname(os.path.abspath(__file__))
    return Path(base) / name


def open_in_shell(target: Path) -> None:
    """Hand a file or folder to the OS default handler.

    os.startfile avoids the `start` shell-out, so a windowed .exe never flashes a
    console. AttributeError covers non-Windows, where startfile does not exist.
    """
    try:
        os.startfile(str(target))
    except (AttributeError, OSError):
        pass


class Config:
    """Settings kept in memory, written to disk only when a value actually changes."""

    def __init__(self) -> None:
        local_appdata = os.getenv('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local'
        self.path = Path(local_appdata) / VENDOR / APP_NAME / 'config.json'
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self) -> None:
        try:
            stored = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            stored = None

        # Reset only when the file's structure is unrecognisable, not when the
        # app version moves. Settings survive upgrades.
        if isinstance(stored, dict) and stored.get('schema') == CONFIG_SCHEMA:
            self._data.update({k: v for k, v in stored.items() if k in DEFAULTS})
            if self._data.get('version') != VERSION:
                self._data['version'] = VERSION   # record which build wrote it
                self.save()
        else:
            self.save()

        # Clean up config files from versions that used YAML.
        try:
            self.path.with_name('config.yml').unlink(missing_ok=True)
        except OSError:
            pass

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=2), encoding='utf-8')
        except OSError:
            pass  # Locked-down profile: carry on with in-memory settings.

    def __getitem__(self, key: str):
        return self._data[key]

    def set(self, key: str, value) -> None:
        if self._data.get(key) != value:
            self._data[key] = value
            self.save()


class QRGenerator:
    """Turns text into a saved PNG."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.logo_path = resource_path('fp_logo.png')

    def _embed_path(self) -> str | None:
        """Resolve the logo to embed, or None if it is switched off or missing."""
        if not self.config['option_embed_logo']:
            return None
        chosen = self.config['embed_image']
        candidate = self.logo_path if chosen == DEFAULT_LOGO else Path(chosen)
        return str(candidate) if candidate.is_file() else None

    @staticmethod
    def _unique_path(folder: Path, stem: str, suffix: str = '.png') -> Path:
        stem = ''.join(c for c in stem if c not in INVALID_FILENAME_CHARS).strip() or 'qr_code'
        candidate = folder / f'{stem}{suffix}'
        counter = 1
        while candidate.exists():
            candidate = folder / f'{stem} ({counter}){suffix}'
            counter += 1
        return candidate

    def generate(self, data: str) -> Path:
        folder = Path(self.config['saveto_path'])
        folder.mkdir(parents=True, exist_ok=True)

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(data)

        # Build kwargs once instead of branching through every on/off combination.
        kwargs = {}
        embed = self._embed_path()
        if embed:
            kwargs['embeded_image_path'] = embed
        if self.config['option_round_edges']:
            kwargs['module_drawer'] = RoundedModuleDrawer()
            kwargs['eye_drawer'] = RoundedModuleDrawer()

        image = qr.make_image(image_factory=StyledPilImage, **kwargs)
        path = self._unique_path(folder, self.config['saveto_name'])
        image.save(path)
        return path

    def reveal(self, path: Path) -> None:
        if self.config['option_open_image']:
            open_in_shell(path)
        if self.config['option_open_folder']:
            open_in_shell(path.parent)


def vcard_escape(value: str) -> str:
    """Escape the characters that carry structural meaning in a vCard field."""
    return (value.replace('\\', '\\\\')
                 .replace(';', r'\;')
                 .replace(',', r'\,')
                 .replace('\n', r'\n'))


class Gui:
    VCARD_FIELDS = (
        ('firstn', 'First name: ', 20),
        ('lastn', 'Last name: ', 20),
        ('email', 'Email: ', 40),
        ('cell', 'Mobile: ', 20),
        ('work', 'Work: ', 20),
        ('org', 'Company: ', 40),
        ('title', 'Title: ', 35),
        ('website_url', 'Web URL: ', 100),
    )
    PHONE_FIELDS = {'cell', 'work'}

    def __init__(self, config: Config, generator: QRGenerator) -> None:
        self.config = config
        self.qr = generator
        self.icon_path = resource_path('fp.ico')

        self.root = tk.Tk()
        # Hide before anything can map it. iconbitmap() and other wm calls below
        # force Tk to realise the window, so withdrawing later means it appears,
        # vanishes, then reappears centred - a flash of its own.
        self.root.withdraw()
        self.root.title(f'{VENDOR} {APP_NAME} v{VERSION}')
        self.root.resizable(False, False)
        self._set_icon(self.root)

        self.tabs = ttk.Notebook(self.root)
        self.url_tab = ttk.Frame(self.tabs)
        self.vcard_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.url_tab, text='URL')
        self.tabs.add(self.vcard_tab, text='vCard')

        self.url_var = tk.StringVar(self.root)
        self.vcard_vars = {key: tk.StringVar(self.root) for key, _, _ in self.VCARD_FIELDS}
        self.option_vars: dict[str, tk.BooleanVar] = {}  # Held here so tkinter cannot GC them.

    # ------------------------------------------------------------------ helpers

    def _set_icon(self, window: tk.Misc) -> None:
        try:
            window.iconbitmap(str(self.icon_path))
        except tk.TclError:
            pass  # Icon file absent when running from source.

    def _dialog(self, title: str) -> tuple[tk.Toplevel, ttk.Frame]:
        """Create a modal child window offset from the main one, plus its body frame."""
        window = tk.Toplevel(self.root)

        # A Toplevel is mapped the moment it is created, before geometry() moves
        # it and before any widgets exist. Windows therefore paints a small empty
        # frame at Tk's default position, which then jumps and fills - it reads
        # as a stray window flashing open and shut. Stay hidden until the dialog
        # is fully built, then reveal it in one step.
        window.withdraw()

        window.title(title)
        window.resizable(False, False)
        self._set_icon(window)

        # Tie the dialog to the main window: it stays on top of its parent and
        # gets no taskbar button of its own, which is another source of flicker.
        window.transient(self.root)

        x, y = (int(part) for part in self.root.geometry().split('+')[1:])
        window.geometry('+%d+%d' % (x + self.root.winfo_width() // 4,
                                    y + self.root.winfo_height() // 4))

        body = ttk.Frame(window)
        body.grid(column=0, row=0, sticky=tk.NW, padx=20, pady=20)

        window.bind('<Escape>', lambda _event: window.destroy())

        # Callers add their widgets after this returns, so reveal on the next
        # idle cycle - by then the layout is final and the window can be shown
        # at its true size. grab_set must wait too, or the modal grab applies
        # to a window the user cannot yet see.
        def reveal() -> None:
            window.deiconify()
            window.grab_set()
            window.focus_force()
            target = getattr(window, '_initial_focus', None)
            if target is not None:
                target.focus_set()

        window.after_idle(reveal)
        return window, body

    def _option_checkbutton(self, menu: tk.Menu, label: str, key: str) -> None:
        var = tk.BooleanVar(value=self.config[key])
        self.option_vars[key] = var
        menu.add_checkbutton(
            label=label, onvalue=True, offvalue=False, variable=var,
            command=lambda: self.config.set(key, var.get()),
        )

    @staticmethod
    def validate_phone(value: str) -> bool:
        return all(c.isdigit() or c in '+-() ' for c in value)

    # --------------------------------------------------------------------- menu

    def create_menubar(self) -> None:
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label='Change folder\u2026', command=self.choose_folder)
        file_menu.add_command(label='Check for updates\u2026',
                              command=lambda: self.check_for_updates(manual=True))
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.root.destroy)
        menubar.add_cascade(label='File', menu=file_menu)

        options_menu = tk.Menu(menubar, tearoff=False)
        options_menu.add_command(label='Change filename', command=self.draw_name_window)
        options_menu.add_command(label='Change embedded image', command=self.draw_embed_window)
        options_menu.add_separator()
        self._option_checkbutton(options_menu, 'Open image on generate', 'option_open_image')
        self._option_checkbutton(options_menu, 'Open folder on generate', 'option_open_folder')
        options_menu.add_separator()
        self._option_checkbutton(options_menu, 'Embed logo', 'option_embed_logo')
        self._option_checkbutton(options_menu, 'Round edges', 'option_round_edges')
        menubar.add_cascade(label='Options', menu=options_menu)

        menubar.add_command(label='Help', command=self.draw_help_window)
        self.root.config(menu=menubar)

    # --------------------------------------------------------------------- body

    def create_body(self) -> None:
        self.tabs.grid(column=0, row=0, sticky=tk.NW, padx=10, pady=(0, 10))

        # URL tab
        ttk.Label(self.url_tab, text='Enter URL: ').grid(
            column=0, row=0, sticky=tk.NE, padx=(10, 0), pady=(10, 0))
        url_entry = ttk.Entry(self.url_tab, textvariable=self.url_var, width=100)
        url_entry.grid(column=1, row=0, sticky=tk.NW, padx=(0, 10), pady=(10, 0))

        url_buttons = ttk.Frame(self.url_tab)
        url_buttons.grid(column=1, row=1, sticky=tk.NW)
        ttk.Button(url_buttons, text='Generate QR Code', command=self.generate_url).grid(
            column=0, row=0, sticky=tk.NW, pady=10)
        ttk.Button(url_buttons, text='Clear URL Field',
                   command=lambda: [self.url_var.set(''), url_entry.focus()]).grid(
            column=1, row=0, sticky=tk.NW, pady=10, padx=(10, 0))

        # vCard tab
        vcmd = (self.vcard_tab.register(self.validate_phone), '%P')
        for row, (key, label, width) in enumerate(self.VCARD_FIELDS):
            ttk.Label(self.vcard_tab, text=label).grid(
                column=0, row=row, sticky=tk.NE, pady=(10, 0), padx=(10, 0))
            extra = {'validate': 'key', 'validatecommand': vcmd} if key in self.PHONE_FIELDS else {}
            ttk.Entry(self.vcard_tab, textvariable=self.vcard_vars[key],
                      width=width, **extra).grid(
                column=1, row=row, sticky=tk.NW, pady=(10, 0), padx=(0, 10))

        vcard_buttons = ttk.Frame(self.vcard_tab)
        vcard_buttons.grid(column=1, row=len(self.VCARD_FIELDS), sticky=tk.NW)
        ttk.Button(vcard_buttons, text='Generate QR Code', command=self.generate_vcard).grid(
            column=0, row=0, sticky=tk.NW, pady=10)
        ttk.Button(vcard_buttons, text='Clear vCard Fields', command=self.clear_vcard).grid(
            column=1, row=0, sticky=tk.NW, pady=10, padx=(10, 0))

        self.root.bind('<Return>', lambda _event: self.generate_current_tab())
        url_entry.focus()

    # ---------------------------------------------------------------- generating

    def generate_current_tab(self) -> None:
        if self.tabs.index(self.tabs.select()) == 0:
            self.generate_url()
        else:
            self.generate_vcard()

    def generate_url(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning('Nothing to encode', 'Enter a URL first.', parent=self.root)
            return
        self._save_and_open(url)

    def generate_vcard(self) -> None:
        values = {key: var.get().strip() for key, var in self.vcard_vars.items()}
        if not values['firstn'] or not values['lastn']:
            messagebox.showwarning('Missing name',
                                   'First and last name are required.', parent=self.root)
            return

        first, last = vcard_escape(values['firstn']), vcard_escape(values['lastn'])
        lines = ['BEGIN:VCARD', 'VERSION:3.0',
                 f'N:{last};{first};;;', f'FN:{first} {last}']
        for key, prefix in (('org', 'ORG:'), ('title', 'TITLE:'),
                            ('cell', 'TEL;TYPE=CELL:'), ('work', 'TEL;TYPE=WORK:'),
                            ('email', 'EMAIL;TYPE=INTERNET,WORK:'), ('website_url', 'URL:')):
            if values[key]:
                lines.append(prefix + vcard_escape(values[key]))
        lines.append('END:VCARD')

        self._save_and_open('\r\n'.join(lines))

    def _save_and_open(self, data: str) -> None:
        try:
            path = self.qr.generate(data)
        except Exception as exc:
            messagebox.showerror('Could not create QR code', str(exc), parent=self.root)
            return
        self.qr.reveal(path)

    def clear_vcard(self) -> None:
        for var in self.vcard_vars.values():
            var.set('')
        self.vcard_tab.focus()

    # ------------------------------------------------------------------ updates

    def check_for_updates(self, manual: bool = False) -> None:
        """Look for a newer release. Silent on failure unless the user asked.

        Always runs off the UI thread: a synchronous call blocks the event loop
        for up to NETWORK_TIMEOUT seconds, which freezes and greys the window.
        """
        def done(manifest: dict | None) -> None:
            if manifest:
                self.offer_update(manifest)
            elif manual:
                messagebox.showinfo('No updates',
                                    f'You are running the latest version ({VERSION}).',
                                    parent=self.root)

        def worker() -> None:
            manifest = updater.check(VERSION)
            self.root.after(0, done, manifest)

        threading.Thread(target=worker, daemon=True).start()

    def offer_update(self, manifest: dict) -> None:
        notes = manifest.get('notes', '').strip()
        prompt = f'Version {manifest["version"]} is available.\nYou have {VERSION}.'
        if notes:
            prompt += f'\n\n{notes}'
        prompt += '\n\nInstall it now? The program will close briefly.'

        if not messagebox.askyesno('Update available', prompt, parent=self.root):
            return

        self.root.config(cursor='watch')
        self.root.update_idletasks()
        try:
            installer = updater.download(manifest)
            updater.apply(installer)
        except updater.UpdateError as exc:
            self.root.config(cursor='')
            messagebox.showerror('Update failed', str(exc), parent=self.root)
            return
        self.root.destroy()

    # ------------------------------------------------------------------ dialogs

    def draw_name_window(self) -> None:
        window, body = self._dialog('Change filename:')
        name_var = tk.StringVar(body, value=self.config['saveto_name'])

        def confirm(_event=None):
            self.config.set('saveto_name', name_var.get().strip() or 'qr_code')
            window.destroy()

        entry = ttk.Entry(body, textvariable=name_var, width=40)
        entry.grid(column=0, row=0, sticky=tk.NW, columnspan=2)
        ttk.Button(body, text='Confirm', command=confirm).grid(
            column=0, row=1, sticky=tk.NW, pady=10)
        ttk.Button(body, text='Cancel', command=window.destroy).grid(
            column=1, row=1, sticky=tk.NE, pady=10)

        window.bind('<Return>', confirm)
        window._initial_focus = entry

    def choose_folder(self) -> None:
        """Open the system folder picker at the current save location."""
        current = Path(self.config['saveto_path'])
        # A picker pointed at a deleted folder opens somewhere arbitrary, so
        # walk up to the nearest parent that still exists.
        while not current.is_dir() and current != current.parent:
            current = current.parent

        path = filedialog.askdirectory(
            parent=self.root,
            title='Select folder to save QR codes',
            initialdir=str(current),
            mustexist=True,
        )
        if path:
            self.config.set('saveto_path', os.path.normpath(path))

    def draw_embed_window(self) -> None:
        window, body = self._dialog('Change embedded image:')

        def change(_event=None):
            window.destroy()
            path = filedialog.askopenfilename(parent=self.root, filetypes=IMAGE_TYPES)
            if path:
                self.config.set('embed_image', os.path.normpath(path))

        def reset():
            self.config.set('embed_image', DEFAULT_LOGO)
            window.destroy()

        ttk.Label(body, text=f'Current embedded image: {self.config["embed_image"]}').grid(
            column=0, row=0, sticky=tk.NW, columnspan=3)
        ttk.Button(body, text='Change', command=change).grid(
            column=0, row=1, sticky=tk.NW, pady=10)
        ttk.Button(body, text='Reset', command=reset).grid(
            column=1, row=1, sticky=tk.N, pady=10)
        ttk.Button(body, text='Cancel', command=window.destroy).grid(
            column=2, row=1, sticky=tk.NE, pady=10)

        window.bind('<Return>', change)

    def draw_help_window(self) -> None:
        window, body = self._dialog('Help')
        message = (
            'Steps to use this program are below.\n\n'
            'URL:\n'
            '1. Copy the URL you want to convert into a QR code.\n'
            '2. Click the text field next to "Enter URL:" and press Ctrl + V.\n'
            '3. Click the "Generate QR Code" button.\n\n'
            'vCard:\n'
            '1. Fill out contact information in the vCard tab. First and last names '
            'are mandatory; every other field is optional and is left out of the\n'
            '   contact card if blank.\n'
            '2. Click the "Generate QR Code" button.\n\n'
            'File:\n'
            'Change folder - change where the QR code is saved\n'
            'Exit - close the program\n\n'
            'Options:\n'
            'Change filename - change the name of the file when a QR code is generated\n'
            'Change embedded image - use your own image in the middle of the QR code\n'
            'Open image on generate - open the finished QR code in your image viewer\n'
            'Open folder on generate - open the folder the QR code was saved to\n'
            'Embed logo - choose whether a logo is embedded in the created QR code\n'
            'Round edges - give the generated QR code rounded corners'
        )
        tk.Label(body, text=message, anchor='w', justify='left').grid(
            column=0, row=0, sticky=tk.NW, columnspan=2)
        ttk.Button(body, text='Close', command=window.destroy).grid(
            column=1, row=1, sticky=tk.NE, pady=10)
        window.bind('<Return>', lambda _event: window.destroy())

    # ---------------------------------------------------------------------- run

    def start(self) -> None:
        self.create_menubar()
        self.create_body()

        # Centre using the real requested size rather than hard-coded numbers.
        self.root.update_idletasks()
        width, height = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        self.root.geometry('+%d+%d' % (
            (self.root.winfo_screenwidth() - width) // 2,
            (self.root.winfo_screenheight() - height) // 2,
        ))
        self.root.deiconify()

        # Fire after the window is drawn so a slow network never delays startup.
        self.root.after(1200, self.check_for_updates)
        self.root.mainloop()


if __name__ == '__main__':
    config = Config()
    Gui(config, QRGenerator(config)).start()
