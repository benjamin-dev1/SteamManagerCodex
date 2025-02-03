import customtkinter as ctk
import os
from tkinter import filedialog, messagebox
import re
import configparser

class SteamManagerApp:
    def __init__(self):
        # Config file and default settings
        self.config_file = 'config.ini'
        self.config = configparser.ConfigParser()
        self.saved_main_path = None
        self.saved_paths = []
        self.saved_theme = 'dark-blue'
        self.saved_appearance_mode = 'system'
        self.config_error = None

        # Load configuration from file (or set defaults)
        self.load_config()

        # Set appearance and theme
        ctk.set_appearance_mode(self.saved_appearance_mode)
        ctk.set_default_color_theme(self.saved_theme)

        # Initialize main window
        self.root = ctk.CTk()
        self.root.geometry("800x500")
        self.root.title("Steam Manager")
        self.root.resizable(True, True)

        # Frames that will be created in the main UI
        self.sidebar_frame = None
        self.content_frame = None

        # Show splash screen then the appropriate window (firstboot/config error/main)
        self.show_loading_screen()
        self.root.mainloop()

    # ───────────────────────────────
    # CONFIGURATION METHODS
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
            except (configparser.Error, KeyError):
                self.config_error = "Config file is corrupted."
        else:
            # First boot scenario – no config exists
            self.saved_main_path = None
            self.saved_paths = []
            self.saved_theme = 'dark-blue'
            self.saved_appearance_mode = 'system'

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

        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

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

        # Decide what to show next based on config status
        if self.config_error:
            splash.withdraw()
            self.show_config_error()
        elif not self.saved_main_path or not os.path.exists(os.path.join(self.saved_main_path, "steam.exe")):
            self.root.after(2000, lambda: [splash.destroy(), self.firstboot()])
        else:
            self.root.after(500, lambda: [splash.destroy(), self.initialize_main_window()])

    def show_config_error(self):
        error_window = ctk.CTkToplevel(self.root)
        error_window.geometry("350x200")
        error_window.title("Configuration Error")
        error_window.grab_set()

        error_label = ctk.CTkLabel(
            error_window, 
            text="Config file is corrupted.\nPlease reset it.",
            text_color="red", 
            font=("Helvetica", 14)
        )
        error_label.pack(pady=20)

        reset_button = ctk.CTkButton(error_window, text="Reset Config", command=self.reset_config)
        reset_button.pack(pady=5)
        exit_button = ctk.CTkButton(error_window, text="Exit", command=self.root.quit)
        exit_button.pack(pady=5)

    def reset_config(self):
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        self.root.quit()

    # ───────────────────────────────
    # FIRST BOOT & FOLDER SELECTION
    # ───────────────────────────────
    def firstboot(self):
        fb_window = ctk.CTkToplevel(self.root)
        fb_window.title("First Boot - Select Steam Folder")
        fb_window.geometry("400x250")
        fb_window.grab_set()

        label = ctk.CTkLabel(fb_window, text="Please select your Steam folder:", font=("Helvetica", 14))
        label.pack(pady=20)

        select_button = ctk.CTkButton(
            fb_window, 
            text="Select Folder", 
            command=lambda: self.open_folder(fb_window, is_main_path=True)
        )
        select_button.pack(pady=10)

    def open_folder(self, window, is_main_path=False):
        folder_path = filedialog.askdirectory(title="Select Folder")
        if folder_path and os.path.exists(folder_path):
            if is_main_path:
                steam_exe = os.path.join(folder_path, "steam.exe")
                if os.path.exists(steam_exe):
                    self.saved_main_path = folder_path
                    self.save_config(main_path=self.saved_main_path, extra_paths=self.saved_paths)
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
                window.destroy()
                self.initialize_main_window()
        else:
            messagebox.showerror("Error", "Invalid folder selected.")

    # ───────────────────────────────
    # MAIN UI INITIALIZATION (MODERN, STEAM‑LIKE)
    # ───────────────────────────────
    def initialize_main_window(self):
        # Clear any existing widgets in the root window
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create a sidebar frame on the left
        self.sidebar_frame = ctk.CTkFrame(self.root, width=200, corner_radius=10)
        self.sidebar_frame.pack(side="left", fill="y", padx=10, pady=10)

        # Sidebar buttons with modern styling
        btn_open = ctk.CTkButton(self.sidebar_frame, text="Open Steam", command=self.open_steam, width=180)
        btn_open.pack(pady=(20, 10))
        btn_close = ctk.CTkButton(self.sidebar_frame, text="Close Steam", command=self.close_steam, width=180)
        btn_close.pack(pady=10)
        btn_manifest = ctk.CTkButton(self.sidebar_frame, text="Manifest Adder", command=self.manifest_adder, width=180)
        btn_manifest.pack(pady=10)
        btn_toggle = ctk.CTkButton(self.sidebar_frame, text="Toggle Luma", command=self.toggle_luma, width=180)
        btn_toggle.pack(pady=10)
        btn_config = ctk.CTkButton(self.sidebar_frame, text="Settings", command=self.config_window, width=180)
        btn_config.pack(pady=10)
        btn_exit = ctk.CTkButton(self.sidebar_frame, text="Exit", command=self.root.quit, width=180)
        btn_exit.pack(pady=10)

        # Create a main content frame on the right
        self.content_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.content_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        title_label = ctk.CTkLabel(self.content_frame, text="Steam Manager", font=("Helvetica", 24, "bold"))
        title_label.pack(pady=20)

        # Display the saved main Steam path
        main_path_label = ctk.CTkLabel(self.content_frame, text="Main Steam Path:", font=("Helvetica", 16))
        main_path_label.pack(pady=(10, 5))
        main_path_text = self.saved_main_path if self.saved_main_path else "No path set"
        main_path_color = "green" if self.saved_main_path else "red"
        main_path_value = ctk.CTkLabel(self.content_frame, text=main_path_text, text_color=main_path_color, font=("Helvetica", 14))
        main_path_value.pack(pady=(0, 10))

        # Display additional manifest paths in a scrollable frame
        extra_paths_label = ctk.CTkLabel(self.content_frame, text="Additional Manifest Paths:", font=("Helvetica", 16))
        extra_paths_label.pack(pady=(10, 5))
        if self.saved_paths:
            scrollable_frame = ctk.CTkScrollableFrame(self.content_frame, height=150)
            scrollable_frame.pack(pady=5, padx=5, fill="both", expand=True)
            for path in self.saved_paths:
                path_item = ctk.CTkLabel(scrollable_frame, text=path, font=("Helvetica", 12))
                path_item.pack(pady=2, padx=5, anchor="w")
        else:
            no_paths_label = ctk.CTkLabel(self.content_frame, text="No extra paths set", font=("Helvetica", 12))
            no_paths_label.pack(pady=5)

    # ───────────────────────────────
    # FUNCTIONALITY METHODS
    # ───────────────────────────────
    def open_steam(self):
        if self.saved_main_path:
            steam_exe = os.path.join(self.saved_main_path, "steam.exe")
            if os.path.exists(steam_exe):
                try:
                    os.startfile(steam_exe)
                    # Optionally open a cache cleaner if present
                    appcache = os.path.join(self.saved_main_path, "DeleteSteamAppCache.exe")
                    if os.path.exists(appcache):
                        os.startfile(appcache)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to open Steam: {str(e)}")
            else:
                messagebox.showerror("Error", "Steam executable not found in the saved path.")
        else:
            messagebox.showerror("Error", "Main Steam path is not set.")

    def close_steam(self):
        try:
            os.system("taskkill /f /im steam.exe")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to close Steam: {str(e)}")

    def toggle_luma(self):
        try:
            luma_on = os.path.join(self.saved_main_path, "user32.dll")
            luma_off = os.path.join(self.saved_main_path, "User321.dll")
            if os.path.exists(luma_on):
                os.rename(luma_on, luma_off)
            elif os.path.exists(luma_off):
                os.rename(luma_off, luma_on)
            else:
                messagebox.showerror("Error", "Luma files not found.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle Luma: {str(e)}")

    def manifest_adder(self):
        if not self.saved_main_path or not os.path.exists(self.saved_main_path):
            messagebox.showerror("Error", "Main Steam path is invalid.")
            return

        output_folder = os.path.join(self.saved_main_path, "applist")
        # Clear or create the output folder
        if os.path.exists(output_folder):
            try:
                for f in os.listdir(output_folder):
                    file_path = os.path.join(output_folder, f)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear output folder: {str(e)}")
                return
        else:
            try:
                os.makedirs(output_folder)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create output folder: {str(e)}")
                return

        total_files = 0
        file_counter = 1

        # Process the main Steam manifest folder
        main_steamapps = os.path.join(self.saved_main_path, "steamapps")
        if os.path.exists(main_steamapps):
            initial_counter = file_counter
            file_counter = self.process_manifest_files(main_steamapps, output_folder, file_counter)
            total_files += (file_counter - initial_counter)

        # Process any additional manifest paths
        for path in self.saved_paths:
            steamapps_path = os.path.join(path, "steamapps")
            if os.path.exists(steamapps_path):
                initial_counter = file_counter
                file_counter = self.process_manifest_files(steamapps_path, output_folder, file_counter)
                total_files += (file_counter - initial_counter)
            else:
                messagebox.showwarning("Warning", f"Skipping invalid path: {path} (steamapps not found)")

        # Create a preset file (example: "0.txt")
        preset_path = os.path.join(output_folder, "0.txt")
        try:
            with open(preset_path, "w") as f:
                f.write("480\n")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create preset file: {str(e)}")
            return

        messagebox.showinfo("Success", f"Successfully added {total_files} games to the manifest list.")

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
        return file_counter

    # ───────────────────────────────
    # SETTINGS / CONFIGURATION WINDOW
    # ───────────────────────────────
    def config_window(self):
        config_win = ctk.CTkToplevel(self.root)
        config_win.title("Settings")
        config_win.geometry("400x350")
        config_win.attributes('-topmost', True)
        config_win.grab_set()

        appearance_label = ctk.CTkLabel(config_win, text="Appearance Mode:", font=("Helvetica", 14))
        appearance_label.pack(pady=10)
        appearance_option = ctk.CTkOptionMenu(
            config_win,
            values=["System", "Light", "Dark"],
            command=lambda mode: self.change_appearance_mode(mode)
        )
        appearance_option.set(self.saved_appearance_mode.capitalize())
        appearance_option.pack(pady=5)

        theme_label = ctk.CTkLabel(config_win, text="Select Theme:", font=("Helvetica", 14))
        theme_label.pack(pady=10)
        theme_option = ctk.CTkOptionMenu(
            config_win,
            values=["dark-blue", "green", "blue"],
            command=lambda theme: self.change_theme(theme)
        )
        theme_option.set(self.saved_theme)
        theme_option.pack(pady=5)

        add_folder_label = ctk.CTkLabel(config_win, text="Add Manifest Folder:", font=("Helvetica", 14))
        add_folder_label.pack(pady=10)
        btn_add_folder = ctk.CTkButton(config_win, text="Add Folder", command=lambda: self.open_folder(config_win, is_main_path=False))
        btn_add_folder.pack(pady=5)

    def change_appearance_mode(self, mode):
        mode = mode.lower()
        ctk.set_appearance_mode(mode)
        self.saved_appearance_mode = mode
        self.save_config(appearance_mode=mode)
        self.reload_gui()

    def change_theme(self, theme):
        ctk.set_default_color_theme(theme)
        self.saved_theme = theme
        self.save_config(theme=theme)
        self.reload_gui()

    def reload_gui(self):
        current_geometry = self.root.geometry()
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.geometry(current_geometry)
        self.initialize_main_window()

if __name__ == "__main__":
    SteamManagerApp()
