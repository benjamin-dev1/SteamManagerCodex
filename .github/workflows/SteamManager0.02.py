import customtkinter as tk
import os
from tkinter import filedialog
import re

tk.set_appearance_mode("system")
tk.set_default_color_theme("dark-blue")

# Window Size, Intalizes the Size
root = tk.CTk()
root.geometry("500x350")

# Function to change Path of steam folder
def Openfolder():
    global steam_exe, file_path
    # file path is the directory of where the users steam folder is
    file_path = filedialog.askdirectory(title="Select the folder that stream is located")
    
    if file_path and os.path.exists(file_path):
        steam_exe = os.path.join(file_path, "steam.exe")
        if os.path.exists(steam_exe):
           return steam_exe
    return file_path
        

def OpenSteam():
    global appcache
    os.startfile(steam_exe)
    appcache = os.path.join(file_path, "DeleteSteamAppCache.exe")
    os.startfile(appcache)
   

# Function to close Steam
def CloseSteam():
    os.system("taskkill /f /im steam.exe")


def onLuma():
    luma = os.path.join(file_path, "user32.dll")
    if os.path.exists(luma):
        os.rename(luma, os.path.join(file_path,"User321.dll"))
    else:
        os.rename(os.path.join(file_path,"User321.dll"), luma)
        

def applist():
    global manifest1
    manifest1 = os.path.join(file_path, "steamapps")
    output_folder = os.path.join(file_path,"applist")
    if os.path.exists(manifest1):
        items = os.listdir(manifest1)
        file_counter = 0
        
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

        
Openfolder()
# Create and place the "Open Steam" button
button_open = tk.CTkButton(root, text="Open Steam", command=OpenSteam)
button_open.grid(row=0, column=0, padx=340, pady=15)


# Create and place the "Close Steam" button
button_close = tk.CTkButton(root, text="Close Steam", command=CloseSteam)
button_close.grid(row=1, column=0, padx=340, pady=5)

button_open = tk.CTkButton(root, text="Change Folder", command=Openfolder)
button_open.grid(row=2, column=0, padx=340, pady=15)

button_open = tk.CTkButton(root, text="Manifest File Adder", command=applist)
button_open.grid(row=3, column=0, padx=340, pady=15)

buttonOff = tk.CTkButton(root, text="ON/OFF", command=onLuma)
buttonOff.grid(row=4, column=0, padx=340, pady=15)

root.mainloop()


# if file_path and os.path.exists(file_path):
        # try:
           #  with open (file_path, "r") as file:
                # content = file.read()
                # print("File Content:", content)
        # except Exception as e:
            #print(f"Error opening file: {e}")
   # else:
       # print("file doesn't exist buddy")
