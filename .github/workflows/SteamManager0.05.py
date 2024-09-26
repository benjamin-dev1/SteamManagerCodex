import customtkinter as tk
import os
from tkinter import filedialog
import re
import configparser

# Initialize ConfigParser
config = configparser.ConfigParser()
config_file = 'config.ini'

# Global variables to hold the main Steam path and additional manifest paths
saved_main_path = None
saved_paths = []

current_frame = None

def load_config():
    """Load the main Steam path, additional paths, and theme settings from the config file."""
    if os.path.exists(config_file):
        try:
            config.read(config_file)
            steam_path = config['Paths'].get('steam_path', None)
            extra_paths = config['Paths'].get('extra_paths', '').split('|') if config['Paths'].get('extra_paths') else []
            theme = config['Settings'].get('theme', 'dark-blue')
            appearance_mode = config['Settings'].get('appearance_mode', 'system')
            return steam_path, extra_paths, theme, appearance_mode, None
        except (configparser.Error, KeyError):
            return None, [], 'dark-blue', 'system', "Config file is corrupted."
    return None, [], 'dark-blue', 'system', None

def save_config(main_path=None, extra_paths=None, theme=None, appearance_mode=None):
    """Save the main Steam path, additional paths, theme, and appearance mode to the config file."""
    if not config.has_section('Paths'):
        config.add_section('Paths')
    
    if main_path:
        config['Paths']['steam_path'] = main_path
    
    if extra_paths is not None:
        config['Paths']['extra_paths'] = '|'.join(extra_paths)

    if not config.has_section('Settings'):
        config.add_section('Settings')
    
    if theme:
        config['Settings']['theme'] = theme
    if appearance_mode:
        config['Settings']['appearance_mode'] = appearance_mode
    
    with open(config_file, 'w') as configfile:
        config.write(configfile)

# Load initial configuration
saved_main_path, saved_paths, saved_theme, saved_appearance_mode, config_error = load_config()

# Set the theme and appearance mode
tk.set_appearance_mode(saved_appearance_mode)
tk.set_default_color_theme(saved_theme)

# Initialize the main window
# Initialize the main window
root = tk.CTk()
root.geometry("510x400")
root.resizable(True, True)  # Allow the window to be resizable
root.title("Steam Manager")


def show_loading_screen():
    """Display a loading screen and check for config file issues."""
    splash = tk.CTkToplevel(root)
    splash.geometry("300x200")
    splash.title("Loading")

    splash_label = tk.CTkLabel(splash, text="Loading, please wait...", font=("Helvetica", 16))
    splash_label.pack(expand=True, padx=20, pady=50)

    root.update_idletasks()
    x = (root.winfo_screenwidth() - splash.winfo_reqwidth()) // 2
    y = (root.winfo_screenheight() - splash.winfo_reqheight()) // 2
    splash.geometry(f"+{x}+{y}")

    if config_error:
        splash.withdraw()
        show_config_error()
    elif not saved_main_path or not os.path.exists(os.path.join(saved_main_path, "steam.exe")):
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
    """Prompt the user to select the main Steam folder during the first boot."""
    firstboot_window = tk.CTkToplevel(root)
    firstboot_window.title("Firstboot")
    firstboot_window.geometry("400x300")
    firstboot_window.grab_set()

    label = tk.CTkLabel(firstboot_window, text="Please select your Steam folder:")
    label.pack(pady=10)

    button_change_folder = tk.CTkButton(firstboot_window, text="Change Folder", command=lambda: Openfolder(firstboot_window, is_main_path=True))
    button_change_folder.pack(pady=5)

def Openfolder(window, is_main_path=False):
    """Open a folder dialog to select the main Steam folder or additional manifest directories."""
    global steam_exe, file_path, saved_paths, saved_main_path

    file_path = filedialog.askdirectory(title="Select the folder")

    if file_path and os.path.exists(file_path):
        if is_main_path:  # Validate main Steam folder
            steam_exe = os.path.join(file_path, "steam.exe")
            if os.path.exists(steam_exe):
                saved_main_path = file_path
                save_config(main_path=saved_main_path, extra_paths=saved_paths)
                window.destroy()
                initialize_main_window()
            else:
                error_label = tk.CTkLabel(window, text="Steam executable not found in the selected folder.", fg_color="red")
                error_label.pack(pady=5)
        else:  # Additional folders for manifest files
            saved_paths.append(file_path)
            save_config(main_path=saved_main_path, extra_paths=saved_paths)
            window.destroy()
            initialize_main_window()
    else:
        error_label = tk.CTkLabel(window, text="Invalid folder selected.", fg_color="red")
        error_label.pack(pady=5)

