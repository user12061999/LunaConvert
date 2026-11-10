#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LunaPA Converter - chuyen playable ad export tu Luna Playground (Unity Ads / MRAID)
sang build hop le cho Mintegral, Google Ads (App campaigns / AdMob), AppLovin, Meta va TikTok.

Chi dung Python standard library. Khong can cai gi.

    python3 convert_pa.py INPUT.zip
    python3 convert_pa.py INPUT.zip --universal        # dung universal adapter (feature-detection)
    python3 convert_pa.py INPUT.html -n mintegral
    python3 convert_pa.py INPUT.zip -n mintegral,google,applovin,meta,tiktok -o ./dist
    python3 convert_pa.py INPUT.zip --inspect          # chi soi file, khong xuat

INPUT co the la .html hoac .zip tai tu playground.lunalabs.io.
"""

import argparse
import io
import os
import re
import sys
import zipfile

VERSION = "1.0"
MARKER = "LUNA-PA-CONVERTER"

# ---------------------------------------------------------------------------
# Gioi han cua tung network (bytes)
# ---------------------------------------------------------------------------
LIMIT_5MB = 5 * 1024 * 1024

NETWORKS = {
    "mintegral": {
        "label": "Mintegral / Mindworks (PlayTurbo)",
        "limit_html": LIMIT_5MB,
        "limit_zip": LIMIT_5MB,
        "emit_html": True,
        "emit_zip": True,
        "needs_exitapi": False,
        "needs_orientation_meta": False,
    },
    "google": {
        "label": "Google Ads (App campaigns / AdMob)",
        "limit_html": None,          # Google chi nhan ZIP
        "limit_zip": LIMIT_5MB,
        "emit_html": False,
        "emit_zip": True,
        "needs_exitapi": True,
        "needs_orientation_meta": True,
    },
    "applovin": {
        "label": "AppLovin (AppDiscovery / MAX)",
        "limit_html": LIMIT_5MB,
        "limit_zip": None,           # AppLovin chi nhan single HTML, khong ZIP
        "emit_html": True,
        "emit_zip": False,
        "needs_exitapi": False,
        "needs_orientation_meta": False,
    },
    "tiktok": {
        "label": "TikTok (Ads Manager)",
        # TikTok chi nhan ZIP: index.html + config.json o thu muc goc.
        # Doc chinh thuc cua TikTok: <5MB nen. Bang cua Luna ghi 3MB -> canh bao tu 3MB.
        "limit_html": None,
        "limit_zip": LIMIT_5MB,
        "emit_html": False,
        "emit_zip": True,
        "needs_exitapi": False,
        "needs_orientation_meta": False,
        "needs_tiktok_sdk": True,
        "zip_extra": "tiktok_config",
        "soft_limit_zip": 3 * 1024 * 1024,
    },
    "meta": {
        "label": "Meta / Facebook (Ads Manager)",
        # Meta: single HTML toi da 2MB, HOAC ZIP toi da 5MB (<=100 files)
        "limit_html": 2 * 1024 * 1024,
        "limit_zip": LIMIT_5MB,
        "emit_html": "if_fits",      # chi xuat single HTML khi lot duoi 2MB
        "emit_zip": True,
        "needs_exitapi": False,
        "needs_orientation_meta": False,
    },
}

# Host debug-only, thay bang about:blank
DEBUG_HOSTS = ("mrdoob.github.io", "cdn.jsdelivr.net")

# Host duoc phep ton tai trong file (khong phai runtime request, hoac network yeu cau)
ALLOWED_HOSTS = ("play.google.com", "apps.apple.com", "itunes.apple.com",
                 "tpc.googlesyndication.com", "sf16-muse-va.ibytedtos.com")


# ---------------------------------------------------------------------------
# Adapter inject vao cuoi <body>
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Ban RUT GON cua adapter (mac dinh). Cung logic voi ban readable o tren,
# nhung da minify + doi ten bien + bo comment/log, va co marker khong lo ten
# network. Muc dich: phan them vao khong noi bat giua bundle da minify cua Luna.
# Chuoi API ma validator quet van con nguyen van - bat buoc phai vay.
# Sinh bang terser, da doi chieu hanh vi runtime voi ban readable.
# ---------------------------------------------------------------------------
ADAPTER_MIN = {
    "mintegral": r"""!function(){function n(n,i){var t=window.$environment&&window.$environment.packageConfig||{};n=n||t.iosLink,i=i||t.androidLink;var o=(window.navigator.userAgent||'').toLowerCase();return/iphone|ipad|ipod|macintosh/i.test(o)?n:i}function i(i,t){try{window.pi&&window.pi.logCta&&window.pi.logCta()}catch(n){}return'function'==typeof window.install?void window.install():'function'==typeof window.openStore?void window.openStore():'undefined'!=typeof mraid&&mraid.open?void mraid.open(n(i,t)):void window.open(n(i,t),'_blank')}i._lz='q3';var t=!1;function o(){try{window.dispatchEvent(new Event('luna:ended'))}catch(n){}try{window.pi&&window.pi.logGameEnd&&window.pi.logGameEnd()}catch(n){}t||'function'!=typeof window.gameEnd||(t=!0,window.gameEnd())}o._lz='q3','function'!=typeof window.gameStart&&(window.gameStart=function(){try{window.dispatchEvent(new Event('luna:resume'))}catch(n){}}),'function'!=typeof window.gameClose&&(window.gameClose=function(){try{window.dispatchEvent(new Event('luna:pause'))}catch(n){}});var e=0,a=setInterval(function(){e++;try{var n=window.Luna&&window.Luna.Unity&&window.Luna.Unity.Playable,t=window.Luna&&window.Luna.Unity&&window.Luna.Unity.LifeCycle;n&&n.InstallFullGame&&'q3'!==n.InstallFullGame._lz&&(n.InstallFullGame=i),!t||t.GameEnded&&'q3'===t.GameEnded._lz||(t.GameEnded=o)}catch(n){}e>600&&clearInterval(a)},100);window.addEventListener('luna:start',function(){if('function'==typeof window.gameReady)try{window.gameReady()}catch(n){}})}();""",
    "google": r"""!function(){function n(n,i){var o=window.$environment&&window.$environment.packageConfig||{};n=n||o.iosLink,i=i||o.androidLink;var e=(window.navigator.userAgent||'').toLowerCase();return/iphone|ipad|ipod|macintosh/i.test(e)?n:i}function i(i,o){try{window.pi&&window.pi.logCta&&window.pi.logCta()}catch(n){}return'undefined'!=typeof ExitApi&&ExitApi.exit?void ExitApi.exit():'string'==typeof window.clickTag&&window.clickTag?void window.open(window.clickTag,'_blank'):'undefined'!=typeof mraid&&mraid.open?void mraid.open(n(i,o)):void window.open(n(i,o),'_blank')}function o(){try{window.dispatchEvent(new Event('luna:ended'))}catch(n){}try{window.pi&&window.pi.logGameEnd&&window.pi.logGameEnd()}catch(n){}}i._lz='k8',o._lz='k8';var e=0,a=setInterval(function(){e++;try{var n=window.Luna&&window.Luna.Unity&&window.Luna.Unity.Playable,d=window.Luna&&window.Luna.Unity&&window.Luna.Unity.LifeCycle;n&&n.InstallFullGame&&'k8'!==n.InstallFullGame._lz&&(n.InstallFullGame=i),!d||d.GameEnded&&'k8'===d.GameEnded._lz||(d.GameEnded=o)}catch(n){}e>600&&clearInterval(a)},100)}();""",
    "applovin": r"""!function(){function n(n){try{void 0!==window.ALPlayableAnalytics&&window.ALPlayableAnalytics.trackEvent&&window.ALPlayableAnalytics.trackEvent(n)}catch(n){}}function a(a,e){try{window.pi&&window.pi.logCta&&window.pi.logCta()}catch(n){}n('CTA_CLICKED');var t=function(n,a){var e=window.$environment&&window.$environment.packageConfig||{};n=n||e.iosLink,a=a||e.androidLink;var t=(window.navigator.userAgent||'').toLowerCase();return/iphone|ipad|ipod|macintosh/i.test(t)?n:a}(a,e);(function(n){if('undefined'==typeof mraid||!mraid.open)return!1;var a=function(){try{mraid.open(n)}catch(n){}};try{if(mraid.getState&&'loading'===mraid.getState())return mraid.addEventListener('ready',function n(){try{mraid.removeEventListener('ready',n)}catch(n){}a()}),!0}catch(n){}return a(),!0})(t)||window.open(t,'_blank')}a._lz='w5';var e=!1;function t(){try{window.dispatchEvent(new Event('luna:ended'))}catch(n){}try{window.pi&&window.pi.logGameEnd&&window.pi.logGameEnd()}catch(n){}e||(e=!0,n('ENDCARD_SHOWN'))}t._lz='w5';var i={LogChallengeStarted:'CHALLENGE_STARTED',LogChallengeFailed:'CHALLENGE_FAILED',LogChallengeRetry:'CHALLENGE_RETRY',LogChallengePass25:'CHALLENGE_PASS_25',LogChallengePass50:'CHALLENGE_PASS_50',LogChallengePass75:'CHALLENGE_PASS_75',LogChallengeSolved:'CHALLENGE_SOLVED'};function o(a,e,t){var i=function(){n(t)};i._lz='w5';try{Object.defineProperty(a,e,{value:i,writable:!0,enumerable:!1,configurable:!0})}catch(n){try{a[e]=i}catch(n){return!1}}try{return!!a[e]&&'w5'===a[e]._lz}catch(n){return!1}}var r=0,l=setInterval(function(){r++;try{var n=window.Luna&&window.Luna.Unity,e=n&&n.Playable,d=n&&n.LifeCycle,c=n&&n.Analytics;e&&e.InstallFullGame&&'w5'!==e.InstallFullGame._lz&&(e.InstallFullGame=a),!d||d.GameEnded&&'w5'===d.GameEnded._lz||(d.GameEnded=t),c&&(c.Applovin||(c.Applovin={}),function(n){try{var a=n.LogChallengeStarted;return!!a&&'w5'===a._lz}catch(n){return!1}}(c.Applovin)||function(n){for(var a in i)i.hasOwnProperty(a)&&(o(n,a,i[a]),o(n,a+'$1',i[a]))}(c.Applovin))}catch(n){}r>600&&clearInterval(l)},100),d=['LOADING','LOADED','DISPLAYED'],c=0;function L(a){for(var e=d.indexOf(a)+1;c<e;)n(d[c]),c++}L('LOADING'),window.addEventListener('luna:build',function(){L('LOADED')}),window.addEventListener('luna:start',function(){L('DISPLAYED')})}();""",
    "meta": r"""!function(){function n(n){try{return'undefined'!=typeof FbPlayableAd&&'function'==typeof FbPlayableAd[n]}catch(n){return!1}}function a(n,a){var e=window.$environment&&window.$environment.packageConfig||{};n=n||e.iosLink,a=a||e.androidLink;var i=(window.navigator.userAgent||'').toLowerCase();return/iphone|ipad|ipod|macintosh/i.test(i)?n:a}function e(e,i){try{window.pi&&window.pi.logCta&&window.pi.logCta()}catch(n){}if(n('onCTAClick'))try{return void FbPlayableAd.onCTAClick()}catch(n){}'undefined'!=typeof mraid&&mraid.open?mraid.open(a(e,i)):window.open(a(e,i),'_blank')}e._lz='z2';var i=!1;function t(){try{window.dispatchEvent(new Event('luna:ended'))}catch(n){}try{window.pi&&window.pi.logGameEnd&&window.pi.logGameEnd()}catch(n){}if(!i&&(i=!0,n('logLevelComplete')))try{FbPlayableAd.logLevelComplete('game_end')}catch(n){}}t._lz='z2';var o=!1;function d(){if(!o&&n('logGameLoad')){o=!0;try{FbPlayableAd.logGameLoad()}catch(n){}}}var l=0,w=setInterval(function(){l++;try{var n=window.Luna&&window.Luna.Unity&&window.Luna.Unity.Playable,a=window.Luna&&window.Luna.Unity&&window.Luna.Unity.LifeCycle;n&&n.InstallFullGame&&'z2'!==n.InstallFullGame._lz&&(n.InstallFullGame=e),!a||a.GameEnded&&'z2'===a.GameEnded._lz||(a.GameEnded=t)}catch(n){}l>600&&clearInterval(w)},100);window.addEventListener('luna:build',d),window.addEventListener('luna:start',d)}();""",
    "tiktok": r"""!function(){function n(n,i){try{window.pi&&window.pi.logCta&&window.pi.logCta()}catch(n){}if('function'==typeof window.openAppStore)try{return void window.openAppStore()}catch(n){}window.open(function(n,i){var t=window.$environment&&window.$environment.packageConfig||{};n=n||t.iosLink,i=i||t.androidLink;var o=(window.navigator.userAgent||'').toLowerCase();return/iphone|ipad|ipod|macintosh/i.test(o)?n:i}(n,i),'_blank')}function i(){try{window.dispatchEvent(new Event('luna:ended'))}catch(n){}try{window.pi&&window.pi.logGameEnd&&window.pi.logGameEnd()}catch(n){}}n._lz='b6',i._lz='b6';var t=0,o=setInterval(function(){t++;try{var a=window.Luna&&window.Luna.Unity&&window.Luna.Unity.Playable,e=window.Luna&&window.Luna.Unity&&window.Luna.Unity.LifeCycle;a&&a.InstallFullGame&&'b6'!==a.InstallFullGame._lz&&(a.InstallFullGame=n),!e||e.GameEnded&&'b6'===e.GameEnded._lz||(e.GameEnded=i)}catch(n){}t>600&&clearInterval(o)},100)}();""",
}

MIN_MARKER = "._lz="   # dau nhan de tool tu nhan ra file da convert o che do rut gon


def adapter_mintegral(debug=False):
    return """
