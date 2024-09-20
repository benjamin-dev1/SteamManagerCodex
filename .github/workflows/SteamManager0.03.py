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
        config.read(config_file)
        steam_path = config['Paths'].get('steam_path', None) if 'Paths' in config else None
        theme = config['Settings'].get('theme', 'dark-blue') if 'Settings' in config else 'dark-blue'
        appearance_mode = config['Settings'].get('appearance_mode', 'system') if 'Settings' in config else 'system'
        return steam_path, theme, appearance_mode
    return None, 'dark-blue', 'system'

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
        config['Settings']['appearance_mode'] = appearance_mode
    
    with open(config_file, 'w') as configfile:
        config.write(configfile)

# Load initial configuration
saved_path, saved_theme, saved_appearance_mode = load_config()
tk.set_appearance_mode(saved_appearance_mode)
tk.set_default_color_theme(saved_theme)

# Initialize the main window
root = tk.CTk()
root.geometry("500x400")
root.resizable(False, False)
root.title("Steam Manager")

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

    # Open file dialog to select the Steam folder
    file_path = filedialog.askdirectory(title="Select the folder where Steam is located")
    
    if file_path and os.path.exists(file_path):
        steam_exe = os.path.join(file_path, "steam.exe")
        if os.path.exists(steam_exe):
            save_config(path=file_path)  # Save the selected path to config
            window.destroy()  # Close the window after folder is selected
            initialize_main_window()  # Initialize the main window
        else:
            # Show error if steam.exe is not found
            error_label = tk.CTkLabel(window, text="Steam executable not found in the selected folder.", fg_color="red")
            error_label.pack(pady=5)

def config_window():
    """Open the configuration window for appearance settings and folder change."""
    # Create a new Toplevel window for the configuration
    config_window = tk.CTkToplevel(root)
    config_window.title("Configuration")
    config_window.geometry("300x250")

    # Get the current position of the root window and offset the config window
    main_x = root.winfo_x()
    main_y = root.winfo_y()
    
    # Set the config window to open offset from the main window (for example, 50 pixels to the right and down)
    offset_x = main_x + -165
    offset_y = main_y + 1
    
    config_window.geometry(f"+{offset_x}+{offset_y}")  # Set new position for the config window

    appearance_label = tk.CTkLabel(config_window, text="Appearance Mode:")
    appearance_label.pack(pady=10)

    # Dropdown menu for selecting appearance mode
    appearance_option = tk.CTkOptionMenu(
        config_window,
        values=["System", "Light", "Dark"],
        command=lambda mode: change_appearance_mode(mode)
    )
    appearance_option.set(saved_appearance_mode.capitalize())  # Set initial value from config
    appearance_option.pack(pady=5)

    # Dropdown menu for selecting theme
    theme_label = tk.CTkLabel(config_window, text="Select Theme:")
    theme_label.pack(pady=10)

    theme_option = tk.CTkOptionMenu(
        config_window,
        values=["dark-blue", "green", "blue"],
        command=lambda theme: change_theme(theme)
    )
    theme_option.set(saved_theme)  # Set initial value from config
    theme_option.pack(pady=5)

    button_change_folder = tk.CTkButton(config_window, text="Change Steam Folder", command=lambda: Openfolder(config_window))
    button_change_folder.pack(pady=10)

def change_appearance_mode(mode):
    """Change the appearance mode and save it to the config."""
    tk.set_appearance_mode(mode.lower())
    save_config(appearance_mode=mode.lower())
    reload_gui()  # Reload the GUI to apply appearance mode change

def change_theme(theme):
    """Change the theme and save it to the config."""
    tk.set_default_color_theme(theme)
    save_config(theme=theme)
    reload_gui()  # Reload the GUI to apply theme change

def reload_gui():
    """Reload the GUI to apply the new theme and appearance mode."""
    global main_frame
    
    # Save the current geometry
    current_geometry = root.geometry()
    
    for widget in root.winfo_children():
        widget.destroy()
    
    # Reapply the saved geometry
    root.geometry(current_geometry)
    
    initialize_main_window()  # Reinitialize the main window with new settings

def initialize_main_window():
    """Initialize the main window after the Steam path is set."""
    frame = tk.CTkFrame(root)
    frame.pack(pady=20, padx=60, fill="both", expand=True)

    title_label = tk.CTkLabel(frame, text="Steam Manager", font=("Helvetica", 20, "bold"))
    title_label.pack(pady=10)

    button_open_steam = tk.CTkButton(frame, text="Open Steam", command=OpenSteam)
    button_open_steam.pack(pady=(10, 5))

    button_close_steam = tk.CTkButton(frame, text="Close Steam", command=CloseSteam)
    button_close_steam.pack(pady=5)

    button_manifest = tk.CTkButton(frame, text="Manifest File Adder", command=applist)
    button_manifest.pack(pady=5)

    button_toggle_luma = tk.CTkButton(frame, text="ON/OFF", command=onLuma)
    button_toggle_luma.pack(pady=5)

    button_config = tk.CTkButton(root, text="⚙", width=30, command=config_window)
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
        os.makedirs(output_folder)  # Ensure output folder exists

    if os.path.exists(manifest1):
        items = os.listdir(manifest1)
        file_counter = 1  # Start counter from 1
        
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
                    print(f"Manifest numbers from {item} written to {output_file_path}")
                else:
                    print(f"Not a manifest file: {item}")

        # Create a file with the number 480
        preset_file_path = os.path.join(output_folder, "0.txt")
        with open(preset_file_path, "w") as preset_file:
            preset_file.write("480\n")  # Write 480 to the file
        
        print(f"Preset file created: {preset_file_path}")
    else:
        print(f"Manifest directory does not exist: {manifest1}")

# Load the configuration and decide whether to start firstboot or initialize the main window
if saved_path and os.path.exists(os.path.join(saved_path, "steam.exe")):
    file_path = saved_path
    steam_exe = os.path.join(file_path, "steam.exe")
    initialize_main_window()
else:
    firstboot()

root.mainloop()
