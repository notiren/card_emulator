#include <stdio.h>
#include <stdint.h>


#define OFFSET 0x01042E

uint32_t convert(uint32_t input) {
    if (input >= OFFSET) {
        return input - OFFSET;
    }
    return input;
}

uint32_t convert24(uint32_t in)
{
    in &= 0xFFFFFF;

    uint8_t high = (in >> 16) & 0xFF;
    uint8_t folded_high = (high & 0x80) | (high & 0x07);

    uint32_t out = (in & 0x00FFFF) | ((uint32_t)folded_high << 16);

    if ((folded_high & 0x07) >= 4) {
        out = (out - 0x01042E) & 0xFFFFFF;
    }

    return out;
}

void print24(uint32_t v) {
    printf("%08x  ", v);
    for (int i = 23; i >= 0; i--) {
        putchar( (v >> i) & 1 ? '1' : '0');
        if (i % 4 == 0 && i > 0) putchar(' ');
    }
    putchar('\n');
}

int main(void) {
    int results = 0;

    struct { uint32_t in; uint32_t expected; } tests[] = {
            {0x006AE3,0x006AE3},
            {0x00F21C,0x00F21C},
            {0x003597,0x003597},
            {0x00AC41,0x00AC41},
            {0x001E6A,0x001E6A},
            {0x00D0B5,0x00D0B5},
            {0x009728,0x009728},
            {0x004BF0,0x004BF0},
            {0x00FECB,0x00FECB},
            {0x01042E,0x01042E},
            {0x01B685,0x01B685},
            {0x035C12,0x035C12},
            {0x011E79,0x011E79},
            {0x0A63D4,0x0263D4},
            {0x0149AF,0x0149AF},
            {0x32D701,0x02D701},
            {0x078E5B,0x068A2D},
            {0xE1349C,0x81349C},
            {0x4B216E,0x03216E},
            {0x9C5A31,0x835603},
            {0x09E21C,0x01E21C},
            {0x08E21C,0x00E21C},
            {0x07E21C,0x06DDEE},
            {0x06E21C,0x05DDEE},
            {0x06221C,0x051DEE},
            {0x062211,0x051DE3},
            {0x2CB354,0x03AF26},
            {0x0DBE35,0x04BA07},
            {0x09F591,0x01F591},
            {0xC585C3,0x848195},
            {0xC8D1C0,0x80D1C0},
            {0x415E3E,0x015E3E},
            {0x09BA8A,0x01BA8A},
            {0x3EEC51,0x05E823},
            {0x6E2D8C,0x05295E},
            {0xB28A3B,0x828A3B},
            {0x0940EE,0x0140EE},
            {0x727E71,0x027E71},
            {0xEE311C,0x852CEE},
            {0x0B4DF1,0x034DF1},
            {0xCA0620,0x820620},
            {0xEA77D9,0x8277D9},
            {0x332E63,0x032E63},
            {0x05779E,0x047370},
            {0x690643,0x010643},
            {0x2A1480,0x021480},
            {0xA1AEB5,0x81AEB5},
            {0x0DC82F,0x04C401},
            {0xC4E7AF,0x83E381},
            {0x642BAE,0x032780},
            {0xE2A30E,0x82A30E},
            {0x260ACA,0x05069C},
            {0x72554C,0x02554C},
            {0x5FA655,0x06A227},
            {0xE0259B,0x80259B},
            {0x622A78,0x022A78},
            {0x0E4C73,0x054845},
            {0x3B24D6,0x0324D6},
            {0xACB0A4,0x83AC76},
            {0x65E03D,0x04DC0F},
            {0x9F23A7,0x861F79},
            {0x9F23A7,0x861F79}
    };
        
    for (int i = 0; i < sizeof(tests)/sizeof(tests[0]); i++) {
        uint32_t out = convert24(tests[i].in);
        printf("Test %d:\n", i+1);
        printf("  in : "); print24(tests[i].in);
        printf("  out: "); print24(out);
        printf("  match? %s\n\n", (out == tests[i].expected) ? "YES" : "NO");
        if (out != tests[i].expected) {
            results++;
        }
    }

    if (results == 0) {
        printf("URRRRRAAAAAA!");
    } else {
        printf("we are fucked %d times!", results);
    }

    return 0;
}