<script>
/* %s v%s -- Mintegral adapter */
!function(){
  var DBG = %s;
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
""" % (MARKER, VERSION, "true" if debug else "false")


def adapter_google(debug=False):
    return """
<script>
/* %s v%s -- Google Ads adapter */
!function(){
  var DBG = %s;
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
""" % (MARKER, VERSION, "true" if debug else "false")


def adapter_applovin(debug=False):
    return """
<script>
/* %s v%s -- AppLovin adapter */
!function(){
  var DBG = %s;
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
""" % (MARKER, VERSION, "true" if debug else "false")


def adapter_meta(debug=False):
    return """
<script>
/* %s v%s -- Meta / Facebook adapter */
!function(){
  var DBG = %s;
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
""" % (MARKER, VERSION, "true" if debug else "false")


TIKTOK_SDK_SRC = ("https://sf16-muse-va.ibytedtos.com/obj/union-fe-nc-i18n/"
                  "Playable/sdk/Playable-sdk.js")


def adapter_tiktok(debug=False):
    return """
<script>
/* %s v%s -- TikTok adapter */
!function(){
  var DBG = %s;
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
""" % (MARKER, VERSION, "true" if debug else "false")


# ---------------------------------------------------------------------------
# Universal Adapter (feature-detection cho moi network)
# ---------------------------------------------------------------------------
UNIVERSAL_MIN = r"""!function(){function n(n){try{void 0!==window.ALPlayableAnalytics&&window.ALPlayableAnalytics.trackEvent&&window.ALPlayableAnalytics.trackEvent(n)}catch(n){}}function t(n){try{return'undefined'!=typeof FbPlayableAd&&'function'==typeof FbPlayableAd[n]}catch(n){return!1}}function e(e,a){try{window.pi&&window.pi.logCta&&window.pi.logCta()}catch(n){}if(n('CTA_CLICKED'),t('onCTAClick'))try{return void FbPlayableAd.onCTAClick()}catch(n){}if('function'==typeof window.openAppStore)try{return void window.openAppStore()}catch(n){}if('undefined'!=typeof ExitApi&&ExitApi.exit)try{return void ExitApi.exit()}catch(n){}if('function'==typeof window.install)try{return void window.install()}catch(n){}if('function'==typeof window.openStore)try{return void window.openStore()}catch(n){}var i=function(n,t){var e=window.$environment&&window.$environment.packageConfig||{};n=n||e.iosLink,t=t||e.androidLink;var a=(window.navigator.userAgent||'').toLowerCase();return/iphone|ipad|ipod|macintosh/i.test(a)?n:t}(e,a);(function(n){if('undefined'==typeof mraid||!mraid.open)return!1;var t=function(){try{mraid.open(n)}catch(n){}};try{if(mraid.getState&&'loading'===mraid.getState())return mraid.addEventListener('ready',function n(){try{mraid.removeEventListener('ready',n)}catch(n){}t()}),!0}catch(n){}return t(),!0})(i)||window.open(i,'_blank')}var a=!1;function i(){try{window.dispatchEvent(new Event('luna:ended'))}catch(n){}try{window.pi&&window.pi.logGameEnd&&window.pi.logGameEnd()}catch(n){}if(!a){if(a=!0,'function'==typeof window.gameEnd)try{window.gameEnd()}catch(n){}if(n('ENDCARD_SHOWN'),t('logLevelComplete'))try{FbPlayableAd.logLevelComplete('game_end')}catch(n){}}}'function'!=typeof window.gameStart&&(window.gameStart=function(){try{window.dispatchEvent(new Event('luna:resume'))}catch(n){}}),'function'!=typeof window.gameClose&&(window.gameClose=function(){try{window.dispatchEvent(new Event('luna:pause'))}catch(n){}});var o={LogChallengeStarted:'CHALLENGE_STARTED',LogChallengeFailed:'CHALLENGE_FAILED',LogChallengeRetry:'CHALLENGE_RETRY',LogChallengePass25:'CHALLENGE_PASS_25',LogChallengePass50:'CHALLENGE_PASS_50',LogChallengePass75:'CHALLENGE_PASS_75',LogChallengeSolved:'CHALLENGE_SOLVED'};function r(t,e,a){var i=function(){n(a)};i.__k=1;try{Object.defineProperty(t,e,{value:i,writable:!0,enumerable:!1,configurable:!0})}catch(n){try{t[e]=i}catch(n){}}}var d=0,l=setInterval(function(){d++;try{var n=window.Luna&&window.Luna.Unity,t=n&&n.Playable,a=n&&n.LifeCycle,c=n&&n.Analytics;if(t&&t.InstallFullGame&&t.InstallFullGame!==e&&(t.InstallFullGame=e),a&&a.GameEnded!==i&&(a.GameEnded=i),c&&(c.Applovin||(c.Applovin={}),!function(n){try{var t=n.LogChallengeStarted;return!!t&&1===t.__k}catch(n){return!1}}(c.Applovin)))for(var w in o)o.hasOwnProperty(w)&&(r(c.Applovin,w,o[w]),r(c.Applovin,w+'$1',o[w]))}catch(n){}d>600&&clearInterval(l)},100),c=['LOADING','LOADED','DISPLAYED'],w=0,f=!1;function u(t){for(var e=c.indexOf(t)+1;w<e;)n(c[w]),w++}function y(){if(!f&&t('logGameLoad')){f=!0;try{FbPlayableAd.logGameLoad()}catch(n){}}}u('LOADING'),window.addEventListener('luna:build',function(){u('LOADED'),y()}),window.addEventListener('luna:start',function(){if(u('DISPLAYED'),y(),'function'==typeof window.gameReady)try{window.gameReady()}catch(n){}})}();"""

UNIVERSAL_NOMRAID_MIN = r"""!function(){function n(n){try{void 0!==window.ALPlayableAnalytics&&window.ALPlayableAnalytics.trackEvent&&window.ALPlayableAnalytics.trackEvent(n)}catch(n){}}function t(n){try{return'undefined'!=typeof FbPlayableAd&&'function'==typeof FbPlayableAd[n]}catch(n){return!1}}function e(e,i){try{window.pi&&window.pi.logCta&&window.pi.logCta()}catch(n){}if(n('CTA_CLICKED'),t('onCTAClick'))try{return void FbPlayableAd.onCTAClick()}catch(n){}if('function'==typeof window.openAppStore)try{return void window.openAppStore()}catch(n){}if('undefined'!=typeof ExitApi&&ExitApi.exit)try{return void ExitApi.exit()}catch(n){}if('function'==typeof window.install)try{return void window.install()}catch(n){}if('function'==typeof window.openStore)try{return void window.openStore()}catch(n){}window.open(function(n,t){var e=window.$environment&&window.$environment.packageConfig||{};n=n||e.iosLink,t=t||e.androidLink;var i=(window.navigator.userAgent||'').toLowerCase();return/iphone|ipad|ipod|macintosh/i.test(i)?n:t}(e,i),'_blank')}var i=!1;function a(){try{window.dispatchEvent(new Event('luna:ended'))}catch(n){}try{window.pi&&window.pi.logGameEnd&&window.pi.logGameEnd()}catch(n){}if(!i){if(i=!0,'function'==typeof window.gameEnd)try{window.gameEnd()}catch(n){}if(n('ENDCARD_SHOWN'),t('logLevelComplete'))try{FbPlayableAd.logLevelComplete('game_end')}catch(n){}}}'function'!=typeof window.gameStart&&(window.gameStart=function(){try{window.dispatchEvent(new Event('luna:resume'))}catch(n){}}),'function'!=typeof window.gameClose&&(window.gameClose=function(){try{window.dispatchEvent(new Event('luna:pause'))}catch(n){}});var o={LogChallengeStarted:'CHALLENGE_STARTED',LogChallengeFailed:'CHALLENGE_FAILED',LogChallengeRetry:'CHALLENGE_RETRY',LogChallengePass25:'CHALLENGE_PASS_25',LogChallengePass50:'CHALLENGE_PASS_50',LogChallengePass75:'CHALLENGE_PASS_75',LogChallengeSolved:'CHALLENGE_SOLVED'};function l(t,e,i){var a=function(){n(i)};a.__k=1;try{Object.defineProperty(t,e,{value:a,writable:!0,enumerable:!1,configurable:!0})}catch(n){try{t[e]=a}catch(n){}}}var r=0,d=setInterval(function(){r++;try{var n=window.Luna&&window.Luna.Unity,t=n&&n.Playable,i=n&&n.LifeCycle,c=n&&n.Analytics;if(t&&t.InstallFullGame&&t.InstallFullGame!==e&&(t.InstallFullGame=e),i&&i.GameEnded!==a&&(i.GameEnded=a),c&&(c.Applovin||(c.Applovin={}),!function(n){try{var t=n.LogChallengeStarted;return!!t&&1===t.__k}catch(n){return!1}}(c.Applovin)))for(var w in o)o.hasOwnProperty(w)&&(l(c.Applovin,w,o[w]),l(c.Applovin,w+'$1',o[w]))}catch(n){}r>600&&clearInterval(d)},100),c=['LOADING','LOADED','DISPLAYED'],w=0,f=!1;function u(t){for(var e=c.indexOf(t)+1;w<e;)n(c[w]),w++}function p(){if(!f&&t('logGameLoad')){f=!0;try{FbPlayableAd.logGameLoad()}catch(n){}}}u('LOADING'),window.addEventListener('luna:build',function(){u('LOADED'),p()}),window.addEventListener('luna:start',function(){if(u('DISPLAYED'),p(),'function'==typeof window.gameReady)try{window.gameReady()}catch(n){}})}();"""


def adapter_universal(nomraid=False):
    mraid_part = "" if nomraid else """  function openMraid(url){
    if (typeof mraid === "undefined" || !mraid.open) return false;
    var go = function(){ try { mraid.open(url); } catch(e){} };
    try {
      if (mraid.getState && mraid.getState() === "loading") {
        mraid.addEventListener("ready", function once(){
          try { mraid.removeEventListener("ready", once); } catch(e){}
          go();
        });
        return true;
      }
    } catch(e){}
    go(); return true;
  }
"""
    cta_part = """    window.open(storeUrl(ios, android), "_blank");""" if nomraid else """    var u = storeUrl(ios, android);
    if (openMraid(u)) return;
    window.open(u, "_blank");"""

    label = "Universal Adapter (TikTok - no MRAID)" if nomraid else "Universal Adapter (Feature Detection)"
    return """/* %s */
!function(){
  function storeUrl(ios, android){
    var cfg = (window.$environment && window.$environment.packageConfig) || {};
    ios = ios || cfg.iosLink; android = android || cfg.androidLink;
    var ua = (window.navigator.userAgent || "").toLowerCase();
    return /iphone|ipad|ipod|macintosh/i.test(ua) ? ios : android;
  }
  function al(ev){
    try {
      if (typeof window.ALPlayableAnalytics !== "undefined" && window.ALPlayableAnalytics.trackEvent)
        window.ALPlayableAnalytics.trackEvent(ev);
    } catch(e){}
  }
  function fb(fn){
    try { return typeof FbPlayableAd !== "undefined" && typeof FbPlayableAd[fn] === "function"; }
    catch(e){ return false; }
  }
%s
  function cta(ios, android){
    try { if (window.pi && window.pi.logCta) window.pi.logCta(); } catch(e){}
    al("CTA_CLICKED");
    if (fb("onCTAClick")) { try { FbPlayableAd.onCTAClick(); return; } catch(e){} }
    if (typeof window.openAppStore === "function") { try { window.openAppStore(); return; } catch(e){} }
    if (typeof ExitApi !== "undefined" && ExitApi.exit) { try { ExitApi.exit(); return; } catch(e){} }
    if (typeof window.install === "function") { try { window.install(); return; } catch(e){} }
    if (typeof window.openStore === "function") { try { window.openStore(); return; } catch(e){} }
%s
  }

  var done = false;
  function ended(){
    try { window.dispatchEvent(new Event("luna:ended")); } catch(e){}
    try { if (window.pi && window.pi.logGameEnd) window.pi.logGameEnd(); } catch(e){}
    if (done) return; done = true;
    if (typeof window.gameEnd === "function") { try { window.gameEnd(); } catch(e){} }
    al("ENDCARD_SHOWN");
    if (fb("logLevelComplete")) { try { FbPlayableAd.logLevelComplete("game_end"); } catch(e){} }
  }

  if (typeof window.gameStart !== "function")
    window.gameStart = function(){ try { window.dispatchEvent(new Event("luna:resume")); } catch(e){} };
  if (typeof window.gameClose !== "function")
    window.gameClose = function(){ try { window.dispatchEvent(new Event("luna:pause")); } catch(e){} };

  var CH = { LogChallengeStarted:"CHALLENGE_STARTED", LogChallengeFailed:"CHALLENGE_FAILED",
             LogChallengeRetry:"CHALLENGE_RETRY", LogChallengePass25:"CHALLENGE_PASS_25",
             LogChallengePass50:"CHALLENGE_PASS_50", LogChallengePass75:"CHALLENGE_PASS_75",
             LogChallengeSolved:"CHALLENGE_SOLVED" };
  function setFn(ns, name, ev){
    var f = function(){ al(ev); }; f.__k = 1;
    try { Object.defineProperty(ns, name, {value:f, writable:true, enumerable:false, configurable:true}); }
    catch(e){ try { ns[name] = f; } catch(e2){} }
  }
  function wired(ns){ try { var f = ns.LogChallengeStarted; return !!f && f.__k === 1; } catch(e){ return false; } }

  var n = 0, iv = setInterval(function(){
    n++;
    try {
      var U = window.Luna && window.Luna.Unity;
      var P = U && U.Playable, L = U && U.LifeCycle, A = U && U.Analytics;
      if (P && P.InstallFullGame && P.InstallFullGame !== cta) P.InstallFullGame = cta;
      if (L && L.GameEnded !== ended) L.GameEnded = ended;
      if (A) {
        if (!A.Applovin) A.Applovin = {};
        if (!wired(A.Applovin))
          for (var k in CH) if (CH.hasOwnProperty(k)) { setFn(A.Applovin, k, CH[k]); setFn(A.Applovin, k + "$1", CH[k]); }
      }
    } catch(e){}
    if (n > 600) clearInterval(iv);
  }, 100);

  var F = ["LOADING","LOADED","DISPLAYED"], sent = 0, loaded = false;
  function mark(st){ var to = F.indexOf(st) + 1; while (sent < to) { al(F[sent]); sent++; } }
  function onLoad(){
    if (!loaded && fb("logGameLoad")) { loaded = true; try { FbPlayableAd.logGameLoad(); } catch(e){} }
  }
  mark("LOADING");
  window.addEventListener("luna:build", function(){ mark("LOADED"); onLoad(); });
  window.addEventListener("luna:start", function(){
    mark("DISPLAYED"); onLoad();
    if (typeof window.gameReady === "function") { try { window.gameReady(); } catch(e){} }
  });
}();""" % (label, mraid_part, cta_part)


EXITAPI_SRC = "https://tpc.googlesyndication.com/pagead/gadgets/html5/api/exitapi.js"

# Chuoi phai xuat hien nguyen van trong source vi validator cua network quet text,
# khong chay code. Vi du: Meta playable preview bao "Can trien khai
# FbPlayableAd.onCTAClick()" neu goi qua bien trung gian.
REQUIRED_TOKENS = {
    "meta": ("FbPlayableAd.onCTAClick(",),
    "tiktok": ("window.openAppStore(",),
    "google": ("ExitApi.exit(",),
    "mintegral": ("window.install(", "window.gameEnd("),
    "applovin": ("mraid.open(", "ALPlayableAnalytics.trackEvent("),
}


# ---------------------------------------------------------------------------
# Doc input
# ---------------------------------------------------------------------------
def load_input(path):
    """Tra ve (html_text, base_name, notes[])."""
    notes = []
    if not os.path.isfile(path):
        raise SystemExit("Khong tim thay file: %s" % path)

    raw = open(path, "rb").read()
    base = os.path.splitext(os.path.basename(path))[0]

    if raw[:2] == b"PK":
        zf = zipfile.ZipFile(io.BytesIO(raw))
        html_names = [n for n in zf.namelist()
                      if n.lower().endswith((".html", ".htm")) and not n.startswith("__MACOSX")]
        if not html_names:
            raise SystemExit("ZIP khong chua file .html nao")
        # uu tien index.html, khong thi lay file lon nhat
        html_names.sort(key=lambda n: (os.path.basename(n).lower() != "index.html",
                                       -zf.getinfo(n).file_size))
        pick = html_names[0]
        if len(html_names) > 1:
            notes.append("ZIP co %d file HTML, dung: %s" % (len(html_names), pick))
        others = [n for n in zf.namelist()
                  if not n.endswith("/") and n != pick
                  and os.path.basename(n) not in ("README.txt", "urls.txt")
                  and not n.startswith("__MACOSX")]
        if others:
            notes.append("CANH BAO: ZIP con %d file khac (%s...) - tool chi xu ly playable "
                         "single-file, cac file nay bi bo qua"
                         % (len(others), ", ".join(others[:3])))
        html = zf.read(pick).decode("utf-8", "replace")
        # Luna de ten app trong README.txt: "Creatives for <App> exported at ..."
        app = None
        for cand in zf.namelist():
            if os.path.basename(cand).lower() == "readme.txt":
                m = re.search(r"Creatives for (.+?) exported at",
                              zf.read(cand).decode("utf-8", "replace"))
                if m:
                    app = m.group(1).strip()
                break
        base = app or (re.sub(r"[_-]?(unityads|default\s*creative)", "",
                             os.path.splitext(os.path.basename(pick))[0],
                             flags=re.I).strip(" _-") or base)
    else:
        html = raw.decode("utf-8", "replace")
        base = re.sub(r"[_-]?(unityads|default\s*creative)", "", base, flags=re.I).strip(" _-") or base

    base = re.sub(r"[_-]?unityads", "", base, flags=re.I)
    base = re.sub(r"\s+", "_", base).strip(" _-") or "playable"
    return html, base, notes


# ---------------------------------------------------------------------------
# Soi file & Patch Store Links
# ---------------------------------------------------------------------------
def patch_store_links(html, ios_link=None, android_link=None):
    """Ghi de iosLink / androidLink trong html cua Luna."""
    log = []
    if ios_link is not None:
        if re.search(r'iosLink\s*:\s*["\'][^"\']*["\']', html):
            html = re.sub(r'iosLink\s*:\s*["\'][^"\']*["\']', 'iosLink:"%s"' % ios_link, html, count=1)
            log.append("Cap nhat iosLink -> %s" % ios_link)
        elif re.search(r'packageConfig\s*:\s*\{', html):
            html = re.sub(r'(packageConfig\s*:\s*\{)', r'\1iosLink:"%s",' % ios_link, html, count=1)
            log.append("Chen them iosLink vao packageConfig -> %s" % ios_link)

    if android_link is not None:
        if re.search(r'androidLink\s*:\s*["\'][^"\']*["\']', html):
            html = re.sub(r'androidLink\s*:\s*["\'][^"\']*["\']', 'androidLink:"%s"' % android_link, html, count=1)
            log.append("Cap nhat androidLink -> %s" % android_link)
        elif re.search(r'packageConfig\s*:\s*\{', html):
            html = re.sub(r'(packageConfig\s*:\s*\{)', r'\1androidLink:"%s",' % android_link, html, count=1)
            log.append("Chen them androidLink vao packageConfig -> %s" % android_link)

    return html, log


def inspect(html):
    info = {}
    m = re.search(r'targetPlatform:"([^"]*)"', html)
    info["targetPlatform"] = m.group(1) if m else None
    m = re.search(r'buildId:(\d+)', html)
    info["buildId"] = m.group(1) if m else None
    m = re.search(r'orientation:"([^"]*)"', html)
    info["orientation"] = m.group(1) if m else None
    m = re.search(r'androidLink:"([^"]*)"', html)
    info["androidLink"] = m.group(1) if m else ""
    m = re.search(r'iosLink:"([^"]*)"', html)
    info["iosLink"] = m.group(1) if m else ""
    info["is_luna"] = ("$environment" in html and "luna:build" in html)
    info["already_converted"] = ((MARKER in html) or (MIN_MARKER in html) or
                                  ("__k=1" in html) or ("1===t.__k" in html))
    info["uses_mraid"] = "mraid" in html
    info["hosts"] = sorted(set(re.findall(r'https?://([a-zA-Z0-9._-]+)', html)))
    return info


def enclosing_script(html, idx):
    """Tra ve (start, end) cua the <script>...</script> bao quanh vi tri idx."""
    start = html.rfind("<script", 0, idx)
    if start < 0:
        return None
    end = html.find("</script>", idx)
    if end < 0:
        return None
    return start, end + len("</script>")


# ---------------------------------------------------------------------------
# Lam sach
# ---------------------------------------------------------------------------
def sanitize(html):
    log, warn = [], []

    # --- 1. sua tag dong bi loi cua Luna -------------------------------------
    stripped = html.rstrip()
    tail = stripped[-40:]
    if re.search(r"</html>\s*(</head>|</html>|</body>)", tail, re.I):
        i = stripped.rindex("</body>")
        html = stripped[:i] + "</body>\n</html>\n"
        log.append("Sua tag dong bi loi o cuoi file (Luna de lai </head></html> thua)")
    elif not stripped.lower().endswith("</html>"):
        if "</body>" in stripped:
            i = stripped.rindex("</body>")
            html = stripped[:i] + "</body>\n</html>\n"
            log.append("Bo sung the </html> con thieu")

    # --- 2. xoa block override console (console.re remote debugging) ---------
    anchor = None
    for probe in ("console.re/connector.js", "devToolsAreOpen", "consolerescript"):
        j = html.find(probe)
        if j >= 0:
            anchor = j
            break
    if anchor is not None:
        span = enclosing_script(html, anchor)
        if span:
            s, e = span
            block = html[s:e]
            if "devToolsAreOpen" in block and "console" in block and len(block) < 8000:
                html = html[:s] + html[e:]
                log.append("Xoa block remote-debugging cua Luna (%d bytes) "
                           "-> console khong con bi override" % len(block))
                for tok in ("devToolsAreOpen", "console.re", "consolerescript"):
                    if tok in html:
                        warn.append("Van con tham chieu '%s' sau khi xoa block - kiem tra lai tay" % tok)
            else:
                warn.append("Tim thay dau hieu console override nhung block khong khop mau "
                            "(%d bytes) - KHONG xoa, can kiem tra tay" % len(block))
        else:
            warn.append("Tim thay dau hieu console override nhung khong xac dinh duoc the <script>")
    else:
        log.append("Khong co block override console (file da sach hoac Luna doi pipeline)")

    # kiem tra con pattern override console nao khac
    if re.search(r'console\s*\[\s*[a-zA-Z_$]+\s*\]\s*=', html) or \
       re.search(r'console\.(log|warn|error|info|debug|trace)\s*=[^=]', html):
        warn.append("Van con code gan vao console.* -> PlayTurbo se bao loi #15, can soi tay")

    # --- 3. playgroundAssetOverrides tro ra CDN ------------------------------
    m = re.search(r'window\.playgroundAssetOverrides\s*=\s*\{[^}]*\}\s*;', html)
    if m:
        body = m.group(0)
        if "http" in body:
            if html.count("playgroundAssetOverrides") == 1:
                html = html[:m.start()] + "window.playgroundAssetOverrides = {};" + html[m.end():]
                log.append("window.playgroundAssetOverrides -> {} "
                           "(bo URL asset tro ra CDN Luna; asset da bake san trong build)")
            else:
                warn.append("playgroundAssetOverrides co URL ngoai VA duoc doc o noi khac "
                            "(%d refs) - KHONG dam bo, can xu ly tay"
                            % html.count("playgroundAssetOverrides"))

    # --- 4. de-host cac script debug ----------------------------------------
    for host in DEBUG_HOSTS:
        for url in sorted(set(re.findall(r'https?://%s[^"\')\s]*' % re.escape(host), html))):
            html = html.replace(url, "about:blank")
            log.append("%s -> about:blank (script debug, chi chay khi co query param)" % host)

    # --- 5. bao cao host con lai --------------------------------------------
    hosts = sorted(set(re.findall(r'https?://([a-zA-Z0-9._-]+)', html)))
    unexpected = [h for h in hosts if h not in ALLOWED_HOSTS]
    if unexpected:
        warn.append("Con host ngoai trong file: %s - kiem tra xem co phai runtime request khong"
                    % ", ".join(unexpected))
    log.append("Host con lai: %s" % (", ".join(hosts) if hosts else "khong co"))

    return html, log, warn


# ---------------------------------------------------------------------------
# Build cho tung network
# ---------------------------------------------------------------------------
def build(html, network, orientation=None, debug=False, readable=False, universal=False):
    cfg = NETWORKS[network]
    log = []

    if cfg["needs_orientation_meta"]:
        if 'name="ad.orientation"' in html:
            log.append("Da co meta ad.orientation, giu nguyen")
        else:
            o = orientation if orientation in ("portrait", "landscape") else "portrait,landscape"
            tag = '<meta name="ad.orientation" content="%s">' % o
            html = html.replace("</head>", tag + "</head>", 1)
            log.append('Them <meta name="ad.orientation" content="%s">' % o)

    if cfg["needs_exitapi"]:
        if EXITAPI_SRC in html:
            log.append("Da co exitapi.js, giu nguyen")
        else:
            tag = '<script type="text/javascript" src="%s"></script>' % EXITAPI_SRC
            html = html.replace("</head>", tag + "</head>", 1)
            log.append("Them exitapi.js cua Google vao <head>")

    if cfg.get("needs_tiktok_sdk"):
        if TIKTOK_SDK_SRC in html:
            log.append("Da co Playable-sdk.js cua TikTok, giu nguyen")
        else:
            # TikTok yeu cau SDK nam o cuoi <body>, TRUOC moi custom JS
            i = html.rindex("</body>")
            html = html[:i] + ('\n<script src="%s"></script>\n' % TIKTOK_SDK_SRC) + "</body>\n</html>\n"
            log.append("Them Playable-sdk.js cua TikTok truoc adapter")

    if universal:
        if network == "tiktok":
            if readable:
                adapter = "\n<script>\n%s\n</script>\n" % adapter_universal(nomraid=True)
                log.append("Universal nomraid adapter ban DE DOC cho TikTok")
            else:
                adapter = "\n<script>%s</script>\n" % UNIVERSAL_NOMRAID_MIN
                log.append("Universal nomraid adapter ban RUT GON (%d B) cho TikTok" % len(UNIVERSAL_NOMRAID_MIN))
            i = html.rindex("</body>")
            html = html[:i] + adapter + "</body>\n</html>\n"
            log.append("Inject universal nomraid adapter vao the <script> rieng truoc </body> (sau SDK)")
        else:
            k = html.rindex("</script>")
            if readable:
                adapter_code = "\n" + adapter_universal(nomraid=False) + "\n"
                log.append("Universal adapter ban DE DOC - noi vao the <script> cuoi cua Luna")
            else:
                adapter_code = ";" + UNIVERSAL_MIN
                log.append("Universal adapter ban RUT GON (%d B) - noi vao the <script> cuoi cua Luna" % len(UNIVERSAL_MIN))
            html = html[:k] + adapter_code + html[k:]
            log.append("Noi universal adapter vao the <script> cuoi cung cua Luna (khong tao the moi)")
    else:
        if readable:
            adapter = {"mintegral": adapter_mintegral,
                       "google": adapter_google,
                       "applovin": adapter_applovin,
                       "meta": adapter_meta,
                       "tiktok": adapter_tiktok}[network](debug)
            log.append("Adapter ban DE DOC - co comment, ten bien day du, co bat duoc log")
        else:
            adapter = "\n<script>%s</script>\n" % ADAPTER_MIN[network]
            log.append("Adapter ban RUT GON (%d B) - khong comment, ten bien da doi, "
                       "marker khong lo ten network" % len(ADAPTER_MIN[network]))
        i = html.rindex("</body>")
        html = html[:i] + adapter + "</body>\n</html>\n"
        log.append("Inject adapter %s truoc </body>" % network)

    # Mot so validator quet CHUOI LITERAL trong source chu khong chay code,
    # nen kiem tra lai cho chac an truoc khi giao file.
    for token in REQUIRED_TOKENS.get(network, ()):
        if token in html:
            log.append("Self-check: source co chuoi '%s' (validator quet literal)" % token)
        else:
            log.append("! Self-check THAT BAI: khong tim thay chuoi '%s' trong source - "
                       "validator cua network se bao thieu API" % token)

    return html, log


def tiktok_config(orientation, languages=None):
    """config.json bat buoc o thu muc goc cua ZIP TikTok."""
    o = {"portrait": 1, "landscape": 2}.get(orientation, 0)   # 0 = responsive
    langs = languages or ["en"]
    return ('{\n  "playable_orientation": %d,\n  "playable_languages": %s\n}\n'
            % (o, "[" + ", ".join('"%s"' % l for l in langs) + "]"))


def make_zip(html, extra=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("index.html", html)
        for name, data in (extra or {}).items():
            z.writestr(name, data)
    return buf.getvalue()


def fmt(n):
    return "%.2f MB (%s bytes)" % (n / 1048576.0, format(n, ","))


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="LunaPA Converter v%s - Luna Playground export -> Mintegral / Google Ads" % VERSION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    ap.add_argument("input", help="file .html hoac .zip tai tu playground.lunalabs.io")
    ap.add_argument("-n", "--network", default="mintegral,google,applovin,meta,tiktok",
                    help="network can build, cach nhau bang dau phay: mintegral, google, applovin, meta, tiktok "
                         "(default: tat ca)")
    ap.add_argument("-o", "--outdir", default=".", help="thu muc xuat (default: thu muc hien tai)")
    ap.add_argument("--universal", action="store_true",
                    help="dung universal adapter (1 adapter feature-detect chung cho moi network, noi vao the script cuoi)")
    ap.add_argument("--readable", action="store_true",
                    help="xuat adapter ban de doc (co comment) thay vi ban rut gon mac dinh")
    ap.add_argument("--debug-logs", action="store_true",
                    help="bat console.log trong adapter (chi co tac dung cung --readable)")
    ap.add_argument("--ios-link", default=None, help="ghi de iosLink (URL App Store)")
    ap.add_argument("--android-link", default=None, help="ghi de androidLink (URL Google Play)")
    ap.add_argument("--zip-all", action="store_true", help="dong goi tat ca file build thanh 1 file ZIP tong")
    ap.add_argument("--inspect", action="store_true", help="chi soi file, khong xuat gi")
    args = ap.parse_args()

    nets = [n.strip().lower() for n in args.network.split(",") if n.strip()]
    for n in nets:
        if n not in NETWORKS:
            raise SystemExit("Network khong ho tro: %s (chi co: %s)"
                             % (n, ", ".join(NETWORKS)))

    html, base, notes = load_input(args.input)
    for n in notes:
        print("  ! %s" % n)

    if args.ios_link or args.android_link:
        html, link_logs = patch_store_links(html, args.ios_link, args.android_link)
        print("\n=== CAP NHAT STORE LINKS ===")
        for l in link_logs:
            print("  - %s" % l)

    info = inspect(html)
    print("\n=== SOI FILE ===")
    print("  targetPlatform : %s" % (info["targetPlatform"] or "?"))
    print("  buildId        : %s" % (info["buildId"] or "?"))
    print("  orientation    : %s" % (info["orientation"] or "?"))
    print("  androidLink    : %s" % (info["androidLink"] or "(TRONG)"))
    print("  iosLink        : %s" % (info["iosLink"] or "(TRONG)"))
    print("  build Luna     : %s" % ("co" if info["is_luna"] else "KHONG NHAN RA"))
    print("  size HTML goc  : %s" % fmt(len(html.encode("utf-8"))))

    if not info["is_luna"]:
        print("\n  ! File nay khong giong build Luna. Tool van chay nhung ket qua co the sai.")
    if info["already_converted"]:
        print("\n  ! File nay DA duoc convert boi tool nay truoc do. Nen dung file goc tu Luna.")

    if args.inspect:
        html2, log, warn = sanitize(html)
        print("\n=== SE LAM SACH ===")
        for l in log:
            print("  - %s" % l)
        for w in warn:
            print("  ! %s" % w)
        return 0

    html, log, warn = sanitize(html)
    print("\n=== LAM SACH ===")
    for l in log:
        print("  - %s" % l)
    for w in warn:
        print("  ! %s" % w)

    os.makedirs(args.outdir, exist_ok=True)
    print("\n=== XUAT FILE ===")
    problems = []

    emitted_files = []

    for net in nets:
        cfg = NETWORKS[net]
        out_html, blog = build(html, net, info["orientation"], args.debug_logs, args.readable, args.universal)
        print("\n  [%s] %s" % (net, cfg["label"]))
        for l in blog:
            print("    - %s" % l)

        data = out_html.encode("utf-8")

        lim_h = cfg["limit_html"]
        fits_html = lim_h is None or len(data) <= lim_h

        if cfg["emit_html"] == "if_fits" and not fits_html:
            print("    -> BO QUA single HTML: %s > limit %s cua network nay."
                  % (fmt(len(data)), fmt(lim_h)))
            print("       Dung file ZIP ben duoi.")
        elif cfg["emit_html"]:
            fname = "%s_%s.html" % (base, net)
            p = os.path.join(args.outdir, fname)
            open(p, "wb").write(data)
            emitted_files.append((fname, data))
            print("    -> %-42s %s %s" % (os.path.basename(p), fmt(len(data)),
                                          "OK" if fits_html else "VUOT LIMIT %s!" % fmt(lim_h)))
            if not fits_html:
                problems.append("%s single HTML vuot limit %s" % (net, fmt(lim_h)))
            elif lim_h and len(data) > lim_h * 0.95:
                print("       ! con du duoi %s truoc limit %s - rat sat"
                      % (fmt(lim_h - len(data)), fmt(lim_h)))

        if cfg["emit_zip"]:
            extra = None
            if cfg.get("zip_extra") == "tiktok_config":
                langs = re.findall(r'languages:\["([^\]]*)"\]', html)
                lang_list = None
                if langs:
                    seen, lang_list = set(), []
                    for l in re.split(r'"\s*,\s*"', langs[0]):
                        if l and l not in seen:
                            seen.add(l); lang_list.append(l)
                extra = {"config.json": tiktok_config(info["orientation"], lang_list)}
                print("    - Them config.json vao ZIP: orientation=%s, languages=%s"
                      % (info["orientation"] or "?", lang_list or ["en"]))
            z = make_zip(out_html, extra)
            zname = "%s_%s.zip" % (base, net)
            p = os.path.join(args.outdir, zname)
            open(p, "wb").write(z)
            emitted_files.append((zname, z))
            ok = len(z) <= cfg["limit_zip"]
            print("    -> %-42s %s %s  (index.html ben trong)"
                  % (os.path.basename(p), fmt(len(z)), "OK" if ok else "VUOT LIMIT %s!" % fmt(cfg["limit_zip"])))
            if not ok:
                problems.append("%s ZIP vuot limit %s" % (net, fmt(cfg["limit_zip"])))
            soft = cfg.get("soft_limit_zip")
            if ok and soft and len(z) > soft:
                print("       ! Vuot %s. Doc chinh thuc cua TikTok ghi <5MB nen, nhung bang"
                      % fmt(soft))
                print("         yeu cau cua Unity Playworks ghi 3MB. Hoi rep TikTok truoc khi chay.")

    if args.zip_all and emitted_files:
        master_buf = io.BytesIO()
        with zipfile.ZipFile(master_buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as mz:
            for fname, fdata in emitted_files:
                mz.writestr(fname, fdata)
        master_data = master_buf.getvalue()
        master_p = os.path.join(args.outdir, "%s_all_networks.zip" % base)
        open(master_p, "wb").write(master_data)
        print("\n  [MASTER ZIP] %-40s %s (chua tat ca %d file build)"
              % (os.path.basename(master_p), fmt(len(master_data)), len(emitted_files)))

    print("\n=== LUU Y ===")
    if "tiktok" in nets:
        print("  ! TikTok CAM material dang MRAID. Adapter tiktok khong co nhanh mraid nao,")
        print("    nhung code mraid cua Luna van con trong file (tro, vi TikTok khong inject mraid).")
        print("    Neu bi reject vi MRAID thi day la cho can soi.")
        print("  ! TikTok chua co playable tester rieng - test qua Ads Manager.")
    if "meta" in nets:
        print("  ! Meta chay creative o che do MUTED va cam moi request ra ngoai / script tracking.")
        if args.universal:
            print("  ! Dang dung Universal Adapter: ban Meta se chua tham chieu ham fallback toi cac network khac")
            print("    (ALPlayableAnalytics, window.install). Rui ro thap nhung nen test tren Meta playable preview:")
        else:
            print("    Test bang Meta playable preview truoc khi upload len Ads Manager:")
        print("    https://developers.facebook.com/tools/playable-preview/")
    if "applovin" in nets and info["orientation"] in ("portrait", "landscape"):
        print("  ! AppLovin yeu cau creative chay duoc ca portrait VA landscape, nhung build nay")
        print("    orientation=%s. Test bang AppLovin Playable Preview o ca 2 huong:" % info["orientation"])
        print("    https://p.applov.in/playablePreview?create=1")
    if not info["iosLink"]:
        print("  ! iosLink TRONG -> traffic iOS bam CTA se khong mo gi.")
        print("    Sua trong Application Settings tren Playworks roi export lai,")
        print("    hoac sua truc tiep iosLink:\"\" trong file neu chi chay Android.")
    for w in warn:
        print("  ! %s" % w)
    for p in problems:
        print("  ! %s" % p)
    print("  - Van phai test tren playable tester cua network truoc khi chay tien.")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
