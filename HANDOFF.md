# Bàn giao — Convert playable ads Luna sang các ad network

Gói này là toàn bộ kết quả của một phiên làm việc dài. Đọc file này trước, các file khác là phụ lục.

**Bối cảnh:** NSTAGE có creative playable export từ Luna Playground. Plan free của Luna **chỉ cho tải bản Unity Ads** (`*_unityads.html`) — muốn bản cho network khác phải có Pro plan. Phiên này dựng đường đi vòng: patch trực tiếp file unityads thành build hợp lệ cho 5 network khác, và đóng gói thành tool để dùng lại.

File tham chiếu dùng suốt phiên: `Halloween_Concept1`, Luna pipeline `3.1.0`, buildId `18792341`, 5.011.322 B (4,78 MB), single self-contained HTML. **File gốc không có trong gói này** — cần upload lại nếu muốn chạy lại tool.

---

## 1. Tình trạng hiện tại

| Hạng mục | Trạng thái |
|---|---|
| Tool convert (web + CLI) | ✅ xong, 5 network |
| Mintegral | ✅ đã pass PlayTurbo review |
| Google Ads | ✅ build xong, chưa có xác nhận từ giao diện Google Ads |
| AppLovin | ✅ build xong, chưa xác nhận trên Playable Preview |
| Meta | ✅ đã pass Meta playable preview (sau khi fix lỗi literal) |
| TikTok | ✅ build xong, **chưa test** — TikTok không có tester riêng |
| Ẩn code adapter | ✅ mặc định xuất bản minify |
| Adapter dùng chung 1 file cho mọi network | ✅ đã wire vào tool dạng tuỳ chọn (`--universal` trên CLI / checkbox trên Web) — xem mục 6 |
| Ghi đè Store Links & Master ZIP | ✅ xong (`--ios-link`, `--android-link`, `--zip-all`, ô input & nút tải tất cả trên Web) |
| In-Tool Emulator Sandbox ("👁️ Test CTA") | ✅ xong (mock 5 SDKs, frame điện thoại dọc/ngang, monitor CTA & analytics thời gian thực) |

Mọi build đều được verify bằng headless Chromium (viewport 390×844, UA Android, touch emulation) với SDK giả của từng network. Tiêu chí pass: game boot và render, CTA gọi đúng API của network (**không** rơi xuống `window.open`), `console.log` còn native, số external request đúng như kỳ vọng.

---

## 2. Spec từng network — bảng chốt

| Network | Format nhận | Limit | API mở store | Bắt buộc thêm |
|---|---|---|---|---|
| Unity Ads | single HTML | 5 MB | `mraid.open(url)` | chờ `mraid` ready |
| Mintegral | HTML **hoặc** ZIP | 5 MB | `window.install()` | `window.gameEnd()` |
| Google Ads | **chỉ ZIP** | 5 MB · ≤512 files | `ExitApi.exit()` | `exitapi.js` + meta orientation |
| AppLovin | **chỉ single HTML** | 5 MB | `mraid.open(url)` | chạy được cả 2 orientation |
| Meta | HTML **hoặc** ZIP | **2 MB** HTML / 5 MB ZIP | `FbPlayableAd.onCTAClick()` | không MRAID, không tracking ngoài |
| TikTok | **chỉ ZIP** | 5 MB (Luna ghi 3 MB) | `window.openAppStore()` | SDK riêng + `config.json` · **cấm MRAID** |

Ba chỗ dễ trượt nhất:

1. **Google và AppLovin loại trừ nhau về format.** Google chỉ ZIP, AppLovin chỉ HTML rời. Không có một file nào chạy được cả hai.
2. **Meta limit single HTML chỉ 2 MB** — bằng nửa mọi network khác. File 4,78 MB bắt buộc đi đường ZIP.
3. **TikTok có hai chỗ nguồn không khớp nhau.** Limit: docs TikTok ghi <5 MB nén, bảng Unity Playworks ghi 3 MB. Tên key trong `config.json`: TikTok help viết `Playable_orientation` hoa chữ P, Playworks viết thường. Tool đang dùng chữ thường và cảnh báo từ mốc 3 MB.

