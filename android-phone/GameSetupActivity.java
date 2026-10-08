package com.ps2x.runner;

import android.app.Activity;
import android.app.NativeActivity;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.DocumentsContract;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;

/** Phone-only import of a user-selected disc folder; no broad storage permission. */
public final class GameSetupActivity extends Activity {
    private static final int PICK_GAME = 41;
    private static final int EXPORT_LAST_LOG = 42;
    private static final String ELF = "SLUS_204.20";
    private static final String ELF_SHA = "51c56737105d1186f0b14155e39d8af67e63b12c4ac0543e1f0e178ccd6a4304";
    private TextView status;
    private Button choose;
    private Button launch;
    private volatile boolean importing;
    private String pendingLogExport;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        File root = getExternalFilesDir(null);
        LinearLayout view = new LinearLayout(this);
        view.setOrientation(LinearLayout.VERTICAL);
        view.setGravity(Gravity.CENTER);
        view.setPadding(32, 32, 32, 32);
        view.setBackgroundColor(Color.rgb(16, 22, 32));
        TextView title = new TextView(this);
        title.setText("Bounty Hunter");
        title.setTextSize(28);
        title.setTextColor(Color.WHITE);
        title.setGravity(Gravity.CENTER);
        view.addView(title);
        status = new TextView(this);
        status.setText("Choose the game folder containing SLUS_204.20, IOPRP254.IMG, IRX and DATA.\n\nKeep the app open while the files copy.");
        status.setTextSize(17);
        status.setTextColor(Color.LTGRAY);
        status.setGravity(Gravity.CENTER);
        status.setPadding(0, 24, 0, 24);
        view.addView(status);
        choose = new Button(this);
        choose.setText("Import game folder");
        choose.setOnClickListener(v -> {
            Intent pick = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
            pick.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION
                    | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
            startActivityForResult(pick, PICK_GAME);
        });
        view.addView(choose);
        boolean installed = root != null && new File(root, ".bounty-import-complete").isFile()
                && new File(root, ELF).isFile();
        if (installed && RunLog.exists(root)) {
            status.setText("The last game run has a saved log. Export it here, or start the game again.");
            launch = new Button(this);
            launch.setText("Start game");
            launch.setOnClickListener(v -> { launch.setEnabled(false); startGame(); });
            view.addView(launch, view.getChildCount() - 1);
            Button logs = new Button(this);
            logs.setText("Export last run log");
            logs.setOnClickListener(v -> exportLastLog());
            view.addView(logs, view.getChildCount() - 1);
        }
        setContentView(view);
        if (installed && !RunLog.exists(root)) startGame();
    }

    private void exportLastLog() {
        new Thread(() -> {
            try {
                String text = new RunLog(getExternalFilesDir(null)).snapshot();
                runOnUiThread(() -> {
                    pendingLogExport = text;
                    Intent pick = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                    pick.addCategory(Intent.CATEGORY_OPENABLE);
                    pick.setType("text/plain");
                    pick.putExtra(Intent.EXTRA_TITLE, "Bounty-Hunter-last-run.txt");
                    try { startActivityForResult(pick, EXPORT_LAST_LOG); }
                    catch (RuntimeException error) {
                        pendingLogExport = null;
                        Toast.makeText(this, "Could not open the save picker: " + error.getMessage(), Toast.LENGTH_LONG).show();
                    }
                });
            } catch (Exception error) {
                runOnUiThread(() -> Toast.makeText(this, "Could not read the saved log: " + error.getMessage(), Toast.LENGTH_LONG).show());
            }
        }, "last-run-export").start();
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == EXPORT_LAST_LOG) {
            String text = pendingLogExport;
            pendingLogExport = null;
            if (result == RESULT_OK && data != null && data.getData() != null && text != null) {
                Uri destination = data.getData();
                new Thread(() -> {
                    try (java.io.OutputStream out = getContentResolver().openOutputStream(destination, "wt")) {
                        if (out == null) throw new IOException("The selected document is unavailable.");
                        out.write(text.getBytes(java.nio.charset.StandardCharsets.UTF_8));
                        runOnUiThread(() -> Toast.makeText(this, "Saved. Attach the text file in chat.", Toast.LENGTH_LONG).show());
                    } catch (Exception error) {
                        runOnUiThread(() -> Toast.makeText(this, "Could not export log: " + error.getMessage(), Toast.LENGTH_LONG).show());
                    }
                }, "last-run-save").start();
            }
            return;
        }
        if (request != PICK_GAME || result != RESULT_OK || data == null || data.getData() == null) return;
        Uri tree = data.getData();
        importing = true;
        choose.setEnabled(false);
        getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        status.setText("Checking the game folder…");
        new Thread(() -> {
            try {
                importGame(tree);
                runOnUiThread(() -> {
                    importing = false;
                    getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                    startGame();
                });
            } catch (Exception e) {
                final String message = e.getMessage() == null ? "Could not copy the selected folder." : e.getMessage();
                runOnUiThread(() -> {
                    importing = false;
                    getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                    choose.setEnabled(true);
                    if (launch != null) launch.setEnabled(true);
                    status.setText(message + "\n\nChoose the game folder to try again.");
                });
            }
        }, "game-import").start();
    }

    @Override public void onBackPressed() {
        if (importing) Toast.makeText(this, "Please wait for the game files to finish copying.", Toast.LENGTH_SHORT).show();
        else super.onBackPressed();
    }

    private void startGame() {
        importing = true;
        choose.setEnabled(false);
        status.setText("Preparing game startup files…");
        new Thread(() -> {
            try {
                File root = getExternalFilesDir(null);
                if (root == null) throw new IOException("Game storage is unavailable.");
                BootModules.prepare(root);
                runOnUiThread(() -> {
                    importing = false;
                    startActivity(new Intent(this, NativeActivity.class));
                    finish();
                });
            } catch (Exception e) {
                final String message = e.getMessage() == null ? "Could not prepare game startup files." : e.getMessage();
                runOnUiThread(() -> {
                    importing = false;
                    choose.setEnabled(true);
                    if (launch != null) launch.setEnabled(true);
                    status.setText(message + "\n\nChoose the game folder to try again.");
                });
            }
        }, "game-startup").start();
    }

    private static final class Entry {
        final String id, name;
        final boolean directory;
        Entry(String id, String name, boolean directory) {
            this.id = id; this.name = name; this.directory = directory;
        }
    }

    private List<Entry> children(Uri tree, String parent) throws IOException {
        List<Entry> entries = new ArrayList<>();
        Uri uri = DocumentsContract.buildChildDocumentsUriUsingTree(tree, parent);
        String[] columns = {DocumentsContract.Document.COLUMN_DOCUMENT_ID,
                DocumentsContract.Document.COLUMN_DISPLAY_NAME,
                DocumentsContract.Document.COLUMN_MIME_TYPE};
        try (Cursor c = getContentResolver().query(uri, columns, null, null, null)) {
            if (c == null) throw new IOException("The selected folder could not be read.");
            while (c.moveToNext()) {
                String name = c.getString(1);
                if (name == null || name.equals(".") || name.equals("..")
                        || name.contains("/") || name.contains("\\") || name.indexOf('\0') >= 0)
                    throw new IOException("The selected folder contains an invalid file name.");
                entries.add(new Entry(c.getString(0), name,
                        DocumentsContract.Document.MIME_TYPE_DIR.equals(c.getString(2))));
            }
        }
        return entries;
    }

    private void importGame(Uri tree) throws Exception {
        List<Entry> top = children(tree, DocumentsContract.getTreeDocumentId(tree));
        Entry elf = null, image = null;
        boolean data = false, irx = false;
        for (Entry e : top) {
            if (e.name.equals(ELF) && !e.directory) elf = e;
            if (e.name.equals("IOPRP254.IMG") && !e.directory) image = e;
            if (e.name.equals("DATA") && e.directory) data = true;
            if (e.name.equals("IRX") && e.directory) irx = true;
        }
        if (elf == null || image == null || !data || !irx)
            throw new IOException("Choose the parent game folder containing SLUS_204.20, IOPRP254.IMG, IRX and DATA, rather than DATA itself.");
        File root = getExternalFilesDir(null);
        if (root == null) throw new IOException("The phone's app storage is unavailable.");
        File marker = new File(root, ".bounty-import-complete");
        if (marker.exists() && !marker.delete()) throw new IOException("The previous import could not be updated.");
        copy(tree, elf, root, 0);
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream in = new java.io.FileInputStream(new File(root, ELF))) {
            byte[] bytes = new byte[65536];
            int read;
            while ((read = in.read(bytes)) != -1) digest.update(bytes, 0, read);
        }
        StringBuilder hex = new StringBuilder();
        for (byte b : digest.digest()) hex.append(String.format(java.util.Locale.ROOT, "%02x", b & 255));
        if (!ELF_SHA.equals(hex.toString()))
            throw new IOException("This build needs the original SLUS_204.20 game file used for this project. The selected file is a different version.");
        copy(tree, image, root, 0);
        BootModules.prepare(root);
        for (Entry e : top) {
            if ((e.directory && (e.name.equals("DATA") || e.name.equals("IRX")))
                    || (!e.directory && (e.name.equals("SYSTEM.CNF") || e.name.equals("CDROM.TXT"))))
                copy(tree, e, root, 0);
        }
        try (FileOutputStream out = new FileOutputStream(marker)) {
            out.write("import-complete-v1\n".getBytes(java.nio.charset.StandardCharsets.UTF_8));
        }
    }

    private void copy(Uri tree, Entry e, File parent, int depth) throws IOException {
        if (depth > 32) throw new IOException("The selected folder has too many nested folders.");
        File target = new File(parent, e.name);
        if (e.directory) {
            if (!target.isDirectory() && !target.mkdirs()) throw new IOException("Could not create a game folder. Check available storage.");
            for (Entry child : children(tree, e.id)) {
                // These are user's transfer archives, rather than disc files.
                if (!child.directory && (child.name.equals("DATA.zip") || child.name.equals("BUNDLES.zip"))) continue;
                copy(tree, child, target, depth + 1);
            }
            return;
        }
        runOnUiThread(() -> status.setText("Copying " + e.name + "…"));
        File partial = File.createTempFile("bounty-import-", ".part", parent);
        try {
            Uri document = DocumentsContract.buildDocumentUriUsingTree(tree, e.id);
            try (InputStream in = getContentResolver().openInputStream(document);
                 FileOutputStream out = new FileOutputStream(partial)) {
                if (in == null) throw new IOException("Could not read " + e.name);
                byte[] buffer = new byte[65536];
                int read;
                while ((read = in.read(buffer)) != -1) out.write(buffer, 0, read);
            }
            // POSIX rename replaces the prior file only after the copy is complete.
            try { android.system.Os.rename(partial.getAbsolutePath(), target.getAbsolutePath()); }
            catch (android.system.ErrnoException error) { throw new IOException("Could not save " + e.name + ". Check available storage.", error); }
        } finally {
            if (partial.exists()) partial.delete();
        }
    }
}
