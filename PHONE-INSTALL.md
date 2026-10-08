# Phone installation and first test

## Controls update, APK version 2

Install `Bounty-Hunter-Controls-Fix.apk` as an update to preserve the imported
game files. Open Bounty Hunter and tap Down, Up, then Cross on the warning.
Buttons should light up while held. The caption identifies the last touch and
whether the game received it. If it stays at `Game: waiting`, send a screenshot;
the guest has not consumed that input. If it says `Game: received` but the
warning stays, report that too: the next investigation is the game/menu path.
This is a candidate fix; it has not yet been tested on the user's phone.

## First installation

1. Download `Bounty-Hunter-ARM64.apk` to the phone and tap it to install.
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
but the buttons do not respond. The queued-input update awaits phone validation.
Full gameplay, sound,
videos, background/resume and later screens remain unverified.
