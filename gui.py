#!/usr/bin/env python3
"""
gui.py -- Desktop GUI for the Student Attendance Management System.

Wraps the exact same classes used by sams.py / infovis.py / investigate.py
(SamsPipeline, AttendanceRepository, AttendanceVisualizer, SignatureVerifier)
so the GUI and the CLI tools stay in sync -- no logic is duplicated here,
only presentation.

Run with: python gui.py
"""

import os
import sys
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk

from core.roster import Roster
from data.repository import AttendanceRepository
from sams import SamsPipeline
from viz.visualizer import AttendanceVisualizer
from core.verifier import SignatureVerifier

APP_BG = "#F4F3EF"
CARD_BG = "#FFFFFF"
ACCENT = "#185FA5"
SUCCESS = "#0F6E56"
DANGER = "#993C1D"
TEXT_PRIMARY = "#2C2C2A"
TEXT_SECONDARY = "#5F5E5A"
BORDER = "#D3D1C7"


class SamsGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SAMS - Student Attendance Management System")
        self.geometry("1180x760")
        self.configure(bg=APP_BG)
        self.minsize(900, 600)

        self.db_path = tk.StringVar(value="attendance.db")
        self.log_queue = queue.Queue()

        self._build_style()
        self._build_layout()
        self._poll_log_queue()
        self._refresh_overview()
        self._refresh_student_lists()

    # ---------- styling ----------

    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=APP_BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 8), font=("Helvetica", 11))
        style.configure("TFrame", background=APP_BG)
        style.configure("Card.TFrame", background=CARD_BG)
        style.configure("TLabel", background=APP_BG, foreground=TEXT_PRIMARY, font=("Helvetica", 11))
        style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT_PRIMARY, font=("Helvetica", 11))
        style.configure("Heading.TLabel", background=APP_BG, foreground=TEXT_PRIMARY, font=("Helvetica", 15, "bold"))
        style.configure("Secondary.TLabel", background=APP_BG, foreground=TEXT_SECONDARY, font=("Helvetica", 10))
        style.configure("Accent.TButton", font=("Helvetica", 11, "bold"))
        style.configure("Treeview", rowheight=26, font=("Helvetica", 10))
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))

    def _build_layout(self):
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill="x", padx=20, pady=(16, 8))
        ttk.Label(header, text="Student Attendance Management System", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(header, text="CS402.3 - image processing + attendance visualization",
                  style="Secondary.TLabel").pack(anchor="w")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=20, pady=10)

        self.process_tab = ttk.Frame(notebook, style="TFrame")
        self.overview_tab = ttk.Frame(notebook, style="TFrame")
        self.visualize_tab = ttk.Frame(notebook, style="TFrame")
        self.investigate_tab = ttk.Frame(notebook, style="TFrame")

        notebook.add(self.process_tab, text="  Process sheet  ")
        notebook.add(self.overview_tab, text="  Attendance overview  ")
        notebook.add(self.visualize_tab, text="  Student chart  ")
        notebook.add(self.investigate_tab, text="  Signature check  ")

        self._build_process_tab()
        self._build_overview_tab()
        self._build_visualize_tab()
        self._build_investigate_tab()

    # ---------- Tab 1: Process sheet ----------

    def _build_process_tab(self):
        form = ttk.Frame(self.process_tab, style="Card.TFrame", padding=16)
        form.pack(fill="x", pady=(0, 12))

        self.image_path = tk.StringVar()
        self.xml_path = tk.StringVar(value=os.path.join("sample_images", "info.xml"))

        self._file_row(form, "Signing sheet image:", self.image_path, 0,
                        filetypes=[("Images", "*.png *.jpg *.jpeg")])
        self._file_row(form, "info.xml roster:", self.xml_path, 1,
                        filetypes=[("XML files", "*.xml")])
        self._file_row(form, "Database file:", self.db_path, 2,
                        filetypes=[("SQLite DB", "*.db")], save=True)

        btn = ttk.Button(form, text="Process sheet", style="Accent.TButton", command=self._on_process_clicked)
        btn.grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))

        body = ttk.Frame(self.process_tab, style="TFrame")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        log_card = ttk.Frame(body, style="Card.TFrame", padding=12)
        log_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(log_card, text="Processing log", style="Card.TLabel", font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.log_text = tk.Text(log_card, bg="#111111", fg="#D3D1C7", font=("Courier", 9),
                                 height=20, relief="flat", wrap="word")
        self.log_text.pack(fill="both", expand=True, pady=(6, 0))
        self.log_text.configure(state="disabled")

        result_card = ttk.Frame(body, style="Card.TFrame", padding=12)
        result_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ttk.Label(result_card, text="Result for this sheet", style="Card.TLabel", font=("Helvetica", 11, "bold")).pack(anchor="w")

        columns = ("student", "index", "status", "ink_ratio")
        self.result_tree = ttk.Treeview(result_card, columns=columns, show="headings", height=12)
        for col, label, width in [("student", "Student", 170), ("index", "Index", 90),
                                   ("status", "Status", 80), ("ink_ratio", "Ink ratio", 80)]:
            self.result_tree.heading(col, text=label)
            self.result_tree.column(col, width=width, anchor="w")
        self.result_tree.tag_configure("present", foreground=SUCCESS)
        self.result_tree.tag_configure("absent", foreground=DANGER)
        self.result_tree.pack(fill="both", expand=True, pady=(6, 0))

    def _file_row(self, parent, label, var, row, filetypes, save=False):
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        entry = tk.Entry(parent, textvariable=var, width=50, relief="solid", bd=1)
        entry.grid(row=row, column=1, sticky="we", padx=8, pady=4)
        parent.columnconfigure(1, weight=1)

        def browse():
            if save:
                path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=filetypes)
            else:
                path = filedialog.askopenfilename(filetypes=filetypes)
            if path:
                var.set(path)

        ttk.Button(parent, text="Browse...", command=browse).grid(row=row, column=2, pady=4)

    def _on_process_clicked(self):
        image_path = self.image_path.get().strip()
        xml_path = self.xml_path.get().strip()
        if not image_path or not os.path.exists(image_path):
            messagebox.showerror("Missing image", "Please choose a valid signing sheet image.")
            return
        if not xml_path or not os.path.exists(xml_path):
            messagebox.showerror("Missing roster", "Please choose a valid info.xml file.")
            return

        self._clear_log()
        for row in self.result_tree.get_children():
            self.result_tree.delete(row)

        thread = threading.Thread(target=self._run_pipeline, args=(image_path, xml_path), daemon=True)
        thread.start()

    def _run_pipeline(self, image_path, xml_path):
        try:
            roster = Roster.from_xml(xml_path)
            pipeline = SamsPipeline(db_path=self.db_path.get(), output_dir="output")

            original_log = pipeline._log

            def gui_log(msg):
                original_log(msg)
                self.log_queue.put(("log", msg))

            pipeline._log = gui_log
            records = pipeline.process_sheet(image_path, roster)
            self.log_queue.put(("done", records))
        except Exception as e:
            self.log_queue.put(("error", str(e)))

    def _poll_log_queue(self):
        try:
            while True:
                kind, payload = self.log_queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "done":
                    self._append_log("Processing complete.")
                    self._populate_results(payload)
                    self._refresh_overview()
                    self._refresh_student_lists()
                elif kind == "error":
                    self._append_log(f"ERROR: {payload}")
                    messagebox.showerror("Processing failed", payload)
        except queue.Empty:
            pass
        self.after(150, self._poll_log_queue)

    def _append_log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _populate_results(self, records):
        for r in records:
            status = "Present" if r.present else "Absent"
            tag = "present" if r.present else "absent"
            self.result_tree.insert("", "end", values=(r.student_name, r.student_index, status,
                                                         f"{r.ink_ratio:.4f}"), tags=(tag,))

    # ---------- Tab 2: Attendance overview ----------

    def _build_overview_tab(self):
        top = ttk.Frame(self.overview_tab, style="TFrame")
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="All processed sheets, all students", style="Heading.TLabel").pack(side="left")
        ttk.Button(top, text="Refresh", command=self._refresh_overview).pack(side="right")

        card = ttk.Frame(self.overview_tab, style="Card.TFrame", padding=12)
        card.pack(fill="both", expand=True)
        self.overview_tree = ttk.Treeview(card, show="headings", height=16)
        self.overview_tree.pack(fill="both", expand=True)

    def _refresh_overview(self):
        try:
            repo = AttendanceRepository(self.db_path.get())
        except Exception:
            return
        rows = repo.conn.execute(
            "SELECT DISTINCT sheet_id FROM sheets ORDER BY processed_at"
        ).fetchall()
        sheet_ids = [r["sheet_id"] for r in rows]

        students = repo.conn.execute("SELECT student_index, name FROM students").fetchall()

        columns = ["student"] + sheet_ids
        self.overview_tree.configure(columns=columns)
        self.overview_tree.heading("student", text="Student")
        self.overview_tree.column("student", width=220, anchor="w")
        for sid in sheet_ids:
            self.overview_tree.heading(sid, text=f"Sheet {sid}")
            self.overview_tree.column(sid, width=90, anchor="center")

        for row in self.overview_tree.get_children():
            self.overview_tree.delete(row)

        for s in students:
            records = repo.conn.execute(
                "SELECT sheet_id, present FROM attendance_records WHERE student_index = ?",
                (s["student_index"],),
            ).fetchall()
            status_by_sheet = {r["sheet_id"]: r["present"] for r in records}
            values = [s["name"]] + [
                ("Present" if status_by_sheet.get(sid) else "Absent") if sid in status_by_sheet else "-"
                for sid in sheet_ids
            ]
            self.overview_tree.insert("", "end", values=values)
        repo.close()

    # ---------- Tab 3: Student chart ----------

    def _build_visualize_tab(self):
        left = ttk.Frame(self.visualize_tab, style="Card.TFrame", padding=12)
        left.pack(side="left", fill="y", padx=(0, 12))
        ttk.Label(left, text="Students", style="Card.TLabel", font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.viz_student_list = tk.Listbox(left, width=32, height=20, relief="solid", bd=1)
        self.viz_student_list.pack(pady=(6, 8))
        ttk.Button(left, text="Show attendance chart", command=self._on_show_chart).pack(fill="x")

        right = ttk.Frame(self.visualize_tab, style="Card.TFrame", padding=12)
        right.pack(side="left", fill="both", expand=True)
        self.chart_label = ttk.Label(right, text="Select a student and click 'Show attendance chart'.",
                                      style="Card.TLabel")
        self.chart_label.pack(fill="both", expand=True)
        self._chart_image_ref = None

    def _on_show_chart(self):
        sel = self.viz_student_list.curselection()
        if not sel:
            messagebox.showinfo("Select a student", "Please select a student from the list first.")
            return
        student_index = self.viz_student_list.get(sel[0]).split(" - ")[0]
        try:
            repo = AttendanceRepository(self.db_path.get())
            viz = AttendanceVisualizer(repo)
            out_path = os.path.join("output", f"infovis_{student_index}.png")
            viz.render(student_index, output_path=out_path)
            repo.close()

            img = Image.open(out_path)
            img.thumbnail((650, 400))
            self._chart_image_ref = ImageTk.PhotoImage(img)
            self.chart_label.configure(image=self._chart_image_ref, text="")
        except Exception as e:
            messagebox.showerror("Could not render chart", str(e))

    # ---------- Tab 4: Signature check ----------

    def _build_investigate_tab(self):
        left = ttk.Frame(self.investigate_tab, style="Card.TFrame", padding=12)
        left.pack(side="left", fill="y", padx=(0, 12))
        ttk.Label(left, text="Students", style="Card.TLabel", font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.inv_student_list = tk.Listbox(left, width=32, height=20, relief="solid", bd=1)
        self.inv_student_list.pack(pady=(6, 8))
        ttk.Button(left, text="Check signature consistency", command=self._on_investigate).pack(fill="x")

        right = ttk.Frame(self.investigate_tab, style="Card.TFrame", padding=12)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="Pairwise signature similarity", style="Card.TLabel",
                  font=("Helvetica", 11, "bold")).pack(anchor="w")
        columns = ("sheet_a", "sheet_b", "similarity", "flag")
        self.inv_tree = ttk.Treeview(right, columns=columns, show="headings", height=14)
        for col, label, width in [("sheet_a", "Sheet A", 90), ("sheet_b", "Sheet B", 90),
                                   ("similarity", "Similarity", 100), ("flag", "Flag", 140)]:
            self.inv_tree.heading(col, text=label)
            self.inv_tree.column(col, width=width, anchor="center")
        self.inv_tree.tag_configure("flagged", foreground=DANGER)
        self.inv_tree.pack(fill="both", expand=True, pady=(6, 0))
        self.inv_note = ttk.Label(right, text="", style="Card.TLabel", wraplength=500)
        self.inv_note.pack(anchor="w", pady=(8, 0))

    def _on_investigate(self):
        sel = self.inv_student_list.curselection()
        if not sel:
            messagebox.showinfo("Select a student", "Please select a student from the list first.")
            return
        student_index = self.inv_student_list.get(sel[0]).split(" - ")[0]
        for row in self.inv_tree.get_children():
            self.inv_tree.delete(row)

        try:
            repo = AttendanceRepository(self.db_path.get())
            crops = repo.get_signature_crops_for_student(student_index)
            if len(crops) < 2:
                self.inv_note.configure(text="Need at least 2 signed sheets for this student to compare.")
                repo.close()
                return
            verifier = SignatureVerifier()
            result = verifier.verify_student(crops)
            for c in result["comparisons"]:
                flagged = c in result["flagged"]
                self.inv_tree.insert("", "end", values=(c["sheet_a"], c["sheet_b"], f"{c['similarity']:.3f}",
                                                          "Review suggested" if flagged else "OK"),
                                      tags=("flagged",) if flagged else ())
            self.inv_note.configure(
                text=f"{len(result['flagged'])} of {len(result['comparisons'])} pair(s) flagged. "
                     "Similarity is a weak signal on small crops -- treat flags as worth a manual look, "
                     "not definitive proof (see README)."
            )
            repo.close()
        except Exception as e:
            messagebox.showerror("Signature check failed", str(e))

    # ---------- shared ----------

    def _refresh_student_lists(self):
        try:
            repo = AttendanceRepository(self.db_path.get())
        except Exception:
            return
        students = repo.conn.execute("SELECT student_index, name FROM students ORDER BY student_index").fetchall()
        repo.close()
        for listbox in (self.viz_student_list, self.inv_student_list):
            listbox.delete(0, "end")
            for s in students:
                listbox.insert("end", f"{s['student_index']} - {s['name']}")


def main():
    app = SamsGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
