#pragma once
#include <cstdint>
// Test-only host input. Reads advance through original scePadRead calls.
inline uint16_t menuScriptButtons(uint32_t reads) {
    if (reads < 128u) return 0xffffu;
    const uint32_t step=(reads-128u)%128u;
    if (step<8u) return 0xfff7u;       // Start
    if (step>=32u && step<40u) return 0xbfffu; // Cross
    if (step>=64u && step<72u) return 0xffbfu; // Down
    if (step>=96u && step<104u) return 0xdfffu; // Circle
    return 0xffffu;
}
