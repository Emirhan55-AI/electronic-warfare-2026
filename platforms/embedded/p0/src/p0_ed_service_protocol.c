#include "p0_ed_service_protocol.h"

#include <math.h>
#include <string.h>

static uint16_t load_le16(const uint8_t *source)
{
    return (uint16_t)((uint16_t)source[0] | ((uint16_t)source[1] << 8));
}

static uint32_t load_le32(const uint8_t *source)
{
    return (uint32_t)source[0] | ((uint32_t)source[1] << 8) |
           ((uint32_t)source[2] << 16) | ((uint32_t)source[3] << 24);
}

static uint64_t load_le64(const uint8_t *source)
{
    return (uint64_t)load_le32(source) | ((uint64_t)load_le32(source + 4) << 32);
}

static void store_le16(uint8_t *target, uint16_t value)
{
    target[0] = (uint8_t)value;
    target[1] = (uint8_t)(value >> 8);
}

static void store_le32(uint8_t *target, uint32_t value)
{
    target[0] = (uint8_t)value;
    target[1] = (uint8_t)(value >> 8);
    target[2] = (uint8_t)(value >> 16);
    target[3] = (uint8_t)(value >> 24);
}

static void store_le64(uint8_t *target, uint64_t value)
{
    store_le32(target, (uint32_t)value);
    store_le32(target + 4, (uint32_t)(value >> 32));
}

static double load_le_double(const uint8_t *source)
{
    uint64_t bits = load_le64(source);
    double value;

    memcpy(&value, &bits, sizeof(value));
    return value;
}

int p0_detection_message_decode(const uint8_t *bytes, size_t size, int response,
                                 p0_detection_message_t *message)
{
    uint16_t version;
    uint32_t wire_fft_size;
    int has_profile;

    if (bytes == NULL || message == NULL || size != P0_DETECTION_MESSAGE_BYTES ||
        memcmp(bytes, response ? "P0DR" : "P0DC", 4U) != 0 ||
        load_le16(bytes + 6) != P0_DETECTION_MESSAGE_BYTES ||
        load_le32(bytes + 44) != p0_ed_crc32(bytes, 44U))
        return -1;
    version = load_le16(bytes + 4);
    wire_fft_size = load_le32(bytes + 40);
    if (version != 1U && version != 2U)
        return -1;
    message->protocol_version = version;
    message->operation = load_le32(bytes + 8);
    message->request_id = load_le32(bytes + 12);
    message->status = load_le32(bytes + 16);
    message->generation = load_le32(bytes + 20);
    message->alpha_q32 = load_le64(bytes + 24);
    message->weak_alpha_q32 = load_le64(bytes + 32);
    if ((message->operation != P0_DETECTION_GET && message->operation != P0_DETECTION_SET) ||
        message->status > P0_DETECTION_INTERNAL || (!response && message->status != 0U))
        return -1;
    has_profile = (!response && message->operation == P0_DETECTION_SET) ||
                  (response && message->status == P0_DETECTION_OK);
    if (!has_profile) {
        if (message->generation || message->alpha_q32 || message->weak_alpha_q32 ||
            wire_fft_size != 0U) return -1;
        message->fft_size = 0U;
    } else if (message->alpha_q32 < (UINT64_C(1) << 32) ||
               message->alpha_q32 >= (UINT64_C(1) << 36) ||
               message->weak_alpha_q32 < (UINT64_C(1) << 32) ||
               message->weak_alpha_q32 >= (UINT64_C(1) << 34) ||
               message->weak_alpha_q32 > message->alpha_q32 ||
               (version == 1U && wire_fft_size != 0U) ||
               (version == 2U && wire_fft_size != 4096U &&
                wire_fft_size != 8192U && wire_fft_size != 16384U)) return -1;
    else
        message->fft_size = version == 1U ? 4096U : wire_fft_size;
    return 0;
}

int p0_detection_message_encode(const p0_detection_message_t *message, int response,
                                 uint8_t bytes[P0_DETECTION_MESSAGE_BYTES])
{
    p0_detection_message_t checked;
    if (message == NULL || bytes == NULL) return -1;
    memset(bytes, 0, P0_DETECTION_MESSAGE_BYTES);
    memcpy(bytes, response ? "P0DR" : "P0DC", 4U);
    store_le16(bytes + 4, message->protocol_version == 2U ? 2U : 1U);
    store_le16(bytes + 6, P0_DETECTION_MESSAGE_BYTES);
    store_le32(bytes + 8, message->operation); store_le32(bytes + 12, message->request_id);
    store_le32(bytes + 16, message->status); store_le32(bytes + 20, message->generation);
    store_le64(bytes + 24, message->alpha_q32); store_le64(bytes + 32, message->weak_alpha_q32);
    if (message->protocol_version == 2U)
        store_le32(bytes + 40, message->fft_size);
    store_le32(bytes + 44, p0_ed_crc32(bytes, 44U));
    return p0_detection_message_decode(bytes, P0_DETECTION_MESSAGE_BYTES, response, &checked);
}

static void store_le_double(uint8_t *target, double value)
{
    uint64_t bits;

    memcpy(&bits, &value, sizeof(bits));
    store_le64(target, bits);
}