def initialize_main_window():
    """Initialize the main window and display the saved main Steam path and additional paths."""
    global current_frame
    
    if current_frame is not None:
        current_frame.destroy()

    current_frame = tk.CTkFrame(root, corner_radius=15)
    current_frame.pack(pady=10, padx=60, fill="both", expand=True) 

    title_label = tk.CTkLabel(current_frame, text="Steam Manager", font=("Helvetica", 20, "bold"))
    title_label.pack(pady=20)

    button_open_steam = tk.CTkButton(current_frame, text="Open Steam", command=OpenSteam)
    button_open_steam.pack(pady=(10, 5))

    button_close_steam = tk.CTkButton(current_frame, text="Close Steam", command=CloseSteam)
    button_close_steam.pack(pady=5)

    button_manifest = tk.CTkButton(current_frame, text="Manifest File Adder", command=applist)
    button_manifest.pack(pady=5)

    button_toggle_luma = tk.CTkButton(current_frame, text="ON/OFF", command=onLuma)
    button_toggle_luma.pack(pady=5)

    # Display main Steam path
    main_path_label = tk.CTkLabel(current_frame, text="Main Steam Path:")
    main_path_label.pack(pady=10)
    
    main_path_value = tk.CTkLabel(current_frame, text=saved_main_path or "No path set", fg_color="green" if saved_main_path else "red")
    main_path_value.pack(pady=2)

    # Display additional manifest paths
    extra_paths_label = tk.CTkLabel(current_frame, text="Additional Manifest Paths:")
    extra_paths_label.pack(pady=10)

    if saved_paths:
        # Create a scrollable frame to handle many paths
        scrollable_frame = tk.CTkScrollableFrame(current_frame, width=400, height=150)
        scrollable_frame.pack(pady=5, padx=5)

        for path in saved_paths:
            path_item = tk.CTkLabel(scrollable_frame, text=path)
            path_item.pack(pady=2)
    else:
        no_paths_label = tk.CTkLabel(current_frame, text="No extra paths set")
        no_paths_label.pack(pady=2)

    # Settings button in top-right corner
    button_config = tk.CTkButton(root, text="⚙", width=30, corner_radius=50, command=config_window)
    button_config.place(relx=0.98, rely=0.02, anchor='ne')

def OpenSteam():
    """Open Steam and optionally the cache cleaner executable."""
    global steam_exe, saved_main_path
    if saved_main_path:
        steam_exe = os.path.join(saved_main_path, "steam.exe")
        if os.path.exists(steam_exe):
            os.startfile(steam_exe)
            appcache = os.path.join(saved_main_path, "DeleteSteamAppCache.exe")
            if os.path.exists(appcache):
                os.startfile(appcache)
        else:
            print("Steam executable not found in the saved path.")
    else:
        print("Main Steam path is not set.")
def CloseSteam():
    """Close the Steam application."""
    os.system("taskkill /f /im steam.exe")

def onLuma():
    """Toggle the luma file state."""
    luma = os.path.join(saved_main_path, "user32.dll")
    if os.path.exists(luma):
        os.rename(luma, os.path.join(saved_main_path, "User321.dll"))
    else:
        os.rename(os.path.join(saved_main_path, "User321.dll"), luma)

def applist():
    """Generate manifest files list from both the main Steam directory and additional directories."""
    output_folder = os.path.join(saved_main_path, "applist")
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    file_counter = 1
    all_folders = [saved_main_path] + saved_paths

    for folder in all_folders:
        if os.path.exists(folder):
            items = os.listdir(folder)
            for item in items:
                item_path = os.path.join(folder, item)
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
    """Open a window to manage theme, appearance, and extra manifest paths."""
    config_window = tk.CTkToplevel(root)
    config_window.title("Configuration")
    config_window.geometry("400x350")
    
    # Make the config window always on top
    config_window.attributes('-topmost', True)

    # Appearance mode settings
    appearance_label = tk.CTkLabel(config_window, text="Appearance Mode:")
    appearance_label.pack(pady=10)

    appearance_option = tk.CTkOptionMenu(
        config_window,
        values=["System", "Light", "Dark"],
        command=lambda mode: change_appearance_mode(mode)
    )
    appearance_option.set(saved_appearance_mode.capitalize())
    appearance_option.pack(pady=5)

    # Theme settings
    theme_label = tk.CTkLabel(config_window, text="Select Theme:")
    theme_label.pack(pady=10)

    theme_option = tk.CTkOptionMenu(
        config_window,
        values=["dark-blue", "green", "blue"],
        command=lambda theme: change_theme(theme)
    )
    theme_option.set(saved_theme)
    theme_option.pack(pady=5)

    # Add manifest folder
    add_folder_label = tk.CTkLabel(config_window, text="Add Manifest Folder:")
    add_folder_label.pack(pady=10)

    button_open_folder = tk.CTkButton(config_window, text="Add Folder", command=lambda: Openfolder(config_window, is_main_path=False))
    button_open_folder.pack(pady=5)

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
