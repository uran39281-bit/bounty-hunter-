#pragma once
#include <cstdint>
// Test-only host input. Reads advance through original scePadRead calls.
inline uint16_t menuScriptButtons(uint32_t reads) {
    if (reads < 128u) return 0xffffu;
    // After opening the real save warning and selecting No, cover every
    // direction and back/start through original pad reads.
    if (reads >= 336u) {
        const uint32_t step=(reads-336u)%112u;
        if (step<8u) return 0xffefu;       // Up
        if (step>=16u && step<24u) return 0xff7fu; // Left
        if (step>=32u && step<40u) return 0xffdfu; // Right
        if (step>=48u && step<56u) return 0xdfffu; // Circle
        if (step>=64u && step<72u) return 0xfff7u; // Start
        if (step>=80u && step<88u) return 0xbfffu; // Cross
        if (step>=96u && step<104u) return 0xffbfu; // Down
        return 0xffffu;
    }
    const uint32_t step=(reads-128u)%128u;
    if (step<8u) return 0xfff7u;       // Start
    if (step>=32u && step<40u) return 0xbfffu; // Cross
    if (step>=64u && step<72u) return 0xffbfu; // Down
    if (step>=96u && step<104u) return 0xdfffu; // Circle
    return 0xffffu;
}
