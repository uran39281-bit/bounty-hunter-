# Phone installation and diagnostics

## Main-menu diagnostics, APK version 3

Install `Bounty-Hunter-Diagnostics.apk` over the current app. Choose **Update**
and keep the existing app installed so its imported files remain available.

1. Open Bounty Hunter and reach the main menu.
2. Tap **X**, wait about five seconds, then tap **Down** and **X** again.
3. Tap **EXPORT LOGS** at the top right.
4. Save `Bounty-Hunter-logs.txt` in **Downloads** using the phone file picker.
5. Attach that text file in the chat.

The latest APK 2 screenshot shows PLAY GAME selected with `Touch: X | Game: waiting`.
That confirms the overlay saw the press but the primary guest pad read has not
consumed it. APK 3 records its own runtime log plus touch serials and pad-read
counts to identify the cause. It reuses the exact APK 2 native library and does
not yet fix the blocked main menu. Device export still needs this phone test.

## First installation

1. Download `Bounty-Hunter-Diagnostics.apk` to the phone and tap it to install.
2. Open **Bounty Hunter**, then tap **Import game folder**.
3. Choose `Download/Star Wars file`, or whichever folder contains the original
   `SLUS_204.20` and `IOPRP254.IMG` files and both `IRX` and `DATA` folders. Select the parent game
   folder, rather than `DATA` itself. If the files are zipped, extract them first.
4. Wait for the import to finish. The app then launches the native runner.
5. Send a screenshot or short screen recording of the first screen, including
   what happens when you tap Cross and the directional buttons.

The importer reads only the selected folder, checks the original executable's
SHA-256, and copies game files into app storage. Your source files stay in
their original folder. Transfer archives named `DATA.zip` and `BUNDLES.zip`
are skipped; their extracted contents are needed. The phone may need several
gigabytes of free space for a complete disc copy. The importer prepares the two
startup modules automatically from your original `IOPRP254.IMG` file.

After a successful import, subsequent launches open the native runner directly.
Menu touch buttons are Start, Cross, Circle and the four directions. The
first build was tested by the user on an S24 and reaches the save warning,
and APK 2 now reaches the original main menu. Input at PLAY GAME is still blocked.
Full gameplay, sound,
videos, background/resume and later screens remain unverified.
