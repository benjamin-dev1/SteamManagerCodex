import customtkinter as tk
import os
from tkinter import filedialog
import re
import configparser

# Initialize ConfigParser
config = configparser.ConfigParser()
config_file = 'config.ini'

def load_config():
    """Load the Steam path and theme settings from the config file if it exists."""
    if os.path.exists(config_file):
        try:
            config.read(config_file)
            steam_path = config['Paths'].get('steam_path', None)
            theme = config['Settings'].get('theme', 'dark-blue')
            appearance_mode = config['Settings'].get('appearance_mode', 'system')
            return steam_path, theme, appearance_mode, None
        except (configparser.Error, KeyError):
            return None, 'dark-blue', 'system', "Config file is corrupted."
    return None, 'dark-blue', 'system', None

def save_config(path=None, theme=None, appearance_mode=None):
    """Save the Steam path, theme, and appearance mode to the config file."""
    if not config.has_section('Paths'):
        config.add_section('Paths')
    if path:
        config['Paths']['steam_path'] = path
    
    if not config.has_section('Settings'):
        config.add_section('Settings')
    if theme:
        config['Settings']['theme'] = theme
    if appearance_mode:
        config['Settingsp']['appearance_mode'] = appearance_mode
    
    with open(config_file, 'w') as configfile:
        config.write(configfile)

# Load initial configuration
saved_path, saved_theme, saved_appearance_mode, config_error = load_config()

# Set the theme and appearance mode
tk.set_appearance_mode(saved_appearance_mode)
tk.set_default_color_theme(saved_theme)

# Initialize the main window
root = tk.CTk()
root.geometry("500x400")
root.resizable(False, False)
root.title("Steam Manager")

def show_loading_screen():
    """Display a loading screen and check for config file issues."""
    splash = tk.CTkToplevel(root)
    splash.geometry("300x200")
    splash.title("Loading")

    splash_label = tk.CTkLabel(splash, text="Loading, please wait...", font=("Helvetica", 16))
    splash_label.pack(expand=True, padx=20, pady=50)

    # Center the splash screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() - splash.winfo_reqwidth()) // 2
    y = (root.winfo_screenheight() - splash.winfo_reqheight()) // 2
    splash.geometry(f"+{x}+{y}")

    # Check for config file errors or missing steam path
    if config_error:
        splash.withdraw()
        show_config_error()
    elif not saved_path or not os.path.exists(os.path.join(saved_path, "steam.exe")):
        root.after(2000, lambda: [splash.destroy(), firstboot()])
    else:
        root.after(500, lambda: [splash.destroy(), initialize_main_window()])

def show_config_error():
    """Display a message if the config file is corrupted."""
    error_window = tk.CTkToplevel(root)
    error_window.geometry("300x200")
    error_window.title("Error")

    error_label = tk.CTkLabel(error_window, text="Config file is corrupted.\nPlease reset it.", fg_color="red")
    error_label.pack(pady=10)

    reset_button = tk.CTkButton(error_window, text="Reset Config", command=reset_config)
    reset_button.pack(pady=5)

    exit_button = tk.CTkButton(error_window, text="Exit", command=root.quit)
    exit_button.pack(pady=5)

def reset_config():
    """Reset the config file by deleting it and restarting."""
    if os.path.exists(config_file):
        os.remove(config_file)
    root.quit()

def firstboot():
    """Prompt the user to select the Steam folder."""
    firstboot_window = tk.CTkToplevel(root)
    firstboot_window.title("Firstboot")
    firstboot_window.geometry("300x200")
    firstboot_window.grab_set()

    label = tk.CTkLabel(firstboot_window, text="Please select your Steam folder:")
    label.pack(pady=10)

    button_change_folder = tk.CTkButton(firstboot_window, text="Change Folder", command=lambda: Openfolder(firstboot_window))
    button_change_folder.pack(pady=5)

def Openfolder(window):
    """Open a folder dialog to select the Steam folder and validate the selection."""
    global steam_exe, file_path

    file_path = filedialog.askdirectory(title="Select the folder where Steam is located")
    
    if file_path and os.path.exists(file_path):
        steam_exe = os.path.join(file_path, "steam.exe")
        if os.path.exists(steam_exe):
            save_config(path=file_path)
            window.destroy()
            initialize_main_window()
        else:
            error_label = tk.CTkLabel(window, text="Steam executable not found in the selected folder.", fg_color="red")
            error_label.pack(pady=5)
    else:
        error_label = tk.CTkLabel(window, text="Invalid folder selected.", fg_color="red")
        error_label.pack(pady=5)

