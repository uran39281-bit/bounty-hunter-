package com.ps2x.runner;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.Arrays;

/** Extract exact startup modules from the user's original IOP image. */
final class BootModules {
    private static final String IMAGE_SHA = "bc91fc6ce5f8afc30b9431688b0c02e90249600982401a419d971ec736326b64";
    private static final String[] NAMES = {"SIFCMD", "CDVDFSV", "LOADFILE"};
    private static final String[] HASHES = {
        "c40e0ac2d27bb5bb4d052a3ee85710f1ceb2c82aa5216915b17abc1c37c068e3",
        "bba46bc27c14472e8e0b06397f5b909c6e32c92d17022dfc4ff0a767b5e272d4",
        "67ee7d0f91c312fedb7ccceb8826d7dba421dac879cb5e9714c3362499f58232"
    };

    private static String sha(byte[] bytes) throws IOException {
        try {
            StringBuilder hex = new StringBuilder();
            for (byte b : MessageDigest.getInstance("SHA-256").digest(bytes))
                hex.append(String.format(java.util.Locale.ROOT, "%02x", b & 255));
            return hex.toString();
        } catch (java.security.NoSuchAlgorithmException e) { throw new IOException(e); }
    }

    static void prepare(File root) throws IOException {
        File boot = new File(root, "BOOT");
        boolean ready = true;
        for (int i = 0; i < NAMES.length; ++i) {
            File module = new File(boot, NAMES[i] + ".IRX");
            ready &= module.isFile() && module.length() < 1000000
                    && HASHES[i].equals(sha(Files.readAllBytes(module.toPath())));
        }
        File file = new File(root, "IOPRP254.IMG");
        if (ready && !file.exists()) return;
        if (!file.isFile() || file.length() > 1000000)
            throw new IOException("The game folder needs the original IOPRP254.IMG startup file.");
        byte[] image = Files.readAllBytes(file.toPath());
        if (!IMAGE_SHA.equals(sha(image)))
            throw new IOException("The selected IOPRP254.IMG startup file is a different version.");
        if (ready) return;
        ByteBuffer bytes = ByteBuffer.wrap(image).order(ByteOrder.LITTLE_ENDIAN);
        byte[][] modules = new byte[NAMES.length][];
        int position = 0, offset = 0, entries = 0, romdirSize = -1;
        boolean terminated = false;
        String[] prefix = {"RESET", "ROMDIR", "EXTINFO"};
        while (position + 16 <= image.length) {
            int end = position;
            while (end < position + 10 && image[end] != 0) ++end;
            String name = new String(image, position, end - position, StandardCharsets.US_ASCII);
            if (name.isEmpty()) { terminated = true; break; }
            if (!name.matches("[A-Z0-9_]+") || (entries < 3 && !prefix[entries].equals(name)))
                throw new IOException("The startup image has an invalid module table.");
            long size = bytes.getInt(position + 12) & 0xffffffffL;
            if (offset + size > image.length) throw new IOException("The startup image is incomplete.");
            if (name.equals("ROMDIR")) romdirSize = (int)size;
            for (int i = 0; i < NAMES.length; ++i) {
                if (name.equals(NAMES[i])) {
                    modules[i] = Arrays.copyOfRange(image, offset, offset + (int)size);
                    if (!HASHES[i].equals(sha(modules[i])))
                        throw new IOException("A startup module does not match the original game.");
                }
            }
            offset = (offset + (int)size + 15) & ~15;
            position += 16;
            ++entries;
        }
        if (!terminated || entries < 3 || romdirSize != position + 16)
            throw new IOException("The startup image has an invalid module table.");
        if (!boot.isDirectory() && !boot.mkdirs()) throw new IOException("Could not prepare game startup files.");
        for (int i = 0; i < NAMES.length; ++i) {
            if (modules[i] == null) throw new IOException("The startup image is missing a required module.");
            File partial = File.createTempFile("bounty-boot-", ".part", boot);
            try {
                try (FileOutputStream out = new FileOutputStream(partial)) { out.write(modules[i]); }
                if (!partial.renameTo(new File(boot, NAMES[i] + ".IRX")))
                    throw new IOException("Could not save a game startup file.");
            } finally { if (partial.exists()) partial.delete(); }
        }
    }
}
