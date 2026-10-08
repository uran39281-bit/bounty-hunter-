package com.ps2x.runner;

import android.app.NativeActivity;
import android.os.Bundle;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.PopupWindow;
import android.content.Intent;
import android.graphics.RectF;
import android.widget.Toast;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

public final class BountyNativeActivity extends NativeActivity {
    static { System.loadLibrary("ps2EntryRunner"); }
    private static native long nativeTouch(int buttons);
    private static native long nativeInputStatus();
    private static native void nativeCancelTouch();
    private Controls controls;
    private PopupWindow overlay;
    private PhoneDiagnostics diagnostics;
    private String pendingExport;
    private static final int SAVE_LOGS = 63;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        diagnostics = new PhoneDiagnostics();
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN |
                            WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        controls = new Controls();
        // NativeActivity owns the main window surface and its native input queue.
        // A separate, non-focusable popup surface lets Android draw and receive
        // these controls independently of the game's render/input-poll loop.
        overlay = new PopupWindow(controls,
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.MATCH_PARENT, false);
        overlay.setBackgroundDrawable(new ColorDrawable(Color.TRANSPARENT));
        overlay.setInputMethodMode(PopupWindow.INPUT_METHOD_NOT_NEEDED);
        overlay.setAnimationStyle(0);
        overlay.setTouchable(true);
        overlay.setClippingEnabled(true);
        getWindow().getDecorView().addOnLayoutChangeListener(
            (view,left,top,right,bottom,oldLeft,oldTop,oldRight,oldBottom) -> {
                if(overlay.isShowing()) overlay.update(right-left,bottom-top);
            });
    }
    @Override public void onResume() {
        super.onResume();
        getWindow().getDecorView().post(() -> {
            if(!isFinishing() && !isDestroyed() && !overlay.isShowing()) {
                View decor=getWindow().getDecorView();
                if(decor.getWidth()>0 && decor.getHeight()>0) {
                    overlay.setWidth(decor.getWidth());
                    overlay.setHeight(decor.getHeight());
                }
                overlay.showAtLocation(decor,Gravity.TOP|Gravity.LEFT,0,0);
            }
        });
    }
    @Override public void onPause() {
        nativeCancelTouch();
        if (controls != null) controls.clearTouch();
        if (overlay != null) overlay.dismiss();
        super.onPause();
    }
    @Override public void onWindowFocusChanged(boolean focused) {
        super.onWindowFocusChanged(focused);
        if (!focused) {
            nativeCancelTouch();
            if (controls != null) controls.clearTouch();
        }
    }

    private void exportLogs() {
        if (pendingExport != null) return;
        long status = nativeInputStatus();
        diagnostics.add("EXPORT padReads=" + (status >>> 32) +
                " consumedSerial=" + (status & 0xffffffffL) +
                " lastPress=" + controls.lastPressSerial + " touch=" + controls.lastTouch);
        pendingExport = diagnostics.snapshot();
        Intent save = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        save.addCategory(Intent.CATEGORY_OPENABLE);
        save.setType("text/plain");
        save.putExtra(Intent.EXTRA_TITLE, "Bounty-Hunter-logs.txt");
        try { startActivityForResult(save, SAVE_LOGS); }
        catch (RuntimeException error) {
            pendingExport = null;
            Toast.makeText(this, "Could not open file picker: " + error.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request != SAVE_LOGS) return;
        final String report = pendingExport;
        pendingExport = null;
        if (result != RESULT_OK || data == null || data.getData() == null || report == null) return;
        final android.net.Uri destination = data.getData();
        new Thread(() -> {
            String message;
            try (OutputStream output = getContentResolver().openOutputStream(destination, "wt")) {
                if (output == null) throw new java.io.IOException("No output stream");
                output.write(report.getBytes(StandardCharsets.UTF_8));
                message = "Logs saved. Attach Bounty-Hunter-logs.txt in the chat.";
            } catch (Exception error) { message = "Could not save logs: " + error.getMessage(); }
            final String display = message;
            runOnUiThread(() -> Toast.makeText(this, display, Toast.LENGTH_LONG).show());
        }, "bounty-export").start();
    }

    @Override public void onDestroy() {
        if (diagnostics != null) diagnostics.close();
        super.onDestroy();
    }

    private final class Controls extends View {
        private final float[] xs = {.14f, .07f, .21f, .14f, .50f, .86f, .94f};
        private final float[] ys = {.60f, .75f, .75f, .90f, .90f, .83f, .64f};
        private final int[] masks = {0x10, 0x80, 0x20, 0x40, 0x08, 0x4000, 0x2000};
        private final String[] labels = {"UP", "LEFT", "RIGHT", "DOWN", "START", "X", "O"};
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private int pressed;
        private String lastTouch = "";
        private long lastPressSerial;
        private long lastSampleTime;
        private boolean logButtonDown;
        Controls() { super(BountyNativeActivity.this); setClickable(true); }
        private float scale() { return Math.min(getWidth()/640f, getHeight()/448f); }
        private float originX() { return (getWidth()-640f*scale())/2f; }
        private float originY() { return (getHeight()-448f*scale())/2f; }
        private float centerX(int i) { return originX()+xs[i]*640f*scale(); }
        private float centerY(int i) { return originY()+ys[i]*448f*scale(); }
        private float radius() { return 448f*.072f*scale(); }
        private RectF logButton() {
            float unit = Math.max(1f, scale());
            return new RectF(getWidth()-144f*unit, originY()+6f*unit,
                    getWidth()-8f*unit, originY()+34f*unit);
        }
        private int hit(float x,float y) {
            int result=0;
            for(int i=0;i<masks.length;i++) {
                float dx=x-centerX(i),dy=y-centerY(i);
                if(dx*dx+dy*dy<=radius()*radius()) result|=masks[i];
            }
            return result;
        }
        void clearTouch() { pressed=0; lastTouch=""; lastPressSerial=0; logButtonDown=false; invalidate(); }
        @Override public boolean onTouchEvent(MotionEvent event) {
            int action=event.getActionMasked(),next=0;
            if (action == MotionEvent.ACTION_DOWN && logButton().contains(event.getX(), event.getY())) {
                logButtonDown = true;
                nativeTouch(0); pressed = 0;
                invalidate(); return true;
            }
            if (logButtonDown) {
                if (action == MotionEvent.ACTION_UP) {
                    logButtonDown = false;
                    if (logButton().contains(event.getX(), event.getY())) exportLogs();
                } else if (action == MotionEvent.ACTION_CANCEL) logButtonDown = false;
                return true;
            }
            if(action==MotionEvent.ACTION_CANCEL) {
                nativeCancelTouch(); clearTouch(); return true;
            }
            if(action!=MotionEvent.ACTION_UP) {
                for(int p=0;p<event.getPointerCount();p++) {
                    if(action==MotionEvent.ACTION_POINTER_UP && p==event.getActionIndex()) continue;
                    next|=hit(event.getX(p),event.getY(p));
                }
            }
            int newlyPressed=next & ~pressed;
            if(next!=pressed) {
                long serial=nativeTouch(next);
                diagnostics.add("TOUCH buttons=0x" + Integer.toHexString(next) + " serial=" + serial);
                if(newlyPressed!=0) {
                    lastPressSerial=serial; lastTouch="";
                    for(int i=0;i<masks.length;i++) if((newlyPressed&masks[i])!=0)
                        lastTouch+=(lastTouch.isEmpty()?"":"+")+labels[i];
                }
                pressed=next;
            }
            invalidate();
            if(action==MotionEvent.ACTION_UP) performClick();
            return true;
        }
        @Override public boolean performClick() { super.performClick(); return true; }
        @Override protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            long status = nativeInputStatus();
            long now = android.os.SystemClock.elapsedRealtime();
            if (now-lastSampleTime >= 1000) {
                diagnostics.add("PAD reads="+(status >>> 32)+" consumed="+(status & 0xffffffffL));
                lastSampleTime = now;
            }
            float radius=radius(),font=Math.max(12f,448f*.028f*scale());
            paint.setTextSize(font);paint.setTextAlign(Paint.Align.CENTER);
            for(int i=0;i<masks.length;i++) {
                paint.setStyle(Paint.Style.FILL);
                paint.setColor((pressed&masks[i])!=0?0xaa5a96d2:0x87192332);
                canvas.drawCircle(centerX(i),centerY(i),radius,paint);
                paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(Math.max(1f,scale()));
                paint.setColor(0xbec8d2dc);
                canvas.drawCircle(centerX(i),centerY(i),radius,paint);
                paint.setStyle(Paint.Style.FILL);paint.setColor(0xdcf0f5fa);
                canvas.drawText(labels[i],centerX(i),centerY(i)-(paint.ascent()+paint.descent())/2f,paint);
            }
            if(!lastTouch.isEmpty()) {
                long consumed=status&0xffffffffL;
                paint.setTextSize(Math.max(12f,10f*scale()));
                paint.setTextAlign(Paint.Align.CENTER);paint.setColor(0xffdddddd);
                canvas.drawText("Touch: "+lastTouch+" | Game: "+
                    (consumed>=lastPressSerial?"received":"waiting"),
                    getWidth()/2f,originY()+20f*scale(),paint);
            }
            RectF logs = logButton();
            paint.setStyle(Paint.Style.FILL); paint.setColor(0xcc26394d);
            canvas.drawRoundRect(logs, 6f*scale(), 6f*scale(), paint);
            paint.setColor(Color.WHITE); paint.setTextSize(Math.max(12f, 10f*scale()));
            paint.setTextAlign(Paint.Align.CENTER);
            canvas.drawText("EXPORT LOGS", logs.centerX(), logs.centerY()-(paint.ascent()+paint.descent())/2f, paint);
            postInvalidateDelayed(200);
        }
    }
}