---

## 3. Sáu cái bẫy đã gặp thật

Phần giá trị nhất của phiên này. Không có cái nào trong docs của network.

### 3.1 Luna ghi đè `console` → Mintegral lỗi #15

Mọi build từ Luna Playground có một thẻ `<script>` remote-debugging (console.re) wrap cả 6 method của `console`. PlayTurbo báo *"Do not override global console method"*. Block này còn nuốt log khi devtools đóng, và poll `console.re` mỗi 100 ms **không bao giờ clear**.

Fix: xoá cả thẻ `<script>` (1.268 B, offset ~4772). Là IIFE độc lập, không gì khác phụ thuộc.

### 3.2 Validator quét chuỗi literal, không chạy code

**Bẫy tốn nhiều thời gian nhất.** Bản Meta đầu tiên gọi CTA qua biến cho gọn:

```js
var F = window.FbPlayableAd;
if (F && F.onCTAClick) F.onCTAClick();      // chạy đúng 100%
```

Runtime test pass hoàn toàn. Nhưng chuỗi `FbPlayableAd.onCTAClick` không hề xuất hiện trong file → preview tool của Meta báo chấm than đỏ *"Cần triển khai FbPlayableAd.onCTAClick()"*.

Fix: viết nguyên văn tên đầy đủ ở mọi call site. Và vì **runtime test không bắt được loại lỗi này**, tool có thêm bước self-check quét literal sau khi inject.

### 3.3 Luna dispatch `luna:start` TRƯỚC `luna:build`

Map thẳng hai event đó sang funnel của AppLovin thì nó nhận `DISPLAYED` trước `LOADED`. Đọc code không thấy, chỉ lộ khi chạy thật.

Fix: state machine tự bù bước còn thiếu, đảm bảo đúng thứ tự và không lặp.

### 3.4 Bridge định nghĩa member là accessor và thay cả object sau init