uint32_t p0_ed_crc32(const uint8_t *data, size_t length)
{
    static const uint32_t table[4][256] = {{
        UINT32_C(0x00000000), UINT32_C(0x77073096), UINT32_C(0xEE0E612C), UINT32_C(0x990951BA),
        UINT32_C(0x076DC419), UINT32_C(0x706AF48F), UINT32_C(0xE963A535), UINT32_C(0x9E6495A3),
        UINT32_C(0x0EDB8832), UINT32_C(0x79DCB8A4), UINT32_C(0xE0D5E91E), UINT32_C(0x97D2D988),
        UINT32_C(0x09B64C2B), UINT32_C(0x7EB17CBD), UINT32_C(0xE7B82D07), UINT32_C(0x90BF1D91),
        UINT32_C(0x1DB71064), UINT32_C(0x6AB020F2), UINT32_C(0xF3B97148), UINT32_C(0x84BE41DE),
        UINT32_C(0x1ADAD47D), UINT32_C(0x6DDDE4EB), UINT32_C(0xF4D4B551), UINT32_C(0x83D385C7),
        UINT32_C(0x136C9856), UINT32_C(0x646BA8C0), UINT32_C(0xFD62F97A), UINT32_C(0x8A65C9EC),
        UINT32_C(0x14015C4F), UINT32_C(0x63066CD9), UINT32_C(0xFA0F3D63), UINT32_C(0x8D080DF5),
        UINT32_C(0x3B6E20C8), UINT32_C(0x4C69105E), UINT32_C(0xD56041E4), UINT32_C(0xA2677172),
        UINT32_C(0x3C03E4D1), UINT32_C(0x4B04D447), UINT32_C(0xD20D85FD), UINT32_C(0xA50AB56B),
        UINT32_C(0x35B5A8FA), UINT32_C(0x42B2986C), UINT32_C(0xDBBBC9D6), UINT32_C(0xACBCF940),
        UINT32_C(0x32D86CE3), UINT32_C(0x45DF5C75), UINT32_C(0xDCD60DCF), UINT32_C(0xABD13D59),
        UINT32_C(0x26D930AC), UINT32_C(0x51DE003A), UINT32_C(0xC8D75180), UINT32_C(0xBFD06116),
        UINT32_C(0x21B4F4B5), UINT32_C(0x56B3C423), UINT32_C(0xCFBA9599), UINT32_C(0xB8BDA50F),
        UINT32_C(0x2802B89E), UINT32_C(0x5F058808), UINT32_C(0xC60CD9B2), UINT32_C(0xB10BE924),
        UINT32_C(0x2F6F7C87), UINT32_C(0x58684C11), UINT32_C(0xC1611DAB), UINT32_C(0xB6662D3D),
        UINT32_C(0x76DC4190), UINT32_C(0x01DB7106), UINT32_C(0x98D220BC), UINT32_C(0xEFD5102A),
        UINT32_C(0x71B18589), UINT32_C(0x06B6B51F), UINT32_C(0x9FBFE4A5), UINT32_C(0xE8B8D433),
        UINT32_C(0x7807C9A2), UINT32_C(0x0F00F934), UINT32_C(0x9609A88E), UINT32_C(0xE10E9818),
        UINT32_C(0x7F6A0DBB), UINT32_C(0x086D3D2D), UINT32_C(0x91646C97), UINT32_C(0xE6635C01),
        UINT32_C(0x6B6B51F4), UINT32_C(0x1C6C6162), UINT32_C(0x856530D8), UINT32_C(0xF262004E),
        UINT32_C(0x6C0695ED), UINT32_C(0x1B01A57B), UINT32_C(0x8208F4C1), UINT32_C(0xF50FC457),
        UINT32_C(0x65B0D9C6), UINT32_C(0x12B7E950), UINT32_C(0x8BBEB8EA), UINT32_C(0xFCB9887C),
        UINT32_C(0x62DD1DDF), UINT32_C(0x15DA2D49), UINT32_C(0x8CD37CF3), UINT32_C(0xFBD44C65),
        UINT32_C(0x4DB26158), UINT32_C(0x3AB551CE), UINT32_C(0xA3BC0074), UINT32_C(0xD4BB30E2),
        UINT32_C(0x4ADFA541), UINT32_C(0x3DD895D7), UINT32_C(0xA4D1C46D), UINT32_C(0xD3D6F4FB),
        UINT32_C(0x4369E96A), UINT32_C(0x346ED9FC), UINT32_C(0xAD678846), UINT32_C(0xDA60B8D0),
        UINT32_C(0x44042D73), UINT32_C(0x33031DE5), UINT32_C(0xAA0A4C5F), UINT32_C(0xDD0D7CC9),
        UINT32_C(0x5005713C), UINT32_C(0x270241AA), UINT32_C(0xBE0B1010), UINT32_C(0xC90C2086),
        UINT32_C(0x5768B525), UINT32_C(0x206F85B3), UINT32_C(0xB966D409), UINT32_C(0xCE61E49F),
        UINT32_C(0x5EDEF90E), UINT32_C(0x29D9C998), UINT32_C(0xB0D09822), UINT32_C(0xC7D7A8B4),
        UINT32_C(0x59B33D17), UINT32_C(0x2EB40D81), UINT32_C(0xB7BD5C3B), UINT32_C(0xC0BA6CAD),
        UINT32_C(0xEDB88320), UINT32_C(0x9ABFB3B6), UINT32_C(0x03B6E20C), UINT32_C(0x74B1D29A),
        UINT32_C(0xEAD54739), UINT32_C(0x9DD277AF), UINT32_C(0x04DB2615), UINT32_C(0x73DC1683),
        UINT32_C(0xE3630B12), UINT32_C(0x94643B84), UINT32_C(0x0D6D6A3E), UINT32_C(0x7A6A5AA8),
        UINT32_C(0xE40ECF0B), UINT32_C(0x9309FF9D), UINT32_C(0x0A00AE27), UINT32_C(0x7D079EB1),
        UINT32_C(0xF00F9344), UINT32_C(0x8708A3D2), UINT32_C(0x1E01F268), UINT32_C(0x6906C2FE),
        UINT32_C(0xF762575D), UINT32_C(0x806567CB), UINT32_C(0x196C3671), UINT32_C(0x6E6B06E7),
        UINT32_C(0xFED41B76), UINT32_C(0x89D32BE0), UINT32_C(0x10DA7A5A), UINT32_C(0x67DD4ACC),
        UINT32_C(0xF9B9DF6F), UINT32_C(0x8EBEEFF9), UINT32_C(0x17B7BE43), UINT32_C(0x60B08ED5),
        UINT32_C(0xD6D6A3E8), UINT32_C(0xA1D1937E), UINT32_C(0x38D8C2C4), UINT32_C(0x4FDFF252),
        UINT32_C(0xD1BB67F1), UINT32_C(0xA6BC5767), UINT32_C(0x3FB506DD), UINT32_C(0x48B2364B),
        UINT32_C(0xD80D2BDA), UINT32_C(0xAF0A1B4C), UINT32_C(0x36034AF6), UINT32_C(0x41047A60),
        UINT32_C(0xDF60EFC3), UINT32_C(0xA867DF55), UINT32_C(0x316E8EEF), UINT32_C(0x4669BE79),
        UINT32_C(0xCB61B38C), UINT32_C(0xBC66831A), UINT32_C(0x256FD2A0), UINT32_C(0x5268E236),
        UINT32_C(0xCC0C7795), UINT32_C(0xBB0B4703), UINT32_C(0x220216B9), UINT32_C(0x5505262F),
        UINT32_C(0xC5BA3BBE), UINT32_C(0xB2BD0B28), UINT32_C(0x2BB45A92), UINT32_C(0x5CB36A04),
        UINT32_C(0xC2D7FFA7), UINT32_C(0xB5D0CF31), UINT32_C(0x2CD99E8B), UINT32_C(0x5BDEAE1D),
        UINT32_C(0x9B64C2B0), UINT32_C(0xEC63F226), UINT32_C(0x756AA39C), UINT32_C(0x026D930A),
        UINT32_C(0x9C0906A9), UINT32_C(0xEB0E363F), UINT32_C(0x72076785), UINT32_C(0x05005713),
        UINT32_C(0x95BF4A82), UINT32_C(0xE2B87A14), UINT32_C(0x7BB12BAE), UINT32_C(0x0CB61B38),
        UINT32_C(0x92D28E9B), UINT32_C(0xE5D5BE0D), UINT32_C(0x7CDCEFB7), UINT32_C(0x0BDBDF21),
        UINT32_C(0x86D3D2D4), UINT32_C(0xF1D4E242), UINT32_C(0x68DDB3F8), UINT32_C(0x1FDA836E),
        UINT32_C(0x81BE16CD), UINT32_C(0xF6B9265B), UINT32_C(0x6FB077E1), UINT32_C(0x18B74777),
        UINT32_C(0x88085AE6), UINT32_C(0xFF0F6A70), UINT32_C(0x66063BCA), UINT32_C(0x11010B5C),
        UINT32_C(0x8F659EFF), UINT32_C(0xF862AE69), UINT32_C(0x616BFFD3), UINT32_C(0x166CCF45),
        UINT32_C(0xA00AE278), UINT32_C(0xD70DD2EE), UINT32_C(0x4E048354), UINT32_C(0x3903B3C2),
        UINT32_C(0xA7672661), UINT32_C(0xD06016F7), UINT32_C(0x4969474D), UINT32_C(0x3E6E77DB),
        UINT32_C(0xAED16A4A), UINT32_C(0xD9D65ADC), UINT32_C(0x40DF0B66), UINT32_C(0x37D83BF0),
        UINT32_C(0xA9BCAE53), UINT32_C(0xDEBB9EC5), UINT32_C(0x47B2CF7F), UINT32_C(0x30B5FFE9),
        UINT32_C(0xBDBDF21C), UINT32_C(0xCABAC28A), UINT32_C(0x53B39330), UINT32_C(0x24B4A3A6),
        UINT32_C(0xBAD03605), UINT32_C(0xCDD70693), UINT32_C(0x54DE5729), UINT32_C(0x23D967BF),
        UINT32_C(0xB3667A2E), UINT32_C(0xC4614AB8), UINT32_C(0x5D681B02), UINT32_C(0x2A6F2B94),
        UINT32_C(0xB40BBE37), UINT32_C(0xC30C8EA1), UINT32_C(0x5A05DF1B), UINT32_C(0x2D02EF8D),
    }, {
        UINT32_C(0x00000000), UINT32_C(0x191B3141), UINT32_C(0x32366282), UINT32_C(0x2B2D53C3),
        UINT32_C(0x646CC504), UINT32_C(0x7D77F445), UINT32_C(0x565AA786), UINT32_C(0x4F4196C7),
        UINT32_C(0xC8D98A08), UINT32_C(0xD1C2BB49), UINT32_C(0xFAEFE88A), UINT32_C(0xE3F4D9CB),
        UINT32_C(0xACB54F0C), UINT32_C(0xB5AE7E4D), UINT32_C(0x9E832D8E), UINT32_C(0x87981CCF),
        UINT32_C(0x4AC21251), UINT32_C(0x53D92310), UINT32_C(0x78F470D3), UINT32_C(0x61EF4192),
        UINT32_C(0x2EAED755), UINT32_C(0x37B5E614), UINT32_C(0x1C98B5D7), UINT32_C(0x05838496),
        UINT32_C(0x821B9859), UINT32_C(0x9B00A918), UINT32_C(0xB02DFADB), UINT32_C(0xA936CB9A),
        UINT32_C(0xE6775D5D), UINT32_C(0xFF6C6C1C), UINT32_C(0xD4413FDF), UINT32_C(0xCD5A0E9E),
        UINT32_C(0x958424A2), UINT32_C(0x8C9F15E3), UINT32_C(0xA7B24620), UINT32_C(0xBEA97761),
        UINT32_C(0xF1E8E1A6), UINT32_C(0xE8F3D0E7), UINT32_C(0xC3DE8324), UINT32_C(0xDAC5B265),
        UINT32_C(0x5D5DAEAA), UINT32_C(0x44469FEB), UINT32_C(0x6F6BCC28), UINT32_C(0x7670FD69),
        UINT32_C(0x39316BAE), UINT32_C(0x202A5AEF), UINT32_C(0x0B07092C), UINT32_C(0x121C386D),
        UINT32_C(0xDF4636F3), UINT32_C(0xC65D07B2), UINT32_C(0xED705471), UINT32_C(0xF46B6530),
        UINT32_C(0xBB2AF3F7), UINT32_C(0xA231C2B6), UINT32_C(0x891C9175), UINT32_C(0x9007A034),
        UINT32_C(0x179FBCFB), UINT32_C(0x0E848DBA), UINT32_C(0x25A9DE79), UINT32_C(0x3CB2EF38),
        UINT32_C(0x73F379FF), UINT32_C(0x6AE848BE), UINT32_C(0x41C51B7D), UINT32_C(0x58DE2A3C),
        UINT32_C(0xF0794F05), UINT32_C(0xE9627E44), UINT32_C(0xC24F2D87), UINT32_C(0xDB541CC6),
        UINT32_C(0x94158A01), UINT32_C(0x8D0EBB40), UINT32_C(0xA623E883), UINT32_C(0xBF38D9C2),
        UINT32_C(0x38A0C50D), UINT32_C(0x21BBF44C), UINT32_C(0x0A96A78F), UINT32_C(0x138D96CE),
        UINT32_C(0x5CCC0009), UINT32_C(0x45D73148), UINT32_C(0x6EFA628B), UINT32_C(0x77E153CA),
        UINT32_C(0xBABB5D54), UINT32_C(0xA3A06C15), UINT32_C(0x888D3FD6), UINT32_C(0x91960E97),
        UINT32_C(0xDED79850), UINT32_C(0xC7CCA911), UINT32_C(0xECE1FAD2), UINT32_C(0xF5FACB93),
        UINT32_C(0x7262D75C), UINT32_C(0x6B79E61D), UINT32_C(0x4054B5DE), UINT32_C(0x594F849F),
        UINT32_C(0x160E1258), UINT32_C(0x0F152319), UINT32_C(0x243870DA), UINT32_C(0x3D23419B),
        UINT32_C(0x65FD6BA7), UINT32_C(0x7CE65AE6), UINT32_C(0x57CB0925), UINT32_C(0x4ED03864),
        UINT32_C(0x0191AEA3), UINT32_C(0x188A9FE2), UINT32_C(0x33A7CC21), UINT32_C(0x2ABCFD60),
        UINT32_C(0xAD24E1AF), UINT32_C(0xB43FD0EE), UINT32_C(0x9F12832D), UINT32_C(0x8609B26C),
        UINT32_C(0xC94824AB), UINT32_C(0xD05315EA), UINT32_C(0xFB7E4629), UINT32_C(0xE2657768),
        UINT32_C(0x2F3F79F6), UINT32_C(0x362448B7), UINT32_C(0x1D091B74), UINT32_C(0x04122A35),
        UINT32_C(0x4B53BCF2), UINT32_C(0x52488DB3), UINT32_C(0x7965DE70), UINT32_C(0x607EEF31),
        UINT32_C(0xE7E6F3FE), UINT32_C(0xFEFDC2BF), UINT32_C(0xD5D0917C), UINT32_C(0xCCCBA03D),
        UINT32_C(0x838A36FA), UINT32_C(0x9A9107BB), UINT32_C(0xB1BC5478), UINT32_C(0xA8A76539),
        UINT32_C(0x3B83984B), UINT32_C(0x2298A90A), UINT32_C(0x09B5FAC9), UINT32_C(0x10AECB88),
        UINT32_C(0x5FEF5D4F), UINT32_C(0x46F46C0E), UINT32_C(0x6DD93FCD), UINT32_C(0x74C20E8C),
        UINT32_C(0xF35A1243), UINT32_C(0xEA412302), UINT32_C(0xC16C70C1), UINT32_C(0xD8774180),
        UINT32_C(0x9736D747), UINT32_C(0x8E2DE606), UINT32_C(0xA500B5C5), UINT32_C(0xBC1B8484),
        UINT32_C(0x71418A1A), UINT32_C(0x685ABB5B), UINT32_C(0x4377E898), UINT32_C(0x5A6CD9D9),
        UINT32_C(0x152D4F1E), UINT32_C(0x0C367E5F), UINT32_C(0x271B2D9C), UINT32_C(0x3E001CDD),
        UINT32_C(0xB9980012), UINT32_C(0xA0833153), UINT32_C(0x8BAE6290), UINT32_C(0x92B553D1),
        UINT32_C(0xDDF4C516), UINT32_C(0xC4EFF457), UINT32_C(0xEFC2A794), UINT32_C(0xF6D996D5),
        UINT32_C(0xAE07BCE9), UINT32_C(0xB71C8DA8), UINT32_C(0x9C31DE6B), UINT32_C(0x852AEF2A),
        UINT32_C(0xCA6B79ED), UINT32_C(0xD37048AC), UINT32_C(0xF85D1B6F), UINT32_C(0xE1462A2E),
        UINT32_C(0x66DE36E1), UINT32_C(0x7FC507A0), UINT32_C(0x54E85463), UINT32_C(0x4DF36522),
        UINT32_C(0x02B2F3E5), UINT32_C(0x1BA9C2A4), UINT32_C(0x30849167), UINT32_C(0x299FA026),
        UINT32_C(0xE4C5AEB8), UINT32_C(0xFDDE9FF9), UINT32_C(0xD6F3CC3A), UINT32_C(0xCFE8FD7B),
        UINT32_C(0x80A96BBC), UINT32_C(0x99B25AFD), UINT32_C(0xB29F093E), UINT32_C(0xAB84387F),
        UINT32_C(0x2C1C24B0), UINT32_C(0x350715F1), UINT32_C(0x1E2A4632), UINT32_C(0x07317773),
        UINT32_C(0x4870E1B4), UINT32_C(0x516BD0F5), UINT32_C(0x7A468336), UINT32_C(0x635DB277),
        UINT32_C(0xCBFAD74E), UINT32_C(0xD2E1E60F), UINT32_C(0xF9CCB5CC), UINT32_C(0xE0D7848D),
        UINT32_C(0xAF96124A), UINT32_C(0xB68D230B), UINT32_C(0x9DA070C8), UINT32_C(0x84BB4189),
        UINT32_C(0x03235D46), UINT32_C(0x1A386C07), UINT32_C(0x31153FC4), UINT32_C(0x280E0E85),
        UINT32_C(0x674F9842), UINT32_C(0x7E54A903), UINT32_C(0x5579FAC0), UINT32_C(0x4C62CB81),
        UINT32_C(0x8138C51F), UINT32_C(0x9823F45E), UINT32_C(0xB30EA79D), UINT32_C(0xAA1596DC),
        UINT32_C(0xE554001B), UINT32_C(0xFC4F315A), UINT32_C(0xD7626299), UINT32_C(0xCE7953D8),
        UINT32_C(0x49E14F17), UINT32_C(0x50FA7E56), UINT32_C(0x7BD72D95), UINT32_C(0x62CC1CD4),
        UINT32_C(0x2D8D8A13), UINT32_C(0x3496BB52), UINT32_C(0x1FBBE891), UINT32_C(0x06A0D9D0),
        UINT32_C(0x5E7EF3EC), UINT32_C(0x4765C2AD), UINT32_C(0x6C48916E), UINT32_C(0x7553A02F),
        UINT32_C(0x3A1236E8), UINT32_C(0x230907A9), UINT32_C(0x0824546A), UINT32_C(0x113F652B),
        UINT32_C(0x96A779E4), UINT32_C(0x8FBC48A5), UINT32_C(0xA4911B66), UINT32_C(0xBD8A2A27),
        UINT32_C(0xF2CBBCE0), UINT32_C(0xEBD08DA1), UINT32_C(0xC0FDDE62), UINT32_C(0xD9E6EF23),
        UINT32_C(0x14BCE1BD), UINT32_C(0x0DA7D0FC), UINT32_C(0x268A833F), UINT32_C(0x3F91B27E),
        UINT32_C(0x70D024B9), UINT32_C(0x69CB15F8), UINT32_C(0x42E6463B), UINT32_C(0x5BFD777A),
        UINT32_C(0xDC656BB5), UINT32_C(0xC57E5AF4), UINT32_C(0xEE530937), UINT32_C(0xF7483876),
        UINT32_C(0xB809AEB1), UINT32_C(0xA1129FF0), UINT32_C(0x8A3FCC33), UINT32_C(0x9324FD72),
    }, {
        UINT32_C(0x00000000), UINT32_C(0x01C26A37), UINT32_C(0x0384D46E), UINT32_C(0x0246BE59),
        UINT32_C(0x0709A8DC), UINT32_C(0x06CBC2EB), UINT32_C(0x048D7CB2), UINT32_C(0x054F1685),
        UINT32_C(0x0E1351B8), UINT32_C(0x0FD13B8F), UINT32_C(0x0D9785D6), UINT32_C(0x0C55EFE1),
        UINT32_C(0x091AF964), UINT32_C(0x08D89353), UINT32_C(0x0A9E2D0A), UINT32_C(0x0B5C473D),
        UINT32_C(0x1C26A370), UINT32_C(0x1DE4C947), UINT32_C(0x1FA2771E), UINT32_C(0x1E601D29),
        UINT32_C(0x1B2F0BAC), UINT32_C(0x1AED619B), UINT32_C(0x18ABDFC2), UINT32_C(0x1969B5F5),
        UINT32_C(0x1235F2C8), UINT32_C(0x13F798FF), UINT32_C(0x11B126A6), UINT32_C(0x10734C91),
        UINT32_C(0x153C5A14), UINT32_C(0x14FE3023), UINT32_C(0x16B88E7A), UINT32_C(0x177AE44D),
        UINT32_C(0x384D46E0), UINT32_C(0x398F2CD7), UINT32_C(0x3BC9928E), UINT32_C(0x3A0BF8B9),
        UINT32_C(0x3F44EE3C), UINT32_C(0x3E86840B), UINT32_C(0x3CC03A52), UINT32_C(0x3D025065),
        UINT32_C(0x365E1758), UINT32_C(0x379C7D6F), UINT32_C(0x35DAC336), UINT32_C(0x3418A901),
        UINT32_C(0x3157BF84), UINT32_C(0x3095D5B3), UINT32_C(0x32D36BEA), UINT32_C(0x331101DD),
        UINT32_C(0x246BE590), UINT32_C(0x25A98FA7), UINT32_C(0x27EF31FE), UINT32_C(0x262D5BC9),
        UINT32_C(0x23624D4C), UINT32_C(0x22A0277B), UINT32_C(0x20E69922), UINT32_C(0x2124F315),
        UINT32_C(0x2A78B428), UINT32_C(0x2BBADE1F), UINT32_C(0x29FC6046), UINT32_C(0x283E0A71),
        UINT32_C(0x2D711CF4), UINT32_C(0x2CB376C3), UINT32_C(0x2EF5C89A), UINT32_C(0x2F37A2AD),
        UINT32_C(0x709A8DC0), UINT32_C(0x7158E7F7), UINT32_C(0x731E59AE), UINT32_C(0x72DC3399),
        UINT32_C(0x7793251C), UINT32_C(0x76514F2B), UINT32_C(0x7417F172), UINT32_C(0x75D59B45),
        UINT32_C(0x7E89DC78), UINT32_C(0x7F4BB64F), UINT32_C(0x7D0D0816), UINT32_C(0x7CCF6221),
        UINT32_C(0x798074A4), UINT32_C(0x78421E93), UINT32_C(0x7A04A0CA), UINT32_C(0x7BC6CAFD),
        UINT32_C(0x6CBC2EB0), UINT32_C(0x6D7E4487), UINT32_C(0x6F38FADE), UINT32_C(0x6EFA90E9),
        UINT32_C(0x6BB5866C), UINT32_C(0x6A77EC5B), UINT32_C(0x68315202), UINT32_C(0x69F33835),
        UINT32_C(0x62AF7F08), UINT32_C(0x636D153F), UINT32_C(0x612BAB66), UINT32_C(0x60E9C151),
        UINT32_C(0x65A6D7D4), UINT32_C(0x6464BDE3), UINT32_C(0x662203BA), UINT32_C(0x67E0698D),
        UINT32_C(0x48D7CB20), UINT32_C(0x4915A117), UINT32_C(0x4B531F4E), UINT32_C(0x4A917579),
        UINT32_C(0x4FDE63FC), UINT32_C(0x4E1C09CB), UINT32_C(0x4C5AB792), UINT32_C(0x4D98DDA5),
        UINT32_C(0x46C49A98), UINT32_C(0x4706F0AF), UINT32_C(0x45404EF6), UINT32_C(0x448224C1),
        UINT32_C(0x41CD3244), UINT32_C(0x400F5873), UINT32_C(0x4249E62A), UINT32_C(0x438B8C1D),
        UINT32_C(0x54F16850), UINT32_C(0x55330267), UINT32_C(0x5775BC3E), UINT32_C(0x56B7D609),
        UINT32_C(0x53F8C08C), UINT32_C(0x523AAABB), UINT32_C(0x507C14E2), UINT32_C(0x51BE7ED5),
        UINT32_C(0x5AE239E8), UINT32_C(0x5B2053DF), UINT32_C(0x5966ED86), UINT32_C(0x58A487B1),
        UINT32_C(0x5DEB9134), UINT32_C(0x5C29FB03), UINT32_C(0x5E6F455A), UINT32_C(0x5FAD2F6D),
        UINT32_C(0xE1351B80), UINT32_C(0xE0F771B7), UINT32_C(0xE2B1CFEE), UINT32_C(0xE373A5D9),
        UINT32_C(0xE63CB35C), UINT32_C(0xE7FED96B), UINT32_C(0xE5B86732), UINT32_C(0xE47A0D05),
        UINT32_C(0xEF264A38), UINT32_C(0xEEE4200F), UINT32_C(0xECA29E56), UINT32_C(0xED60F461),
        UINT32_C(0xE82FE2E4), UINT32_C(0xE9ED88D3), UINT32_C(0xEBAB368A), UINT32_C(0xEA695CBD),
        UINT32_C(0xFD13B8F0), UINT32_C(0xFCD1D2C7), UINT32_C(0xFE976C9E), UINT32_C(0xFF5506A9),
        UINT32_C(0xFA1A102C), UINT32_C(0xFBD87A1B), UINT32_C(0xF99EC442), UINT32_C(0xF85CAE75),
        UINT32_C(0xF300E948), UINT32_C(0xF2C2837F), UINT32_C(0xF0843D26), UINT32_C(0xF1465711),
        UINT32_C(0xF4094194), UINT32_C(0xF5CB2BA3), UINT32_C(0xF78D95FA), UINT32_C(0xF64FFFCD),
        UINT32_C(0xD9785D60), UINT32_C(0xD8BA3757), UINT32_C(0xDAFC890E), UINT32_C(0xDB3EE339),
        UINT32_C(0xDE71F5BC), UINT32_C(0xDFB39F8B), UINT32_C(0xDDF521D2), UINT32_C(0xDC374BE5),
        UINT32_C(0xD76B0CD8), UINT32_C(0xD6A966EF), UINT32_C(0xD4EFD8B6), UINT32_C(0xD52DB281),
        UINT32_C(0xD062A404), UINT32_C(0xD1A0CE33), UINT32_C(0xD3E6706A), UINT32_C(0xD2241A5D),
        UINT32_C(0xC55EFE10), UINT32_C(0xC49C9427), UINT32_C(0xC6DA2A7E), UINT32_C(0xC7184049),
        UINT32_C(0xC25756CC), UINT32_C(0xC3953CFB), UINT32_C(0xC1D382A2), UINT32_C(0xC011E895),
        UINT32_C(0xCB4DAFA8), UINT32_C(0xCA8FC59F), UINT32_C(0xC8C97BC6), UINT32_C(0xC90B11F1),
        UINT32_C(0xCC440774), UINT32_C(0xCD866D43), UINT32_C(0xCFC0D31A), UINT32_C(0xCE02B92D),
        UINT32_C(0x91AF9640), UINT32_C(0x906DFC77), UINT32_C(0x922B422E), UINT32_C(0x93E92819),
        UINT32_C(0x96A63E9C), UINT32_C(0x976454AB), UINT32_C(0x9522EAF2), UINT32_C(0x94E080C5),
        UINT32_C(0x9FBCC7F8), UINT32_C(0x9E7EADCF), UINT32_C(0x9C381396), UINT32_C(0x9DFA79A1),
        UINT32_C(0x98B56F24), UINT32_C(0x99770513), UINT32_C(0x9B31BB4A), UINT32_C(0x9AF3D17D),
        UINT32_C(0x8D893530), UINT32_C(0x8C4B5F07), UINT32_C(0x8E0DE15E), UINT32_C(0x8FCF8B69),
        UINT32_C(0x8A809DEC), UINT32_C(0x8B42F7DB), UINT32_C(0x89044982), UINT32_C(0x88C623B5),
        UINT32_C(0x839A6488), UINT32_C(0x82580EBF), UINT32_C(0x801EB0E6), UINT32_C(0x81DCDAD1),
        UINT32_C(0x8493CC54), UINT32_C(0x8551A663), UINT32_C(0x8717183A), UINT32_C(0x86D5720D),
        UINT32_C(0xA9E2D0A0), UINT32_C(0xA820BA97), UINT32_C(0xAA6604CE), UINT32_C(0xABA46EF9),
        UINT32_C(0xAEEB787C), UINT32_C(0xAF29124B), UINT32_C(0xAD6FAC12), UINT32_C(0xACADC625),
        UINT32_C(0xA7F18118), UINT32_C(0xA633EB2F), UINT32_C(0xA4755576), UINT32_C(0xA5B73F41),
        UINT32_C(0xA0F829C4), UINT32_C(0xA13A43F3), UINT32_C(0xA37CFDAA), UINT32_C(0xA2BE979D),
        UINT32_C(0xB5C473D0), UINT32_C(0xB40619E7), UINT32_C(0xB640A7BE), UINT32_C(0xB782CD89),
        UINT32_C(0xB2CDDB0C), UINT32_C(0xB30FB13B), UINT32_C(0xB1490F62), UINT32_C(0xB08B6555),
        UINT32_C(0xBBD72268), UINT32_C(0xBA15485F), UINT32_C(0xB853F606), UINT32_C(0xB9919C31),
        UINT32_C(0xBCDE8AB4), UINT32_C(0xBD1CE083), UINT32_C(0xBF5A5EDA), UINT32_C(0xBE9834ED),
    }, {
        UINT32_C(0x00000000), UINT32_C(0xB8BC6765), UINT32_C(0xAA09C88B), UINT32_C(0x12B5AFEE),
        UINT32_C(0x8F629757), UINT32_C(0x37DEF032), UINT32_C(0x256B5FDC), UINT32_C(0x9DD738B9),
        UINT32_C(0xC5B428EF), UINT32_C(0x7D084F8A), UINT32_C(0x6FBDE064), UINT32_C(0xD7018701),
        UINT32_C(0x4AD6BFB8), UINT32_C(0xF26AD8DD), UINT32_C(0xE0DF7733), UINT32_C(0x58631056),
        UINT32_C(0x5019579F), UINT32_C(0xE8A530FA), UINT32_C(0xFA109F14), UINT32_C(0x42ACF871),
        UINT32_C(0xDF7BC0C8), UINT32_C(0x67C7A7AD), UINT32_C(0x75720843), UINT32_C(0xCDCE6F26),
        UINT32_C(0x95AD7F70), UINT32_C(0x2D111815), UINT32_C(0x3FA4B7FB), UINT32_C(0x8718D09E),
        UINT32_C(0x1ACFE827), UINT32_C(0xA2738F42), UINT32_C(0xB0C620AC), UINT32_C(0x087A47C9),
        UINT32_C(0xA032AF3E), UINT32_C(0x188EC85B), UINT32_C(0x0A3B67B5), UINT32_C(0xB28700D0),
        UINT32_C(0x2F503869), UINT32_C(0x97EC5F0C), UINT32_C(0x8559F0E2), UINT32_C(0x3DE59787),
        UINT32_C(0x658687D1), UINT32_C(0xDD3AE0B4), UINT32_C(0xCF8F4F5A), UINT32_C(0x7733283F),
        UINT32_C(0xEAE41086), UINT32_C(0x525877E3), UINT32_C(0x40EDD80D), UINT32_C(0xF851BF68),
        UINT32_C(0xF02BF8A1), UINT32_C(0x48979FC4), UINT32_C(0x5A22302A), UINT32_C(0xE29E574F),
        UINT32_C(0x7F496FF6), UINT32_C(0xC7F50893), UINT32_C(0xD540A77D), UINT32_C(0x6DFCC018),
        UINT32_C(0x359FD04E), UINT32_C(0x8D23B72B), UINT32_C(0x9F9618C5), UINT32_C(0x272A7FA0),
        UINT32_C(0xBAFD4719), UINT32_C(0x0241207C), UINT32_C(0x10F48F92), UINT32_C(0xA848E8F7),
        UINT32_C(0x9B14583D), UINT32_C(0x23A83F58), UINT32_C(0x311D90B6), UINT32_C(0x89A1F7D3),
        UINT32_C(0x1476CF6A), UINT32_C(0xACCAA80F), UINT32_C(0xBE7F07E1), UINT32_C(0x06C36084),
        UINT32_C(0x5EA070D2), UINT32_C(0xE61C17B7), UINT32_C(0xF4A9B859), UINT32_C(0x4C15DF3C),
        UINT32_C(0xD1C2E785), UINT32_C(0x697E80E0), UINT32_C(0x7BCB2F0E), UINT32_C(0xC377486B),
        UINT32_C(0xCB0D0FA2), UINT32_C(0x73B168C7), UINT32_C(0x6104C729), UINT32_C(0xD9B8A04C),
        UINT32_C(0x446F98F5), UINT32_C(0xFCD3FF90), UINT32_C(0xEE66507E), UINT32_C(0x56DA371B),
        UINT32_C(0x0EB9274D), UINT32_C(0xB6054028), UINT32_C(0xA4B0EFC6), UINT32_C(0x1C0C88A3),
        UINT32_C(0x81DBB01A), UINT32_C(0x3967D77F), UINT32_C(0x2BD27891), UINT32_C(0x936E1FF4),
        UINT32_C(0x3B26F703), UINT32_C(0x839A9066), UINT32_C(0x912F3F88), UINT32_C(0x299358ED),
        UINT32_C(0xB4446054), UINT32_C(0x0CF80731), UINT32_C(0x1E4DA8DF), UINT32_C(0xA6F1CFBA),
        UINT32_C(0xFE92DFEC), UINT32_C(0x462EB889), UINT32_C(0x549B1767), UINT32_C(0xEC277002),
        UINT32_C(0x71F048BB), UINT32_C(0xC94C2FDE), UINT32_C(0xDBF98030), UINT32_C(0x6345E755),
        UINT32_C(0x6B3FA09C), UINT32_C(0xD383C7F9), UINT32_C(0xC1366817), UINT32_C(0x798A0F72),
        UINT32_C(0xE45D37CB), UINT32_C(0x5CE150AE), UINT32_C(0x4E54FF40), UINT32_C(0xF6E89825),
        UINT32_C(0xAE8B8873), UINT32_C(0x1637EF16), UINT32_C(0x048240F8), UINT32_C(0xBC3E279D),
        UINT32_C(0x21E91F24), UINT32_C(0x99557841), UINT32_C(0x8BE0D7AF), UINT32_C(0x335CB0CA),
        UINT32_C(0xED59B63B), UINT32_C(0x55E5D15E), UINT32_C(0x47507EB0), UINT32_C(0xFFEC19D5),
        UINT32_C(0x623B216C), UINT32_C(0xDA874609), UINT32_C(0xC832E9E7), UINT32_C(0x708E8E82),
        UINT32_C(0x28ED9ED4), UINT32_C(0x9051F9B1), UINT32_C(0x82E4565F), UINT32_C(0x3A58313A),
        UINT32_C(0xA78F0983), UINT32_C(0x1F336EE6), UINT32_C(0x0D86C108), UINT32_C(0xB53AA66D),
        UINT32_C(0xBD40E1A4), UINT32_C(0x05FC86C1), UINT32_C(0x1749292F), UINT32_C(0xAFF54E4A),
        UINT32_C(0x322276F3), UINT32_C(0x8A9E1196), UINT32_C(0x982BBE78), UINT32_C(0x2097D91D),
        UINT32_C(0x78F4C94B), UINT32_C(0xC048AE2E), UINT32_C(0xD2FD01C0), UINT32_C(0x6A4166A5),
        UINT32_C(0xF7965E1C), UINT32_C(0x4F2A3979), UINT32_C(0x5D9F9697), UINT32_C(0xE523F1F2),
        UINT32_C(0x4D6B1905), UINT32_C(0xF5D77E60), UINT32_C(0xE762D18E), UINT32_C(0x5FDEB6EB),
        UINT32_C(0xC2098E52), UINT32_C(0x7AB5E937), UINT32_C(0x680046D9), UINT32_C(0xD0BC21BC),
        UINT32_C(0x88DF31EA), UINT32_C(0x3063568F), UINT32_C(0x22D6F961), UINT32_C(0x9A6A9E04),
        UINT32_C(0x07BDA6BD), UINT32_C(0xBF01C1D8), UINT32_C(0xADB46E36), UINT32_C(0x15080953),
        UINT32_C(0x1D724E9A), UINT32_C(0xA5CE29FF), UINT32_C(0xB77B8611), UINT32_C(0x0FC7E174),
        UINT32_C(0x9210D9CD), UINT32_C(0x2AACBEA8), UINT32_C(0x38191146), UINT32_C(0x80A57623),
        UINT32_C(0xD8C66675), UINT32_C(0x607A0110), UINT32_C(0x72CFAEFE), UINT32_C(0xCA73C99B),
        UINT32_C(0x57A4F122), UINT32_C(0xEF189647), UINT32_C(0xFDAD39A9), UINT32_C(0x45115ECC),
        UINT32_C(0x764DEE06), UINT32_C(0xCEF18963), UINT32_C(0xDC44268D), UINT32_C(0x64F841E8),
        UINT32_C(0xF92F7951), UINT32_C(0x41931E34), UINT32_C(0x5326B1DA), UINT32_C(0xEB9AD6BF),
        UINT32_C(0xB3F9C6E9), UINT32_C(0x0B45A18C), UINT32_C(0x19F00E62), UINT32_C(0xA14C6907),
        UINT32_C(0x3C9B51BE), UINT32_C(0x842736DB), UINT32_C(0x96929935), UINT32_C(0x2E2EFE50),
        UINT32_C(0x2654B999), UINT32_C(0x9EE8DEFC), UINT32_C(0x8C5D7112), UINT32_C(0x34E11677),
        UINT32_C(0xA9362ECE), UINT32_C(0x118A49AB), UINT32_C(0x033FE645), UINT32_C(0xBB838120),
        UINT32_C(0xE3E09176), UINT32_C(0x5B5CF613), UINT32_C(0x49E959FD), UINT32_C(0xF1553E98),
        UINT32_C(0x6C820621), UINT32_C(0xD43E6144), UINT32_C(0xC68BCEAA), UINT32_C(0x7E37A9CF),
        UINT32_C(0xD67F4138), UINT32_C(0x6EC3265D), UINT32_C(0x7C7689B3), UINT32_C(0xC4CAEED6),
        UINT32_C(0x591DD66F), UINT32_C(0xE1A1B10A), UINT32_C(0xF3141EE4), UINT32_C(0x4BA87981),
        UINT32_C(0x13CB69D7), UINT32_C(0xAB770EB2), UINT32_C(0xB9C2A15C), UINT32_C(0x017EC639),
        UINT32_C(0x9CA9FE80), UINT32_C(0x241599E5), UINT32_C(0x36A0360B), UINT32_C(0x8E1C516E),
        UINT32_C(0x866616A7), UINT32_C(0x3EDA71C2), UINT32_C(0x2C6FDE2C), UINT32_C(0x94D3B949),
        UINT32_C(0x090481F0), UINT32_C(0xB1B8E695), UINT32_C(0xA30D497B), UINT32_C(0x1BB12E1E),
        UINT32_C(0x43D23E48), UINT32_C(0xFB6E592D), UINT32_C(0xE9DBF6C3), UINT32_C(0x516791A6),
        UINT32_C(0xCCB0A91F), UINT32_C(0x740CCE7A), UINT32_C(0x66B96194), UINT32_C(0xDE0506F1),
    }};
    uint32_t crc = UINT32_MAX;
    size_t index = 0U;

    if (data == NULL && length != 0U)
        return 0U;
    while (length - index >= 4U) {
        uint32_t word = crc ^ load_le32(data + index);

        crc = table[3][word & 0xFFU] ^
              table[2][(word >> 8) & 0xFFU] ^
              table[1][(word >> 16) & 0xFFU] ^
              table[0][word >> 24];
        index += 4U;
    }
    while (index < length) {
        crc = (crc >> 8) ^ table[0][(crc ^ data[index]) & 0xFFU];
        ++index;
    }
    return crc ^ UINT32_MAX;
}

