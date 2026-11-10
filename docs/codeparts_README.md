# Code thật: base đã làm sạch + thẻ cuối của từng network

Toàn bộ file trong thư mục này **trích thẳng từ build thật**, không viết lại tay.

| File | Là gì |
|---|---|
| `00_unityads_the_cuoi.js` | Thẻ `<script>` cuối cùng của **file unityads gốc** — chỗ Luna gán CTA |
| `01_base_lam_sach.md` | **Bốn sửa của bước làm sạch** — code bị xoá và code trước/sau, kèm diff dạng ngắn |
| `01_block_console_bi_xoa.js` | Nguyên khối 1.268 byte bị xoá ở sửa A1 |
| `adapters_5_network.md` | **Adapter của cả 5 network gộp một file** — kèm phần chèn `<head>` của Google, SDK + `config.json` của TikTok |

Năm adapter trong file gộp đã được kiểm **khớp byte-for-byte** với build thật đã pass
preview tool của từng network.

---

## Cấu trúc một file sau khi convert

```
<!DOCTYPE html><html><head>
  … meta, style …
  [Google: + meta ad.orientation + exitapi.js]     ← chỉ Google sửa head
</head><body>

  … engine bundle Unity + asset base64 …           ← KHÔNG đụng tới
  … module pi, code MRAID của Luna …               ← KHÔNG đụng tới
  <script>… Luna gán InstallFullGame …</script>    ← GIỮ NGUYÊN, không xoá

  <script>… adapter của network …</script>         ← THÊM MỚI, ghi đè lúc runtime

</body></html>
```

Điểm hay bị hiểu nhầm: **thẻ cuối của unityads không bị xoá hay sửa**. Adapter được thêm vào *sau* nó và ghi đè `Luna.Unity.Playable.InstallFullGame` lúc chạy. Vì vậy diff giữa hai bản chỉ là "thêm một khối", không phải "sửa code cũ" — an toàn hơn nhiều khi engine bundle bị minify.

---

## Dùng `adapters_5_network.md` thế nào

Chọn **đúng một** khối, dán vào ngay trước `</body>` của file đã làm sạch. Đừng dán
nhiều khối cùng lúc — cả năm đều ghi đè `Luna.Unity.Playable.InstallFullGame`, khối nào
chạy sau sẽ thắng, và bạn sẽ mất nhiều thời gian tìm hiểu vì sao CTA gọi sai API.

Riêng Google còn phải chèn thêm hai thẻ vào `<head>`. Riêng TikTok còn phải thêm SDK **trước** adapter và bỏ `config.json` vào ZIP.

Kiểm sau khi dán: `grep -c 'LUNA-PA-CONVERTER' build.html` phải ra **1**, không được **2**.

---

## Thẻ cuối của unityads gốc

456 byte, đã format lại cho dễ đọc (trong file là một dòng minify):

```js
window.addEventListener("luna:build", function(){
  Bridge.ready(function(){
    Luna.Unity.Playable.InstallFullGame = function(ios, android){
      window.pi.logCta();
      ios     = ios     || window.$environment.packageConfig.iosLink;
      android = android || window.$environment.packageConfig.androidLink;
      const url = /iphone|ipad|ipod|macintosh/i.test(navigator.userAgent.toLowerCase()) ? ios : android;

      "undefined" != typeof mraid
        ? mraid.open(url)                                    // ← đường duy nhất Luna dùng
        : (console.warn("Mraid is not defined"),
           window.open(url, "_blank"));                      // ← fallback khi không có mraid
    };
  });
});
```

Đọc kỹ nhánh `else`: **nếu network không inject `mraid`, CTA rơi xuống `window.open()`**. Game vẫn chạy, store vẫn mở, nên nhìn bằng mắt tưởng ổn — nhưng network không đếm được click. Đó chính là toàn bộ lý do phải thay thẻ này ở Mintegral, Google và Meta.

---

## Năm network khác nhau ở đâu

Cả năm adapter dùng chung một khung: helper `storeUrl()`, vòng poll 100 ms ghi đè `InstallFullGame` + `GameEnded`, cờ `__paConverter` để không gán lại vô ích.

Phần thực sự khác nhau chỉ là thân hàm CTA:

