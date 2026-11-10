# LunaConvert — Luna Playable Ads Converter

Công cụ chuyển đổi playable ad export từ **Luna Playground (Unity Playworks)** sang các ad network lớn: **Mintegral**, **Google Ads**, **AppLovin**, **Meta (Facebook)**, và **TikTok**.

---

## 🌟 Tính năng nổi bật

- 🚀 **2 phiên bản tiện lợi**:
  - **Web Tool (`tool/PA_Converter.html`)**: Chạy 100% offline ngay trên trình duyệt (Chrome/Edge/Safari), giao diện trực quan, kéo thả file để convert.
  - **Python CLI (`tool/convert_pa.py`)**: Không cần cài thêm thư viện (chỉ dùng Python standard library), phù hợp cho batch processing và CI/CD.
- 🔗 **Ghi đè Store Links**: Cho phép chỉnh sửa trực tiếp `iosLink` / `androidLink` ngay trên giao diện hoặc CLI mà không cần mở Unity để re-export.
- 📦 **Tải tất cả bản build (All-in-one ZIP)**: Nén toàn bộ file HTML & ZIP của các network đã chọn thành 1 file ZIP duy nhất (`--zip-all`).
- 👁️ **In-Tool Sandbox Emulator ("Test CTA")**:
  - Trực tiếp chơi thử playable trên khung mô phỏng Smartphone (chuyển đổi linh hoạt giữa Portrait / Landscape).
  - Mock đầy đủ SDK của 5 mạng quảng cáo (`window.install`, `ExitApi.exit`, `FbPlayableAd.onCTAClick`, `window.openAppStore`, `mraid.open`).
  - Monitor sự kiện CTA và theo dõi luồng analytics thời gian thực (`LOADED`, `DISPLAYED`, `CHALLENGE_*`, `game_end`).
- 🌐 **Universal Adapter (Tùy chọn)**: Dùng chung 1 file adapter thông minh cho mọi network qua cơ chế runtime feature-detection.
- 🛡️ **Tự động làm sạch & tối ưu hóa**: Xóa block override console (tránh lỗi PlayTurbo #15), sửa tag đóng HTML, chặn external requests ngoài luồng.

---

## 📋 Bảng đặc tả các Ad Network

| Network | Format hỗ trợ | Giới hạn dung lượng | API mở Store | Yêu cầu bắt buộc |
|---|---|---|---|---|
| **Mintegral** | `.html` hoặc `.zip` | 5 MB | `window.install()` | `window.gameEnd()` |
| **Google Ads** | **Chỉ `.zip`** | 5 MB (≤512 files) | `ExitApi.exit()` | `exitapi.js` + meta orientation |
| **AppLovin** | **Chỉ single `.html`** | 5 MB | `mraid.open(url)` | Chạy được cả Portrait & Landscape |
| **Meta (Facebook)** | `.zip` (hoặc `.html` nếu <2MB) | **2 MB** HTML / 5 MB ZIP | `FbPlayableAd.onCTAClick()` | Không MRAID, không tracking ngoài |
| **TikTok** | **Chỉ `.zip`** | 5 MB (cảnh báo từ 3 MB) | `window.openAppStore()` | SDK TikTok + `config.json` (**cấm MRAID**) |

---

## 🚀 Hướng dẫn nhanh

### 1. Dùng giao diện Web (`tool/PA_Converter.html`)
1. Mở file `tool/PA_Converter.html` bằng trình duyệt Chrome hoặc Edge (không cần web server).
2. Kéo thả file `.html` hoặc `.zip` từ Luna vào tool.
3. Nhập/chỉnh sửa store link nếu cần.
4. Chọn các network cần xuất, bấm **Chuyển đổi**.
5. Bấm **👁️ Test CTA** để kiểm thử gameplay & CTA click trực tiếp, hoặc bấm **📦 Tải tất cả bản build (.zip)** để tải về.

### 2. Dùng Python CLI (`tool/convert_pa.py`)
```bash
# Convert tất cả 5 network và gom vào 1 master zip
python tool/convert_pa.py Halloween_Concept1.zip --zip-all

# Ghi đè store links iOS / Android
python tool/convert_pa.py build.zip \
  --ios-link "https://apps.apple.com/app/id123456789" \
  --android-link "https://play.google.com/store/apps/details?id=com.game" \
  --zip-all

# Dùng universal adapter
python tool/convert_pa.py build.zip --universal -o dist/
```

---

## 📁 Cấu trúc thư mục

```
LunaConvert/
├── README.md                   # Tài liệu giới thiệu chính
├── HANDOFF.md                  # Báo cáo kỹ thuật chi tiết & 6 bẫy đã gặp
├── tool/
│   ├── PA_Converter.html       # Web converter offline kèm Test CTA Emulator
│   ├── convert_pa.py           # Python CLI converter
│   └── README.md               # Chi tiết cách hoạt động của tool
├── docs/                       # Tài liệu phân tích và quy trình
└── experimental/               # Bản adapter đa năng (Universal)
```

Chi tiết kỹ thuật, các vấn đề lưu ý và bẫy thường gặp vui lòng tham khảo [HANDOFF.md](HANDOFF.md) và [tool/README.md](tool/README.md).
