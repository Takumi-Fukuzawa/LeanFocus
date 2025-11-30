# LeanFocus
LeanFocus は、Windows専用のタスクトレイ常駐型ポモドーロタイマーです。
メインウィンドウを排除し、タスクトレイとフローティングオーバーレイのみで構成されるUIにより、作業画面の占有領域とシステム負荷を最小化しています。  
   > [English version is available below](#leanfocusenglish)  

# 特徴
- **タスクトレイ常駐型設計**: メインウィンドウを持たず、すべての操作をタスクトレイアイコンのコンテキストメニューから実行します。  
- **フローティングオーバーレイ**: タイマーの残り時間を最前面に表示します。透過表示や非表示設定に対応しています。  
- **自動オーディオ切り替え**: 作業時間と休憩時間のステータス変更に合わせて、設定された音源を自動的に再生・切り替えます。  
- **カスタマイズ機能**:
   - オーバーレイの透明度およびサイズの変更  
   - システム設定とは独立したアプリケーション音量調整  
   - ユーザー独自の音声ファイル（MP3/WAV/OGG）の追加
- **軽量設計**: Python (tkinter + pygame + pystray) で実装されており、低リソース環境でも動作します。

# ダウンロード
最新バージョンは [Releasesページ](https://github.com/Takumi-Fukuzawa/LeanFocus/releases)からダウンロードできます。  
1. `LeanFocus_vX.X.X.zip` をダウンロードします。
2. ファイルを解凍（展開）します。
3. `LeanFocus.exe` を実行してください。

# 使い方
1. **開始/一時停止**: トレイアイコンを 左クリック すると、タイマーの開始・一時停止・再開ができます。
2. **メニュー**: トレイアイコンを 右クリック すると、設定、リセット、終了などのメニューが開きます。
3. **オーバーレイ**: タイマーの文字部分をドラッグすると、画面上の好きな位置に移動できます。位置は記憶されます。
4. **設定**: メニューの「設定...」から、音源の選択、音量、見た目の調整ができます。

# 好きな音源を追加する方法
お気に入りのホワイトノイズや音楽を追加できます！  
1. アプリフォルダ内の assets/sounds フォルダを開きます。  
2. その中に `.mp3`, `.wav`, `.ogg` ファイルを入れます。
3. （任意） `assets/sounds/sound_names.json` を編集すると、メニューに表示される名前を変更できます。
4. アプリを再起動すると、メニューに自動的に追加されます。

# 開発者向け (ソースコードからの実行)
ソースコードを実行・改変したい場合の手順です：  
1. このリポジトリをクローンします。
2. 依存ライブラリをインストールします:
   ```
   pip install pygame pystray pillow
   ```
3. 注意: このリポジトリには、著作権および容量の理由から**音源ファイルは含まれていません**。 
   - 音声機能をテストするには、独自のダミー音源ファイルを `assets/sounds/` に配置してください。
4. スクリプトを実行します:
   ```
   python LeanFocus.py
   ```

# ライセンス & クレジット
配布用バイナリ（Releases）に含まれる音声素材の詳細については、同梱の `assets/CREDITS.txt` をご覧ください。
ソースコードは MIT License の下でライセンスされています。

&nbsp;  

# LeanFocus(English)
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
Download the latest version from the [Releases Page](https://github.com/Takumi-Fukuzawa/LeanFocus/releases).  
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