```js
// ── Mintegral ────────────────────────────────────────────
if (typeof window.install === "function"){ window.install(); return; }
if (typeof window.openStore === "function"){ window.openStore(); return; }
if (typeof mraid !== "undefined" && mraid.open){ mraid.open(storeUrl(...)); return; }
window.open(storeUrl(...), "_blank");

// ── Google Ads ───────────────────────────────────────────
if (typeof ExitApi !== "undefined" && ExitApi.exit){ ExitApi.exit(); return; }
if (typeof window.clickTag === "string" && window.clickTag){ window.open(window.clickTag, "_blank"); return; }
if (typeof mraid !== "undefined" && mraid.open){ mraid.open(storeUrl(...)); return; }
window.open(storeUrl(...), "_blank");

// ── AppLovin ─────────────────────────────────────────────
al("CTA_CLICKED");
if (mraid.getState && mraid.getState() === "loading") {      // gate chờ ready
  mraid.addEventListener("ready", function once(){
    mraid.removeEventListener("ready", once);
    mraid.open(url);
  });
  return;
}
mraid.open(url);

// ── Meta ─────────────────────────────────────────────────
if (hasFb("onCTAClick")) { FbPlayableAd.onCTAClick(); return; }
window.open(storeUrl(...), "_blank");

// ── TikTok ───────────────────────────────────────────────
if (typeof window.openAppStore === "function"){ window.openAppStore(); return; }
window.open(storeUrl(...), "_blank");     // KHÔNG có nhánh mraid — TikTok cấm MRAID
```

Và phần `GameEnded`:

| Network | `GameEnded` làm gì thêm |
|---|---|
| Mintegral | `window.gameEnd()` — **bắt buộc**, có cờ `endedSent` chặn gọi 2 lần |
| Google Ads | không gì cả — Google không có API game-end |
| AppLovin | `ALPlayableAnalytics.trackEvent("ENDCARD_SHOWN")` |
| Meta | `FbPlayableAd.logLevelComplete("game_end")` |
| TikTok | không có API game-end |

Ngoài ra:

- **Mintegral** định nghĩa thêm `window.gameStart` / `window.gameClose` để network gọi ngược vào, và gọi `window.gameReady()` ở `luna:start`.
- **AppLovin** có thêm funnel state machine (`LOADING → LOADED → DISPLAYED`) và 7 challenge event wire bằng `Object.defineProperty` — đây là lý do adapter của nó dài gấp đôi ba cái kia.
- **Meta** có thêm `FbPlayableAd.logGameLoad()` gọi một lần, bắt cả `luna:build` lẫn `luna:start` vì Luna dispatch ngược thứ tự.
- **TikTok** là adapter ngắn nhất (1.912 B) vì bỏ hẳn nhánh MRAID, nhưng lại là network cần nhiều thứ ngoài adapter nhất: SDK riêng đặt trước adapter, và `config.json` trong ZIP.

---

## Vì sao dùng poll thay vì sửa thẳng thẻ cũ

```js
var tries = 0;
var iv = setInterval(function(){
  tries++;
  var P = window.Luna && window.Luna.Unity && window.Luna.Unity.Playable;
  var L = window.Luna && window.Luna.Unity && window.Luna.Unity.LifeCycle;
  if (P && P.InstallFullGame && P.InstallFullGame.__paConverter !== "mintegral") P.InstallFullGame = mtgInstall;
  if (L && !(L.GameEnded && L.GameEnded.__paConverter === "mintegral"))          L.GameEnded      = mtgGameEnded;
  if (tries > 600) clearInterval(iv);      // bỏ cuộc sau 60 s
}, 100);
```

Luna gán `InstallFullGame` bên trong `Bridge.ready()` ở event `luna:build`. Nếu adapter cũng nghe `luna:build` thì nó có thể chạy **trước** Luna rồi bị Luna ghi đè lại. Poll thì luôn thắng, bất kể thứ tự.

Cờ `__paConverter` vừa để tránh gán lại mỗi 100 ms, vừa là cách kiểm khi test: `Luna.Unity.Playable.InstallFullGame.__paConverter` phải trả về đúng tên network.

---

## Ba dòng kiểm nhanh

```bash
# base đã sạch chưa
grep -c 'devToolsAreOpen' build.html                        # 0
grep -oE 'https?://[a-zA-Z0-9._-]+' build.html | sort -u    # chỉ store link (+ exitapi.js nếu là Google)

# adapter đã vào đúng chưa
grep -c 'LUNA-PA-CONVERTER' build.html                      # 1
```
