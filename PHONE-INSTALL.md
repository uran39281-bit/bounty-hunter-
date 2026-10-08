# Phone installation and diagnostics

## Saved logs after exit, APK version 6

Install `Bounty-Hunter-Saved-Logs.apk` as an **Update** over the current app.
Keep the app installed so its imported game files remain available.

1. Open Bounty Hunter; tap **Start game** if the setup screen appears.
2. Select **PLAY GAME** and press **X** to reproduce the exit.
3. Reopen Bounty Hunter and tap **Export last run log** before starting again.
4. Save `Bounty-Hunter-last-run.txt` in Downloads and attach it in chat.

The user confirms APK 5 restores Up/Down navigation. PLAY GAME now exits.
APK 6 saves logs across process exit and adds native stop status; it does not
claim to fix the gameplay exit. The cause remains unknown. A hard native crash
may leave progress entries without a precise stop reason.


## Original LOADFILE startup service, APK version 5

Install `Bounty-Hunter-Startup-Fix.apk` as an **Update** over the existing app.
It extracts the original LOADFILE service from the already imported IOP image
before launch. You do not need to uninstall or reimport your game folder.

1. Reach the original main menu.
2. Tap **DOWN** once and check whether the selected option changes.
3. Return to **PLAY GAME** with **UP**, then tap **X**.
4. If it still stops, wait ten seconds, tap **EXPORT LOGS**, and attach the new text file.

The APK 4 phone log locates a LOADFILE initialization retry at guest PC
`0x196bd8` with no new pad reads for at least 110.986 seconds. The prior boot
did not load that original module. The local regression reproduces the missing
service, then executes the original IRX and verifies its version RPC and reset/reload.
Extraction checks confirm exact bytes, repair and migration of an older import.
The user confirms menu navigation works after this change; PLAY GAME exits. Full gameplay is not established.
The imported SOUND and VIDEO folders are also absent in the APK 4 log.

## Native stall trace, APK version 4

Install `Bounty-Hunter-Menu-Candidate.apk` as an **Update** over the existing app
so the imported game files stay available.

1. Open Bounty Hunter and reach the screen where it stops.
2. Tap **X** once and wait ten seconds.
3. Tap **EXPORT LOGS** at the top right.
4. Save `Bounty-Hunter-logs.txt` in Downloads and attach it in the chat.

The APK 3 log confirms the game consumed Start and two X presses, then stopped
reading its pad at count 318 for at least 50 seconds. Later Down/Circle events
remained queued. There is no missing-function or fatal guest-exception message
in that capture. These facts establish the input delivery path works initially;
they do not establish the underlying cause of the stall.

APK 4 adds an independent native progress watcher so its log includes the last
game branch, render progress, published EE thread/wait state and asset-open
failures even if the render or game thread stops. It also counts the imported
SOUND, VIDEO and other DATA files. This candidate also corrects a verified VCALLMSR translation defect: it reads
CMSAR0 instead of the out-of-bounds vi[27] element. The baseline wrapper fails
under the bounds sanitizer; the corrected actual wrapper passes 1,536 address
and return cases. The effect on the phone stall remains unverified. Original
ELF instructions remain unchanged; exactly one generated C++ operand is corrected.

## First installation

1. Download `Bounty-Hunter-Saved-Logs.apk` to the phone and tap it to install.
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
gigabytes of free space for a complete disc copy. The importer prepares the three
startup modules automatically from your original `IOPRP254.IMG` file.

After a successful import, launches show the log export screen when a saved run exists.
Menu touch buttons are Start, Cross, Circle and the four directions. The
first build was tested by the user on an S24 and reaches the save warning,
and APK 2 now reaches the original main menu. APK 5 restores Up/Down navigation; selecting PLAY GAME exits the app.
Full gameplay, sound,
videos, background/resume and later screens remain unverified.
