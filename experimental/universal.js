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
  function openMraid(url){
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

  function cta(ios, android){
    try { if (window.pi && window.pi.logCta) window.pi.logCta(); } catch(e){}
    al("CTA_CLICKED");
    if (fb("onCTAClick")) { try { FbPlayableAd.onCTAClick(); return; } catch(e){} }
    if (typeof window.openAppStore === "function") { try { window.openAppStore(); return; } catch(e){} }
    if (typeof ExitApi !== "undefined" && ExitApi.exit) { try { ExitApi.exit(); return; } catch(e){} }
    if (typeof window.install === "function") { try { window.install(); return; } catch(e){} }
    if (typeof window.openStore === "function") { try { window.openStore(); return; } catch(e){} }
    var u = storeUrl(ios, android);
    if (openMraid(u)) return;
    window.open(u, "_blank");
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
}();
