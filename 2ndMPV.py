import mpv
import keyboard
import threading
import time
import tkinter as tk
from tkinter import filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD

# Global variables for user input
video1_path = ""
video2_path = ""
seek_forward_time = 5  # Default value
seek_backward_time = -5  # Default value

short_seek_forward_time = 1  # Default value
short_seek_backward_time = -1  # Default value

def open_file_dialog(entry):
    file_path = filedialog.askopenfilename()
    entry.delete(0, tk.END)
    entry.insert(0, file_path)


def submit_and_close(root, video1_entry, video2_entry, seek_forward_entry, seek_backward_entry):
    global video1_path, video2_path, seek_forward_time, seek_backward_time, short_seek_forward_time, short_seek_backward_time
    video1_path = video1_entry.get()
    video2_path = video2_entry.get()
    seek_forward_time = int(seek_forward_entry.get())
    seek_backward_time = int(seek_backward_entry.get())
    root.destroy()

# Create the tkinter window
root = TkinterDnD.Tk()
root.title("Video Player Setup")

tk.Label(root, text="Video 1:").grid(row=0, column=0)
video1_entry = tk.Entry(root, width=50)
video1_entry.grid(row=0, column=1)
tk.Button(root, text="Browse", command=lambda: open_file_dialog(video1_entry)).grid(row=0, column=2)

tk.Label(root, text="Video 2:").grid(row=1, column=0)
video2_entry = tk.Entry(root, width=50)
video2_entry.grid(row=1, column=1)
tk.Button(root, text="Browse", command=lambda: open_file_dialog(video2_entry)).grid(row=1, column=2)

tk.Label(root, text="Seek Forward Time (s):").grid(row=2, column=0)
seek_forward_entry = tk.Entry(root, width=10)
seek_forward_entry.insert(0, "5")
seek_forward_entry.grid(row=2, column=1)

tk.Label(root, text="Seek Backward Time (s):").grid(row=3, column=0)
seek_backward_entry = tk.Entry(root, width=10)
seek_backward_entry.insert(0, "-5")
seek_backward_entry.grid(row=3, column=1)

tk.Button(root, text="Submit", command=lambda: submit_and_close(root, video1_entry, video2_entry, seek_forward_entry, seek_backward_entry)).grid(row=4, column=1)

def drop_video1(event):
    file_path = event.data.strip('{}')
    video1_entry.delete(0, tk.END)
    video1_entry.insert(0, file_path)

def drop_video2(event):
    file_path = event.data.strip('{}')
    video2_entry.delete(0, tk.END)
    video2_entry.insert(0, file_path)


video1_entry.drop_target_register(DND_FILES)
video1_entry.dnd_bind('<<Drop>>', drop_video1)

video2_entry.drop_target_register(DND_FILES)
video2_entry.dnd_bind('<<Drop>>', drop_video2)


root.mainloop()

# Create multiple MPV instances
players = [mpv.MPV(input_default_bindings=True, osc=True), mpv.MPV(input_default_bindings=True, osc=True)]

# Load different videos for each player instance
players[0].play(video1_path)
players[1].play(video2_path)

# Function to toggle play/pause on all players
def toggle_play_pause():
    for player in players:
        player.pause = not player.pause

# Function to seek forward on all players
def seek_forward():
    for player in players:
        player.command('seek', str(seek_forward_time), 'relative')

def short_seek_forward():
    for player in players:
        player.command('seek', str(short_seek_forward_time), 'relative')

# Function to seek backward on all players
def seek_backward():
    for player in players:
        player.command('seek', str(seek_backward_time), 'relative')

def short_seek_backward():
    for player in players:
        player.command('seek', str(short_seek_backward_time), 'relative')

def toggle_subtitles():
    for player in players:
        # Toggle subtitle visibility
        # This assumes 'sub-visibility' is a valid property in mpv for toggling subtitles
        player.command('cycle', 'sub-visibility')

# Function to show OSD progress bar for each player
def show_osd(player, stop_event):
    try:
        timer_run = True
        while timer_run:
            if not player.core_idle:
                continue
            time_pos = player.time_pos or 0
            duration = player.duration or 1
            time_pos_minutes = int(time_pos // 60)
            time_pos_seconds = int(time_pos % 60)
            duration_minutes = int(duration // 60)
            duration_seconds = int(duration % 60)
            osd_message = f'{time_pos_minutes:02d}:{time_pos_seconds:02d}/{duration_minutes:02d}:{duration_seconds:02d} ({(time_pos / duration) * 100:.2f}%)'
            player.command('show-text', osd_message)
            time.sleep(1)
    except mpv.ShutdownError:
        print(f"Player {player} has been closed.")

# Event to stop the OSD thread
stop_events = [threading.Event(), threading.Event()]

# Bind the hotkeys
keyboard.add_hotkey('ctrl+space', toggle_play_pause)
keyboard.add_hotkey('ctrl+1', seek_backward)
keyboard.add_hotkey('ctrl+2', seek_forward)

keyboard.add_hotkey('-', short_seek_backward)
keyboard.add_hotkey('=', short_seek_forward)

keyboard.add_hotkey('\\', toggle_subtitles)

# Start OSD threads for each player
threads = []
for player, stop_event in zip(players, stop_events):
    thread = threading.Thread(target=show_osd, args=(player, stop_event), daemon=True)
    threads.append(thread)
    thread.start()

# Function to stop all players and their OSD threads
def stop_all_players():
    for player, stop_event in zip(players, stop_events):
        stop_event.set()  # Signal the thread to stop
        player.terminate()  # Terminate the MPV player instance

# Listen for shutdown events to gracefully handle window close
def listen_for_shutdown(player, stop_event):
    def on_shutdown(name, value):
        print(f"Shutdown event received for player {player}")
        stop_event.set()
    player.observe_property('shutdown', on_shutdown)

for player, stop_event in zip(players, stop_events):
    listen_for_shutdown(player, stop_event)

# Keep the script running to listen for hotkeys
try:
    print("Press Ctrl+Space to toggle play/pause, Ctrl+Right to seek forward, and Ctrl+Left to seek backward for all MPV players")
    keyboard.wait('esc')  # Script will keep running until 'esc' is pressed
finally:
    stop_all_players()
    for thread in threads:
        thread.join()
