package com.ps2x.runner;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

/** Host regression: reopen after process loss, bounded rotation and native status. */
public final class RunLogTest {
    private static void check(boolean value) { if (!value) throw new AssertionError(); }
    public static void main(String[] args) throws Exception {
        File root = new File(args[0]);
        RunLog first = new RunLog(root);
        check(!RunLog.exists(root));
        first.append("SESSION1: Play Game pressed\n");
        check(RunLog.exists(root));
        check(new RunLog(root).snapshot().contains("SESSION1: Play Game pressed"));
        String chunk = new String(new char[600000]).replace('\0', 'x');
        for (int i = 0; i < 8; i++) first.append(chunk + "\nchunk=" + i + "\n");
        first.append("LAST LINE BEFORE EXIT\n");
        check(new File(root, ".bounty-current.log").length() <= RunLog.LIMIT);
        check(new File(root, ".bounty-previous.log").length() <= RunLog.LIMIT);
        check(new RunLog(root).snapshot().contains("LAST LINE BEFORE EXIT"));
        Files.write(new File(root, ".bounty-native-stop.txt").toPath(),
            "MISSING_TRANSLATED_TARGET pc=0x1234\n".getBytes(StandardCharsets.UTF_8));
        check(new RunLog(root).snapshot().contains("MISSING_TRANSLATED_TARGET pc=0x1234"));
        first.append(new String(new char[RunLog.LIMIT]).replace('\0', '\u20ac'));
        check(new File(root, ".bounty-current.log").length() <= RunLog.LIMIT);
        System.out.println("PASS saved log survives reopen, rotation, Unicode oversize and native status");
    }
}
