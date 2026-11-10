# Adapter của 5 network

Thẻ `<script>` thêm vào **ngay trước `</body>`** của file đã làm sạch.

Chọn **đúng một** khối. Cả năm đều ghi đè `Luna.Unity.Playable.InstallFullGame` — dán hai khối thì khối chạy sau thắng.

Thẻ CTA gốc của Luna **giữ nguyên, không xoá**. Adapter đứng sau nó và ghi đè lúc runtime.

| Network | Khối | Kích thước | Thêm ngoài adapter |
|---|---|---|---|
| Mintegral | [1](#1--mintegral) | 2425 B | — |
| Google Ads | [2](#2--google-ads) | 1837 B | chèn `<head>` |
| AppLovin | [3](#3--applovin) | 5081 B | — |
| Meta | [4](#4--meta) | 2913 B | — |
| TikTok | [5](#5--tiktok) | 1912 B | SDK trước adapter + `config.json` trong ZIP |

Toàn bộ code dưới đây trích nguyên văn từ build đã pass preview tool của từng network.

---

## Khung chung của cả 5

**Vòng poll** — dùng poll chứ không `addEventListener("luna:build")`, vì listener của mình có thể chạy trước listener của Luna rồi bị ghi đè lại:

```js
var iv = setInterval(function(){
  var P = window.Luna && window.Luna.Unity && window.Luna.Unity.Playable;
  var L = window.Luna && window.Luna.Unity && window.Luna.Unity.LifeCycle;
  if (P && P.InstallFullGame && P.InstallFullGame.__paConverter !== "<net>") P.InstallFullGame = <cta>;
  if (L && !(L.GameEnded && L.GameEnded.__paConverter === "<net>"))          L.GameEnded      = <ended>;
  if (tries > 600) clearInterval(iv);
}, 100);
```

**Helper store link** — giống hệt nhau ở cả 5:

```js
function storeUrl(ios, android){
  var cfg = (window.$environment && window.$environment.packageConfig) || {};
  ios = ios || cfg.iosLink; android = android || cfg.androidLink;
  var ua = (window.navigator.userAgent || "").toLowerCase();
  return /iphone|ipad|ipod|macintosh/i.test(ua) ? ios : android;
}
```

**Cờ `DBG`** — để `false` khi giao file.

**Tên API viết nguyên văn** — validator quét chuỗi literal trong source, không chạy code.

---

## Khác nhau ở đâu

CTA:

```js
// Mintegral
if (typeof window.install === "function"){ window.install(); return; }

// Google Ads
if (typeof ExitApi !== "undefined" && ExitApi.exit){ ExitApi.exit(); return; }

// AppLovin — có gate chờ mraid ready
if (mraid.getState && mraid.getState() === "loading") { /* chờ event ready rồi mới open */ }
mraid.open(url);

// Meta
if (hasFb("onCTAClick")) { FbPlayableAd.onCTAClick(); return; }

// TikTok
if (typeof window.openAppStore === "function"){ window.openAppStore(); return; }
```

`GameEnded`:

| Network | Gọi thêm |
|---|---|
| Mintegral | `window.gameEnd()` — bắt buộc, cờ `endedSent` chặn gọi 2 lần |
| Google Ads | không có API game-end |
| AppLovin | `ALPlayableAnalytics.trackEvent("ENDCARD_SHOWN")` |
| Meta | `FbPlayableAd.logLevelComplete("game_end")` |
| TikTok | không có API game-end |

Riêng từng network: Mintegral định nghĩa `window.gameStart` / `gameClose` / gọi `gameReady`; AppLovin có funnel state machine và 7 challenge event; Meta có `logGameLoad` gọi một lần; TikTok **không có nhánh MRAID nào** — xem mục 5.

---

## 1 · Mintegral

```html
<script>
/* LUNA-PA-CONVERTER v1.0 -- Mintegral adapter */
!function(){
  var DBG = false;
  function log(m){ if (DBG) { try { console.log("mtg-adapter: " + m); } catch(e){} } }

  function storeUrl(ios, android){
    var cfg = (window.$environment && window.$environment.packageConfig) || {};
    ios = ios || cfg.iosLink; android = android || cfg.androidLink;
    var ua = (window.navigator.userAgent || "").toLowerCase();
    return /iphone|ipad|ipod|macintosh/i.test(ua) ? ios : android;
  }

  function mtgInstall(ios, android){
    try { if (window.pi && window.pi.logCta) window.pi.logCta(); } catch(e){}
    if (typeof window.install === "function"){ log("install()"); window.install(); return; }
    if (typeof window.openStore === "function"){ log("openStore()"); window.openStore(); return; }
    if (typeof mraid !== "undefined" && mraid.open){ log("mraid.open()"); mraid.open(storeUrl(ios, android)); return; }
    log("fallback window.open");
    window.open(storeUrl(ios, android), "_blank");
  }
  mtgInstall.__paConverter = "mintegral";

  var endedSent = false;
  function mtgGameEnded(){
    try { window.dispatchEvent(new Event("luna:ended")); } catch(e){}
    try { if (window.pi && window.pi.logGameEnd) window.pi.logGameEnd(); } catch(e){}
    if (!endedSent && typeof window.gameEnd === "function"){ endedSent = true; log("gameEnd()"); window.gameEnd(); }
  }
  mtgGameEnded.__paConverter = "mintegral";

  if (typeof window.gameStart !== "function"){
    window.gameStart = function(){ try { window.dispatchEvent(new Event("luna:resume")); } catch(e){} };
  }
  if (typeof window.gameClose !== "function"){
    window.gameClose = function(){ try { window.dispatchEvent(new Event("luna:pause")); } catch(e){} };
  }

  var tries = 0;
  var iv = setInterval(function(){
    tries++;
    try {
      var P = window.Luna && window.Luna.Unity && window.Luna.Unity.Playable;
      var L = window.Luna && window.Luna.Unity && window.Luna.Unity.LifeCycle;
      if (P && P.InstallFullGame && P.InstallFullGame.__paConverter !== "mintegral") P.InstallFullGame = mtgInstall;
      if (L && !(L.GameEnded && L.GameEnded.__paConverter === "mintegral")) L.GameEnded = mtgGameEnded;
    } catch(e){}
    if (tries > 600) clearInterval(iv);
  }, 100);

  window.addEventListener("luna:start", function(){
    if (typeof window.gameReady === "function"){ try { window.gameReady(); } catch(e){} }
  });
}();
</script>
```

---

## 2 · Google Ads

Chèn vào `<head>`, ngay trước `</head>` — `content` lấy từ `orientation` trong config Luna:

```html
<meta name="ad.orientation" content="portrait"><script type="text/javascript" src="https://tpc.googlesyndication.com/pagead/gadgets/html5/api/exitapi.js"></script>
```

Chèn trước `</body>`:

```html
<script>
/* LUNA-PA-CONVERTER v1.0 -- Google Ads adapter */
!function(){
  var DBG = false;
  function log(m){ if (DBG) { try { console.log("gads-adapter: " + m); } catch(e){} } }

  function storeUrl(ios, android){
    var cfg = (window.$environment && window.$environment.packageConfig) || {};
    ios = ios || cfg.iosLink; android = android || cfg.androidLink;
    var ua = (window.navigator.userAgent || "").toLowerCase();
    return /iphone|ipad|ipod|macintosh/i.test(ua) ? ios : android;
  }

  function gExit(ios, android){
    try { if (window.pi && window.pi.logCta) window.pi.logCta(); } catch(e){}
    if (typeof ExitApi !== "undefined" && ExitApi.exit){ log("ExitApi.exit()"); ExitApi.exit(); return; }
    if (typeof window.clickTag === "string" && window.clickTag){ log("clickTag"); window.open(window.clickTag, "_blank"); return; }
    if (typeof mraid !== "undefined" && mraid.open){ log("mraid.open()"); mraid.open(storeUrl(ios, android)); return; }
    log("fallback window.open");
    window.open(storeUrl(ios, android), "_blank");
  }
  gExit.__paConverter = "google";

  function gGameEnded(){
    try { window.dispatchEvent(new Event("luna:ended")); } catch(e){}
    try { if (window.pi && window.pi.logGameEnd) window.pi.logGameEnd(); } catch(e){}
  }
  gGameEnded.__paConverter = "google";

  var tries = 0;
  var iv = setInterval(function(){
    tries++;
    try {
      var P = window.Luna && window.Luna.Unity && window.Luna.Unity.Playable;
      var L = window.Luna && window.Luna.Unity && window.Luna.Unity.LifeCycle;
      if (P && P.InstallFullGame && P.InstallFullGame.__paConverter !== "google") P.InstallFullGame = gExit;
      if (L && !(L.GameEnded && L.GameEnded.__paConverter === "google")) L.GameEnded = gGameEnded;
    } catch(e){}
    if (tries > 600) clearInterval(iv);
  }, 100);
}();
</script>
```

---

## 3 · AppLovin

```html
<script>
/* LUNA-PA-CONVERTER v1.0 -- AppLovin adapter */
!function(){
  var DBG = false;
  function log(m){ if (DBG) { try { console.log("al-adapter: " + m); } catch(e){} } }

  /* AppLovin HTML analytics -- luon bao boc theo dung yeu cau cua AppLovin,
     de creative van chay binh thuong khi test local hoac chay o network khac */
  function al(ev){
    try {
      if (typeof window.ALPlayableAnalytics !== "undefined" && window.ALPlayableAnalytics.trackEvent) {
        window.ALPlayableAnalytics.trackEvent(ev);
        log(ev);
      }
    } catch(e){}
  }

  function storeUrl(ios, android){
    var cfg = (window.$environment && window.$environment.packageConfig) || {};
    ios = ios || cfg.iosLink; android = android || cfg.androidLink;
    var ua = (window.navigator.userAgent || "").toLowerCase();
    return /iphone|ipad|ipod|macintosh/i.test(ua) ? ios : android;
  }

  /* AppLovin bat buoc: khong goi MRAID API truoc khi mraid ready */
  function mraidOpen(url){
    if (typeof mraid === "undefined" || !mraid.open) return false;
    var go = function(){ try { log("mraid.open()"); mraid.open(url); } catch(e){} };
    try {
      if (mraid.getState && mraid.getState() === "loading") {
        log("mraid dang loading, cho ready");
        mraid.addEventListener("ready", function once(){
          try { mraid.removeEventListener("ready", once); } catch(e){}
          go();
        });
        return true;
      }
    } catch(e){}
    go();
    return true;
  }

  function alInstall(ios, android){
    try { if (window.pi && window.pi.logCta) window.pi.logCta(); } catch(e){}
    al("CTA_CLICKED");
    var url = storeUrl(ios, android);
    if (mraidOpen(url)) return;
    log("mraid khong co, fallback window.open");
    window.open(url, "_blank");
  }
  alInstall.__paConverter = "applovin";

  var endcardSent = false;
  function alGameEnded(){
    try { window.dispatchEvent(new Event("luna:ended")); } catch(e){}
    try { if (window.pi && window.pi.logGameEnd) window.pi.logGameEnd(); } catch(e){}
    if (!endcardSent){ endcardSent = true; al("ENDCARD_SHOWN"); }
  }
  alGameEnded.__paConverter = "applovin";

  /* Luna.Unity.Analytics.Applovin -- build unityads chi tao object rong,
     nen neu game co goi cac ham nay thi chung khong di dau ca. Map lai vao AppLovin. */
  var CHALLENGE = {
    LogChallengeStarted: "CHALLENGE_STARTED",
    LogChallengeFailed:  "CHALLENGE_FAILED",
    LogChallengeRetry:   "CHALLENGE_RETRY",
    LogChallengePass25:  "CHALLENGE_PASS_25",
    LogChallengePass50:  "CHALLENGE_PASS_50",
    LogChallengePass75:  "CHALLENGE_PASS_75",
    LogChallengeSolved:  "CHALLENGE_SOLVED"
  };
  /* Bridge dinh nghia cac member nay la accessor (get/set) khong enumerable, nen
     dung defineProperty de chac chan ghi de duoc, fallback ve phep gan thuong. */
  function setFn(ns, name, ev){
    var f = function(){ al(ev); };
    f.__paConverter = "applovin";
    try {
      Object.defineProperty(ns, name, { value: f, writable: true, enumerable: false, configurable: true });
    } catch(e) {
      try { ns[name] = f; } catch(e2) { return false; }
    }
    try { return !!ns[name] && ns[name].__paConverter === "applovin"; } catch(e){ return false; }
  }
  function wireChallenge(ns){
    var ok = true;
    for (var k in CHALLENGE) {
      if (!CHALLENGE.hasOwnProperty(k)) continue;
      /* Bridge sinh ca ten tran va ten co hau to $1 */
      if (!setFn(ns, k, CHALLENGE[k])) ok = false;
      if (!setFn(ns, k + "$1", CHALLENGE[k])) ok = false;
    }
    return ok;
  }
  function challengeWired(ns){
    try {
      var f = ns.LogChallengeStarted;
      return !!f && f.__paConverter === "applovin";
    } catch(e){ return false; }
  }

  var tries = 0;
  var iv = setInterval(function(){
    tries++;
    try {
      var U = window.Luna && window.Luna.Unity;
      var P = U && U.Playable;
      var L = U && U.LifeCycle;
      var A = U && U.Analytics;
      if (P && P.InstallFullGame && P.InstallFullGame.__paConverter !== "applovin") P.InstallFullGame = alInstall;
      if (L && !(L.GameEnded && L.GameEnded.__paConverter === "applovin")) L.GameEnded = alGameEnded;
      if (A) {
        if (!A.Applovin) A.Applovin = {};
        /* Bridge co the thay the ca object nay sau khi khoi tao -> kiem tra ham
           thuc te co phai cua minh khong, thay vi danh dau mot lan roi bo qua */
        if (!challengeWired(A.Applovin)) wireChallenge(A.Applovin);
      }
    } catch(e){}
    if (tries > 600) clearInterval(iv);
  }, 100);

  /* Funnel LOADING -> LOADED -> DISPLAYED phai dung thu tu va khong lap.
     Khong tin thu tu event noi bo cua Luna: ban 3.1.0 dispatch luna:start
     TRUOC luna:build, nen state machine tu bu cac buoc con thieu. */
  var FUNNEL = ["LOADING", "LOADED", "DISPLAYED"], sent = 0;
  function mark(stage){
    var upto = FUNNEL.indexOf(stage) + 1;
    while (sent < upto) { al(FUNNEL[sent]); sent++; }
  }
  mark("LOADING");
  window.addEventListener("luna:build", function(){ mark("LOADED"); });
  window.addEventListener("luna:start", function(){ mark("DISPLAYED"); });
}();
</script>
```

---

## 4 · Meta

```html
<script>
/* LUNA-PA-CONVERTER v1.0 -- Meta / Facebook adapter */
!function(){
  var DBG = false;
  function log(m){ if (DBG) { try { console.log("fb-adapter: " + m); } catch(e){} } }

  /* SDK cua Meta duoc chinh platform inject, khong co khi test local ->
     luon kiem tra truoc khi goi.
     QUAN TRONG: playable preview cua Meta quet chuoi literal trong source, nen
     moi call site phai viet nguyen van ten day du cua ham. Goi qua bien trung
     gian se bi bao thieu API du code chay dung. */
  function hasFb(fn){
    try { return typeof FbPlayableAd !== "undefined" && typeof FbPlayableAd[fn] === "function"; }
    catch(e){ return false; }
  }

  function storeUrl(ios, android){
    var cfg = (window.$environment && window.$environment.packageConfig) || {};
    ios = ios || cfg.iosLink; android = android || cfg.androidLink;
    var ua = (window.navigator.userAgent || "").toLowerCase();
    return /iphone|ipad|ipod|macintosh/i.test(ua) ? ios : android;
  }

  function fbInstall(ios, android){
    try { if (window.pi && window.pi.logCta) window.pi.logCta(); } catch(e){}
    if (hasFb("onCTAClick")) {
      log("FbPlayableAd.onCTAClick()");
      try { FbPlayableAd.onCTAClick(); return; } catch(e){}
    }
    if (typeof mraid !== "undefined" && mraid.open){ log("mraid.open()"); mraid.open(storeUrl(ios, android)); return; }
    log("khong co SDK, fallback window.open");
    window.open(storeUrl(ios, android), "_blank");
  }
  fbInstall.__paConverter = "meta";

  var endedSent = false;
  function fbGameEnded(){
    try { window.dispatchEvent(new Event("luna:ended")); } catch(e){}
    try { if (window.pi && window.pi.logGameEnd) window.pi.logGameEnd(); } catch(e){}
    if (!endedSent) {
      endedSent = true;
      if (hasFb("logLevelComplete")) {
        log("FbPlayableAd.logLevelComplete(game_end)");
        try { FbPlayableAd.logLevelComplete("game_end"); } catch(e){}
      }
    }
  }
  fbGameEnded.__paConverter = "meta";

  var loadSent = false;
  function logLoadOnce(){
    if (loadSent) return;
    if (hasFb("logGameLoad")) {
      loadSent = true;
      log("FbPlayableAd.logGameLoad()");
      try { FbPlayableAd.logGameLoad(); } catch(e){}
    }
  }

  var tries = 0;
  var iv = setInterval(function(){
    tries++;
    try {
      var P = window.Luna && window.Luna.Unity && window.Luna.Unity.Playable;
      var L = window.Luna && window.Luna.Unity && window.Luna.Unity.LifeCycle;
      if (P && P.InstallFullGame && P.InstallFullGame.__paConverter !== "meta") P.InstallFullGame = fbInstall;
      if (L && !(L.GameEnded && L.GameEnded.__paConverter === "meta")) L.GameEnded = fbGameEnded;
    } catch(e){}
    if (tries > 600) clearInterval(iv);
  }, 100);

  /* Luna 3.1.0 dispatch luna:start truoc luna:build -> bat ca hai, chi log 1 lan */
  window.addEventListener("luna:build", logLoadOnce);
  window.addEventListener("luna:start", logLoadOnce);
}();
</script>
```

---

## 5 · TikTok

TikTok khác 4 network kia ở ba chỗ, cả ba đều bắt buộc.

**a) SDK của TikTok phải nằm trước adapter.** TikTok yêu cầu script này ở cuối `<body>`, **trước mọi custom JS** — nó là thứ định nghĩa `window.openAppStore`:

```html
<script src="https://sf16-muse-va.ibytedtos.com/obj/union-fe-nc-i18n/Playable/sdk/Playable-sdk.js"></script>
```

**b) Adapter không có nhánh MRAID nào.** TikTok cấm creative dựa trên chuẩn MRAID, nên CTA chỉ có `window.openAppStore()` rồi thẳng xuống `window.open` để test local — không có `mraid.open` như 4 network kia:

```html
<script>
/* LUNA-PA-CONVERTER v1.0 -- TikTok adapter */
!function(){
  var DBG = false;
  function log(m){ if (DBG) { try { console.log("tt-adapter: " + m); } catch(e){} } }

  function storeUrl(ios, android){
    var cfg = (window.$environment && window.$environment.packageConfig) || {};
    ios = ios || cfg.iosLink; android = android || cfg.androidLink;
    var ua = (window.navigator.userAgent || "").toLowerCase();
    return /iphone|ipad|ipod|macintosh/i.test(ua) ? ios : android;
  }

  /* TikTok cam creative dua tren chuan quang cao cu -> adapter nay khong goi
     bat ky API nao cua chuan do. Chi window.openAppStore() do SDK cua TikTok inject.
     Nhanh window.open ben duoi chi de test local, tren TikTok khong bao gio chay den. */
  function ttInstall(ios, android){
    try { if (window.pi && window.pi.logCta) window.pi.logCta(); } catch(e){}
    if (typeof window.openAppStore === "function"){
      log("window.openAppStore()");
      try { window.openAppStore(); return; } catch(e){}
    }
    log("chua co SDK TikTok, fallback window.open");
    window.open(storeUrl(ios, android), "_blank");
  }
  ttInstall.__paConverter = "tiktok";

  function ttGameEnded(){
    try { window.dispatchEvent(new Event("luna:ended")); } catch(e){}
    try { if (window.pi && window.pi.logGameEnd) window.pi.logGameEnd(); } catch(e){}
  }
  ttGameEnded.__paConverter = "tiktok";

  var tries = 0;
  var iv = setInterval(function(){
    tries++;
    try {
      var P = window.Luna && window.Luna.Unity && window.Luna.Unity.Playable;
      var L = window.Luna && window.Luna.Unity && window.Luna.Unity.LifeCycle;
      if (P && P.InstallFullGame && P.InstallFullGame.__paConverter !== "tiktok") P.InstallFullGame = ttInstall;
      if (L && !(L.GameEnded && L.GameEnded.__paConverter === "tiktok")) L.GameEnded = ttGameEnded;
    } catch(e){}
    if (tries > 600) clearInterval(iv);
  }, 100);
}();
</script>
```

**c) ZIP phải có `config.json` ở thư mục gốc**, cạnh `index.html`:

```json
{
  "playable_orientation": 1,
  "playable_languages": ["en"]
}
```

`playable_orientation`: `0` = responsive, `1` = portrait, `2` = landscape — map từ `orientation` trong config Luna.
`playable_languages`: TikTok hỗ trợ `en`, `ja`, `ko`, `zh-Hant`.

> Nếu bị reject vì key sai tên, thử `Playable_orientation` viết hoa chữ P — help article của TikTok viết hoa trong ví dụ, còn bảng của Unity Playworks viết thường. Hai nguồn không khớp nhau.

**Còn lại trong file:** code MRAID của Luna vẫn nằm trong engine bundle (`mraid.open`, `getMraidAdData`, `viewableChange`). Chúng trơ vì TikTok không inject `mraid`, nhưng nếu bị reject vì MRAID thì đây là chỗ cần soi — không phải adapter.
