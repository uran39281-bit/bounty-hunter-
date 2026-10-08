package com.ps2x.runner;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/** Host check against privately supplied original files; does not execute game code. */
public final class AndroidBootModulesTest {
    private static void compare(Path root, Path original) throws IOException {
        for (String name : new String[]{"SIFCMD.IRX", "CDVDFSV.IRX", "LOADFILE.IRX"}) {
            if (!Arrays.equals(Files.readAllBytes(root.resolve("BOOT").resolve(name)),
                    Files.readAllBytes(original.resolve("BOOT").resolve(name))))
                throw new AssertionError("Extracted startup module differs: " + name);
        }
    }

    private static void expectRejected(Path root) throws IOException {
        try { BootModules.prepare(root.toFile()); }
        catch (IOException expected) { return; }
        throw new AssertionError("Invalid startup image was accepted");
    }

    public static void main(String[] args) throws Exception {
        Path original = new File(args[0]).toPath();
        Path work = Files.createTempDirectory("bounty-boot-test-");
        try {
            Path good = Files.createDirectory(work.resolve("good"));
            Files.copy(original.resolve("IOPRP254.IMG"), good.resolve("IOPRP254.IMG"));
            BootModules.prepare(good.toFile());
            compare(good, original);
            Files.delete(good.resolve("BOOT/LOADFILE.IRX"));
            BootModules.prepare(good.toFile());
            compare(good, original);
            BootModules.prepare(good.toFile());
            compare(good, original);
            byte[] damaged = Files.readAllBytes(good.resolve("BOOT/SIFCMD.IRX"));
            damaged[0] ^= 1;
            Files.write(good.resolve("BOOT/SIFCMD.IRX"), damaged);
            BootModules.prepare(good.toFile());
            compare(good, original);
            byte[] changed = Files.readAllBytes(good.resolve("IOPRP254.IMG"));
            changed[changed.length-1] ^= 1;
            Files.write(good.resolve("IOPRP254.IMG"), changed);
            expectRejected(good);
            Files.copy(original.resolve("IOPRP254.IMG"), good.resolve("IOPRP254.IMG"),
                    java.nio.file.StandardCopyOption.REPLACE_EXISTING);
            Path missing = Files.createDirectory(work.resolve("missing"));
            expectRejected(missing);
            Path wrong = Files.createDirectory(work.resolve("wrong"));
            byte[] image = Files.readAllBytes(original.resolve("IOPRP254.IMG"));
            image[image.length-1] ^= 1;
            Files.write(wrong.resolve("IOPRP254.IMG"), image);
            expectRejected(wrong);
            System.out.println("{\"original_module_bytes_match\":true,\"existing_import_migrated\":true,\"repeat_import_passed\":true,\"damaged_module_repaired\":true,\"missing_image_rejected\":true,\"wrong_image_rejected\":true,\"android_execution_tested\":false}");
        } finally {
            try (java.util.stream.Stream<Path> paths = Files.walk(work)) {
                paths.sorted(java.util.Comparator.reverseOrder()).forEach(path -> {
                    try { Files.delete(path); } catch (IOException ignored) { }
                });
            }
        }
    }
}
