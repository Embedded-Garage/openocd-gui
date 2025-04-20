import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import subprocess
import threading

CONFIG_FILE = "configs.json"

class OpenOCDGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OpenOCD GUI Frontend")
        self.geometry("850x700")

        # Process handle for OpenOCD
        self.current_proc = None

        # Load existing configurations or set up default
        self.configs = {}
        self.current_name = None
        self.default_schema = {
            "openocd_path": "",
            "interface": "",
            "target": "",
            "gdb_port": "",
            "tcl_port": "",
            "telnet_port": "",
            "custom_configs": [],
            "pre_cmds": [],
            "custom_cmds": []
        }

        self.create_widgets()
        self.load_all_configs()

    def create_widgets(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)
        for i in range(0, 14):
            frame.rowconfigure(i, weight=0)
        frame.rowconfigure(14, weight=1)

        # Config selector
        toolbar = ttk.Frame(frame)
        toolbar.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0,10))
        ttk.Label(toolbar, text="Configuration:").pack(side=tk.LEFT)
        self.config_cb = ttk.Combobox(toolbar, state="readonly", width=20, postcommand=self.update_config_list)
        self.config_cb.pack(side=tk.LEFT, padx=5)
        self.config_cb.bind("<<ComboboxSelected>>", self.on_config_select)
        ttk.Button(toolbar, text="Save", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Save As...", command=self.save_as_new).pack(side=tk.LEFT)

        # OpenOCD path
        ttk.Label(frame, text="OpenOCD Installation Folder:").grid(row=1, column=0, sticky=tk.W)
        self.path_entry = ttk.Entry(frame)
        self.path_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=5)
        ttk.Button(frame, text="Browse", command=self.browse_openocd).grid(row=1, column=3)

        # Interface/target
        ttk.Label(frame, text="Interface:").grid(row=2, column=0, sticky=tk.W)
        self.interface_cb = ttk.Combobox(frame, state="readonly")
        self.interface_cb.grid(row=2, column=1, sticky="ew", padx=5)
        self.chk_interface = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Use", variable=self.chk_interface).grid(row=2, column=2)

        ttk.Label(frame, text="Target:").grid(row=3, column=0, sticky=tk.W)
        self.target_cb = ttk.Combobox(frame, state="readonly")
        self.target_cb.grid(row=3, column=1, sticky="ew", padx=5)
        self.chk_target = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Use", variable=self.chk_target).grid(row=3, column=2)

        # Ports
        ports = ["gdb_port", "tcl_port", "telnet_port"]
        self.port_vars = {}
        for idx, port in enumerate(ports, start=4):
            ttk.Label(frame, text=f"{port.replace('_',' ').title()}:").grid(row=idx, column=0, sticky=tk.W)
            entry = ttk.Entry(frame)
            entry.grid(row=idx, column=1, sticky="ew", padx=5)
            chk = tk.BooleanVar()
            ttk.Checkbutton(frame, text="Use", variable=chk).grid(row=idx, column=2)
            self.port_vars[port] = (entry, chk)

        # Custom config files
        ttk.Label(frame, text="Custom Config Files:").grid(row=7, column=0, sticky=tk.NW)
        self.config_list = tk.Listbox(frame, height=4)
        self.config_list.grid(row=7, column=1, sticky="ew", padx=5)
        cfg_btns = ttk.Frame(frame)
        cfg_btns.grid(row=7, column=2, sticky=tk.N)
        ttk.Button(cfg_btns, text="Add", command=self.add_custom_cfg).pack(fill=tk.X)
        ttk.Button(cfg_btns, text="Remove", command=self.remove_custom_cfg).pack(fill=tk.X, pady=2)

        # Pre-launch commands
        ttk.Label(frame, text="Pre-Launch Commands:").grid(row=8, column=0, sticky=tk.NW)
        self.pre_cmd_text = tk.Text(frame, height=3)
        self.pre_cmd_text.grid(row=8, column=1, columnspan=3, sticky="ew", padx=5)

        # Post-launch commands
        ttk.Label(frame, text="Post-Launch Commands:").grid(row=9, column=0, sticky=tk.NW)
        self.cmd_text = tk.Text(frame, height=3)
        self.cmd_text.grid(row=9, column=1, columnspan=3, sticky="ew", padx=5)

        # Run and Kill
        self.run_button = ttk.Button(frame, text="Run OpenOCD", command=self.run_openocd)
        self.run_button.grid(row=10, column=3, sticky="e", pady=10)
        ttk.Button(frame, text="Kill OpenOCD", command=self.kill_openocd).grid(row=10, column=2, sticky="e", pady=10)

        # Output
        output_frame = ttk.LabelFrame(frame, text="OpenOCD Output")
        output_frame.grid(row=14, column=0, columnspan=4, sticky="nsew", pady=(10,0))
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        self.output_text = tk.Text(output_frame)
        self.output_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=scroll.set)

    def load_all_configs(self):
        # Load configs.json
        if os.path.isfile(CONFIG_FILE):
            try:
                raw = json.load(open(CONFIG_FILE, 'r'))
                self.configs = raw.get('configs', {})
                self.current_name = raw.get('last')
            except:
                self.configs = {}
        if not self.configs:
            self.configs['Default'] = self.default_schema.copy()
        if not self.current_name or self.current_name not in self.configs:
            self.current_name = next(iter(self.configs))
        self.update_config_list()
        self.config_cb.set(self.current_name)
        self.load_config(self.current_name)

    def update_config_list(self):
        self.config_cb['values'] = sorted(self.configs.keys())

    def on_config_select(self, event):
        self.current_name = self.config_cb.get()
        self.load_config(self.current_name)

    def load_config(self, name):
        cfg = self.configs.get(name, self.default_schema)
        self.path_entry.delete(0, tk.END); self.path_entry.insert(0, cfg['openocd_path'])
        self.populate_options()
        self.interface_cb.set(cfg.get('interface', ''))
        self.chk_interface.set(bool(cfg.get('interface', '')))
        self.target_cb.set(cfg.get('target', ''))
        self.chk_target.set(bool(cfg.get('target', '')))
        for key, (ent, chk) in self.port_vars.items():
            ent.delete(0, tk.END); ent.insert(0, cfg.get(key, '')); chk.set(bool(cfg.get(key, '')))
        self.config_list.delete(0, tk.END)
        for f in cfg.get('custom_configs', []): self.config_list.insert(tk.END, f)
        self.pre_cmd_text.delete('1.0', tk.END); self.pre_cmd_text.insert('1.0', '\n'.join(cfg.get('pre_cmds', [])))
        self.cmd_text.delete('1.0', tk.END); self.cmd_text.insert('1.0', '\n'.join(cfg.get('custom_cmds', [])))

    def save_config(self):
        data = {
            'openocd_path': self.path_entry.get(),
            'interface': self.interface_cb.get(),
            'target': self.target_cb.get(),
            'gdb_port': self.port_vars['gdb_port'][0].get(),
            'tcl_port': self.port_vars['tcl_port'][0].get(),
            'telnet_port': self.port_vars['telnet_port'][0].get(),
            'custom_configs': list(self.config_list.get(0, tk.END)),
            'pre_cmds': self.pre_cmd_text.get('1.0', tk.END).strip().splitlines(),
            'custom_cmds': self.cmd_text.get('1.0', tk.END).strip().splitlines()
        }
        self.configs[self.current_name] = data
        self.persist_configs()
        messagebox.showinfo("Saved", f"Configuration '{self.current_name}' saved.")

    def save_as_new(self):
        name = simpledialog.askstring("Save As", "Enter new configuration name:")
        if not name or name in self.configs: return
        self.current_name = name
        self.save_config()
        self.update_config_list()
        self.config_cb.set(name)

    def persist_configs(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'configs': self.configs, 'last': self.current_name}, f, indent=2)

    def browse_openocd(self):
        path = filedialog.askdirectory(title="Select OpenOCD Installation Directory")
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
            self.populate_options()

    def populate_options(self):
        odir = self.path_entry.get()
        scripts = os.path.join(odir, 'share', 'openocd', 'scripts')
        for cb in (self.interface_cb, self.target_cb):
            cb['values'] = []; cb.set("")
        if not os.path.isdir(scripts):
            messagebox.showerror("Error", f"Scripts directory missing: {scripts}")
            return
        def list_cfg(name):
            folder = os.path.join(scripts, name)
            return sorted([os.path.splitext(f)[0] for f in os.listdir(folder) if f.endswith('.cfg')]) if os.path.isdir(folder) else []
        self.interface_cb['values'] = list_cfg('interface')
        self.target_cb['values'] = list_cfg('target')

    def add_custom_cfg(self):
        path = filedialog.askopenfilename(filetypes=[('CFG files','*.cfg')])
        if path: self.config_list.insert(tk.END, path)

    def remove_custom_cfg(self):
        sel = self.config_list.curselection()
        if sel: self.config_list.delete(sel)

    def run_openocd(self):
        # Prevent starting if already running
        if self.current_proc and self.current_proc.poll() is None:
            messagebox.showwarning("Warning", "OpenOCD is already running.")
            return

        odir = self.path_entry.get()
        if not os.path.isdir(odir): return messagebox.showerror("Error", "Invalid OpenOCD dir")
        execp = None
        for p in [os.path.join(odir,'openocd'), os.path.join(odir,'bin','openocd')]:
            if os.path.isfile(p) or os.path.isfile(p+'.exe'): execp = p; break
        if not execp: return messagebox.showerror("Error", "Executable not found")

        scripts = os.path.join(odir, 'openocd', 'scripts')
        cmd = [execp]
        # pre
        for line in self.pre_cmd_text.get('1.0', tk.END).splitlines():
            line = line.strip();
            if line: cmd += ['-c', line[3:] if line.startswith('-c ') else line]
        # ports
        for key,(ent,chk) in self.port_vars.items():
            if chk.get() and ent.get(): cmd += ['-c', f"{key} {ent.get()}"]
        cmd += ['-s', scripts]
        if self.chk_interface.get() and self.interface_cb.get(): cmd += ['-f', f"interface/{self.interface_cb.get()}.cfg"]
        if self.chk_target.get() and self.target_cb.get(): cmd += ['-f', f"target/{self.target_cb.get()}.cfg"]
        for cfg in self.config_list.get(0, tk.END): cmd += ['-f', cfg]
        # post
        for line in self.cmd_text.get('1.0', tk.END).splitlines():
            line = line.strip();
            if line: cmd += ['-c', line[3:] if line.startswith('-	c ') else line]

        self.output_text.insert(tk.END, f"Running: {' '.join(cmd)}\n")
        self.output_text.see(tk.END)

        def runner():
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            self.current_proc = proc
            for out in proc.stdout: self.output_text.insert(tk.END, out); self.output_text.see(tk.END)
            proc.wait()
            self.output_text.insert(tk.END, f"\nExited {proc.returncode}\n"); self.output_text.see(tk.END)
            self.current_proc = None
        threading.Thread(target=runner, daemon=True).start()

    def kill_openocd(self):
        if self.current_proc and self.current_proc.poll() is None:
            self.current_proc.terminate()
            self.output_text.insert(tk.END, "\nSent terminate signal to OpenOCD process.\n")
            self.output_text.see(tk.END)
        else:
            messagebox.showinfo("Info", "No running OpenOCD process to kill.")

if __name__ == '__main__':
    app = OpenOCDGUI()
    app.mainloop()
