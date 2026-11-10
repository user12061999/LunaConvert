# LunaPA Converter

Chuyển playable ad export từ Luna Playground (Unity Ads / MRAID) sang build hợp lệ cho **Mintegral**, **Google Ads (App campaigns / AdMob)**, **AppLovin**, **Meta / Facebook** và **TikTok**.

Hai bản, cùng một logic:

| File | Dùng khi |
|---|---|
| `PA_Converter.html` | Hằng ngày. Mở bằng Chrome, kéo file vào, tích network, bấm Convert, tải về. |
| `convert_pa.py` | Batch nhiều file, hoặc nhét vào pipeline/CI. |

---

## Web tool

Mở `PA_Converter.html` bằng Chrome / Edge / Safari (double-click là được — không cần server, không cần cài gì).

Kéo vào file `.html` hoặc `.zip` tải từ `playground.lunalabs.io`:
1. **Soi thông tin build**: Tool đọc `targetPlatform`, `buildId`, `orientation`, và store links (`iosLink`, `androidLink`).
2. **Ghi đè Store Links**: Có 2 ô input iOS & Android Link tự động điền link từ file. Bạn có thể sửa trực tiếp link mới vào đây để tool tự vá vào `packageConfig` (giải quyết triệt để vấn đề `iosLink` bị trống mà không cần re-export từ Unity).
3. **Tùy chọn convert**: Chọn các network cần xuất, tùy chọn Adapter rút gọn / Universal adapter.
4. **Convert & Tải về**:
   - Bấm **Convert** để sinh các build.
   - Nút **📦 Tải tất cả bản build (.zip)**: Gom toàn bộ file HTML & ZIP của các network đã chọn thành 1 file ZIP duy nhất để tải về 1 lần.
   - Nút **👁️ Test CTA**: Mở ngay Sandbox Emulator giả lập smartphone để test trực tiếp CTA click và event analytics của từng network mà không cần upload lên previewer bên ngoài!

Chạy **hoàn toàn trong browser**: đọc/ghi ZIP bằng `CompressionStream` native của browser, không CDN, không upload đi đâu. Yêu cầu Chrome/Edge 80+ hoặc Safari 16.4+ (tool tự báo nếu browser không hỗ trợ).

## Python CLI

Chỉ dùng standard library, Python 3.7+.

```bash
python3 convert_pa.py Halloween_Concept1.zip                        # cả 5 network
python3 convert_pa.py build.zip --universal                         # dùng universal adapter (feature-detect)
python3 convert_pa.py build.zip --zip-all                           # xuất thêm file <base>_all_networks.zip gom tất cả build
python3 convert_pa.py build.zip --ios-link "https://..."            # ghi đè link iOS App Store
python3 convert_pa.py build.zip --android-link "https://..."        # ghi đè link Google Play
python3 convert_pa.py build.html -n meta                            # chỉ Meta
python3 convert_pa.py build.zip -n tiktok,meta -o dist               # chỉ định thư mục xuất
python3 convert_pa.py build.zip --inspect                           # chỉ soi, không xuất file
python3 convert_pa.py build.zip --readable                           # adapter bản dễ đọc (debug)
python3 convert_pa.py build.zip --readable --debug-logs              # thêm console.log trong adapter
```

Exit code `1` nếu có file vượt limit 5 MB, `0` nếu sạch — dùng được trong CI.

### Tùy chọn Universal Adapter (`--universal` hoặc checkbox trên Web)

- Sử dụng cơ chế runtime feature-detection: tự nhận diện SDK ad network có mặt để gọi đúng API mở store (`FbPlayableAd.onCTAClick()`, `window.openAppStore()`, `ExitApi.exit()`, `window.install()`, hoặc `mraid.open()`).
- Nối thẳng vào thẻ `<script>` cuối cùng của bundle Luna thay vì tạo thêm thẻ mới (giữ nguyên số lượng thẻ script 25/25 ban đầu).
- Các bản build xuất ra cho **Mintegral**, **AppLovin** và **Meta** có nội dung HTML **trùng khớp từng byte (byte-identical)**.
- Riêng TikTok tự động dùng bản `universal_nomraid` (bỏ nhánh MRAID) và đặt trong thẻ script riêng sau SDK TikTok.