`Luna.Unity.Analytics.Applovin` trong build unityads là **object rỗng** — game gọi `LogChallengeStarted()` thì rơi vào hư không. Khi wire lại thì phát hiện: Bridge (C#→JS) định nghĩa các member đó là **accessor không enumerable** (nên `Object.keys` không thấy), và **thay thế cả object** sau khi khởi tạo.

Fix: `Object.defineProperty` (fallback về gán thường) + mỗi vòng poll kiểm tra *hàm thực tế có phải của mình không*, thay vì đánh dấu object một lần rồi bỏ qua.

### 3.5 `playgroundAssetOverrides` trỏ asset ra CDN Luna

Rác của Playground preview harness — map trỏ một file `.m4a` ra `assets.lunalabs.io`, trong khi asset đó **đã bake inline** trong build. Mọi network đều cấm request ra ngoài lúc chạy ad.

Fix: set `{}` — **nhưng chỉ khi biến xuất hiện đúng 1 lần** trong file (tức là chỉ được gán, không ai đọc). Nhiều hơn 1 thì phải xử lý tay.

### 3.6 Thẻ `<script src>` nuốt nội dung inline

Lúc thử adapter dùng chung: với TikTok, chèn thẻ SDK trước rồi nối adapter vào thẻ `</script>` cuối cùng → adapter rơi vào **trong** thẻ SDK. Thẻ có `src` thì nội dung inline bị bỏ qua, adapter không chạy, CTA im lặng rơi xuống `window.open`.

Fix: với TikTok, adapter buộc phải nằm ở thẻ riêng, đặt **sau** SDK (TikTok yêu cầu SDK trước custom JS).

---

## 4. Tool hoạt động thế nào

Hai bản, **cùng một logic**, output khớp byte-for-byte:

- `tool/PA_Converter.html` — mở bằng Chrome, kéo file vào, tích network, Convert, tải về. Chạy hoàn toàn trong browser (đọc/ghi ZIP bằng `CompressionStream` native), không CDN, không upload đi đâu.
- `tool/convert_pa.py` — chỉ standard library. Exit code 1 nếu có file vượt limit → dùng được trong CI.

### Bước 1 — làm sạch (chung mọi network), −1.543 B

| Sửa | Delta | Không làm thì sao |
|---|---|---|
| Xoá block ghi đè `console` | −1.268 B | Mintegral reject lỗi #15 |
| Sửa tag đóng `</body></html></head></html>` | −13 B | Google reject HTML structure |
| `playgroundAssetOverrides` → `{}` | −164 B | Nguy cơ request CDN lúc chạy ad |
| 2 URL script debug → `about:blank` | −98 B | Google reject external resource |

Mỗi bước có **guard**: pattern không khớp mẫu đã biết thì tool báo warning chứ không sửa bừa.

### Bước 2 — inject adapter

Không đụng engine bundle. Thêm một thẻ `<script>` trước `</body>`, poll 100 ms (tối đa 60 s) ghi đè `Luna.Unity.Playable.InstallFullGame` và `LifeCycle.GameEnded` sau khi Luna khởi tạo.

**Dùng poll chứ không `addEventListener("luna:build")`** — vì listener của mình có thể chạy *trước* listener của Luna rồi bị Luna ghi đè lại.

### Bước 3 — đóng gói + self-check

Self-check quét literal bắt buộc của từng network sau khi inject, in kết quả ra log. Đây là phòng tuyến chống bẫy 3.2 tái diễn.

### Ẩn code (mặc định bật)

Adapter mặc định xuất bản **rút gọn**: minify qua terser, đổi tên biến, bỏ comment/log, marker đổi từ `__paConverter='meta'` sang `_lz='z2'`. `--readable` (CLI) hoặc tích ô (web) để lấy bản có comment.

| Network | Dễ đọc | Rút gọn |
|---|---|---|
| Mintegral | 2.426 B | 1.484 B |
| Google Ads | 1.838 B | 1.071 B |
| AppLovin | 5.082 B | 2.277 B |
| Meta | 2.914 B | 1.359 B |
| TikTok | 1.913 B | 930 B |

**Giới hạn cứng:** chuỗi API mà validator quét *bắt buộc* còn nguyên văn — không giấu được, và không nên giấu. Thứ được ẩn là *cách làm*, không phải *network nào*.

---

## 5. Diff thật — đo trên file

| Giai đoạn | Kích thước | Thay đổi |
|---|---|---|
| File gốc unityads | 5.011.322 B | — |
| Sau bước làm sạch (base dùng chung) | 5.009.779 B | −1.543 |
| → Mintegral | 5.012.206 B | +2.427 |
| → Google Ads | 5.011.781 B | +2.002 |
| → AppLovin | 5.014.862 B | +5.083 |
| → Meta | 5.012.694 B | +2.915 |
| → TikTok | 5.011.803 B | +2.024 |

Chỉ **hai vị trí** bị thêm nội dung: trước `</head>` (chỉ Google) và trước `</body>`. Engine bundle Unity, asset base64 và code game **không bị chạm một byte nào** — đã kiểm bằng cách so từng ký tự phần ở giữa. Tổng phần đụng vào ≈ **0,08 %** file.

### Cái gì KHÔNG bị xoá — và vì sao không sao

Cụm "network X không được có hàm Y" nghĩa là **không được phụ thuộc vào / không được để chạy**, chứ không phải phải xoá khỏi file. Code MRAID gốc của Luna vẫn nằm nguyên trong cả 5 bản:

| Code còn lại | Số lần | Vì sao để yên được |
|---|---|---|
| `mraid.open(` | 3 | Trong nhánh có `typeof mraid !== "undefined"` |
| `getMraidAdData` | 1 | Luna đã bọc `try/catch` sẵn |
| `viewableChange` | 1 | Chỉ đăng ký khi `mraid` tồn tại |
| `initializeLogging` | 1 | **Đừng kích hoạt** — gửi dữ liệu về server Luna, Meta cấm |
| `console.log` | 75 | Gọi console thì không sao, chỉ cấm **ghi đè** |

---

## 6. Adapter dùng chung một file (Universal Adapter)

Đã dựng, verify và **đã wire vào cả CLI (`--universal`) và Web tool (checkbox)** dưới dạng tuỳ chọn bật/tắt (không đặt làm mặc định để phòng ngừa rủi ro chính sách).

**Ý tưởng:** thay vì 5 file mỗi cái may đo cho một mạng, dùng một adapter feature-detect — SDK nào có mặt thì dùng cái đó. Cộng thêm: nối vào thẻ `<script>` cuối của Luna thay vì tạo thẻ mới, và bỏ marker nhân tạo (so sánh tham chiếu hàm `P.InstallFullGame !== cta`).

**Kết quả đo:**

| Network | Thẻ `<script>` | Ghi chú |
|---|---|---|
| Mintegral | 25 → **25** | 3 network này ra file **byte-identical nhau** |
| AppLovin | 25 → **25** | sha256 `d67daaaa…` |
| Meta | 25 → **25** | |
| Google | 25 → 26 | +1 vì `exitapi.js` — Google bắt buộc |
| TikTok | 25 → 27 | +2 vì SDK phải đứng trước custom JS |

Verify runtime cả 5: CTA đúng, không rơi `window.open`, AppLovin giữ nguyên funnel và challenge event.

**Đánh đổi phải cân:** file dùng chung nghĩa là bản Meta cũng chứa `ALPlayableAnalytics.trackEvent(` và `window.install(`. Meta cấm script tracking bên thứ ba. Đây chỉ là lời gọi hàm có guard tới global không tồn tại, không phải script — rủi ro thấp nhưng không bằng không.

**Đề xuất:** để thành **tuỳ chọn**, không thành mặc định.

File: `experimental/universal.js` (bản đọc được), `universal_nomraid.js` (cho TikTok — bỏ hẳn nhánh MRAID), kèm bản `.min.js`.

---

## 7. Một hiểu nhầm cần tránh

File unityads gốc **có** chứa `FACEBOOK_AD_NETWORK_NAME`, `MINTEGRAL_AD_NETWORK_NAME`, `VUNGLE_AD_NETWORK_NAME` và 4 hàm `FbPlayableAd.*`. Nhưng đó là **code analytics**, không phải code CTA — và nó **chết**:

```js
window.pi = function(t, ...) { if (..., t === o.FACEBOOK_AD_NETWORK_NAME) ... }
window.pi.apply(window, [] || [])      // gọi KHÔNG tham số → t = undefined
```

Đếm API mở store trong bản unityads gốc:

| API | Số lần |
|---|---|
| `mraid.open(` | **1** |
| `FbPlayableAd.onCTAClick(` | 0 |
| `window.openAppStore(` | 0 |
| `ExitApi.exit(` | 0 |
| `window.install(` | 0 |
| `window.gameEnd(` | 0 |

Nên **không thể upload thẳng file unityads lên network khác**. Và nó hỏng theo kiểu tệ nhất: **im lặng**. Game vẫn chạy (Luna fallback `luna:start` khi `mraid` vắng), store vẫn mở qua `window.open`, nhưng network không đếm được click. Tiền vẫn tiêu, số liệu thì sai.

---

## 8. Chạy lại / kiểm tra

```bash
python3 convert_pa.py build.zip                     # cả 5 network, adapter rút gọn
python3 convert_pa.py build.zip --readable          # adapter có comment (debug)
python3 convert_pa.py build.zip -n meta,tiktok -o dist
python3 convert_pa.py build.zip --inspect           # chỉ soi, không xuất
```

Kiểm nhanh trên file đã build:

```bash
grep -c 'devToolsAreOpen' build.html                        # 0
grep -oE 'https?://[a-zA-Z0-9._-]+' build.html | sort -u     # chỉ store link
tail -c 60 build.html                                        # </body></html>
grep -c 'FbPlayableAd.onCTAClick(' build.html                # Meta
grep -c 'window.openAppStore('     build.html                # TikTok
```

Preview tool: Mintegral `playturbo.com/review` · AppLovin `p.applov.in/playablePreview` · Meta `developers.facebook.com/tools/playable-preview` · Google qua giao diện Google Ads (đừng dựa vào Playable Tester Beta) · TikTok **không có tester riêng**, test qua Ads Manager.

---

## 9. Hai việc tồn đọng cần xử lý ở phía Unity

1. **`iosLink` đang TRỐNG** trong config Luna gốc: Traffic iOS bấm CTA sẽ mở vào chuỗi rỗng.
   - *Cách 1 (Ngay lập tức, không cần re-export)*: Dùng tính năng ghi đè link mới của tool: nhập trực tiếp vào ô `Link iOS App Store` trên giao diện web hoặc truyền cờ `--ios-link "https://apps.apple.com/..."` trên CLI. Tool sẽ tự động vá link hợp lệ vào `packageConfig`. Bạn có thể dùng nút **👁️ Test CTA** để kiểm tra link URL thực tế khi bấm CTA!
   - *Cách 2*: Điền trong Application Settings trên Playworks rồi export lại từ Unity.

2. **Size 4,78 MB rất sát limit 5 MB** — chỉ dư ~230 KB. Phải giảm từ gốc Unity, không phải nén HTML: nén texture, hạ bitrate audio, strip module runtime không dùng. Build đang load `physics3d`, `physics2d`, `particle_system`, `reflection`, `prefabs`, `mecanim-wasm` — với match-3 2D thì `physics3d` và `mecanim-wasm` gần như chắc bỏ được.

---

## 10. Nội dung gói

```
HANDOFF.md                      ← file này
tool/
  PA_Converter.html             web tool, mở bằng Chrome
  convert_pa.py                 CLI
  README.md                     tài liệu tool đầy đủ
docs/
  quy-trinh-convert.html        quy trình 4 bước, mở bằng browser
  01_base_lam_sach.md           4 sửa làm sạch — code trước/sau
  adapters_5_network.md         adapter 5 network, code đầy đủ
  00_unityads_the_cuoi.js       thẻ CTA gốc của Luna
  01_block_console_bi_xoa.js    khối 1.268 B bị xoá
  codeparts_README.md
experimental/
  universal*.js                 adapter dùng chung — xem mục 6
```

**Không có trong gói:** file `*_unityads.html` gốc và các build đã convert — chạy lại tool là ra.

---

## Nguồn

- [About HTML5/Playable ads for App campaigns — Google Ads Help](https://support.google.com/google-ads/answer/9981650?hl=en)
- [AppLovin — Creative specs & guidelines](https://support.applovin.com/en/growth/promoting-your-apps/welcome-to-applovin/creative-specs-and-guidelines)
- [AppLovin — HTML analytics integration](https://support.applovin.com/en/growth/promoting-your-apps/welcome-to-applovin/playable-analytics-integration)
- [About TikTok Playable ads — TikTok Ads Manager](https://ads.tiktok.com/help/article/playable-ads?lang=en)
- [Playable upload specifications for networks — PlayTurbo Docs](https://doc.playturbo.com/export-and-deployment/playable-upload-specifications-for-networks.md)
- [Ad Networks Overview — Unity Playworks Developer Docs](https://docs.lunalabs.io/docs/playable/ad-networks/overview/)
- [Playable API — Unity Playworks Developer Docs](https://docs.lunalabs.io/docs/playable/playable-setup/playable-api/)
