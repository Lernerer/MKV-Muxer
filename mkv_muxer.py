# SPDX-License-Identifier: GPL-2.0-or-later
"""
MKV Muxer 1.0.1 — пакетное добавление аудиодорожек в MKV.

Copyright (C) 2026 MKV Muxer contributors.

Эта программа распространяется под GNU General Public License версии 2
или (по вашему выбору) любой более поздней версии. Полный текст лицензии
находится в файле LICENSES/GPL-2.0.txt.
"""

import os
import queue
import re
import subprocess
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

APP_NAME = "MKV Muxer"
APP_VERSION = "1.0.1"

# ---------- Палитра ----------
BG = "#0E1015"
CARD = "#161A22"
FIELD = "#1D222C"
BORDER = "#2A3140"
TEXT = "#E9EDF5"
MUTED = "#8C96A8"
ACCENT = "#4C8DFF"
ACCENT_HOVER = "#6BA1FF"
ACCENT_DIM = "#1A2740"
GREEN = "#43D19E"
YELLOW = "#F2B84B"
RED = "#F16D6D"

AUDIO_EXTS = [".mka", ".ac3", ".aac", ".flac", ".dts", ".mp3", ".eac3", ".m4a", ".wav"]


def resource_path(*parts):
    """Путь к файлам, упакованным в EXE.

    В режиме --onefile PyInstaller распаковывает их в sys._MEIPASS.
    При запуске обычного .py берётся папка рядом со скриптом.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def _no_window_flags():
    """Не показывать консольное окно при вызове внешних утилит из GUI-сборки."""
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


class MkvMuxerApp(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1040x840")
        self.minsize(940, 760)
        try:
            self.iconbitmap(resource_path("app.ico"))
        except Exception:
            pass

        # --- Переменные состояния ---
        self.video_dir = tk.StringVar()
        self.audio_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.use_new_suffix = tk.BooleanVar(value=False)
        self.mode_hint = tk.StringVar()

        self._events = queue.Queue()
        self._worker = None
        self._stop_event = threading.Event()
        self._stage = None
        self._about = None

        self._build_ui()

        self.output_dir.trace_add("write", lambda *_: self._update_mode_hint())
        self.use_new_suffix.trace_add("write", lambda *_: self._update_mode_hint())
        self._update_mode_hint()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(80, self._poll_events)
        self.after(120, self._welcome)

    # ==================================================================
    #  Интерфейс
    # ==================================================================
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_header()
        self._build_paths_card()
        self._build_actions()
        self._build_log()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 14))
        header.grid_columnconfigure(0, weight=1)

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            title_block, text=APP_NAME,
            font=ctk.CTkFont("Segoe UI", 27, "bold"), text_color=TEXT
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_block, text="Пакетное добавление аудиодорожек в MKV",
            font=ctk.CTkFont("Segoe UI", 13), text_color=MUTED
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    def _build_paths_card(self):
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        card.grid(row=1, column=0, sticky="ew", padx=28)
        card.grid_columnconfigure(2, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=4, sticky="ew", padx=18, pady=(16, 4))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            head, text="Источники и сохранение",
            font=ctk.CTkFont("Segoe UI", 14, "bold"), text_color=TEXT
        ).grid(row=0, column=0, sticky="w")

        self._field_row(
            card, 1, "1", "Видео",
            self.video_dir, "Папка с .mkv файлами",
            lambda: self.select_dir(self.video_dir),
        )
        self._field_row(
            card, 2, "2", "Аудио",
            self.audio_dir, "Папка с .mka, .ac3, .flac …",
            lambda: self.select_dir(self.audio_dir),
        )
        self._field_row(
            card, 3, "3", "Сохранение",
            self.output_dir, "Пусто — заменить оригинал",
            lambda: self.select_dir(self.output_dir),
        )

        sep = ctk.CTkFrame(card, height=1, fg_color=BORDER, corner_radius=0)
        sep.grid(row=5, column=0, columnspan=4, sticky="ew", padx=18, pady=(10, 2))

        ctk.CTkLabel(
            card,
            text="Аудио: .mka .ac3 .aac .flac .dts .mp3 .eac3 .m4a .wav   ·   "
                 "серия определяется по имени (S01E05, E05)   ·   "
                 "пустое сохранение = замена оригинала",
            font=ctk.CTkFont("Segoe UI", 10), text_color="#5D6678",
            anchor="w",
        ).grid(row=4, column=0, columnspan=4, sticky="ew", padx=20, pady=(2, 0))

        self.suffix_switch = ctk.CTkSwitch(
            card,
            text="Добавлять суффикс _new (не заменять оригинал)",
            variable=self.use_new_suffix,
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=TEXT,
            progress_color=ACCENT,
            fg_color=BORDER,
            button_color="#C9D3E6",
            button_hover_color=TEXT,
            command=self._update_mode_hint,
        )
        self.suffix_switch.grid(row=6, column=1, columnspan=2, sticky="w", pady=(4, 14))

        self.mode_label = ctk.CTkLabel(
            card, textvariable=self.mode_hint,
            font=ctk.CTkFont("Segoe UI", 11), text_color=MUTED
        )
        self.mode_label.grid(row=6, column=2, columnspan=2, sticky="e", padx=(0, 18), pady=(4, 14))
    def _field_row(self, parent, row, number, label, var, placeholder, command):
        badge = ctk.CTkLabel(
            parent, text=number, width=24, height=24, corner_radius=8,
            fg_color=ACCENT_DIM, text_color=ACCENT,
            font=ctk.CTkFont("Segoe UI", 11, "bold")
        )
        badge.grid(row=row, column=0, padx=(18, 10), pady=6)

        ctk.CTkLabel(
            parent, text=label, width=88, anchor="w",
            font=ctk.CTkFont("Segoe UI", 12), text_color=MUTED
        ).grid(row=row, column=1, sticky="w", pady=6)

        entry = ctk.CTkEntry(
            parent, textvariable=var, placeholder_text=placeholder,
            height=36, corner_radius=9, border_width=1, border_color=BORDER,
            fg_color=FIELD, text_color=TEXT,
            font=ctk.CTkFont("Segoe UI", 12),
        )
        entry.grid(row=row, column=2, sticky="ew", padx=(4, 10), pady=6)

        ctk.CTkButton(
            parent, text="Обзор", width=84, height=34, corner_radius=9,
            fg_color=FIELD, hover_color=BORDER, border_width=1, border_color=BORDER,
            text_color=TEXT, font=ctk.CTkFont("Segoe UI", 12),
            command=command,
        ).grid(row=row, column=3, padx=(0, 18), pady=6)
        return entry

    def _build_actions(self):
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=28, pady=(14, 12))
        actions.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            actions, text="Готов к запуску",
            font=ctk.CTkFont("Segoe UI", 12), text_color=MUTED, anchor="w"
        )
        self.status_label.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.progress = ctk.CTkProgressBar(
            actions, height=8, corner_radius=4,
            fg_color=FIELD, progress_color=ACCENT
        )
        self.progress.grid(row=1, column=0, sticky="ew", padx=(0, 18))
        self.progress.set(0)

        self.btn_stop = ctk.CTkButton(
            actions, text="Остановить", width=120, height=42, corner_radius=10,
            fg_color=FIELD, hover_color=BORDER, border_width=1, border_color=BORDER,
            text_color=MUTED, font=ctk.CTkFont("Segoe UI", 12),
            state="disabled", command=self.stop_processing,
        )
        self.btn_stop.grid(row=0, column=1, rowspan=2, padx=(0, 10))

        self.btn_run = ctk.CTkButton(
            actions, text="▶  Запустить", width=196, height=42, corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#08111F",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            command=self.start_processing,
        )
        self.btn_run.grid(row=0, column=2, rowspan=2)

    def _build_log(self):
        log_card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        log_card.grid(row=3, column=0, sticky="nsew", padx=28, pady=(0, 10))
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(log_card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 4))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            head, text="Журнал",
            font=ctk.CTkFont("Segoe UI", 13, "bold"), text_color=TEXT
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            head, text="Очистить", width=84, height=26, corner_radius=8,
            fg_color="transparent", hover_color=FIELD,
            text_color=MUTED, font=ctk.CTkFont("Segoe UI", 11),
            command=self.clear_log,
        ).grid(row=0, column=1, sticky="e")

        self.log_area = ctk.CTkTextbox(
            log_card, fg_color=FIELD, corner_radius=10, border_width=0,
            text_color=TEXT, font=ctk.CTkFont("Consolas", 11),
            wrap="word", activate_scrollbars=True,
        )
        self.log_area.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 16))
        self.log_area.configure(state="disabled")
        for tag, color in (
            ("info", TEXT), ("muted", MUTED), ("ok", GREEN),
            ("warn", YELLOW), ("err", RED), ("accent", ACCENT),
        ):
            self.log_area.tag_config(tag, foreground=color)

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=28, pady=(0, 16))
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            footer,
            text=f"{APP_NAME} {APP_VERSION}  ·  GNU GPL v2+",
            font=ctk.CTkFont("Segoe UI", 10), text_color="#5D6678",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            footer, text="Лицензии и о программе", width=176, height=26,
            corner_radius=8, fg_color="transparent", hover_color=FIELD,
            text_color=MUTED, font=ctk.CTkFont("Segoe UI", 11),
            command=self._open_about,
        ).grid(row=0, column=1, sticky="e")

    # ==================================================================
    #  Диалоги выбора
    # ==================================================================
    def select_dir(self, var):
        path = filedialog.askdirectory(title="Выберите папку")
        if path:
            var.set(path)

    def clear_log(self):
        self.log_area.configure(state="normal")
        self.log_area.delete("1.0", "end")
        self.log_area.configure(state="disabled")

    # ==================================================================
    #  Извлечение номера серии
    # ==================================================================
    @staticmethod
    def extract_episode_number(filename):
        """
        Извлекает номер серии из имени файла.
        Поддерживает: S01E05, E05, Ep05, Episode 5, " - 05", "_05", " 05 ",
        SxxExx с разделителями (точка, _, -, x) и без нулей, формат 1x01,
        а также нумерацию вида "Season 2 Episode 3" / "Сезон 2 ... 3".
        Возвращает строку с номером (2 цифры) или None.
        """
        name = os.path.splitext(os.path.basename(filename))[0]

        m = re.search(r'[Ss]\d{1,2}[\s._xX\-]*[Ee](\d{1,3})', name)
        if m:
            return m.group(1).zfill(2)

        m = re.search(r'(?:^|[^A-Za-z])(?:E|Ep|Episode)[\s._-]*(\d{1,3})', name, re.IGNORECASE)
        if m:
            return m.group(1).zfill(2)

        m = re.search(r'(?<![\d])(\d{1,2})[xX](\d{1,2})(?![\d])', name)
        if m:
            return m.group(2).zfill(2)

        m = re.search(
            r'(?:season|сезон)[\s._-]*(\d+)[\s._-]*(?:episode|episod|часть|part|series|серия)[\s._-]*(\d+)',
            name,
            re.IGNORECASE,
        )
        if m:
            return m.group(2).zfill(2)

        candidates = re.findall(r'(?:^|[\s._-])(\d{1,3})(?=[\s._-]|$)', name)
        if candidates:
            return candidates[-1].zfill(2)

        return None

    # ==================================================================
    #  Запуск и остановка
    # ==================================================================
    def start_processing(self):
        mkvmerge = resource_path("MKVToolNix", "mkvmerge.exe")
        v_dir = self.video_dir.get().strip()
        a_dir = self.audio_dir.get().strip()
        out_dir = self.output_dir.get().strip()
        use_suffix = self.use_new_suffix.get()

        errors = []
        if not v_dir or not os.path.isdir(v_dir):
            errors.append("папка с видео не найдена")
        if not a_dir or not os.path.isdir(a_dir):
            errors.append("папка с аудио не найдена")
        if out_dir:
            try:
                os.makedirs(out_dir, exist_ok=True)
            except OSError as exc:
                errors.append(f"не удалось создать папку вывода:\n{exc}")
            else:
                if not use_suffix and os.path.normcase(os.path.abspath(out_dir)) == \
                        os.path.normcase(os.path.abspath(v_dir)):
                    errors.append(
                        "папка вывода совпадает с папкой видео. "
                        "Включите суффикс _new или выберите другую папку."
                    )
        if errors:
            messagebox.showerror(
                "Проверьте настройки",
                "\n\n".join("• " + e for e in errors),
                parent=self,
            )
            return

        if not out_dir and not use_suffix:
            if not messagebox.askyesno(
                "Замена оригиналов",
                "Папка вывода не выбрана, суффикс _new отключён.\n\n"
                "Оригинальные MKV-файлы будут заменены.\nПродолжить?",
                icon="warning", parent=self,
            ):
                return

        self._stop_event.clear()
        self.progress.set(0)
        mode = ("в выбранную папку" if out_dir
                else "рядом с оригиналом, суффикс _new" if use_suffix
                else "замена оригинала")
        self._append_log("─" * 64, "muted")
        self._append_log(f"Запуск · режим: {mode}", "accent")
        self._set_running(True)
        self.status_label.configure(text="Сканирование папок…", text_color=MUTED)

        self._worker = threading.Thread(
            target=self._process,
            args=(mkvmerge, v_dir, a_dir, out_dir, use_suffix),
            daemon=True,
        )
        self._worker.start()

    def stop_processing(self):
        self._stop_event.set()
        self.btn_stop.configure(state="disabled", text="Останавливаю…")
        self.status_label.configure(
            text="Останавливаю после текущего файла…", text_color=YELLOW
        )
        self._append_log("Запрошена остановка после текущего файла.", "warn")

    def _set_running(self, running):
        if running:
            self.btn_run.configure(state="disabled", text="Обработка…")
            self.btn_stop.configure(state="normal", text="Остановить")
        else:
            self.btn_run.configure(state="normal", text="▶  Запустить")
            self.btn_stop.configure(state="disabled", text="Остановить")

    def _on_close(self):
        if self._worker is not None and self._worker.is_alive():
            if not messagebox.askyesno(
                "Выход",
                "Обработка ещё идёт. Закрыть программу?",
                icon="warning", parent=self,
            ):
                return
            self._stop_event.set()
        self.destroy()

    # ==================================================================
    #  Обмен сообщениями с рабочим потоком
    # ==================================================================
    def _post(self, kind, **payload):
        self._events.put((kind, payload))

    def _poll_events(self):
        try:
            while True:
                kind, data = self._events.get_nowait()
                if kind == "log":
                    self._append_log(data["text"], data.get("tag", "info"))
                elif kind == "progress":
                    total = max(data["total"], 1)
                    self.progress.set(min(data["done"] / total, 1.0))
                elif kind == "status":
                    self.status_label.configure(text=data["text"], text_color=data.get("color", MUTED))
                elif kind == "finished":
                    self._on_finished(data)
        except queue.Empty:
            pass
        self.after(80, self._poll_events)

    def _append_log(self, message, tag="info"):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", message + "\n", tag)
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def _on_finished(self, data):
        self._set_running(False)
        total = data.get("total", 0)
        success = data.get("success", 0)
        skipped = data.get("skipped", 0)
        stopped = data.get("stopped", False)
        fatal = data.get("fatal")

        mode = ("stopped" if stopped else "fatal" if fatal else "done")
        if mode == "stopped":
            self.status_label.configure(
                text=f"Остановлено · успешно {success} из {total}", text_color=YELLOW
            )
            self._append_log(f"Остановлено. Успешно: {success} из {total}", "warn")
        elif mode == "fatal":
            self.status_label.configure(text="Ошибка обработки", text_color=RED)
            self._append_log(f"Критическая ошибка: {fatal}", "err")
        else:
            self.status_label.configure(
                text=f"Готово · успешно {success} из {total}", text_color=GREEN
            )
            self._append_log(f"Готово. Успешно: {success} из {total}", "ok")

        lines = [f"Успешно: {success} из {total}"]
        if skipped:
            lines.append(f"Пропущено: {skipped}")
        if stopped:
            lines.insert(0, "Обработка остановлена пользователем.")
        if fatal:
            lines.insert(0, f"Критическая ошибка: {fatal}")

        if stopped or fatal:
            messagebox.showwarning("Завершено", "\n".join(lines), parent=self)
        else:
            messagebox.showinfo("Завершено", "\n".join(lines), parent=self)

    # ==================================================================
    #  Основная логика (рабочий поток)
    # ==================================================================
    def _process(self, mkvmerge, v_dir, a_dir, out_dir, use_suffix):
        in_place = not out_dir
        success = 0
        skipped = 0
        stopped = False
        total = 0
        processed = 0
        try:
            video_files = sorted(
                f for f in os.listdir(v_dir) if f.lower().endswith(".mkv")
            )
            total = len(video_files)
            if not video_files:
                self._post("log", text="Не найдено видеофайлов .mkv в указанной папке.", tag="err")
                self._post("status", text="Видеофайлы не найдены", color=RED)
                self._post("finished", success=0, total=0, skipped=0, stopped=False)
                return

            audio_files = sorted(
                f for f in os.listdir(a_dir)
                if os.path.splitext(f)[1].lower() in AUDIO_EXTS
            )
            audio_index = {}
            duplicates = 0
            for af in audio_files:
                ep = self.extract_episode_number(af)
                if ep:
                    if ep not in audio_index:
                        audio_index[ep] = os.path.join(a_dir, af)
                    else:
                        duplicates += 1
                        self._post(
                            "log",
                            text=f"  ⚠ серия {ep}: несколько аудио, используется "
                                 f"{os.path.basename(audio_index[ep])}",
                            tag="warn",
                        )
                else:
                    self._post("log", text=f"  ⚠ серия не определена: {af}", tag="warn")

            self._post(
                "log",
                text=f"Видео: {total} · аудио с номером серии: {len(audio_index)}"
                     + (f" · дублей: {duplicates}" if duplicates else ""),
                tag="info",
            )

            for index, v_file in enumerate(video_files, start=1):
                if self._stop_event.is_set():
                    stopped = True
                    break

                v_full_path = os.path.join(v_dir, v_file)
                ep = self.extract_episode_number(v_file)
                processed = index
                self._post("progress", done=index - 1, total=total)

                if not ep:
                    skipped += 1
                    self._post("log", text=f"  ↷ пропуск: {v_file} — номер серии не найден", tag="muted")
                    continue

                found_audio = audio_index.get(ep)
                if not found_audio:
                    skipped += 1
                    self._post("log", text=f"  ↷ пропуск: {v_file} — аудио для серии {ep} не найдено", tag="warn")
                    continue

                # --- Выбор выходного файла (3 варианта) ---
                if not in_place:
                    out_file = os.path.join(out_dir, v_file)
                    replace_original = False
                elif use_suffix:
                    base, ext = os.path.splitext(v_full_path)
                    out_file = f"{base}_new{ext}"
                    replace_original = False
                else:
                    out_file = v_full_path + ".tmp.mkv"
                    replace_original = True

                self._post("status", text=f"Обработка {index} из {total} · серия {ep}", color=ACCENT)
                self._post(
                    "log",
                    text=f"▸ {v_file}  ←  {os.path.basename(found_audio)}",
                    tag="info",
                )

                cmd = [mkvmerge, "-o", out_file, v_full_path, found_audio]
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True,
                        encoding="utf-8", errors="replace",
                        creationflags=_no_window_flags(),
                    )
                except Exception as exc:
                    if replace_original and os.path.exists(out_file):
                        self._cleanup(out_file)
                    self._post("log", text=f"  ✕ системная ошибка: {exc}", tag="err")
                    continue

                # mkvmerge: 0 — успех, 1 — успех с предупреждениями, 2+ — ошибка
                if result.returncode in (0, 1):
                    if replace_original:
                        try:
                            os.replace(out_file, v_full_path)
                        except Exception as exc:
                            self._post(
                                "log",
                                text=f"  ✕ не удалось заменить оригинал: {exc}", tag="err",
                            )
                            self._post("log", text=f"     временный файл: {out_file}", tag="muted")
                            continue
                    success += 1
                    if result.returncode == 1:
                        self._post(
                            "log",
                            text="  ✓ готово (mkvmerge вернул предупреждение)", tag="warn",
                        )
                        warning = self._first_warning(result)
                        if warning:
                            self._post("log", text=f"     {warning}", tag="muted")
                    else:
                        target = "оригинал заменён" if replace_original else out_file
                        self._post("log", text=f"  ✓ готово: {target}", tag="ok")
                else:
                    if replace_original and os.path.exists(out_file):
                        self._cleanup(out_file)
                    details = (result.stderr or "").strip()
                    if not details:
                        lines = [ln.strip() for ln in (result.stdout or "").splitlines() if ln.strip()]
                        details = lines[-1] if lines else "без описания"
                    self._post("log", text=f"  ✕ ошибка mkvmerge: {details[:300]}", tag="err")

                self._post("progress", done=index, total=total)

            if stopped:
                self._post("log", text="Обработка остановлена.", tag="warn")
            self._post("progress", done=processed if stopped else total, total=total)
            self._post("finished", success=success, total=total, skipped=skipped, stopped=stopped)

        except Exception as exc:
            if self._stop_event.is_set():
                self._post("finished", success=success, total=total, skipped=skipped, stopped=True)
            else:
                self._post("finished", success=success, total=total, skipped=skipped,
                           stopped=False, fatal=str(exc))

    @staticmethod
    def _cleanup(path):
        try:
            os.remove(path)
        except OSError:
            pass

    @staticmethod
    def _first_warning(result):
        for line in ((result.stdout or "") + "\n" + (result.stderr or "")).splitlines():
            low = line.lower()
            if "warning" in low or "предупреждение" in low:
                return line.strip()[:240]
        return ""

    # ==================================================================
    #  Режим сохранения и лицензии
    # ==================================================================
    def _update_mode_hint(self):
        out_dir = self.output_dir.get().strip()
        if out_dir:
            self.mode_hint.set("→ в выбранную папку")
            self.mode_label.configure(text_color=ACCENT)
            if hasattr(self, "suffix_switch"):
                self.suffix_switch.configure(state="disabled")
        else:
            if self.use_new_suffix.get():
                self.mode_hint.set("→ рядом с оригиналом, суффикс _new")
                self.mode_label.configure(text_color=ACCENT)
            else:
                self.mode_hint.set("→ замена оригинала")
                self.mode_label.configure(text_color=YELLOW)
            if hasattr(self, "suffix_switch"):
                self.suffix_switch.configure(state="normal")

    def _open_about(self):
        if self._about is not None and self._about.winfo_exists():
            self._about.focus()
            return

        win = ctk.CTkToplevel(self)
        self._about = win
        win.title(f"О программе — {APP_NAME}")
        win.geometry("640x505")
        win.resizable(False, False)
        win.configure(fg_color=BG)
        win.transient(self)
        win.after(120, win.grab_set)

        ctk.CTkLabel(
            win, text=APP_NAME,
            font=ctk.CTkFont("Segoe UI", 24, "bold"), text_color=TEXT
        ).pack(anchor="w", padx=26, pady=(24, 0))
        ctk.CTkLabel(
            win, text=f"Версия {APP_VERSION} · GNU General Public License v2 или новее",
            font=ctk.CTkFont("Segoe UI", 12), text_color=MUTED
        ).pack(anchor="w", padx=26, pady=(2, 14))

        lic_card = ctk.CTkFrame(win, fg_color=CARD, corner_radius=14)
        lic_card.pack(fill="x", padx=26, pady=(0, 12))
        ctk.CTkLabel(
            lic_card, text="Лицензии",
            font=ctk.CTkFont("Segoe UI", 13, "bold"), text_color=TEXT
        ).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(
            lic_card,
            text="Полные тексты лицензий поставляются вместе с программой\n"
                 "и доступны по кнопкам ниже.",
            font=ctk.CTkFont("Segoe UI", 11), text_color=MUTED, justify="left",
        ).pack(anchor="w", padx=16)

        buttons = ctk.CTkFrame(lic_card, fg_color="transparent")
        buttons.pack(anchor="w", padx=14, pady=(10, 14))
        for text, name in (
            ("GPL-2.0", "GPL-2.0.txt"),
            ("Сторонние компоненты", "THIRD_PARTY_NOTICES.txt"),
            ("Исходный код программы", "mkv_muxer.py"),
        ):
            ctk.CTkButton(
                buttons, text=text, width=150, height=30, corner_radius=8,
                fg_color=FIELD, hover_color=BORDER, border_width=1, border_color=BORDER,
                text_color=TEXT, font=ctk.CTkFont("Segoe UI", 11),
                command=lambda n=name: self._open_license(n),
            ).pack(side="left", padx=4)

        ctk.CTkLabel(
            win,
            text="Copyright (C) 2026 MKV Muxer contributors.\n"
                 "Программа предоставляется БЕЗ КАКИХ-ЛИБО ГАРАНТИЙ.",
            font=ctk.CTkFont("Segoe UI", 10), text_color="#5D6678", justify="left",
        ).pack(anchor="w", padx=26, pady=(0, 8))

        ctk.CTkButton(
            win, text="Закрыть", width=120, height=34, corner_radius=9,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#08111F",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            command=win.destroy,
        ).pack(anchor="e", padx=26, pady=(4, 18))

    def _open_license(self, name):
        candidates = [
            resource_path("LICENSES", name),
            resource_path(name),
            os.path.join(os.getcwd(), "LICENSES", name),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "LICENSES", name),
        ]
        for path in candidates:
            if os.path.isfile(path):
                try:
                    os.startfile(path)  # noqa: S606 — Windows-only приложение
                    return
                except OSError as exc:
                    messagebox.showwarning("Лицензии", f"Не удалось открыть файл:\n{exc}", parent=self)
                    return
        messagebox.showwarning(
            "Лицензии",
            f"Файл {name} не найден рядом с программой.\n"
            "Он входит в поставку в папке LICENSES.",
            parent=self,
        )

    def _welcome(self):
        self._append_log(f"{APP_NAME} {APP_VERSION} — готов к работе.", "accent")
        self._append_log(
            "Укажите папки и нажмите «Запустить».",
            "muted",
        )
        self._append_log(
            "Лицензия: GNU GPL v2+. Тексты лицензий — в разделе «Лицензии и о программе».",
            "muted",
        )


def main():
    ctk.set_appearance_mode("dark")
    app = MkvMuxerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
