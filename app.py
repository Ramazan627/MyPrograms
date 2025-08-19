#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


def normalize_phone(raw_phone: str) -> str:
    """Normalize phone to +<digits>, e.g. +79251989091.

    Rules:
    - Keep leading '+' if present; strip all non-digits except leading '+'.
    - If no leading '+', try to infer:
        - If starts with '8' and has 11 digits → replace leading '8' with '+7'.
        - If starts with '7' and has 11 digits → add leading '+'.
        - Otherwise, add '+' prefix to the digits.
    """
    if raw_phone is None:
        return ""

    phone = raw_phone.strip()

    # Extract digits
    digits = re.sub(r"\D", "", phone)

    # Preserve leading + if originally present
    has_plus = phone.startswith("+")

    if has_plus:
        return "+" + digits

    if len(digits) == 11 and digits.startswith("8"):
        return "+7" + digits[1:]

    if len(digits) == 11 and digits.startswith("7"):
        return "+" + digits

    # Fallback: just add plus
    return "+" + digits if digits else ""


def parse_contacts(text: str):
    """Parse input text into list of (name, phone) pairs.

    The simplest rule per requirements: lines come in pairs: name line, then phone line.
    Empty lines are ignored. If trailing name has no phone, it is ignored with a warning.
    """
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]

    pairs = []
    warnings = []

    i = 0
    while i < len(lines):
        name = lines[i]
        phone = None
        if i + 1 < len(lines):
            phone = lines[i + 1]
            i += 2
        else:
            i += 1
            warnings.append(f"Строка с именем без телефона пропущена: '{name}'")
            break

        norm_phone = normalize_phone(phone)
        if not norm_phone:
            warnings.append(f"Не удалось распознать телефон для: '{name}' (строка: '{phone}')")
            continue

        pairs.append((name, norm_phone))

    return pairs, warnings


def to_vcard(entries):
    """Convert list of (name, phone) to vCard 3.0 blocks."""
    blocks = []
    for name, phone in entries:
        block = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"FN:{name}",
            f"TEL;TYPE=CELL:{phone}",
            "END:VCARD",
        ]
        blocks.append("\n".join(block))
    return "\n".join(blocks)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Текст → vCard (VCF)")
        self.geometry("980x540")

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Columns: input | controls | output
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=0)
        main.columnconfigure(2, weight=1)
        main.rowconfigure(1, weight=1)

        # Labels
        ttk.Label(main, text="Ввод (имя на строке, затем телефон)").grid(row=0, column=0, sticky="w")
        ttk.Label(main, text="Результат (vCard 3.0)").grid(row=0, column=2, sticky="w")

        # Input Text with scrollbar
        input_frame = ttk.Frame(main)
        input_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        input_frame.rowconfigure(0, weight=1)
        input_frame.columnconfigure(0, weight=1)

        self.input_text = tk.Text(input_frame, wrap=tk.NONE, undo=True)
        self.input_text.grid(row=0, column=0, sticky="nsew")

        in_scroll_y = ttk.Scrollbar(input_frame, orient="vertical", command=self.input_text.yview)
        in_scroll_y.grid(row=0, column=1, sticky="ns")
        self.input_text.configure(yscrollcommand=in_scroll_y.set)

        in_scroll_x = ttk.Scrollbar(input_frame, orient="horizontal", command=self.input_text.xview)
        in_scroll_x.grid(row=1, column=0, sticky="ew")
        self.input_text.configure(xscrollcommand=in_scroll_x.set)

        # Explicit paste bindings (Ctrl+V)
        self.input_text.bind("<Control-v>", self._on_ctrl_v)
        self.input_text.bind("<Control-V>", self._on_ctrl_v)

        # Controls
        controls = ttk.Frame(main)
        controls.grid(row=1, column=1, sticky="ns")
        for _ in range(6):
            controls.rowconfigure(_, weight=0)
        controls.rowconfigure(6, weight=1)

        ttk.Button(controls, text="Преобразовать →", command=self.on_convert).grid(row=0, column=0, pady=(0, 6))
        ttk.Button(controls, text="Копировать", command=self.on_copy).grid(row=1, column=0, pady=6)
        ttk.Button(controls, text="Сохранить .vcf", command=self.on_save).grid(row=2, column=0, pady=6)
        ttk.Button(controls, text="Очистить", command=self.on_clear).grid(row=3, column=0, pady=6)

        # Output Text with scrollbar
        output_frame = ttk.Frame(main)
        output_frame.grid(row=1, column=2, sticky="nsew", padx=(10, 0))
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)

        self.output_text = tk.Text(output_frame, wrap=tk.NONE)
        self.output_text.grid(row=0, column=0, sticky="nsew")

        out_scroll_y = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        out_scroll_y.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=out_scroll_y.set)

        out_scroll_x = ttk.Scrollbar(output_frame, orient="horizontal", command=self.output_text.xview)
        out_scroll_x.grid(row=1, column=0, sticky="ew")
        self.output_text.configure(xscrollcommand=out_scroll_x.set)

        # Example placeholder
        example = (
            "Азиза Лавры Узбечка\n"
            "+7 925 198-90-91\n"
            "Аида Лавры\n"
            "+7 928 218-00-04\n"
            "Алжана Лавры ASADULAEVA\n"
            "+7 967 619-99-99\n"
        )
        self.input_text.insert("1.0", example)

    def on_convert(self):
        src = self.input_text.get("1.0", tk.END)
        entries, warnings = parse_contacts(src)

        result = to_vcard(entries)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", result)

        if warnings:
            messagebox.showwarning("Предупреждения", "\n".join(warnings))

    def on_copy(self):
        data = self.output_text.get("1.0", tk.END).strip()
        if not data:
            messagebox.showinfo("Копирование", "Нет данных для копирования")
            return
        self.clipboard_clear()
        self.clipboard_append(data)
        messagebox.showinfo("Копирование", "Готово. Результат скопирован в буфер обмена.")

    def on_save(self):
        data = self.output_text.get("1.0", tk.END).strip()
        if not data:
            messagebox.showinfo("Сохранение", "Нет данных для сохранения")
            return
        path = filedialog.asksaveasfilename(
            title="Сохранить как",
            defaultextension=".vcf",
            filetypes=[("vCard files", "*.vcf"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            messagebox.showinfo("Сохранение", f"Файл сохранён: {path}")
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл\n{exc}")

    def on_clear(self):
        self.input_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)

    def _on_ctrl_v(self, event):
        # Ensure Ctrl+V works reliably
        try:
            self.input_text.event_generate("<<Paste>>")
            return "break"
        except Exception:
            return None


def main():
    try:
        app = App()
        app.mainloop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    # Ensure UTF-8 on Windows console if started from terminal
    try:
        if sys.platform.startswith("win"):
            import os
            os.system("")
    except Exception:
        pass
    main()


