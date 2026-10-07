#pragma once
#include <algorithm>
#include <array>
#include <cstdint>

namespace bounty_touch {
struct Button { float x, y; uint16_t mask; const char *label; };
inline constexpr std::array<Button, 7> buttons = {{
    {0.14f,0.60f,0x0010u,"UP"}, {0.07f,0.75f,0x0080u,"LEFT"},
    {0.21f,0.75f,0x0020u,"RIGHT"}, {0.14f,0.90f,0x0040u,"DOWN"},
    {0.50f,0.90f,0x0008u,"START"}, {0.86f,0.83f,0x4000u,"X"},
    {0.94f,0.64f,0x2000u,"O"}
}};
inline float radius(float width, float height) { return std::min(width,height)*0.072f; }
inline uint16_t maskAt(float x, float y, float width, float height) {
    if (!(width>0 && height>0)) return 0u;
    const float r=radius(width,height);
    uint16_t result=0;
    for (const auto &b : buttons) {
        const float dx=x-b.x*width,dy=y-b.y*height;
        if (dx*dx+dy*dy<=r*r) result|=b.mask;
    }
    return result;
}
inline uint16_t merge(uint16_t physicalActiveLow, uint16_t touchPressed) {
    return static_cast<uint16_t>(physicalActiveLow & ~touchPressed);
}
}