static void encode_event(uint8_t *target, const phase06j_event_v1 *event)
{
    store_le64(target + 0U, event->event_id);
    store_le32(target + 8U, event->first_frame_id);
    store_le32(target + 12U, event->last_seen_frame_id);
    store_le64(target + 16U, event->seen_count);
    target[24U] = event->state;
    target[25U] = event->observed_this_frame;
    store_le16(target + 26U, 0U);
    store_le16(target + 28U, event->candidate.start_shifted_bin);
    store_le16(target + 30U, event->candidate.end_shifted_bin);
    store_le16(target + 32U, event->candidate.peak_shifted_bin);
    store_le16(target + 34U, event->candidate.coarse_span_bins);
    target[36U] = event->candidate.pfa_select;
    target[37U] = event->candidate.flags;
    store_le16(target + 38U, 0U);
    store_le64(target + 40U, event->candidate.peak_power_uq28_30);
    store_le64(target + 48U, event->candidate.regional_noise_uq28_30);
    store_le64(target + 56U, event->candidate.threshold_uq32_30);
    store_le32(target + 64U, 0U);
}

static int decode_event(const uint8_t *source, phase06j_event_v1 *event)
{
    memset(event, 0, sizeof(*event));
    if (load_le16(source + 26U) != 0U || load_le16(source + 38U) != 0U ||
        load_le32(source + 64U) != 0U)
        return -1;
    event->event_id = load_le64(source + 0U);
    event->first_frame_id = load_le32(source + 8U);
    event->last_seen_frame_id = load_le32(source + 12U);
    event->seen_count = load_le64(source + 16U);
    event->state = source[24U];
    event->observed_this_frame = source[25U];
    event->candidate.start_shifted_bin = load_le16(source + 28U);
    event->candidate.end_shifted_bin = load_le16(source + 30U);
    event->candidate.peak_shifted_bin = load_le16(source + 32U);
    event->candidate.coarse_span_bins = load_le16(source + 34U);
    event->candidate.pfa_select = source[36U];
    event->candidate.flags = source[37U];
    event->candidate.peak_power_uq28_30 = load_le64(source + 40U);
    event->candidate.regional_noise_uq28_30 = load_le64(source + 48U);
    event->candidate.threshold_uq32_30 = load_le64(source + 56U);
    return 0;
}