def initialize_main_window():
    """Initialize the main window after the Steam path is set."""
    frame = tk.CTkFrame(root, corner_radius=15)  # Added corner radius for modern look
    frame.pack(pady=20, padx=60, fill="both", expand=True)

    title_label = tk.CTkLabel(frame, text="Steam Manager", font=("Helvetica", 20, "bold"))
    title_label.pack(pady=20)

    button_open_steam = tk.CTkButton(frame, text="Open Steam", command=OpenSteam)
    button_open_steam.pack(pady=(10, 5))

    button_close_steam = tk.CTkButton(frame, text="Close Steam", command=CloseSteam)
    button_close_steam.pack(pady=5)

    button_manifest = tk.CTkButton(frame, text="Manifest File Adder", command=applist)
    button_manifest.pack(pady=5)

    button_toggle_luma = tk.CTkButton(frame, text="ON/OFF", command=onLuma)
    button_toggle_luma.pack(pady=5)

    button_config = tk.CTkButton(root, text="⚙", width=30, corner_radius=50, command=config_window)  # More rounded corners for config button
    button_config.place(x=460, y=10)

def OpenSteam():
    """Open Steam and optionally the cache cleaner executable."""
    global appcache
    os.startfile(steam_exe)
    appcache = os.path.join(file_path, "DeleteSteamAppCache.exe")
    if os.path.exists(appcache):
        os.startfile(appcache)

def CloseSteam():
    """Close the Steam application."""
    os.system("taskkill /f /im steam.exe")

def onLuma():
    """Toggle the luma file state."""
    luma = os.path.join(file_path, "user32.dll")
    if os.path.exists(luma):
        os.rename(luma, os.path.join(file_path, "User321.dll"))
    else:
        os.rename(os.path.join(file_path, "User321.dll"), luma)

def applist():
    """Generate manifest files list from the Steam directory and add a preset file."""
    global manifest1
    manifest1 = os.path.join(file_path, "steamapps")
    output_folder = os.path.join(file_path, "applist")
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    if os.path.exists(manifest1):
        items = os.listdir(manifest1)
        file_counter = 1
        
        for item in items:
            item_path = os.path.join(manifest1, item)
            
            if os.path.isfile(item_path):
                numbers = re.findall(r"\d+", item)
                
                if numbers:
                    output_file_path = os.path.join(output_folder, f"{file_counter}.txt")
                    with open(output_file_path, "w") as file:
                        for number in numbers:
                            file.write(f"{number}\n")
                    file_counter += 1

        preset_file_path = os.path.join(output_folder, "0.txt")
        with open(preset_file_path, "w") as preset_file:
            preset_file.write("480\n")

def config_window():
    """Open the configuration window for appearance settings and folder change."""
    config_window = tk.CTkToplevel(root)
    config_window.title("Configuration")
    config_window.geometry("300x250")

    appearance_label = tk.CTkLabel(config_window, text="Appearance Mode:")
    appearance_label.pack(pady=10)

    appearance_option = tk.CTkOptionMenu(
        config_window,
        values=["System", "Light", "Dark"],
        command=lambda mode: change_appearance_mode(mode)
    )
    appearance_option.set(saved_appearance_mode.capitalize())
    appearance_option.pack(pady=5)

    theme_label = tk.CTkLabel(config_window, text="Select Theme:")
    theme_label.pack(pady=10)

    theme_option = tk.CTkOptionMenu(
        config_window,
        values=["dark-blue", "green", "blue"],
        command=lambda theme: change_theme(theme)
    )
    theme_option.set(saved_theme)
    theme_option.pack(pady=5)

    button_change_folder = tk.CTkButton(config_window, text="Change Steam Folder", command=lambda: Openfolder(config_window))
    button_change_folder.pack(pady=10)

def change_appearance_mode(mode):
    """Change the appearance mode and save it to the config."""
    tk.set_appearance_mode(mode.lower())
    save_config(appearance_mode=mode.lower())
    reload_gui()

def change_theme(theme):
    """Change the theme and save it to the config."""
    tk.set_default_color_theme(theme)
    save_config(theme=theme)
    reload_gui()
def reload_gui():
    """Reload the GUI to apply the new theme and appearance mode."""
    current_geometry = root.geometry()
    
    for widget in root.winfo_children():
        widget.destroy()
    
    root.geometry(current_geometry)
    
    initialize_main_window()

# Show loading screen first, then main window or prompt for firstboot
show_loading_screen()

root.mainloop()
