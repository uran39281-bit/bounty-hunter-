#pragma once
#include <cstdint>
#include <deque>
#include <mutex>

namespace bounty_touch {
// Keep touch edges until an actual guest pad read consumes them. This preserves
// a down/up pair even when both Android events arrive between render frames.
class Queue {
    struct Event { uint16_t buttons; uint32_t serial; };
    std::mutex mutex;
    std::deque<Event> pending;
    uint16_t held = 0, delivered = 0;
    uint32_t serial = 0, consumed = 0, reads = 0;
public:
    uint32_t push(uint16_t buttons) {
        std::lock_guard<std::mutex> lock(mutex);
        if (buttons == held) return serial;
        held = buttons;
        // Bound a stalled game's queue. Cancel old input before keeping the
        // latest state; never leave an old button stuck on overflow.
        if (pending.size() >= 128) {
            pending.clear();
            delivered = 0;
            pending.push_back({0, ++serial});
        }
        pending.push_back({buttons, ++serial});
        return serial;
    }
    uint16_t read() {
        std::lock_guard<std::mutex> lock(mutex);
        ++reads;
        if (!pending.empty()) {
            delivered = pending.front().buttons;
            consumed = pending.front().serial;
            pending.pop_front();
        }
        return delivered;
    }
    void cancel() {
        std::lock_guard<std::mutex> lock(mutex);
        pending.clear();
        held = delivered = 0;
        consumed = serial;
    }
    uint64_t status() {
        std::lock_guard<std::mutex> lock(mutex);
        return (uint64_t(reads) << 32) | consumed;
    }
};
}
