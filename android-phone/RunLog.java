package com.ps2x.runner;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;

/** Two bounded UTF-8 log segments survive process exit in the app's own folder. */
final class RunLog {
    static final int LIMIT = 2 * 1024 * 1024;
    private final File root, current, previous;

    RunLog(File root) throws IOException {
        if (root == null || !root.isDirectory()) throw new IOException("Game storage is unavailable.");
        this.root = root;
        current = new File(root, ".bounty-current.log");
        previous = new File(root, ".bounty-previous.log");
    }

    synchronized void append(String text) throws IOException {
        byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
        if (bytes.length > LIMIT) {
            text = text.substring(Math.max(0, text.length() - LIMIT / 4));
            bytes = text.getBytes(StandardCharsets.UTF_8);
        }
        if (current.length() + bytes.length > LIMIT)
            Files.move(current.toPath(), previous.toPath(), StandardCopyOption.REPLACE_EXISTING);
        try (FileOutputStream out = new FileOutputStream(current, true)) { out.write(bytes); }
    }

    static boolean exists(File root) {
        return root != null && (new File(root, ".bounty-current.log").length() > 0
                || new File(root, ".bounty-native-stop.txt").length() > 0);
    }

    private static String read(File file, int limit) throws IOException {
        if (!file.isFile()) return "";
        if (file.length() > limit) return "[Saved log exceeds the size limit.]\n";
        return new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
    }

    synchronized String snapshot() throws IOException {
        return "Bounty Hunter saved run logs\n\nNATIVE RUNNER STATUS\n"
                + read(new File(root, ".bounty-native-stop.txt"), 65536)
                + "\nSAVED APP LOG\n" + read(previous, LIMIT) + read(current, LIMIT);
    }
}
