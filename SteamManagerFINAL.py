import customtkinter as ctk
import os
import re
import configparser
from tkinter import filedialog, messagebox
import shutil
import webbrowser
from datetime import datetime
import requests  # For API calls
from io import BytesIO
from PIL import Image, ImageDraw
import time
import subprocess
import sys
import threading
import pystray  # For system tray icon

# Windows-specific imports for icon extraction and registry access.
if os.name == "nt":
    import winreg  # For Run on Startup

class SteamManagerApp:
    def __init__(self):
        # Configuration variables.
        self.config_file = 'config.ini'
        self.config = configparser.ConfigParser()
        self.saved_main_path = None
        self.saved_paths = []
        self.saved_theme = 'dark-blue'
        self.saved_appearance_mode = 'system'
        self.config_error = None

        # New settings.
        self.run_on_startup = False
        self.luma_toggled = False      # False: original names; True: files renamed (with a "1")
        self.debug_mode = True         # Debug log always enabled
        self.exit_to_tray = True       # When True, closing minimizes to tray; when False, it exits
        self.auto_dark_mode = False    # When True, automatically switch dark/light based on time

        # Logging.
        self.log_text = None
        self.log_frame = None
        self.log_history = []  # Keep last 50 log messages

        # Caches.
        self.appid_cache = {}


        # (Auto-refresh features have been removed.)

        self.load_config()

        ctk.set_appearance_mode(self.saved_appearance_mode)
        ctk.set_default_color_theme(self.saved_theme)

        if self.auto_dark_mode:
            self.update_theme_by_time()

        # Initialize main window.
        self.root = ctk.CTk()
        self.root.geometry("900x600")
        self.root.title("Steam Manager")
        self.root.resizable(True, True)
        self.sidebar_frame = None
        self.content_frame = None

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.tray_icon = None
        self.tray_thread = None
        self.setup_tray_icon()

        self.show_loading_screen()
        self.root.mainloop()

    # ───────────────────────────────
    # CONFIGURATION & LIBRARY
    # ───────────────────────────────
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file)
                self.saved_main_path = self.config['Paths'].get('steam_path', None)
                extra = self.config['Paths'].get('extra_paths', '')
                self.saved_paths = extra.split('|') if extra else []
                self.saved_theme = self.config['Settings'].get('theme', 'dark-blue')
                self.saved_appearance_mode = self.config['Settings'].get('appearance_mode', 'system')
                self.run_on_startup = self.config['Settings'].getboolean('run_on_startup', False)
                self.exit_to_tray = self.config['Settings'].getboolean('exit_to_tray', True)
                self.auto_dark_mode = self.config['Settings'].getboolean('auto_dark_mode', False)
                self.debug_mode = True  # Always enabled
            except (configparser.Error, KeyError):
                self.config_error = "Config file is corrupted."
        else:
            self.saved_main_path = None
            self.saved_paths = []
            self.saved_theme = 'dark-blue'
            self.saved_appearance_mode = 'system'
            self.run_on_startup = False
            self.debug_mode = True
            self.exit_to_tray = True
            self.auto_dark_mode = False

    def save_config(self, main_path=None, extra_paths=None, theme=None, appearance_mode=None):
        if not self.config.has_section('Paths'):
            self.config.add_section('Paths')
        if main_path is not None:
            self.config['Paths']['steam_path'] = main_path
        if extra_paths is not None:
            self.config['Paths']['extra_paths'] = '|'.join(extra_paths)
        if not self.config.has_section('Settings'):
            self.config.add_section('Settings')
        if theme is not None:
            self.config['Settings']['theme'] = theme
        if appearance_mode is not None:
            self.config['Settings']['appearance_mode'] = appearance_mode
        self.config['Settings']['run_on_startup'] = str(self.run_on_startup)
        self.config['Settings']['exit_to_tray'] = str(self.exit_to_tray)
        self.config['Settings']['auto_dark_mode'] = str(self.auto_dark_mode)
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)



    # ───────────────────────────────
    # LOGGING & RECENT ACTIVITIES
    # ───────────────────────────────
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{timestamp}: {message}\n"
        self.log_history.append(log_message)
        if len(self.log_history) > 50:
            self.log_history = self.log_history[-50:]
        if self.log_text is not None:
            try:
                if self.log_text.winfo_exists():
                    self.log_text.insert("end", log_message)
                    self.log_text.yview("end")
                else:
                    self.log_text = None
            except Exception:
                print(log_message)
        else:
            print(log_message)

    def view_recent_activities(self):
        recent_win = ctk.CTkToplevel(self.root)
        recent_win.title("Recent Activities")
        recent_win.geometry("400x300")
        text_box = ctk.CTkTextbox(recent_win)
        text_box.pack(fill="both", expand=True)
        recent_logs = self.log_history[-10:]
        for log in recent_logs:
            text_box.insert("end", log)
        text_box.configure(state="disabled")

    # ───────────────────────────────
    # INNOVATIVE FEATURES: AUTO DARK MODE & RESET SETTINGS & CLEAR CACHE
    # ───────────────────────────────
    def update_theme_by_time(self):
        # Switch to dark mode between 6pm and 6am; light otherwise.
        current_hour = datetime.now().hour
        if current_hour >= 18 or current_hour < 6:
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

    def set_auto_dark_mode(self, choice):
        self.auto_dark_mode = (choice == "On")
        self.save_config()
        self.update_theme_by_time()

    def reset_settings(self):
        self.saved_theme = 'dark-blue'
        self.saved_appearance_mode = 'system'
        self.run_on_startup = False
        self.debug_mode = True
        self.exit_to_tray = True
        self.auto_dark_mode = False
        self.luma_toggled = False
        self.save_config(main_path=self.saved_main_path, extra_paths=self.saved_paths)
        self.initialize_main_window()

    def clear_cache(self):
        self.appid_cache = {}
        self.log("Cache cleared.")

    # ───────────────────────────────
    # MISSING CSV IMPORT METHOD
    # ───────────────────────────────

    # ───────────────────────────────
    # SPLASH & ERROR WINDOWS
    # ───────────────────────────────
    def show_loading_screen(self):
        splash = ctk.CTkToplevel(self.root)
        splash.geometry("300x200")
        splash.title("Loading")
        splash.grab_set()
        splash_label = ctk.CTkLabel(splash, text="Loading, please wait...", font=("Helvetica", 16))
        splash_label.pack(expand=True, padx=20, pady=50)
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - splash.winfo_reqwidth()) // 2
        y = (self.root.winfo_screenheight() - splash.winfo_reqheight()) // 2
        splash.geometry(f"+{x}+{y}")
        if self.config_error:
            splash.withdraw()
            self.show_config_error()
        elif not self.saved_main_path or not os.path.exists(os.path.join(self.saved_main_path, "steam.exe")):
            self.root.after(2000, lambda: [splash.destroy(), self.firstboot()])
        else:
            self.root.after(500, lambda: [splash.destroy(), self.initialize_main_window()])

    def show_config_error(self):
        error_win = ctk.CTkToplevel(self.root)
        error_win.geometry("350x200")
        error_win.title("Configuration Error")
        error_win.grab_set()
        error_label = ctk.CTkLabel(error_win, text="Config file is corrupted.\nPlease reset it.", text_color="red", font=("Helvetica", 14))
        error_label.pack(pady=20)
        reset_btn = ctk.CTkButton(error_win, text="Reset Config", command=self.reset_config)
        reset_btn.pack(pady=5)
        exit_btn = ctk.CTkButton(error_win, text="Exit", command=self.root.quit)
        exit_btn.pack(pady=5)

    def reset_config(self):
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        self.log("Config file reset.")
        self.root.quit()

    # ───────────────────────────────
    # FIRST BOOT & FOLDER SELECTION
    # ───────────────────────────────
    def firstboot(self):
        fb_win = ctk.CTkToplevel(self.root)
        fb_win.title("First Boot - Select Steam Folder")
        fb_win.geometry("400x250")
        fb_win.grab_set()
        label = ctk.CTkLabel(fb_win, text="Please select your Steam folder:", font=("Helvetica", 14))
        label.pack(pady=20)
        select_btn = ctk.CTkButton(fb_win, text="Select Folder", command=lambda: self.open_folder(fb_win, is_main_path=True))
        select_btn.pack(pady=10)

    def open_folder(self, window, is_main_path=False):
        folder_path = filedialog.askdirectory(title="Select Folder")
        if folder_path and os.path.exists(folder_path):
            if is_main_path:
                steam_exe = os.path.join(folder_path, "steam.exe")
                if os.path.exists(steam_exe):
                    self.saved_main_path = folder_path
                    self.save_config(main_path=self.saved_main_path, extra_paths=self.saved_paths)
                    self.log(f"Main Steam folder set: {self.saved_main_path}")
                    window.destroy()
                    self.initialize_main_window()
                else:
                    messagebox.showerror("Error", "Steam executable not found in the selected folder.")
            else:
                if folder_path in self.saved_paths:
                    messagebox.showerror("Error", "This path has already been added.")
                    return
                steamapps_path = os.path.join(folder_path, "steamapps")
                if not os.path.exists(steamapps_path):
                    messagebox.showwarning("Warning", "Selected folder does not contain a steamapps directory.")
                self.saved_paths.append(folder_path)
                self.save_config(main_path=self.saved_main_path, extra_paths=self.saved_paths)
                self.log(f"Additional manifest folder added: {folder_path}")
                window.destroy()
                self.initialize_main_window()
        else:
            messagebox.showerror("Error", "Invalid folder selected.")

    def add_manifest_folder(self):
        folder_path = filedialog.askdirectory(title="Select Additional Manifest Folder")
        if folder_path and os.path.exists(folder_path):
            if folder_path in self.saved_paths:
                messagebox.showerror("Error", "This path has already been added.")
                return
            steamapps_path = os.path.join(folder_path, "steamapps")
            if not os.path.exists(steamapps_path):
                messagebox.showwarning("Warning", "Selected folder does not contain a steamapps directory.")
            self.saved_paths.append(folder_path)
            self.save_config(extra_paths=self.saved_paths)
            self.log(f"Additional manifest folder added: {folder_path}")
            self.initialize_main_window()
        else:
            messagebox.showerror("Error", "Invalid folder selected.")

    # ───────────────────────────────
    # MAIN UI INITIALIZATION (with Top Bar for Donate)
    # ───────────────────────────────
    def initialize_main_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        # Top bar removed; donate button now in sidebar

        # Sidebar.
        self.sidebar_frame = ctk.CTkFrame(self.root, width=240, corner_radius=10)
        self.sidebar_frame.pack(side="left", fill="y", padx=10, pady=10)
        ctk.CTkLabel(self.sidebar_frame, text="Steam Control", font=("Helvetica", 16, "bold")).pack(pady=(10,5))
        ctk.CTkButton(self.sidebar_frame, text="Toggle Steam", command=self.toggle_steam, width=200).pack(pady=2)
        self.luma_sidebar_var = ctk.BooleanVar(value=self.luma_toggled)
        ctk.CTkCheckBox(self.sidebar_frame, text="Toggle Luma", variable=self.luma_sidebar_var,
                        command=lambda: self.set_luma_state(self.luma_sidebar_var.get())).pack(pady=2)
        ctk.CTkLabel(self.sidebar_frame, text="Manifest Operations", font=("Helvetica", 16, "bold")).pack(pady=(10,5))
        ctk.CTkButton(self.sidebar_frame, text="Refresh Manifests", command=self.manifest_adder, width=200).pack(pady=2)
        
        ctk.CTkButton(self.sidebar_frame, text="Open Manifest Folder", command=self.open_manifest_folder, width=200).pack(pady=2)
        ctk.CTkButton(self.sidebar_frame, text="Add Manifest Folder", command=self.add_manifest_folder, width=200).pack(pady=2)
        ctk.CTkLabel(self.sidebar_frame, text="Game Management", font=("Helvetica", 16, "bold")).pack(pady=(10,5))
        ctk.CTkButton(self.sidebar_frame, text="View Installed Games", command=self.view_installed_games, width=200).pack(pady=2)
        ctk.CTkButton(self.sidebar_frame, text="Search Game", command=self.search_game, width=200).pack(pady=2)
        ctk.CTkLabel(self.sidebar_frame, text="Settings", font=("Helvetica", 16, "bold")).pack(pady=(10,5))
        ctk.CTkButton(self.sidebar_frame, text="Settings", command=self.config_window, width=200).pack(pady=2)
        ctk.CTkButton(self.sidebar_frame, text="Tutorial", command=self.tutorial_window, width=200).pack(pady=2)
        ctk.CTkButton(self.sidebar_frame, text="Exit", command=self.exit_app, width=200).pack(pady=2)
        ctk.CTkButton(self.sidebar_frame, text="Donate", fg_color="orange", command=self.donate, width=200).pack(pady=2)

        # Main content area.
        self.content_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.content_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(self.content_frame, text="Steam Manager", font=("Helvetica", 24, "bold")).pack(pady=20)
        ctk.CTkLabel(self.content_frame, text="Main Steam Path:", font=("Helvetica", 16)).pack(pady=(10,5))
        main_path_text = self.saved_main_path if self.saved_main_path else "No path set"
        main_path_color = "green" if self.saved_main_path else "red"
        ctk.CTkLabel(self.content_frame, text=main_path_text, text_color=main_path_color, font=("Helvetica", 14)).pack(pady=(0,10))
        ctk.CTkLabel(self.content_frame, text="Additional Manifest Paths:", font=("Helvetica", 16)).pack(pady=(10,5))
        if self.saved_paths:
            scroll_frame = ctk.CTkScrollableFrame(self.content_frame, height=150)
            scroll_frame.pack(pady=5, padx=5, fill="both", expand=True)
            for path in self.saved_paths:
                frame = ctk.CTkFrame(scroll_frame)
                frame.pack(fill="x", pady=2, padx=5)
                ctk.CTkLabel(frame, text=path, font=("Helvetica", 12)).pack(side="left", padx=(5,0))
                remove_btn = ctk.CTkButton(frame, text="Remove", command=lambda p=path: self.remove_manifest_path(p), width=80)
                remove_btn.pack(side="right", padx=5)
        else:
            ctk.CTkLabel(self.content_frame, text="No extra paths set", font=("Helvetica", 12)).pack(pady=5)

        self.log_frame = ctk.CTkFrame(self.content_frame, corner_radius=10)
        self.log_frame.pack(fill="both", expand=True, pady=(10,0), padx=5)
        ctk.CTkLabel(self.log_frame, text="Activity Log:", font=("Helvetica", 14)).pack(pady=(5,0))
        self.log_text = ctk.CTkTextbox(self.log_frame, width=600, height=150)
        self.log_text.pack(pady=(5,5), padx=5, fill="both", expand=True)
        ctk.CTkButton(self.log_frame, text="Clear Log", command=self.clear_log, width=100).pack(pady=(0,5))
        self.log("Main window initialized.")

    def remove_manifest_path(self, path):
        if messagebox.askyesno("Confirm Remove", f"Remove manifest path:\n{path}?"):
            if path in self.saved_paths:
                self.saved_paths.remove(path)
                self.save_config(extra_paths=self.saved_paths)
                self.log(f"Removed manifest path: {path}")
                self.initialize_main_window()

    def clear_log(self):
        if self.log_text:
            self.log_text.delete("0.0", "end")
            self.log("Log cleared.")

    # ───────────────────────────────
    # SYSTEM TRAY & EXIT BEHAVIOR
    # ───────────────────────────────
    def on_closing(self):
        if self.exit_to_tray:
            self.root.withdraw()
            self.log("Application minimized to system tray.")
        else:
            self.root.destroy()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.log("Main window restored from system tray.")

    def exit_app(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()

    def create_tray_icon_image(self):
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), "blue")
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, width - 8, height - 8), fill="white")
        return image

    def setup_tray_icon(self):
        if self.tray_icon is not None:
            return
        icon_image = self.create_tray_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Toggle Steam", lambda _: self.root.after(0, self.toggle_steam)),
            pystray.MenuItem("Show", lambda _: self.root.after(0, self.show_window)),
            pystray.MenuItem("Exit", lambda _: self.root.after(0, self.exit_app))
        )
        self.tray_icon = pystray.Icon("SteamManager", icon_image, "Steam Manager", menu)
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    # ───────────────────────────────
    # FUNCTIONALITY METHODS
    # ───────────────────────────────
    def toggle_steam(self):
        if os.name != "nt":
            messagebox.showerror("Error", "Steam control is supported only on Windows.")
            return
        try:
            tasks = subprocess.check_output(["tasklist"], text=True)
            running = "steam.exe" in tasks.lower()
        except Exception:
            running = False
        if running:
            try:
                os.system("taskkill /f /im steam.exe")
                self.log("Steam closed.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to close Steam: {str(e)}")
                self.log(f"Error closing Steam: {str(e)}")
        else:
            if self.saved_main_path:
                steam_exe = os.path.join(self.saved_main_path, "steam.exe")
                if os.path.exists(steam_exe):
                    try:
                        os.startfile(steam_exe)
                        appcache = os.path.join(self.saved_main_path, "DeleteSteamAppCache.exe")
                        if os.path.exists(appcache):
                            p = subprocess.Popen([appcache])
                            time.sleep(1)
                            p.kill()
                        self.log("Steam opened and DeleteSteamAppCache.exe executed.")
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to open Steam: {str(e)}")
                        self.log(f"Error opening Steam: {str(e)}")
                else:
                    messagebox.showerror("Error", "Steam executable not found in the saved path.")
                    self.log("Steam executable not found.")
            else:
                messagebox.showerror("Error", "Main Steam path is not set.")
                self.log("Attempted to open Steam without a valid main path.")

    def set_luma_state(self, desired_state):
        if not self.saved_main_path:
            messagebox.showerror("Error", "Main Steam path is not set.")
            return
        file1 = os.path.join(self.saved_main_path, "greenluma_2024_x64.dll")
        file1_toggled = os.path.join(self.saved_main_path, "greenluma_2024_x64_1.dll")
        file2 = os.path.join(self.saved_main_path, "greenluma_2024_x86.dll")
        file2_toggled = os.path.join(self.saved_main_path, "greenluma_2024_x86_1.dll")
        exists1 = os.path.exists(file1) or os.path.exists(file1_toggled)
        exists2 = os.path.exists(file2) or os.path.exists(file2_toggled)
        if not (exists1 or exists2):
            messagebox.showerror("Error", "No Luma files found (greenluma_2024_x64.dll or greenluma_2024_x86.dll).")
            self.log("Luma files not found.")
            return
        if desired_state and not self.luma_toggled:
            if os.path.exists(file1):
                os.rename(file1, file1_toggled)
            if os.path.exists(file2):
                os.rename(file2, file2_toggled)
            self.luma_toggled = True
            self.log("Luma toggled ON (files renamed with '1').")
        elif (not desired_state) and self.luma_toggled:
            if os.path.exists(file1_toggled):
                os.rename(file1_toggled, file1)
            if os.path.exists(file2_toggled):
                os.rename(file2_toggled, file2)
            self.luma_toggled = False
            self.log("Luma toggled OFF (files renamed back to original).")
        self.save_config()

    def toggle_luma(self):
        self.set_luma_state(not self.luma_toggled)

    def manifest_adder(self):
        if not self.saved_main_path or not os.path.exists(self.saved_main_path):
            messagebox.showerror("Error", "Main Steam path is invalid.")
            self.log("Manifest refresh failed: invalid main Steam path.")
            return
        output_folder = os.path.join(self.saved_main_path, "applist")
        if os.path.exists(output_folder):
            try:
                for f in os.listdir(output_folder):
                    file_path = os.path.join(output_folder, f)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                self.log("Cleared old manifest files.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear output folder: {str(e)}")
                self.log(f"Error clearing manifest folder: {str(e)}")
                return
        else:
            try:
                os.makedirs(output_folder)
                self.log("Created manifest output folder.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create output folder: {str(e)}")
                self.log(f"Error creating manifest folder: {str(e)}")
                return
        total_files = 0
        file_counter = 1
        main_steamapps = os.path.join(self.saved_main_path, "steamapps")
        if os.path.exists(main_steamapps):
            initial_counter = file_counter
            file_counter = self.process_manifest_files(main_steamapps, output_folder, file_counter)
            total_files += (file_counter - initial_counter)
        for path in self.saved_paths:
            steamapps_path = os.path.join(path, "steamapps")
            if os.path.exists(steamapps_path):
                initial_counter = file_counter
                file_counter = self.process_manifest_files(steamapps_path, output_folder, file_counter)
                total_files += (file_counter - initial_counter)
            else:
                messagebox.showwarning("Warning", f"Skipping invalid path: {path} (steamapps not found)")
                self.log(f"Skipped invalid path: {path}")
        preset_path = os.path.join(output_folder, "0.txt")
        try:
            with open(preset_path, "w") as f:
                f.write("480\n")
            self.log("Preset file created.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create preset file: {str(e)}")
            self.log(f"Error creating preset file: {str(e)}")
            return
        messagebox.showinfo("Success", f"Successfully added {total_files} games to the manifest list.")
        self.log(f"Manifest refresh completed: {total_files} games added.")

    def process_manifest_files(self, manifest_dir, output_folder, file_counter):
        for item in os.listdir(manifest_dir):
            item_path = os.path.join(manifest_dir, item)
            if os.path.isfile(item_path):
                match = re.match(r"appmanifest_(\d+)\.acf", item)
                if match:
                    appid = match.group(1)
                    output_file = os.path.join(output_folder, f"{file_counter}.txt")
                    try:
                        with open(output_file, "w") as f:
                            f.write(f"{appid}\n")
                        file_counter += 1
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to write {output_file}: {str(e)}")
                        self.log(f"Error writing manifest file {output_file}: {str(e)}")
        return file_counter

    def open_manifest_folder(self):
        if not self.saved_main_path:
            messagebox.showerror("Error", "Main Steam path is not set.")
            self.log("Open Manifest Folder failed: no main Steam path.")
            return
        if os.name != "nt":
            messagebox.showerror("Error", "Opening folders is supported only on Windows.")
            return
        output_folder = os.path.join(self.saved_main_path, "applist")
        if os.path.exists(output_folder):
            os.startfile(output_folder)
            self.log("Opened manifest folder.")
        else:
            messagebox.showerror("Error", "Manifest folder does not exist.")
            self.log("Manifest folder not found when attempting to open it.")

    def view_installed_games(self):
        if not self.saved_main_path:
            messagebox.showerror("Error", "Main Steam path is not set.")
            self.log("View Installed Games failed: no main Steam path.")
            return
        output_folder = os.path.join(self.saved_main_path, "applist")
        if not os.path.exists(output_folder):
            messagebox.showerror("Error", "Manifest folder does not exist. Please refresh manifests first.")
            self.log("View Installed Games failed: manifest folder missing.")
            return
        games_win = ctk.CTkToplevel(self.root)
        games_win.title("Installed Games")
        games_win.geometry("600x500")
        games_win.grab_set()
        self.games_scroll_frame = ctk.CTkScrollableFrame(games_win, width=580, height=400)
        self.games_scroll_frame.pack(pady=10, padx=10)
        self.populate_installed_games(self.games_scroll_frame, output_folder)

    def populate_installed_games(self, scroll_frame, output_folder):
        for widget in scroll_frame.winfo_children():
            widget.destroy()
        files = [f for f in os.listdir(output_folder) if f.endswith(".txt") and f != "0.txt"]
        if not files:
            ctk.CTkLabel(scroll_frame, text="No games found in the manifest list.", font=("Helvetica", 12)).pack(pady=10)
            self.log("View Installed Games: no games found.")
            return
        for file in files:
            file_path = os.path.join(output_folder, file)
            try:
                with open(file_path, "r") as f:
                    appid = f.read().strip()
            except Exception as e:
                appid = "Error reading file"
                self.log(f"Error reading {file_path}: {str(e)}")
            game_name = self.get_game_name(appid)
            frame = ctk.CTkFrame(scroll_frame)
            frame.pack(fill="x", pady=5, padx=5)
            ctk.CTkLabel(frame, text=f"AppID: {appid} - {game_name}", font=("Helvetica", 12)).grid(row=0, column=0, sticky="w", padx=(5,10))
            ctk.CTkButton(frame, text="Open Store", command=lambda a=appid: self.open_store(a), width=90).grid(row=0, column=1, padx=5)
            ctk.CTkButton(frame, text="Details", command=lambda a=appid: self.show_game_details(a), width=90).grid(row=0, column=2, padx=5)
            ctk.CTkButton(frame, text="Remove", command=lambda fp=file_path: self.remove_manifest_file(fp), width=90).grid(row=0, column=3, padx=5)
            frame.grid_columnconfigure(0, weight=1)
        self.log("Displayed installed games.")

    def remove_manifest_file(self, file_path):
        if messagebox.askyesno("Confirm Remove", f"Are you sure you want to remove manifest file '{os.path.basename(file_path)}'?"):
            try:
                os.remove(file_path)
                self.log(f"Removed manifest file: {file_path}")
                messagebox.showinfo("Removed", f"Manifest file removed: {os.path.basename(file_path)}")
                self.refresh_installed_games()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove manifest file: {str(e)}")
                self.log(f"Error removing manifest file {file_path}: {str(e)}")

    def refresh_installed_games(self):
        if self.games_scroll_frame and self.saved_main_path:
            output_folder = os.path.join(self.saved_main_path, "applist")
            self.populate_installed_games(self.games_scroll_frame, output_folder)

    def open_store(self, appid):
        url = f"https://store.steampowered.com/app/{appid}"
        webbrowser.open(url)
        self.log(f"Opened store page for AppID {appid}.")

    def show_game_details(self, appid):
        details = self.get_app_details(appid)
        if not details:
            messagebox.showerror("Error", "Unable to fetch game details.")
            return
        details_win = ctk.CTkToplevel(self.root)
        details_win.title(f"Game Details - {details.get('name', 'Unknown')}")
        details_win.geometry("500x400")
        details_win.grab_set()
        text = f"Name: {details.get('name', 'Unknown')}\n\n"
        text += f"Short Description:\n{details.get('short_description', 'N/A')}\n\n"
        rd = details.get("release_date", {}).get("date", "N/A")
        text += f"Release Date: {rd}\n"
        devs = details.get("developers", [])
        text += f"Developers: {', '.join(devs) if devs else 'N/A'}\n"
        pubs = details.get("publishers", [])
        text += f"Publishers: {', '.join(pubs) if pubs else 'N/A'}\n"
        genres = details.get("genres", [])
        if genres:
            genre_list = [genre.get("description", "") for genre in genres]
            text += f"Genres: {', '.join(genre_list)}\n"
        else:
            text += "Genres: N/A\n"
        metacritic = details.get("metacritic", {}).get("score", "N/A")
        text += f"Metacritic Score: {metacritic}\n"
        details_text = ctk.CTkTextbox(details_win, wrap="word")
        details_text.pack(padx=10, pady=10, fill="both", expand=True)
        details_text.insert("0.0", text)
        details_text.configure(state="disabled")

    def search_game(self):
        search_win = ctk.CTkToplevel(self.root)
        search_win.title("Search Game")
        search_win.geometry("500x600")
        search_win.grab_set()
        search_entry = ctk.CTkEntry(search_win, placeholder_text="Enter game name")
        search_entry.pack(pady=10, padx=10, fill="x")
        results_frame = ctk.CTkScrollableFrame(search_win, height=400)
        results_frame.pack(pady=10, padx=10, fill="both", expand=True)
        ctk.CTkButton(search_win, text="Search", command=lambda: self.perform_search(search_entry.get(), results_frame)).pack(pady=5)

    def perform_search(self, query, results_frame):
        if not query:
            messagebox.showerror("Error", "Please enter a game name to search.")
            return
        self.log(f"Searching for query: '{query}'")
        loading = ctk.CTkToplevel(self.root)
        loading.title("Searching")
        ctk.CTkLabel(loading, text="Searching, please wait...").pack(padx=20, pady=20)
        loading.update()
        try:
            resp = requests.get(
                "https://store.steampowered.com/api/storesearch",
                params={"term": query, "cc": "us", "l": "en"},
                timeout=10,
            )
            data = resp.json()
            matches = data.get("items", [])[:20]
            self.log(f"Found {len(matches)} matches for query '{query}'.")
        except Exception as e:
            loading.destroy()
            messagebox.showerror("Error", f"Failed to search: {str(e)}")
            return
        finally:
            if loading.winfo_exists():
                loading.destroy()
        for widget in results_frame.winfo_children():
            widget.destroy()
        if not matches:
            ctk.CTkLabel(results_frame, text="No games found.", font=("Helvetica", 12)).pack(pady=10)
            return
        for app in matches:
            appid = str(app.get("id", app.get("appid")))
            name = app["name"]
            result_frame = ctk.CTkFrame(results_frame)
            result_frame.pack(fill="x", pady=5, padx=5)
            header_image_url = self.get_app_details(appid).get("header_image", None)
            if header_image_url:
                try:
                    image_data = requests.get(header_image_url, timeout=5).content
                    pil_image = Image.open(BytesIO(image_data))
                    pil_image = pil_image.resize((80, 45))
                    ct_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(80,45))
                    image_label = ctk.CTkLabel(result_frame, image=ct_image, text="")
                    image_label.image = ct_image
                    image_label.grid(row=0, column=0, rowspan=2, padx=5, pady=5)
                except Exception:
                    ctk.CTkLabel(result_frame, text="No Image").grid(row=0, column=0, rowspan=2, padx=5, pady=5)
            else:
                ctk.CTkLabel(result_frame, text="No Image").grid(row=0, column=0, rowspan=2, padx=5, pady=5)
            ctk.CTkLabel(result_frame, text=name, font=("Helvetica", 14), anchor="w").grid(row=0, column=1, sticky="w")
            toggle_btn = ctk.CTkButton(result_frame, text="▼", width=30)
            toggle_btn.grid(row=0, column=2, padx=5)
            ctk.CTkButton(result_frame, text="Add to Manifest", command=lambda a=appid: self.add_game_to_manifest(a), width=120).grid(row=0, column=3, padx=5)
            result_frame.grid_columnconfigure(1, weight=1)
            def toggle_desc(btn=toggle_btn, appid=appid, parent=result_frame):
                if not hasattr(btn, "desc_label"):
                    details = self.get_app_details(appid)
                    desc_text = details.get("short_description", "No description available")
                    desc_label = ctk.CTkLabel(parent, text=desc_text, font=("Helvetica", 10), anchor="w", wraplength=200)
                    desc_label.grid(row=1, column=1, columnspan=3, sticky="w", padx=5, pady=5)
                    btn.desc_label = desc_label
                    btn.configure(text="▲")
                else:
                    btn.desc_label.destroy()
                    del btn.desc_label
                    btn.configure(text="▼")
            toggle_btn.configure(command=toggle_desc)
        self.log("Search complete; results displayed.")

    def add_game_to_manifest(self, appid):
        if not self.saved_main_path:
            messagebox.showerror("Error", "Main Steam path is not set.")
            return
        output_folder = os.path.join(self.saved_main_path, "applist")
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create manifest folder: {str(e)}")
                return
        next_number = self.get_next_manifest_number(output_folder)
        output_file = os.path.join(output_folder, f"{next_number}.txt")
        try:
            with open(output_file, "w") as f:
                f.write(f"{appid}\n")
            messagebox.showinfo("Added", f"Game with AppID {appid} added to manifest folder as file {next_number}.txt")
            self.log(f"Manually added AppID {appid} to manifest folder as file {next_number}.txt")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add game to manifest: {str(e)}")

    def get_next_manifest_number(self, output_folder):
        existing = []
        for f in os.listdir(output_folder):
            if f.endswith(".txt") and f != "0.txt":
                try:
                    num = int(os.path.splitext(f)[0])
                    existing.append(num)
                except ValueError:
                    continue
        return max(existing) + 1 if existing else 1

    def get_app_details(self, appid):
        if appid in self.appid_cache:
            return self.appid_cache[appid]
        try:
            resp = requests.get(
                "https://store.steampowered.com/api/appdetails",
                params={"appids": appid},
                timeout=10,
            )
            data = resp.json()
            details = data.get(str(appid), {}).get("data", {})
            self.appid_cache[appid] = details
            return details
        except Exception as e:
            self.log(f"Failed to fetch details for AppID {appid}: {str(e)}")
            return {}

    def get_game_name(self, appid):
        details = self.get_app_details(appid)
        return details.get("name", "Unknown")


    # ───────────────────────────────
    # SETTINGS WINDOW WITH ADVANCED OPTIONS (Buttons arranged side by side)
    # ───────────────────────────────
    def config_window(self):
        config_win = ctk.CTkToplevel(self.root)
        config_win.title("Settings")
        config_win.geometry("380x420")
        config_win.attributes('-topmost', True)
        config_win.grab_set()

        # Appearance & Theme options.
        top_frame = ctk.CTkFrame(config_win)
        top_frame.pack(pady=10, fill="x")
        ctk.CTkLabel(top_frame, text="Appearance Mode:", font=("Helvetica", 14)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        appearance_option = ctk.CTkOptionMenu(top_frame, values=["System", "Light", "Dark"],
                                               command=lambda mode: self.change_appearance_mode(mode),
                                               width=150)
        appearance_option.set(self.saved_appearance_mode.capitalize())
        appearance_option.grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkLabel(top_frame, text="Select Theme:", font=("Helvetica", 14)).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        theme_option = ctk.CTkOptionMenu(top_frame, values=["dark-blue", "green", "blue"],
                                          command=lambda theme: self.change_theme(theme),
                                          width=150)
        theme_option.set(self.saved_theme)
        theme_option.grid(row=1, column=1, padx=5, pady=5)

        # Donate button is in the sidebar of the main window; no need here.

        # Startup and Exit Behavior options.
        startup_frame = ctk.CTkFrame(config_win)
        startup_frame.pack(pady=5, fill="x")
        ctk.CTkLabel(startup_frame, text="Run on Startup:", font=("Helvetica", 14)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.run_on_startup_var = ctk.BooleanVar(value=self.run_on_startup)
        startup_checkbox = ctk.CTkCheckBox(startup_frame, text="", variable=self.run_on_startup_var, command=self.update_run_on_startup)
        startup_checkbox.grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkLabel(startup_frame, text="Exit Behavior:", font=("Helvetica", 14)).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        exit_behavior_menu = ctk.CTkOptionMenu(startup_frame, values=["Minimize to Tray", "Exit on Close"],
                                              command=lambda choice: self.set_exit_behavior(choice),
                                              width=150)
        exit_behavior_menu.set("Minimize to Tray" if self.exit_to_tray else "Exit on Close")
        exit_behavior_menu.grid(row=1, column=1, padx=5, pady=5)
        
       
        

        # Finally, arrange Reset Settings and Clear Cache buttons side by side.
        bottom_frame = ctk.CTkFrame(config_win)
        bottom_frame.pack(pady=10, fill="x")
        reset_button = ctk.CTkButton(bottom_frame, text="Reset Settings", command=self.reset_settings, width=150)
        reset_button.grid(row=0, column=0, padx=5, pady=5)
        clear_cache_button = ctk.CTkButton(bottom_frame, text="Clear Cache", command=self.clear_cache, width=150)
        clear_cache_button.grid(row=0, column=1, padx=5, pady=5)




    def set_exit_behavior(self, choice):
        self.exit_to_tray = (choice == "Minimize to Tray")
        self.save_config()
        self.log(f"Exit behavior set to: {'Minimize to Tray' if self.exit_to_tray else 'Exit on Close'}.")

    def update_run_on_startup(self):
        self.run_on_startup = self.run_on_startup_var.get()
        if self.run_on_startup:
            self.add_to_startup()
        else:
            self.remove_from_startup()
        self.save_config()
        self.log(f"Run on Startup set to {self.run_on_startup}.")

    def add_to_startup(self):
        if os.name != 'nt':
            return
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            cmd = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
            winreg.SetValueEx(key, "SteamManagerApp", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            self.log("Added to startup in registry.")
        except Exception as e:
            self.log(f"Failed to add to startup: {str(e)}")

    def remove_from_startup(self):
        if os.name != 'nt':
            return
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, "SteamManagerApp")
            winreg.CloseKey(key)
            self.log("Removed from startup in registry.")
        except Exception as e:
            self.log(f"Failed to remove from startup: {str(e)}")

    def export_log(self):
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if not filename:
            return
        try:
            log_content = self.log_text.get("0.0", "end") if self.log_text else ""
            with open(filename, "w", encoding="utf-8") as f:
                f.write(log_content)
            messagebox.showinfo("Exported", f"Log exported successfully to {filename}")
            self.log(f"Log exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export log: {str(e)}")
            self.log(f"Error exporting log: {str(e)}")

    def about_window(self):
        about_win = ctk.CTkToplevel(self.root)
        about_win.title("About Steam Manager")
        about_win.geometry("400x300")
        about_win.grab_set()
        about_text = (
            "Steam Manager v1.0\n\n"
            "This application helps manage your Steam installation and manifests.\n\n"
            "Features:\n"
            "  • Open/Close Steam with auto cache cleanup\n"
            "  • Refresh Steam game manifests\n"
            "  • Search for games via the Steam API\n"
            "  • Minimize to system tray\n"
            "  • Option to run on startup (Windows)\n"
            "  • Toggle Luma (renames greenluma files by appending a '1')\n"
            "  • Exit Behavior toggle (Minimize to Tray or Exit on Close)\n"
            "  • Donate button below the Exit option for donations to 0xFa1F17918319bEA39841F6891A4FC518b22C5738\n"
            "  • Auto Dark Mode (switches theme based on time)\n"
            "  • Reset Settings and Clear Cache\n\n"
            "Developed by Your Name Here\n"
            "For updates and support, visit: https://your-update-url.example.com\n"
        )
        about_label = ctk.CTkLabel(about_win, text=about_text, font=("Helvetica", 12), justify="left")
        about_label.pack(padx=10, pady=10, fill="both", expand=True)

    def check_for_updates(self):
        webbrowser.open("https://your-update-url.example.com")
        self.log("Checked for updates.")

    def change_appearance_mode(self, mode):
        mode = mode.lower()
        ctk.set_appearance_mode(mode)
        self.saved_appearance_mode = mode
        self.save_config(appearance_mode=mode)
        self.log(f"Appearance mode changed to {mode}.")
        self.reload_gui()

    def change_theme(self, theme):
        ctk.set_default_color_theme(theme)
        self.saved_theme = theme
        self.save_config(theme=theme)
        self.log(f"Theme changed to {theme}.")
        self.reload_gui()

    def reload_gui(self):
        current_geometry = self.root.geometry()
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.geometry(current_geometry)
        self.initialize_main_window()

    def backup_config(self):
        if os.path.exists(self.config_file):
            try:
                shutil.copy(self.config_file, "config_backup.ini")
                messagebox.showinfo("Backup", "Configuration backup created successfully.")
                self.log("Configuration backup created.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to backup config: {str(e)}")
                self.log(f"Error during config backup: {str(e)}")
        else:
            messagebox.showerror("Error", "No configuration file to backup.")
            self.log("Backup failed: configuration file not found.")

    def restore_config(self):
        if os.path.exists("config_backup.ini"):
            try:
                shutil.copy("config_backup.ini", self.config_file)
                self.load_config()
                messagebox.showinfo("Restore", "Configuration restored successfully. Restart the application for changes to take effect.")
                self.log("Configuration restored from backup.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restore config: {str(e)}")
                self.log(f"Error during config restore: {str(e)}")
        else:
            messagebox.showerror("Error", "No backup configuration file found.")
            self.log("Restore failed: backup configuration file not found.")

    def tutorial_window(self):
        tut_win = ctk.CTkToplevel(self.root)
        tut_win.title("Tutorial - How to Use Steam Manager")
        tut_win.geometry("600x500")
        tut_win.grab_set()
        tut_text = ctk.CTkTextbox(tut_win, wrap="word")
        tut_text.pack(padx=10, pady=10, fill="both", expand=True)
        tutorial_content = (
            "Welcome to Steam Manager!\n\n"
            "This application allows you to manage your Steam installation and games with many helpful features:\n\n"
            "1. Steam Control:\n"
            "   - Open Steam: Launches the Steam client and automatically clears the app cache.\n"
            "   - Close Steam: Force-closes Steam if it is running.\n\n"
            "2. Manifest Operations:\n"
            "   - Refresh Manifests: Scans your Steam folder (and any extra folders) for installed games and updates the manifest list.\n"
            "   - Toggle Luma: Toggles the Luma files by renaming them (a '1' is appended when toggled on).\n"
            "   - Open Manifest Folder: Opens the folder containing the manifest files.\n"
            "   - Add Manifest Folder: Add an extra manifest folder directly from the sidebar.\n\n"
            "3. Game Management:\n"
            "   - View Installed Games: Displays a list of installed games.\n"
            "     • Click 'Details' to view extended game information.\n"
            "   - Search Game: Use the Steam API to search for games online, view short descriptions, and add them to the manifest.\n\n"
            "4. Settings & Others:\n"
            "   - Settings: Change appearance, theme, add extra folders, and configure options.\n"
            "       • Auto Dark Mode: Automatically switches theme based on time.\n"
            "       • Startup Options: Choose to have Steam Manager run automatically when Windows starts.\n"
            "       • Exit Behavior: Choose between minimizing to tray or exiting on close.\n"
            "   - Donate: Click the Donate button below the Exit option to copy the donation address to your clipboard.\n"
            "   - Tutorial: View this help window at any time.\n"
            "   - Exit: Close the application (or minimize it to the system tray, if enabled).\n\n"
            "Enjoy using Steam Manager!"
        )
        tut_text.insert("0.0", tutorial_content)
        tut_text.configure(state="disabled")
        self.log("Tutorial opened.")

    def donate(self):
        address = "0xFa1F17918319bEA39841F6891A4FC518b22C5738"
        self.root.clipboard_clear()
        self.root.clipboard_append(address)
        messagebox.showinfo("Donate", f"Donation address copied to clipboard:\n{address}")

if __name__ == "__main__":
    SteamManagerApp()