static void encode_result(uint8_t *target, const phase06j_frame_result_v1 *result)
{
    size_t index;

    memset(target, 0, P0_ED_RESULT_BYTES);
    store_le32(target + 0U, result->frame_id);
    store_le16(target + 4U, result->active_count);
    store_le16(target + 6U, result->ended_count);
    store_le16(target + 8U, result->dropped_candidates);
    target[10U] = result->reset_applied;
    store_le64(target + 12U, result->evicted_history_count);
    for (index = 0U; index < PHASE06J_MAX_ACTIVE_TRACKS; ++index)
        encode_event(target + 20U + index * 68U, &result->active[index]);
    for (index = 0U; index < PHASE06J_MAX_ACTIVE_TRACKS; ++index)
        encode_event(target + 4372U + index * 68U, &result->ended[index]);
}

static size_t compact_result_bytes(const phase06j_frame_result_v1 *result)
{
    return P0_ED_RESULT_HEADER_BYTES +
           ((size_t)result->active_count + (size_t)result->ended_count) *
               P0_ED_EVENT_BYTES;
}

static void encode_result_compact(uint8_t *target,
                                  const phase06j_frame_result_v1 *result)
{
    size_t index;
    size_t offset = P0_ED_RESULT_HEADER_BYTES;

    memset(target, 0, compact_result_bytes(result));
    store_le32(target + 0U, result->frame_id);
    store_le16(target + 4U, result->active_count);
    store_le16(target + 6U, result->ended_count);
    store_le16(target + 8U, result->dropped_candidates);
    target[10U] = result->reset_applied;
    store_le64(target + 12U, result->evicted_history_count);
    for (index = 0U; index < result->active_count; ++index) {
        encode_event(target + offset, &result->active[index]);
        offset += P0_ED_EVENT_BYTES;
    }
    for (index = 0U; index < result->ended_count; ++index) {
        encode_event(target + offset, &result->ended[index]);
        offset += P0_ED_EVENT_BYTES;
    }
}

