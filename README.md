# LeanFocus
LeanFocus is a lightweight, distraction-free Pomodoro timer designed for Windows.
Instead of a bulky window, it resides quietly in your system tray and provides a minimal floating overlay to keep you focused.  

# Features
- Unobtrusive Design: No main window. Controls are accessible via the system tray (right-click menu).  
- Floating Overlay: A minimal, semi-transparent timer overlay that stays on top (can be toggled ON/OFF).  
- White Noise Player: Automatically plays focus sounds during work sessions and relaxing sounds during breaks.  
- Customizable:  
  - Adjust overlay transparency and size.
  - Change volume independent of system volume.
  - Add your own MP3/WAV files easily.
- Low Resource Usage: Built with Python (tkinter + pygame + pystray), designed to be lightweight.  

# Download
Download the latest version from the Releases Page[].  
1. Download `LeanFocus_vX.X.X.zip`.
2. Unzip the file.
3. Run `LeanFocus.exe`.  

# How to Use
1. **Start/Stop**: Left-click the tray icon to Start/Pause/Resume.  
2. **Menu**: Right-click the tray icon to access settings, reset timer, or quit.  
3. **Overlay**: Drag the timer text to move it anywhere on your screen. It remembers the position.  
4. **Settings**: Use the "Settings..." menu to change sounds, volume, and appearance.  

# How to Add Custom Sounds
You can add your own favorite white noise or music!  
1. Open the `assets/sounds` folder inside the app directory.  
2. Put your `.mp3`, `.wav`, or `.ogg` files there.  
3. (Optional) Edit `assets/sounds/sound_names.json` to give them a friendly display name in the menu.  
4. Restart the app. Your sounds will appear in the menu automatically.  

# For Developers (Running from Source)
If you want to run or modify the source code:  
1. Clone this repository.  
2. Install dependencies:  
    ```
    pip install pygame pystray pillow
    ```
3. **Note**: This repository does NOT include audio files due to copyright/size reasons.  
   - Please place your own dummy audio files in assets/sounds/ to test the audio features.  
4. Run the script:  
   ```
   python LeanFocus.py
   ```

# License & Credits
See `assets/CREDITS.txt` for details regarding the audio assets used in the binary release.
The source code is licensed under the MIT License.