### Sandbox Emulator / Test CTA trên Web Tool (👁️ Test CTA)

- **Mock đầy đủ SDK của 5 network**:
  - **Mintegral**: `window.install()`, `window.openStore()`, `window.gameEnd()`.
  - **Google Ads**: `ExitApi.exit()`.
  - **Meta**: `FbPlayableAd.onCTAClick()`, `logGameLoad()`, `logLevelComplete()`.
  - **TikTok**: `window.openAppStore()`.
  - **AppLovin / MRAID**: `mraid.open()`, `ALPlayableAnalytics.trackEvent()`.
  - **Fallback**: Bắt cả `window.open()` để cảnh báo nếu playable bị trôi CTA xuống fallback.
- **Mô phỏng điện thoại (Mockup frame)**: Có nút chuyển đổi linh hoạt giữa màn hình dọc (Portrait) và màn hình ngang (Landscape).
- **Event Monitor thời gian thực**:
  - Banner trạng thái CTA lớn báo xanh ngay lập tức khi phát hiện cuộc gọi CTA kèm tên hàm SDK đã gọi và store link nhận được.
  - Luồng log stream thời gian thực theo dõi mọi lifecycle event (`LOADED`, `DISPLAYED`, `CHALLENGE_*`, `game_end`).

---

## Tool làm những gì

### 1. Làm sạch (áp dụng cho mọi network)

| Vấn đề | Xử lý |
|---|---|
| Luna override cả 6 method của `console` (block remote-debugging console.re) | Xoá cả thẻ `<script>` — đây là **nguyên nhân lỗi PlayTurbo #15** |
| Tag đóng sai ở cuối file: `</body></html></head></html>` | Sửa lại thành `</body></html>` — Google validate explicit end tags |
| `window.playgroundAssetOverrides` trỏ asset ra CDN Luna | Set `{}` (asset đã bake sẵn inline trong build) |
| `mrdoob.github.io` (stats.js), `cdn.jsdelivr.net` (SpectorJS) | Đổi thành `about:blank` — Google chỉ cho external resource từ host của Google |

Mỗi bước đều có **guard**: nếu pattern không khớp mẫu đã biết (Luna đổi pipeline chẳng hạn), tool **không sửa bừa** mà báo warning để bạn soi tay. Cuối cùng tool liệt kê toàn bộ host ngoài còn lại trong file.

### 2. Inject adapter

Không sửa engine bundle. Chỉ thêm một script cuối `<body>`, poll 100ms (tối đa 60s) để ghi đè adapter của Luna sau khi nó khởi tạo — cách này chắc chắn thắng override gốc, không phụ thuộc thứ tự đăng ký listener.

**Mintegral**

| Luna API | → | Mintegral |
|---|---|---|
| `Luna.Unity.Playable.InstallFullGame` | → | `window.install()` |
| `Luna.Unity.LifeCycle.GameEnded` | → | `window.gameEnd()` (guard chỉ gọi 1 lần) |
| — | | định nghĩa `window.gameStart` / `gameClose` để network gọi vào → dispatch `luna:resume` / `luna:pause` |
| — | | gọi `window.gameReady()` ở event `luna:start` nếu network cung cấp |

Fallback chain: `install()` → `openStore()` → `mraid.open()` → `window.open()`

**Google Ads**

| Luna API | → | Google |
|---|---|---|
| `Luna.Unity.Playable.InstallFullGame` | → | `ExitApi.exit()` |
| — | | thêm `exitapi.js` vào `<head>` |
| — | | thêm `<meta name="ad.orientation">` (đọc `orientation` từ config Luna) |

Fallback chain: `ExitApi.exit()` → `clickTag` → `mraid.open()` → `window.open()`

**AppLovin**

AppLovin dùng MRAID như Unity Ads nên CTA gần như giữ nguyên, nhưng có hai thứ phải làm thêm.