static int decode_result(const uint8_t *source, phase06j_frame_result_v1 *result)
{
    size_t index;

    memset(result, 0, sizeof(*result));
    if (source[11U] != 0U)
        return -1;
    result->frame_id = load_le32(source + 0U);
    result->active_count = load_le16(source + 4U);
    result->ended_count = load_le16(source + 6U);
    result->dropped_candidates = load_le16(source + 8U);
    result->reset_applied = source[10U];
    result->evicted_history_count = load_le64(source + 12U);
    if (result->active_count > PHASE06J_MAX_ACTIVE_TRACKS ||
        result->ended_count > PHASE06J_MAX_ACTIVE_TRACKS)
        return -1;
    for (index = 0U; index < PHASE06J_MAX_ACTIVE_TRACKS; ++index) {
        if (decode_event(source + 20U + index * 68U, &result->active[index]) != 0)
            return -1;
    }
    for (index = 0U; index < PHASE06J_MAX_ACTIVE_TRACKS; ++index) {
        if (decode_event(source + 4372U + index * 68U, &result->ended[index]) != 0)
            return -1;
    }
    return 0;
}

static int decode_result_compact(const uint8_t *source, size_t source_bytes,
                                 phase06j_frame_result_v1 *result)
{
    size_t index;
    size_t offset = P0_ED_RESULT_HEADER_BYTES;

    if (source_bytes < P0_ED_RESULT_HEADER_BYTES || source[11U] != 0U)
        return -1;
    memset(result, 0, sizeof(*result));
    result->frame_id = load_le32(source + 0U);
    result->active_count = load_le16(source + 4U);
    result->ended_count = load_le16(source + 6U);
    result->dropped_candidates = load_le16(source + 8U);
    result->reset_applied = source[10U];
    result->evicted_history_count = load_le64(source + 12U);
    if (result->active_count > PHASE06J_MAX_ACTIVE_TRACKS ||
        result->ended_count > PHASE06J_MAX_ACTIVE_TRACKS ||
        source_bytes != compact_result_bytes(result))
        return -1;
    for (index = 0U; index < result->active_count; ++index) {
        if (decode_event(source + offset, &result->active[index]) != 0)
            return -1;
        offset += P0_ED_EVENT_BYTES;
    }
    for (index = 0U; index < result->ended_count; ++index) {
        if (decode_event(source + offset, &result->ended[index]) != 0)
            return -1;
        offset += P0_ED_EVENT_BYTES;
    }
    return 0;
}

static void encode_parameter_field(uint8_t *target, const p0_parameter_field_t *field)
{
    target[0U] = field->state;
    target[1U] = field->reason;
    store_le16(target + 2U, 0U);
    store_le_double(target + 4U, field->value);
}

static int parameter_field_valid(const p0_parameter_field_t *field)
{
    return field->state <= P0_PARAMETER_FIELD_UNCERTAIN &&
           field->reason <= P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY &&
           isfinite(field->value) &&
           (field->state != P0_PARAMETER_FIELD_VALID ||
            field->reason == P0_PARAMETER_REASON_NONE);
}

static int decode_parameter_field(const uint8_t *source, p0_parameter_field_t *field)
{
    if (source[0U] > P0_PARAMETER_FIELD_UNCERTAIN ||
        source[1U] > P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY ||
        load_le16(source + 2U) != 0U)
        return -1;
    field->state = source[0U];
    field->reason = source[1U];
    field->value = load_le_double(source + 4U);
    return parameter_field_valid(field) ? 0 : -1;
}

static void encode_parameter_result(uint8_t *target,
                                    const p0_parameter_result_t *result)
{
    memset(target, 0, P0_ED_PARAMETER_RESULT_BYTES);
    store_le64(target + 0U, result->intent_id);
    store_le64(target + 8U, result->event_id);
    store_le32(target + 16U, result->frame_id);
    target[20U] = result->observation_count;
    encode_parameter_field(target + 24U, &result->emission_center_frequency_hz);
    encode_parameter_field(target + 36U, &result->lower_occupied_edge_hz);
    encode_parameter_field(target + 48U, &result->upper_occupied_edge_hz);
    encode_parameter_field(target + 60U, &result->occupied_bandwidth_hz);
    encode_parameter_field(target + 72U, &result->channel_power_dbfs);
    encode_parameter_field(target + 84U, &result->snr_estimate_db);
    store_le_double(target + 96U, isfinite(result->reference_difference_db)
                                      ? result->reference_difference_db : 0.0);
    store_le_double(target + 104U, isfinite(result->detection_significance)
                                       ? result->detection_significance : 0.0);
    store_le_double(target + 112U, isfinite(result->center_uncertainty_bins)
                                       ? result->center_uncertainty_bins : 0.0);
    store_le_double(target + 120U, isfinite(result->temporal_edge_range_bins)
                                       ? result->temporal_edge_range_bins : 0.0);
}

static int decode_parameter_result(const uint8_t *source,
                                   p0_parameter_result_t *result)
{
    if (source[21U] != 0U || source[22U] != 0U || source[23U] != 0U ||
        source[20U] > P0_PARAMETER_REQUIRED_FRAMES)
        return -1;
    memset(result, 0, sizeof(*result));
    result->intent_id = load_le64(source + 0U);
    result->event_id = load_le64(source + 8U);
    result->frame_id = load_le32(source + 16U);
    result->observation_count = source[20U];
    if (decode_parameter_field(source + 24U, &result->emission_center_frequency_hz) != 0 ||
        decode_parameter_field(source + 36U, &result->lower_occupied_edge_hz) != 0 ||
        decode_parameter_field(source + 48U, &result->upper_occupied_edge_hz) != 0 ||
        decode_parameter_field(source + 60U, &result->occupied_bandwidth_hz) != 0 ||
        decode_parameter_field(source + 72U, &result->channel_power_dbfs) != 0 ||
        decode_parameter_field(source + 84U, &result->snr_estimate_db) != 0)
        return -1;
    result->reference_difference_db = load_le_double(source + 96U);
    result->detection_significance = load_le_double(source + 104U);
    result->center_uncertainty_bins = load_le_double(source + 112U);
    result->temporal_edge_range_bins = load_le_double(source + 120U);
    return isfinite(result->reference_difference_db) &&
                   isfinite(result->detection_significance) &&
                   isfinite(result->center_uncertainty_bins) &&
                   isfinite(result->temporal_edge_range_bins)
               ? 0 : -1;
}

