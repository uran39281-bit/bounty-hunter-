package com.ps2x.runner;

import android.os.Build;
import android.os.SystemClock;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.ArrayDeque;
import java.io.File;

/** Bounded, process-only log capture; no broad log/storage permissions. */
final class PhoneDiagnostics {
    private static final int LIMIT = 2 * 1024 * 1024;
    private final ArrayDeque<String> lines = new ArrayDeque<>();
    private int characters;
    private volatile boolean closed;
    private volatile java.lang.Process logger;

    PhoneDiagnostics(File gameRoot) {
        add("Bounty Hunter native trace APK 5 / 0.1.4");
        add("Device=" + Build.MANUFACTURER + " " + Build.MODEL + " SDK=" + Build.VERSION.SDK_INT);
        Thread reader = new Thread(() -> {
            try {
                logger = new ProcessBuilder("logcat", "-v", "threadtime",
                        "--pid=" + android.os.Process.myPid(), "-T", "2000", "*:V")
                        .redirectErrorStream(true).start();
                if (closed) { logger.destroy(); return; }
                add("Own-process logcat capture started");
                inventory(gameRoot);
                try (BufferedReader stream = new BufferedReader(new InputStreamReader(logger.getInputStream()))) {
                    String line;
                    while (!closed && (line = stream.readLine()) != null) add(line);
                }
                if (!closed) add("Logcat stream ended; exit=" + logger.waitFor());
            } catch (Exception error) { add("Logcat unavailable: " + error); }
        }, "bounty-log-reader");
        reader.setDaemon(true);
        reader.start();
    }

    private void inventory(File root) {
        if (root == null) { add("GAME_FILES app directory unavailable"); return; }
        for (String folder : new String[]{"DATA/SOUND", "DATA/VIDEO", "DATA/BUNDLES", "DATA/ALLOCS", "DATA/CHEWIE"}) {
            File path = new File(root, folder);
            long[] totals = new long[2];
            countFiles(path, totals, 0);
            add("GAME_FILES folder="+folder+" present="+path.isDirectory()+
                    " files="+totals[0]+" bytes="+totals[1]);
        }
    }

    private void countFiles(File path, long[] totals, int depth) {
        if (depth > 12 || totals[0] >= 10000) return;
        if (path.isFile()) { totals[0]++; totals[1] += path.length(); return; }
        File[] children = path.listFiles();
        if (children != null) for (File child : children) countFiles(child, totals, depth+1);
    }

    synchronized void add(String text) {
        String line = "[uptime " + SystemClock.elapsedRealtime() + "] " + text + "\n";
        if (line.length() > LIMIT) line = line.substring(line.length()-LIMIT);
        lines.addLast(line); characters += line.length();
        while (characters > LIMIT && lines.size() > 1) characters -= lines.removeFirst().length();
    }

    synchronized String snapshot() {
        StringBuilder result = new StringBuilder(characters+200);
        result.append("Bounty Hunter APK 5 native progress diagnostics\n")
              .append("This is the app's own process log plus input counters.\n")
              .append("Includes native progress, published EE thread state and file-open traces.\n\n");
        for (String line : lines) result.append(line);
        return result.toString();
    }

    void close() {
        closed = true;
        java.lang.Process running = logger;
        if (running != null) running.destroy();
    }
}
