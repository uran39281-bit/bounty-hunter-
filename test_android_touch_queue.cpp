#include "android_touch_queue.h"
#include <cassert>
#include <iostream>
#include <thread>

int main() {
    bounty_touch::Queue q;
    // The old frame sampler sees only zero after this fast down/up pair.
    const auto down = q.push(0x4000);
    q.push(0);
    assert(q.read() == 0x4000);
    assert(uint32_t(q.status()) == down);
    assert(q.read() == 0);
    assert(q.read() == 0);
    // Two taps before the game polls remain two separate edges.
    q.push(0x0040); q.push(0); q.push(0x0040); q.push(0);
    for (uint16_t mask : {0x0040, 0, 0x0040, 0}) assert(q.read() == mask);
    // Held buttons, multi-touch and individual finger release.
    q.push(0x4010); assert(q.read() == 0x4010);
    assert(q.read() == 0x4010);
    q.push(0x0010); assert(q.read() == 0x0010);
    q.push(0); assert(q.read() == 0);
    // Cancel immediately clears both queued and already delivered state.
    q.push(0x4000); q.cancel(); assert(q.read() == 0);
    q.push(0x4000); assert(q.read() == 0x4000);
    q.cancel(); assert(q.read() == 0);
    // A stalled guest cannot cause an unbounded queue or a stuck button.
    for (int i=0;i<1000;++i) q.push((i&1)?0:0x4000);
    for (int i=0;i<130;++i) q.read();
    assert(q.read() == 0);
    // Java input and guest polling run on different threads.
    std::thread input([&]{for(int i=0;i<10000;++i){q.push(0x0010);q.push(0);}});
    std::thread game([&]{for(int i=0;i<20000;++i){q.read();q.status();}});
    input.join();game.join();q.cancel();assert(q.read()==0);
    std::cout << "PASS quick tap, repeated taps, hold, multi-touch, cancel, overflow and concurrent polling\n";
}