static int parameter_result_valid(const p0_parameter_result_t *result)
{
    return result->intent_id != 0U && result->event_id != 0U &&
           parameter_field_valid(&result->emission_center_frequency_hz) &&
           parameter_field_valid(&result->lower_occupied_edge_hz) &&
           parameter_field_valid(&result->upper_occupied_edge_hz) &&
           parameter_field_valid(&result->occupied_bandwidth_hz) &&
           parameter_field_valid(&result->channel_power_dbfs) &&
           parameter_field_valid(&result->snr_estimate_db);
}

int p0_parameter_batch_decode(const uint8_t *bytes, size_t size,
                              p0_parameter_batch_request_t *request)
{
    unsigned int width;
    if (bytes == NULL || request == NULL || (size != P0_PARAMETER_BATCH_REQUEST_BYTES && size != P0_PARAMETER_BATCH_EXTENDED_REQUEST_BYTES) ||
        memcmp(bytes, "P0PM", 4U) != 0 ||
        (load_le16(bytes + 4U) != 1U && load_le16(bytes + 4U) != 2U &&
         load_le16(bytes + 4U) != 3U && load_le16(bytes + 4U) != 4U && load_le16(bytes + 4U) != 5U) ||
        (((load_le16(bytes + 4U) == 3U || load_le16(bytes + 4U) == 5U)) != (size == P0_PARAMETER_BATCH_EXTENDED_REQUEST_BYTES)) ||
        load_le16(bytes + 6U) != P0_PARAMETER_BATCH_HEADER_BYTES ||
        load_le32(bytes + 44U) != 0U || load_le32(bytes + 48U) != 0U ||
        load_le32(bytes + 52U) != 0U || load_le32(bytes + 56U) != 0U ||
        load_le32(bytes + 60U) != p0_ed_crc32(bytes, 60U) ||
        load_le32(bytes + 40U) != p0_ed_crc32(bytes + 64U, size - 64U)) return -1;
    memset(request, 0, sizeof(*request));
    request->token = load_le32(bytes + 8U);
    request->first_frame_id = load_le32(bytes + 12U);
    request->sample_rate_hz = load_le32(bytes + 16U);
    request->center_frequency_hz = (int64_t)load_le64(bytes + 20U);
    request->event_id = load_le64(bytes + 28U);
    request->lower_bin = load_le16(bytes + 36U);
    request->upper_bin = load_le16(bytes + 38U);
    request->iq_crc32 = load_le32(bytes + 40U);
    request->iq = bytes + 64U;
    request->version = load_le16(bytes + 4U);
    request->frame_count = request->version == 3U || request->version == 5U ? 16U : 4U;
    request->locked_channel_power = request->version == 4U ? 1U : 0U;
    width = (unsigned int)request->upper_bin - request->lower_bin + 1U;
    if (request->token == 0U || request->event_id == 0U || request->sample_rate_hz == 0U ||
        request->sample_rate_hz > 20000000U || request->first_frame_id > UINT32_MAX - (request->frame_count - 1U) ||
        request->lower_bin < 56U || request->upper_bin > 4039U ||
        request->lower_bin > request->upper_bin || width < 8U ||
        width > (load_le16(bytes + 4U) == 1U ? 512U : P0_PARAMETER_MAXIMUM_SPAN_BINS)) return -1;
    return 0;
}

int p0_parameter_batch_response_encode(const p0_parameter_batch_request_t *request,
    uint32_t status, uint32_t elapsed_us, uint32_t generation,
    const p0_parameter_result_t *result, uint8_t *bytes)
{
    if (request == NULL || bytes == NULL || status > 5U) return -1;
    if (status == 0U && (result == NULL || !parameter_result_valid(result) ||
        result->observation_count != request->frame_count ||
        result->frame_id != request->first_frame_id + request->frame_count - 1U ||
        result->intent_id != request->token || result->event_id != request->event_id ||
        result->carrier_line_frequency_hz.state > P0_PARAMETER_FIELD_NOT_OBSERVED ||
        result->carrier_line_frequency_hz.reason > P0_PARAMETER_REASON_CARRIER_LOW_SNR ||
        !isfinite(result->carrier_line_frequency_hz.value) ||
        (result->carrier_line_frequency_hz.state == P0_PARAMETER_FIELD_VALID &&
         result->carrier_line_frequency_hz.reason != P0_PARAMETER_REASON_NONE))) return -1;
    memset(bytes, 0, P0_PARAMETER_BATCH_RESPONSE_BYTES);
    memcpy(bytes, "P0PR", 4U);
    store_le16(bytes + 4U, request->version >= 3U ? request->version : 2U);
    store_le16(bytes + 6U, P0_PARAMETER_BATCH_RESPONSE_BYTES);
    store_le32(bytes + 8U, request->token);
    store_le32(bytes + 12U, status);
    if (status == 0U) {
        encode_parameter_result(bytes + 16U, result);
        encode_parameter_field(bytes + 144U, &result->carrier_line_frequency_hz);
        if (request->version == 5U && result->carrier_line_frequency_hz.state != P0_PARAMETER_FIELD_VALID &&
            result->recovered_carrier_frequency_hz.state == P0_PARAMETER_FIELD_VALID) {
            if ((result->carrier_recovery_order != 2U && result->carrier_recovery_order != 4U) ||
                result->recovered_carrier_frequency_hz.reason != P0_PARAMETER_REASON_NONE ||
                !isfinite(result->recovered_carrier_frequency_hz.value)) return -1;
            encode_parameter_field(bytes + 144U, &result->recovered_carrier_frequency_hz);
            bytes[37U] = result->carrier_recovery_order;
        }
        store_le32(bytes + 156U, elapsed_us);
        store_le32(bytes + 160U, request->iq_crc32);
        store_le32(bytes + 164U, generation);
        store_le32(bytes + 168U, 4096U);
    }
    store_le32(bytes + 172U, p0_ed_crc32(bytes, 172U));
    return 0;
}

int p0_parameter_batch_response_check(const uint8_t *bytes, size_t size, uint32_t token)
{
    return bytes != NULL && size == P0_PARAMETER_BATCH_RESPONSE_BYTES &&
        memcmp(bytes, "P0PR", 4U) == 0 &&
        (load_le16(bytes + 4U) == 1U || load_le16(bytes + 4U) == 2U ||
         load_le16(bytes + 4U) == 3U || load_le16(bytes + 4U) == 4U || load_le16(bytes + 4U) == 5U) &&
        load_le16(bytes + 6U) == size && load_le32(bytes + 8U) == token &&
        load_le32(bytes + 12U) <= 5U &&
        bytes[38U] == 0U && bytes[39U] == 0U &&
        (bytes[37U] == 0U || (load_le16(bytes + 4U) == 5U &&
         (bytes[37U] == 2U || bytes[37U] == 4U) &&
         load_le32(bytes + 12U) == 0U && bytes[144U] == P0_PARAMETER_FIELD_VALID)) &&
        load_le32(bytes + 172U) == p0_ed_crc32(bytes, 172U) ? 0 : -1;
}

int p0_df_batch_decode(const uint8_t *bytes, size_t size,
                       p0_df_batch_request_t *request)
{
    uint32_t count;
    size_t index;
    if (bytes == NULL || request == NULL || size != P0_DF_BATCH_REQUEST_BYTES ||
        memcmp(bytes, "P0DF", 4U) != 0 || load_le16(bytes + 4U) != 1U ||
        load_le16(bytes + 6U) != P0_DF_BATCH_HEADER_BYTES ||
        load_le32(bytes + 8U) != P0_DF_BATCH_REQUEST_BYTES ||
        load_le32(bytes + 12U) == 0U || load_le32(bytes + 24U) != 0U ||
        load_le32(bytes + 20U) !=
            p0_ed_crc32(bytes + P0_DF_BATCH_HEADER_BYTES,
                        P0_DF_BATCH_REQUEST_BYTES - P0_DF_BATCH_HEADER_BYTES) ||
        load_le32(bytes + 28U) != p0_ed_crc32(bytes, 28U))
        return -1;
    count = load_le32(bytes + 16U);
    if (count == 0U || count > P0_DF_MAX_MEASUREMENTS)
        return -1;
    memset(request, 0, sizeof(*request));
    request->token = load_le32(bytes + 12U);
    request->measurement_count = count;
    for (index = 0U; index < count; ++index) {
        const uint8_t *source = bytes + P0_DF_BATCH_HEADER_BYTES +
                                index * P0_DF_BATCH_MEASUREMENT_BYTES;
        p0_df_measurement_t *target = &request->measurements[index];
        target->angle_deg = load_le_double(source + 0U);
        target->relative_power_db = load_le_double(source + 8U);
        target->frequency_hz = load_le_double(source + 16U);
        target->confidence = load_le_double(source + 24U);
        target->power_spread_db = load_le_double(source + 32U);
        target->observation_count = load_le32(source + 40U);
        target->frame_id = load_le32(source + 44U);
        target->channel_bandwidth_hz = load_le_double(source + 48U);
        target->receiver_binding_hash = load_le64(source + 56U);
        target->channel_bandwidth_valid = 1U;
        target->receiver_binding_valid = 1U;
        target->frame_id_valid = 1U;
    }
    for (index = P0_DF_BATCH_HEADER_BYTES +
                 (size_t)count * P0_DF_BATCH_MEASUREMENT_BYTES;
         index < P0_DF_BATCH_REQUEST_BYTES; ++index) {
        if (bytes[index] != 0U)
            return -1;
    }
    return 0;
}

int p0_df_batch_response_encode(const p0_df_batch_request_t *request,
                                uint32_t service_status,
                                const p0_df_result_t *result,
                                uint8_t *bytes)
{
    uint32_t flags = 0U;
    if (request == NULL || bytes == NULL ||
        service_status > P0_DF_BATCH_COMPUTATION_FAILED ||
        (service_status == P0_DF_BATCH_OK && result == NULL))
        return -1;
    memset(bytes, 0, P0_DF_BATCH_RESPONSE_BYTES);
    memcpy(bytes, "P0FR", 4U);
    store_le16(bytes + 4U, 1U);
    store_le16(bytes + 6U, P0_DF_BATCH_RESPONSE_BYTES);
    store_le32(bytes + 8U, request->token);
    store_le32(bytes + 12U, service_status);
    if (service_status == P0_DF_BATCH_OK) {
        if (result->status > P0_DF_STATUS_LOB_READY ||
            !isfinite(result->raw_maximum_angle_deg) ||
            !isfinite(result->estimated_angle_deg) ||
            !isfinite(result->peak_power_db) || !isfinite(result->confidence) ||
            !isfinite(result->maximum_angular_gap_deg) ||
            !isfinite(result->peak_prominence_db) ||
            (result->front_to_back_valid && !isfinite(result->front_to_back_db)) ||
            (result->angular_sampling_rms_valid &&
             !isfinite(result->angular_sampling_rms_deg)))
            return -1;
        if (result->front_to_back_valid) flags |= 1U;
        if (result->angular_sampling_rms_valid) flags |= 2U;
        store_le32(bytes + 16U, (uint32_t)result->status);
        store_le32(bytes + 20U, result->measurement_count);
        store_le32(bytes + 24U, result->distinct_angle_count);
        store_le32(bytes + 28U, flags);
        store_le_double(bytes + 32U, result->raw_maximum_angle_deg);
        store_le_double(bytes + 40U, result->estimated_angle_deg);
        store_le_double(bytes + 48U, result->peak_power_db);
        store_le_double(bytes + 56U, result->confidence);
        store_le_double(bytes + 64U, result->maximum_angular_gap_deg);
        store_le_double(bytes + 72U, result->peak_prominence_db);
        if (result->front_to_back_valid)
            store_le_double(bytes + 80U, result->front_to_back_db);
        if (result->angular_sampling_rms_valid)
            store_le_double(bytes + 88U, result->angular_sampling_rms_deg);
    }
    store_le32(bytes + 100U, p0_ed_crc32(bytes, 100U));
    return 0;
}