| Luna API | → | AppLovin |
|---|---|---|
| `Luna.Unity.Playable.InstallFullGame` | → | `mraid.open()` **có gate chờ ready** |
| `Luna.Unity.LifeCycle.GameEnded` | → | `ALPlayableAnalytics.trackEvent("ENDCARD_SHOWN")` |
| `Luna.Unity.Analytics.Applovin.LogChallenge*` | → | `CHALLENGE_STARTED` / `_FAILED` / `_RETRY` / `_PASS_25` / `_PASS_50` / `_PASS_75` / `CHALLENGE_SOLVED` |
| — | | funnel `LOADING` → `LOADED` → `DISPLAYED` + `CTA_CLICKED` |

Fallback chain: `mraid.open()` → `window.open()`

Hai điểm đáng nói:

1. **Gate chờ mraid ready.** AppLovin yêu cầu không gọi MRAID API trước khi mraid signal ready. Nếu bấm CTA lúc `mraid.getState() === "loading"`, adapter đăng ký listener `ready` một lần rồi mới `mraid.open()` — chứ không gọi thẳng rồi hy vọng.
2. **`Luna.Unity.Analytics.Applovin` trong build unityads là object rỗng.** Nếu game có gọi `LogChallengeStarted()` thì call đó rơi vào hư không. Adapter map lại toàn bộ 7 method vào `ALPlayableAnalytics`.

   Chi tiết kỹ thuật: Bridge (C#→JS) định nghĩa các member này là **accessor không enumerable**, và Bridge có thể **thay thế cả object** sau khi khởi tạo. Nên adapter dùng `Object.defineProperty` (fallback về phép gán thường) và mỗi vòng poll kiểm tra *hàm thực tế có phải của mình không* — thay vì đánh dấu object một lần rồi bỏ qua. Không làm vậy thì Bridge ghi đè lại và challenge events im lặng mất.

   Funnel cũng không tin thứ tự event của Luna: pipeline 3.1.0 dispatch `luna:start` **trước** `luna:build`, nên nếu map thẳng thì AppLovin nhận `DISPLAYED` trước `LOADED`. Adapter dùng state machine tự bù các bước còn thiếu, đảm bảo đúng thứ tự và không lặp.

**Meta / Facebook**

Meta là network duy nhất trong 4 cái **không dùng MRAID** — nó inject SDK riêng `window.FbPlayableAd`. Đây chính là chỗ hay làm hỏng creative port từ Unity Ads / AppLovin sang: `mraid` không tồn tại, CTA rơi xuống `window.open()`, Meta không đếm click.

| Luna API | → | Meta |
|---|---|---|
| `Luna.Unity.Playable.InstallFullGame` | → | `FbPlayableAd.onCTAClick()` |
| `Luna.Unity.LifeCycle.GameEnded` | → | `FbPlayableAd.logLevelComplete("game_end")` (chỉ 1 lần) |
| — | | `FbPlayableAd.logGameLoad()` một lần khi game load xong |

Fallback chain: `FbPlayableAd.onCTAClick()` → `mraid.open()` → `window.open()`

**Cố ý KHÔNG bật đường analytics Facebook của Luna.** Build có sẵn code map event sang `FbPlayableAd.logGameLoad` / `logLevelComplete` / `logButtonClick`, nhưng nó chỉ chạy khi module π được init với network name `facebook` + `appId`/`buildId`/`signature`, và bước init đó gọi `FbPlayableAd.initializeLogging(statsUrl + "/facebook", …)` — tức là **gửi dữ liệu về server Luna**. Meta cấm request ra ngoài và cấm script tracking của bên thứ ba, nên bật đường đó là tự đi xin reject. Adapter gọi thẳng SDK của Meta, không qua π.

⚠️ **Bẫy đã gặp thật: playable preview của Meta quét chuỗi literal trong source, không chạy code.**

Bản đầu tiên gọi CTA qua biến trung gian cho gọn:

```js
var F = (typeof window.FbPlayableAd !== "undefined") ? window.FbPlayableAd : null;
if (F && F.onCTAClick) F.onCTAClick();      // chạy đúng, nhưng...
```

Code này **chạy hoàn toàn đúng** — test runtime `onCTAClick` bắn bình thường. Nhưng chuỗi `FbPlayableAd.onCTAClick` không hề xuất hiện trong file, nên preview tool của Meta báo dấu chấm than đỏ **"Cần triển khai FbPlayableAd.onCTAClick()"**.

Bản hiện tại viết nguyên văn tên đầy đủ ở mọi call site:

```js
function hasFb(fn){
  try { return typeof FbPlayableAd !== "undefined" && typeof FbPlayableAd[fn] === "function"; }
  catch(e){ return false; }
}
if (hasFb("onCTAClick")) { FbPlayableAd.onCTAClick(); return; }
```

Vì đây là loại lỗi **test runtime không bắt được**, tool có thêm bước **self-check literal**: sau khi inject adapter, nó kiểm tra các chuỗi mà validator từng network quét và in kết quả ra log.

| Network | Chuỗi bắt buộc có trong source |
|---|---|
| Meta | `FbPlayableAd.onCTAClick(` |
| TikTok | `window.openAppStore(` |
| Google Ads | `ExitApi.exit(` |
| Mintegral | `window.install(` , `window.gameEnd(` |
| AppLovin | `mraid.open(` , `ALPlayableAnalytics.trackEvent(` |

Nếu một chuỗi biến mất (ví dụ sau này ai sửa adapter cho "gọn hơn"), log in ra `! Self-check THAT BAI` ngay lúc convert — chứ không đợi tới lúc bị network reject.

**TikTok**

Khác 4 network kia ở ba chỗ, cả ba đều bắt buộc.

| Luna API | → | TikTok |
|---|---|---|
| `Luna.Unity.Playable.InstallFullGame` | → | `window.openAppStore()` |
| `Luna.Unity.LifeCycle.GameEnded` | → | không có API game-end |
| — | | thêm `Playable-sdk.js` của TikTok **trước** adapter |
| — | | thêm `config.json` vào ZIP (`playable_orientation`, `playable_languages`) |

Fallback chain: `window.openAppStore()` → `window.open()` — **không có `mraid.open`**.

1. **TikTok cấm creative dạng MRAID**, nên đây là adapter duy nhất không có nhánh `mraid` nào. Code MRAID của Luna vẫn nằm trong engine bundle nhưng trơ (TikTok không inject `mraid`) — nếu bị reject vì MRAID thì soi ở đó, không phải adapter.
2. **SDK phải đứng trước adapter.** TikTok yêu cầu `Playable-sdk.js` ở cuối `<body>` trước mọi custom JS — nó chính là thứ định nghĩa `window.openAppStore`. Tool chèn đúng thứ tự đó.
3. **`config.json` ở gốc ZIP.** `playable_orientation` map từ `orientation` của Luna (`0` responsive / `1` portrait / `2` landscape), `playable_languages` đọc từ `languages` trong config Luna, mặc định `["en"]`.

Về limit: docs chính thức của TikTok ghi **<5 MB nén**, nhưng bảng yêu cầu của Unity Playworks ghi **3 MB**. Hai nguồn không khớp, nên tool cảnh báo từ mốc 3 MB thay vì im lặng chọn một con số.

### 2b. Ẩn phần thêm vào

Mặc định tool xuất adapter ở **bản rút gọn**: minify, đổi tên biến, bỏ hết comment và log, và marker đổi từ tên network sang mã 2 ký tự (`_lz='z2'` thay vì `__paConverter='meta'`).

| Network | Bản dễ đọc | Bản rút gọn |
|---|---|---|
| Mintegral | 2.426 B | 1.484 B |
| Google Ads | 1.838 B | 1.071 B |
| AppLovin | 5.082 B | 2.277 B |
| Meta | 2.914 B | 1.359 B |
| TikTok | 1.913 B | 930 B |

Dùng `--readable` (CLI) hoặc tích ô trong web tool để lấy lại bản có comment khi cần debug.

**Giới hạn cứng — phải biết trước khi trông đợi vào việc này.** Validator của network **quét chuỗi literal trong source**, nên những chuỗi này *bắt buộc* phải còn nguyên văn và không giấu được:

`window.install(` · `window.gameEnd(` · `ExitApi.exit(` · `mraid.open(` · `ALPlayableAnalytics.trackEvent(` · `FbPlayableAd.onCTAClick(` · `window.openAppStore(`

Tức là **ai mở file vẫn biết được nó build cho network nào** — đó là thông tin công khai, không giấu được, và cũng không nên giấu. Thứ thực sự được ẩn là *cách làm*: 4 sửa của bước làm sạch, kỹ thuật ghi đè bằng polling, funnel state machine, và mẹo `defineProperty` cho challenge event.

**Vì sao chỉ minify chứ không mã hoá.** Toàn bộ bundle của Luna đã minify sẵn. Một khối JS format đẹp kèm comment tiếng Việt là **thứ duy nhất đọc được** trong file 5 MB — nó tự chỉ vào mình. Minify cho giống phần còn lại giấu tốt hơn nhiều so với đóng gói `eval`/base64, vì khối `eval` vừa nổi bật hơn, vừa là rủi ro bị reject: nhiều network không thích code đóng gói, và một số cấm `eval` thẳng.

Đây là **obfuscation, không phải encryption** — người đủ quyết tâm vẫn deobfuscate được. Nó chặn người liếc qua, không chặn người thật sự muốn đọc.

### 3. Đóng gói & kiểm tra

| Network | Xuất | Limit |
|---|---|---|
| Mintegral | single `.html` + `.zip` (chứa `index.html`) | 5 MB |
| Google Ads | chỉ `.zip` (Google không nhận HTML rời) | 5 MB |
| AppLovin | chỉ single `.html` (AppLovin không nhận ZIP) | 5 MB |
| Meta | `.zip` (chứa `index.html`), + single `.html` **nếu lọt dưới 2 MB** | **2 MB** HTML / **5 MB** ZIP, ≤100 files |
| TikTok | chỉ `.zip` — `index.html` + `config.json` ở gốc | 5 MB (cảnh báo từ 3 MB) |

Meta là network có limit khác hẳn: **single HTML chỉ 2 MB**, ZIP mới được 5 MB. Build 4.78 MB này không có cách nào lọt cửa single HTML, nên tool bỏ qua file `.html` và chỉ xuất ZIP — thay vì đưa bạn một file chắc chắn bị từ chối.

Tool cảnh báo khi vượt 5 MB, khi còn dưới 5% dư địa, khi `iosLink` trống (traffic iOS bấm CTA sẽ không mở gì), và — với AppLovin — khi build chỉ hỗ trợ một orientation.

---

## Đã verify

Cả hai bản cho ra **phần đã làm sạch giống nhau byte-for-byte**, và giống bản đã pass PlayTurbo + Google.

Test trên headless Chromium (viewport 390×844, UA Android, touch emulation), mock sẵn `window.install` / `window.gameEnd` / `ExitApi.exit`:

| Build | Console native 6/6 | Boot & render | CTA | GameEnd | External request khi chạy |
|---|---|---|---|---|---|
| Mintegral | ✅ | ✅ canvas 390×844 | `install()` ✅ | `gameEnd()` ✅ | **0** |
| Google Ads | ✅ | ✅ canvas 390×844 | `ExitApi.exit()` ✅ | ✅ | 1 (`exitapi.js`, Google yêu cầu) |
| AppLovin | ✅ | ✅ canvas 390×844 | `CTA_CLICKED` + `mraid.open()` đúng URL ✅ | `ENDCARD_SHOWN` (chỉ 1 lần dù gọi 2 lần) ✅ | **0** |
| Meta | ✅ | ✅ canvas 390×844 | `onCTAClick()` ✅ (không rơi xuống `window.open`) | `logLevelComplete("game_end")` (1 lần dù gọi 2 lần) ✅ | **0** |
| TikTok | ✅ | ✅ canvas 390×844 | `openAppStore()` ✅ (không rơi xuống `window.open`) | — | 1 (`Playable-sdk.js`, TikTok yêu cầu) |

TikTok test trong sandbox đúng như thật: **không có `mraid`**, chỉ có `window.openAppStore`. ZIP ra đúng 2 entry (`index.html` + `config.json`), `testzip()` pass, SDK nằm trước adapter, và adapter **không chứa token `mraid` nào**.

Ngoài runtime, build Meta còn được kiểm tra ở mức source: sau khi **strip toàn bộ comment**, chuỗi `FbPlayableAd.onCTAClick` vẫn xuất hiện trong code thật — để chắc chắn nó không chỉ nằm trong chú thích.

Meta test trong điều kiện đúng như sandbox thật: **không có `mraid`**, chỉ có `FbPlayableAd` được inject. Build vẫn boot bình thường (Luna có fallback `luna:start` khi `mraid` undefined), `logGameLoad()` bắn đúng 1 lần, CTA vào `onCTAClick()`. ZIP có 1 file, `testzip()` pass, dưới 100 files.

Riêng AppLovin, test với MRAID mock đúng đời thật (bắt đầu ở state `loading`, ready sau 300ms) + `ALPlayableAnalytics` mock. Event thu được đúng thứ tự:

```
LOADING → LOADED → DISPLAYED → CHALLENGE_STARTED → CHALLENGE_PASS_50 → ENDCARD_SHOWN → CTA_CLICKED → MRAID_OPEN
```

Và cả 7 method `LogChallenge*` đều verify là đã trỏ về hàm của adapter, kiểm tra lại sau khi Bridge khởi tạo xong.

ZIP xuất ra đọc được bằng `zipfile` của Python, `testzip()` pass, `index.html` bên trong khớp đúng với bản single HTML.

**Bản rút gọn được verify riêng**, cả 5 network: boot và render đúng, CTA gọi đúng API và **không rơi xuống `window.open`**, console native, marker đúng mã. AppLovin giữ nguyên toàn bộ funnel `LOADING → LOADED → DISPLAYED` và challenge event sau khi minify — tức là mẹo `defineProperty` vẫn sống. Adapter do web tool và CLI sinh ra **khớp byte-for-byte**.

---

## Giới hạn cần biết

- Tool chỉ xử lý **playable single-file** (toàn bộ asset inline). Nếu ZIP có nhiều file asset rời, tool lấy file HTML và **bỏ qua** phần còn lại — nó sẽ nói rõ trong log.
- Không giảm được size. 4.78 MB so với limit 5 MB là rất sát — muốn port sang network chặt hơn thì phải giảm từ **gốc trong Unity** (nén texture, hạ bitrate audio, strip module runtime không dùng như `physics3d` / `mecanim-wasm` với game match-3 2D).
- Đây là đường patch cho trường hợp bị giới hạn plan Luna. Cách chính thống vẫn là re-export từ Playground với network tương ứng (cần Pro plan).
- **TikTok** cấm creative dạng MRAID, chưa có playable tester riêng — test qua Ads Manager. Limit thì hai nguồn nói khác nhau (3 MB vs 5 MB), nên hỏi rep TikTok trước khi chạy nếu file trên 3 MB.
- **Meta** chạy creative ở chế độ **muted** và cấm mọi request ra ngoài / script tracking. Test bằng [Meta playable preview](https://developers.facebook.com/tools/playable-preview/) trước khi upload lên Ads Manager — tool đó báo rõ khi app store click đã thành công.
- **AppLovin** yêu cầu creative chạy được cả portrait và landscape. Build này `orientation=portrait` — tool sẽ cảnh báo; test ở cả 2 hướng bằng [AppLovin Playable Preview](https://p.applov.in/playablePreview?create=1).
- Với **non-dynamic playable**, Google khuyến nghị không tự đặt CTA vì Google tự xử lý end card. Nếu bị reject vì CTA, test qua giao diện Google Ads chứ đừng dựa vào Google Playable Tester (Beta) — tester đó không có click tag.
- **Luôn test trên playable tester của network trước khi chạy tiền.**