int p0_df_batch_response_check(const uint8_t *bytes, size_t size, uint32_t token)
{
    return bytes != NULL && size == P0_DF_BATCH_RESPONSE_BYTES &&
        memcmp(bytes, "P0FR", 4U) == 0 && load_le16(bytes + 4U) == 1U &&
        load_le16(bytes + 6U) == P0_DF_BATCH_RESPONSE_BYTES &&
        load_le32(bytes + 8U) == token &&
        load_le32(bytes + 12U) <= P0_DF_BATCH_COMPUTATION_FAILED &&
        load_le32(bytes + 100U) == p0_ed_crc32(bytes, 100U) ? 0 : -1;
}

int p0_ed_request_encode(uint32_t frame_id, uint32_t flags, const uint8_t *iq,
                         size_t iq_bytes, uint8_t *message, size_t capacity)
{
    if (iq == NULL || message == NULL || iq_bytes != P0_ED_IQ_FRAME_BYTES ||
        capacity < P0_ED_REQUEST_BYTES || (flags & ~P0_ED_REQUEST_FLAGS_ALLOWED) != 0U)
        return -1;
    memset(message, 0, P0_ED_REQUEST_HEADER_BYTES);
    store_le32(message + 0U, P0_ED_REQUEST_MAGIC);
    store_le16(message + 4U, P0_ED_SERVICE_ABI_VERSION);
    store_le16(message + 6U, P0_ED_REQUEST_HEADER_BYTES);
    store_le32(message + 8U, P0_ED_REQUEST_BYTES);
    store_le32(message + 12U, frame_id);
    store_le32(message + 16U, P0_ED_IQ_FRAME_BYTES);
    store_le32(message + 20U, flags);
    store_le32(message + 24U, p0_ed_crc32(iq, iq_bytes));
    store_le32(message + 28U, p0_ed_crc32(message, 28U));
    memcpy(message + P0_ED_REQUEST_HEADER_BYTES, iq, iq_bytes);
    return 0;
}

int p0_ed_request_encode_compact(uint32_t frame_id, uint32_t flags,
                                 const uint8_t *iq, size_t iq_bytes,
                                 uint8_t *message, size_t capacity)
{
    if (iq == NULL || message == NULL || iq_bytes != P0_ED_IQ_FRAME_BYTES ||
        capacity < P0_ED_REQUEST_BYTES_V3 ||
        (flags & ~P0_ED_REQUEST_FLAGS_V3_ALLOWED) != 0U)
        return -1;
    memset(message, 0, P0_ED_REQUEST_HEADER_BYTES_V3);
    store_le32(message + 0U, P0_ED_REQUEST_MAGIC);
    store_le16(message + 4U, P0_ED_SERVICE_ABI_VERSION_V3);
    store_le16(message + 6U, P0_ED_REQUEST_HEADER_BYTES_V3);
    store_le32(message + 8U, P0_ED_REQUEST_BYTES_V3);
    store_le32(message + 12U, frame_id);
    store_le32(message + 16U, P0_ED_IQ_FRAME_BYTES);
    store_le32(message + 20U, flags);
    store_le32(message + 24U, 0U);
    store_le32(message + 28U, p0_ed_crc32(message, 28U));
    memcpy(message + P0_ED_REQUEST_HEADER_BYTES_V3, iq, iq_bytes);
    return 0;
}

static int runtime_iq_bytes_valid(size_t iq_bytes)
{
    return iq_bytes == 8192U || iq_bytes == 16384U || iq_bytes == 32768U;
}

int p0_ed_request_encode_runtime(uint32_t frame_id, uint32_t flags,
                                 const uint8_t *iq, size_t iq_bytes,
                                 uint8_t *message, size_t capacity)
{
    size_t total = P0_ED_REQUEST_HEADER_BYTES_V4 + iq_bytes;

    if (iq == NULL || message == NULL || !runtime_iq_bytes_valid(iq_bytes) ||
        capacity < total || (flags & ~P0_ED_REQUEST_FLAGS_V4_ALLOWED) != 0U)
        return -1;
    memset(message, 0, P0_ED_REQUEST_HEADER_BYTES_V4);
    store_le32(message + 0U, P0_ED_REQUEST_MAGIC);
    store_le16(message + 4U, P0_ED_SERVICE_ABI_VERSION_V4);
    store_le16(message + 6U, P0_ED_REQUEST_HEADER_BYTES_V4);
    store_le32(message + 8U, (uint32_t)total);
    store_le32(message + 12U, frame_id);
    store_le32(message + 16U, (uint32_t)iq_bytes);
    store_le32(message + 20U, flags);
    store_le32(message + 24U, 0U);
    store_le32(message + 28U, p0_ed_crc32(message, 28U));
    memcpy(message + P0_ED_REQUEST_HEADER_BYTES_V4, iq, iq_bytes);
    return 0;
}

int p0_ed_request_encode_v2(uint32_t frame_id, uint32_t flags,
                            uint64_t sample_rate_hz, int64_t center_frequency_hz,
                            uint64_t parameter_intent_id, uint64_t parameter_event_id,
                            uint16_t parameter_lower_shifted_bin,
                            uint16_t parameter_upper_shifted_bin,
                            const uint8_t *iq, size_t iq_bytes,
                            uint8_t *message, size_t capacity)
{
    int parameter_requested = (flags & P0_ED_REQUEST_FLAG_PARAMETER) != 0U;

    if (iq == NULL || message == NULL || iq_bytes != P0_ED_IQ_FRAME_BYTES ||
        capacity < P0_ED_REQUEST_BYTES_V2 ||
        (flags & ~P0_ED_REQUEST_FLAGS_V2_ALLOWED) != 0U ||
        ((flags & P0_ED_REQUEST_FLAG_PARAMETER_START) != 0U && !parameter_requested) ||
        (parameter_requested &&
         (sample_rate_hz == 0U || parameter_intent_id == 0U || parameter_event_id == 0U ||
          parameter_lower_shifted_bin > parameter_upper_shifted_bin)) ||
        (!parameter_requested &&
         (sample_rate_hz != 0U || center_frequency_hz != 0 || parameter_intent_id != 0U ||
          parameter_event_id != 0U || parameter_lower_shifted_bin != 0U ||
          parameter_upper_shifted_bin != 0U)))
        return -1;
    memset(message, 0, P0_ED_REQUEST_HEADER_BYTES_V2);
    store_le32(message + 0U, P0_ED_REQUEST_MAGIC);
    store_le16(message + 4U, P0_ED_SERVICE_ABI_VERSION_V2);
    store_le16(message + 6U, P0_ED_REQUEST_HEADER_BYTES_V2);
    store_le32(message + 8U, P0_ED_REQUEST_BYTES_V2);
    store_le32(message + 12U, frame_id);
    store_le32(message + 16U, P0_ED_IQ_FRAME_BYTES);
    store_le32(message + 20U, flags);
    store_le32(message + 24U, p0_ed_crc32(iq, iq_bytes));
    store_le64(message + 32U, sample_rate_hz);
    store_le64(message + 40U, (uint64_t)center_frequency_hz);
    store_le64(message + 48U, parameter_intent_id);
    store_le64(message + 56U, parameter_event_id);
    store_le16(message + 64U, parameter_lower_shifted_bin);
    store_le16(message + 66U, parameter_upper_shifted_bin);
    store_le32(message + 76U, p0_ed_crc32(message, 76U));
    memcpy(message + P0_ED_REQUEST_HEADER_BYTES_V2, iq, iq_bytes);
    return 0;
}

int p0_ed_request_decode(const uint8_t *message, size_t message_bytes,
                         p0_ed_request_view_t *request)
{
    uint16_t version;
    uint32_t flags;

    if (message == NULL || request == NULL || message_bytes < P0_ED_REQUEST_HEADER_BYTES_V1 ||
        load_le32(message + 0U) != P0_ED_REQUEST_MAGIC)
        return -1;
    memset(request, 0, sizeof(*request));
    version = load_le16(message + 4U);
    if (version == P0_ED_SERVICE_ABI_VERSION_V1 ||
        version == P0_ED_SERVICE_ABI_VERSION_V3) {
        if (message_bytes != P0_ED_REQUEST_BYTES_V1 ||
            load_le16(message + 6U) != P0_ED_REQUEST_HEADER_BYTES_V1 ||
            load_le32(message + 8U) != P0_ED_REQUEST_BYTES_V1 ||
            load_le32(message + 16U) != P0_ED_IQ_FRAME_BYTES ||
            load_le32(message + 28U) != p0_ed_crc32(message, 28U) ||
            (version == P0_ED_SERVICE_ABI_VERSION_V1
                 ? load_le32(message + 24U) !=
                       p0_ed_crc32(message + P0_ED_REQUEST_HEADER_BYTES_V1,
                                   P0_ED_IQ_FRAME_BYTES)
                 : load_le32(message + 24U) != 0U))
            return -1;
        flags = load_le32(message + 20U);
        if ((flags & ~(version == P0_ED_SERVICE_ABI_VERSION_V1
                           ? P0_ED_REQUEST_FLAGS_V1_ALLOWED
                           : P0_ED_REQUEST_FLAGS_V3_ALLOWED)) != 0U)
            return -1;
        request->iq = message + P0_ED_REQUEST_HEADER_BYTES_V1;
        request->iq_bytes = P0_ED_IQ_FRAME_BYTES;
    } else if (version == P0_ED_SERVICE_ABI_VERSION_V4) {
        uint32_t iq_bytes = load_le32(message + 16U);
        if (!runtime_iq_bytes_valid(iq_bytes) ||
            load_le16(message + 6U) != P0_ED_REQUEST_HEADER_BYTES_V4 ||
            load_le32(message + 8U) != P0_ED_REQUEST_HEADER_BYTES_V4 + iq_bytes ||
            message_bytes != P0_ED_REQUEST_HEADER_BYTES_V4 + (size_t)iq_bytes ||
            load_le32(message + 24U) != 0U ||
            load_le32(message + 28U) != p0_ed_crc32(message, 28U))
            return -1;
        flags = load_le32(message + 20U);
        if ((flags & ~P0_ED_REQUEST_FLAGS_V4_ALLOWED) != 0U)
            return -1;
        request->iq = message + P0_ED_REQUEST_HEADER_BYTES_V4;
        request->iq_bytes = iq_bytes;
    } else if (version == P0_ED_SERVICE_ABI_VERSION_V2) {
        if (message_bytes != P0_ED_REQUEST_BYTES_V2 ||
            load_le16(message + 6U) != P0_ED_REQUEST_HEADER_BYTES_V2 ||
            load_le32(message + 8U) != P0_ED_REQUEST_BYTES_V2 ||
            load_le32(message + 16U) != P0_ED_IQ_FRAME_BYTES ||
            load_le32(message + 28U) != 0U || load_le32(message + 68U) != 0U ||
            load_le32(message + 72U) != 0U ||
            load_le32(message + 76U) != p0_ed_crc32(message, 76U) ||
            load_le32(message + 24U) !=
                p0_ed_crc32(message + P0_ED_REQUEST_HEADER_BYTES_V2,
                            P0_ED_IQ_FRAME_BYTES))
            return -1;
        flags = load_le32(message + 20U);
        if ((flags & ~P0_ED_REQUEST_FLAGS_V2_ALLOWED) != 0U ||
            ((flags & P0_ED_REQUEST_FLAG_PARAMETER_START) != 0U &&
             (flags & P0_ED_REQUEST_FLAG_PARAMETER) == 0U))
            return -1;
        request->sample_rate_hz = load_le64(message + 32U);
        request->center_frequency_hz = (int64_t)load_le64(message + 40U);
        request->parameter_intent_id = load_le64(message + 48U);
        request->parameter_event_id = load_le64(message + 56U);
        request->parameter_lower_shifted_bin = load_le16(message + 64U);
        request->parameter_upper_shifted_bin = load_le16(message + 66U);
        if ((flags & P0_ED_REQUEST_FLAG_PARAMETER) != 0U) {
            unsigned int width = (unsigned int)request->parameter_upper_shifted_bin -
                                 request->parameter_lower_shifted_bin + 1U;
            if (request->sample_rate_hz == 0U || request->parameter_intent_id == 0U ||
                request->parameter_event_id == 0U ||
                request->parameter_lower_shifted_bin > request->parameter_upper_shifted_bin ||
                width < P0_PARAMETER_MINIMUM_SPAN_BINS ||
                width > 512U || /* Legacy per-frame ABI retains its original contract. */
                request->parameter_lower_shifted_bin <
                    20U + P0_PARAMETER_LOCAL_PADDING ||
                request->parameter_upper_shifted_bin >
                    4075U - P0_PARAMETER_LOCAL_PADDING)
                return -1;
        } else if (request->sample_rate_hz != 0U || request->center_frequency_hz != 0 ||
                   request->parameter_intent_id != 0U || request->parameter_event_id != 0U ||
                   request->parameter_lower_shifted_bin != 0U ||
                   request->parameter_upper_shifted_bin != 0U) {
            return -1;
        }
        request->iq = message + P0_ED_REQUEST_HEADER_BYTES_V2;
        request->iq_bytes = P0_ED_IQ_FRAME_BYTES;
    } else {
        return -1;
    }
    request->abi_version = version;
    request->frame_id = load_le32(message + 12U);
    request->flags = flags;
    return 0;
}

int p0_ed_response_encode(const p0_ed_response_t *response, uint8_t *message,
                          size_t capacity, size_t *message_bytes)
{
    uint16_t version;
    size_t header_bytes;
    size_t total;
    uint32_t result_bytes;
    uint32_t parameter_bytes;

    if (response == NULL || message == NULL || message_bytes == NULL)
        return -1;
    version = response->abi_version == 0U ? P0_ED_SERVICE_ABI_VERSION_V1 :
                                           response->abi_version;
    if (version != P0_ED_SERVICE_ABI_VERSION_V1 &&
        version != P0_ED_SERVICE_ABI_VERSION_V2 &&
        version != P0_ED_SERVICE_ABI_VERSION_V3 &&
        version != P0_ED_SERVICE_ABI_VERSION_V4)
        return -1;
    if (version != P0_ED_SERVICE_ABI_VERSION_V2 && response->parameter_present != 0U)
        return -1;
    header_bytes = version == P0_ED_SERVICE_ABI_VERSION_V2
                       ? P0_ED_RESPONSE_HEADER_BYTES_V2
                       : P0_ED_RESPONSE_HEADER_BYTES_V1;
    result_bytes = response->status == P0_ED_SERVICE_OK
                       ? (uint32_t)((version == P0_ED_SERVICE_ABI_VERSION_V3 ||
                                    version == P0_ED_SERVICE_ABI_VERSION_V4)
                                        ? compact_result_bytes(&response->result)
                                        : P0_ED_RESULT_BYTES)
                       : 0U;
    parameter_bytes = response->status == P0_ED_SERVICE_OK &&
                              response->parameter_present != 0U
                          ? P0_ED_PARAMETER_RESULT_BYTES
                          : 0U;
    total = header_bytes + result_bytes + parameter_bytes;
    if (capacity < total || response->status > P0_ED_SERVICE_INTERNAL_FAILURE ||
        (response->status == P0_ED_SERVICE_OK &&
         (response->result.frame_id != response->frame_id ||
           response->result.active_count > PHASE06J_MAX_ACTIVE_TRACKS ||
           response->result.ended_count > PHASE06J_MAX_ACTIVE_TRACKS ||
           (parameter_bytes != 0U &&
            (response->parameter.frame_id != response->frame_id ||
             response->parameter.observation_count > P0_PARAMETER_REQUIRED_FRAMES ||
             !parameter_result_valid(&response->parameter))))))
        return -1;
    memset(message, 0, header_bytes);
    store_le32(message + 0U, P0_ED_RESPONSE_MAGIC);
    store_le16(message + 4U, version);
    store_le16(message + 6U, (uint16_t)header_bytes);
    store_le32(message + 8U, (uint32_t)total);
    store_le32(message + 12U, response->frame_id);
    store_le32(message + 16U, response->status);
    store_le32(message + 20U, result_bytes);
    store_le32(message + 24U, response->raw_candidate_count);
    store_le32(message + 28U, response->dma_status_flags);
    if (result_bytes != 0U) {
        if (version == P0_ED_SERVICE_ABI_VERSION_V3 ||
            version == P0_ED_SERVICE_ABI_VERSION_V4)
            encode_result_compact(message + header_bytes, &response->result);
        else
            encode_result(message + header_bytes, &response->result);
        if (version != P0_ED_SERVICE_ABI_VERSION_V3 &&
            version != P0_ED_SERVICE_ABI_VERSION_V4)
            store_le32(message + 32U,
                       p0_ed_crc32(message + header_bytes, result_bytes));
    }
    if (version != P0_ED_SERVICE_ABI_VERSION_V2) {
        store_le32(message + 44U, p0_ed_crc32(message, 44U));
    } else {
        store_le32(message + 36U, parameter_bytes);
        if (parameter_bytes != 0U) {
            encode_parameter_result(message + header_bytes + result_bytes,
                                    &response->parameter);
            store_le32(message + 40U,
                       p0_ed_crc32(message + header_bytes + result_bytes,
                                   parameter_bytes));
            store_le32(message + 44U, 1U);
        }
        store_le32(message + 60U, p0_ed_crc32(message, 60U));
    }
    *message_bytes = total;
    return 0;
}

int p0_ed_response_decode(const uint8_t *message, size_t message_bytes,
                          p0_ed_response_t *response)
{
    uint16_t version;
    size_t header_bytes;
    uint32_t result_bytes;
    uint32_t parameter_bytes = 0U;

    if (message == NULL || response == NULL ||
        message_bytes < P0_ED_RESPONSE_HEADER_BYTES_V1 ||
        message_bytes > P0_ED_RESPONSE_BYTES ||
        load_le32(message + 0U) != P0_ED_RESPONSE_MAGIC)
        return -1;
    version = load_le16(message + 4U);
    if (version == P0_ED_SERVICE_ABI_VERSION_V1 ||
        version == P0_ED_SERVICE_ABI_VERSION_V3 ||
        version == P0_ED_SERVICE_ABI_VERSION_V4) {
        header_bytes = P0_ED_RESPONSE_HEADER_BYTES_V1;
        if (load_le16(message + 6U) != header_bytes ||
            load_le32(message + 8U) != message_bytes ||
            load_le32(message + 36U) != 0U || load_le32(message + 40U) != 0U ||
            load_le32(message + 44U) != p0_ed_crc32(message, 44U))
            return -1;
    } else if (version == P0_ED_SERVICE_ABI_VERSION_V2) {
        header_bytes = P0_ED_RESPONSE_HEADER_BYTES_V2;
        if (message_bytes < header_bytes || load_le16(message + 6U) != header_bytes ||
            load_le32(message + 8U) != message_bytes ||
            load_le32(message + 48U) != 0U || load_le32(message + 52U) != 0U ||
            load_le32(message + 56U) != 0U ||
            load_le32(message + 60U) != p0_ed_crc32(message, 60U))
            return -1;
        parameter_bytes = load_le32(message + 36U);
        if ((parameter_bytes == 0U &&
             (load_le32(message + 40U) != 0U || load_le32(message + 44U) != 0U)) ||
            (parameter_bytes != 0U &&
             (parameter_bytes != P0_ED_PARAMETER_RESULT_BYTES ||
              load_le32(message + 44U) != 1U)))
            return -1;
    } else {
        return -1;
    }
    memset(response, 0, sizeof(*response));
    response->abi_version = version;
    response->frame_id = load_le32(message + 12U);
    response->status = load_le32(message + 16U);
    result_bytes = load_le32(message + 20U);
    response->raw_candidate_count = load_le32(message + 24U);
    response->dma_status_flags = load_le32(message + 28U);
    if (response->status > P0_ED_SERVICE_INTERNAL_FAILURE)
        return -1;
    if (response->status != P0_ED_SERVICE_OK)
        return result_bytes == 0U && parameter_bytes == 0U &&
                       message_bytes == header_bytes && load_le32(message + 32U) == 0U
                   ? 0 : -1;
    if ((version != P0_ED_SERVICE_ABI_VERSION_V3 &&
         version != P0_ED_SERVICE_ABI_VERSION_V4 &&
         result_bytes != P0_ED_RESULT_BYTES) ||
        ((version == P0_ED_SERVICE_ABI_VERSION_V3 ||
          version == P0_ED_SERVICE_ABI_VERSION_V4) &&
         (result_bytes < P0_ED_RESULT_HEADER_BYTES ||
          result_bytes > P0_ED_RESULT_BYTES)) ||
        message_bytes != header_bytes + result_bytes + parameter_bytes ||
        ((version == P0_ED_SERVICE_ABI_VERSION_V3 ||
          version == P0_ED_SERVICE_ABI_VERSION_V4)
             ? load_le32(message + 32U) != 0U
             : load_le32(message + 32U) !=
                   p0_ed_crc32(message + header_bytes, result_bytes)))
        return -1;
    if (((version == P0_ED_SERVICE_ABI_VERSION_V3 ||
          version == P0_ED_SERVICE_ABI_VERSION_V4)
             ? decode_result_compact(message + header_bytes, result_bytes,
                                     &response->result)
             : decode_result(message + header_bytes, &response->result)) != 0 ||
        response->result.frame_id != response->frame_id)
        return -1;
    if (parameter_bytes != 0U) {
        if (load_le32(message + 40U) !=
                p0_ed_crc32(message + header_bytes + result_bytes, parameter_bytes) ||
            decode_parameter_result(message + header_bytes + result_bytes,
                                    &response->parameter) != 0 ||
            response->parameter.frame_id != response->frame_id)
            return -1;
        response->parameter_present = 1U;
    }
    return 0;
}
