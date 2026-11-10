# Bước 1 — Làm sạch: code bị xoá và code bị sửa

Bốn thay đổi. Tất cả trích nguyên văn từ file `*_unityads.html` của Luna.

`5.011.322 B` → `5.009.779 B` (**−1.543 B**)

| | Thay đổi | Delta |
|---|---|---|
| A1 | Xoá một thẻ `<script>` | −1.268 B |
| A2 | Sửa tag đóng cuối file | −13 B |
| A3 | Sửa giá trị một biến | −164 B |
| A4 | Sửa hai chuỗi URL | −98 B |

---

## A1 — Xoá thẻ `<script>` ghi đè `console`

Vị trí: offset `4772`. **Xoá toàn bộ**, không thay bằng gì.

### ✗ XOÁ

```html
<script>(()=>{let e=window.insertYourRemoteDebuggingTokenHere="";if(e){const o=document.createElement("script");o.setAttribute("src","https://console.re/connector.js"),o.setAttribute("data-channel",e),o.setAttribute("id","consolerescript"),document.head.appendChild(o)}window.devToolsAreOpen=!1;let o=0,t=()=>{if(e)return`Remote debugging is enabled, use the following link to access remote console: http://console.re/${e}`;return(o?`Logs are not displayed when dev tools are hidden. Please reload the game with dev tools opened to see ${o} hidden messages.\n`:"")+"Learn how to debug your playable remotely at https://docs.lunalabs.io/docs/playable/ad-networks/remote-debugging"};console.warn(Object.defineProperties(new Error,{toString:{value:()=>((new Error).stack.includes("String@")&&(window.devToolsAreOpen=!0),t())},message:{get:()=>(window.devToolsAreOpen=!0,t())},name:{get:()=>"[DEBUGGING]"}}));let n=new Promise((e=>{const o=()=>{console.re?e(console.re):setTimeout(o,100)};o()}));const s=["debug","trace","info","log","warn","error"];for(const t of s){const s=console[t];console[t]=(...r)=>{r&&r[0]&&"string"==typeof r[0]&&r[0].startsWith("consoleRe")||(e&&n.then((e=>e[t].apply(console.re,r))),window.devToolsAreOpen?s.apply(console,r):o++)}}})()</script>
```

### ✓ SAU

*(trống — thẻ bị xoá hẳn)*

---

## A2 — Tag đóng cuối file

### ✗ TRƯỚC

```html
…window.open(o,"_blank"))}}))}))</script></body>
</html></head></html>
```

### ✓ SAU

```html
…window.open(o,"_blank"))}}))}))</script></body>
</html>
```

Chỉ bỏ cặp `</head></html>` thừa ở cuối. Thẻ `</script>` ngay trước `</body>` là CTA của Luna — giữ nguyên.

---

## A3 — `window.playgroundAssetOverrides`

### ✗ TRƯỚC

```js
window.playgroundAssetOverrides = {"42706":"https://assets.lunalabs.io/uploads/media/file/477217/c47c60d9efd806aa595b21574cecfa22/1fbd9066aa0cee8e555a98c50854e985a9005db3d7704be759d3c33363314759.m4a"};
```

### ✓ SAU

```js
window.playgroundAssetOverrides = {};
```

Hai biến ngay cạnh — `window.playgroundFiltersOverrides` và `window.postProcessesOverrides` — **giữ nguyên**, chúng không chứa URL.

---

## A4 — Hai chuỗi URL script debug

Chỉ đổi **chuỗi URL**, giữ nguyên code xung quanh.

### ✗ TRƯỚC

```js
e.src="https://mrdoob.github.io/stats.js/build/stats.min.js"

e.setAttribute("src","https://cdn.jsdelivr.net/npm/spectorjs@0.9.30/dist/spector.bundle.js")
```

### ✓ SAU

```js
e.src="about:blank"

e.setAttribute("src","about:blank")
```

---

## Toàn bộ diff, dạng ngắn

```diff
- <script>(()=>{let e=window.insertYourRemoteDebuggingTokenHere="";…console[t]=(...r)=>{…}}})()</script>

- </body>\n</html></head></html>
+ </body>\n</html>

- window.playgroundAssetOverrides = {"42706":"https://assets.lunalabs.io/…/….m4a"};
+ window.playgroundAssetOverrides = {};

- e.src="https://mrdoob.github.io/stats.js/build/stats.min.js"
+ e.src="about:blank"

- e.setAttribute("src","https://cdn.jsdelivr.net/npm/spectorjs@0.9.30/dist/spector.bundle.js")
+ e.setAttribute("src","about:blank")
```

---

## Kết quả

| Trước | Sau |
|---|---|
| 6 host ngoài: `console.re`, `docs.lunalabs.io`, `assets.lunalabs.io`, `mrdoob.github.io`, `cdn.jsdelivr.net`, `play.google.com` | 1 host: `play.google.com` (store link) |
| `console.log` bị wrap | `console.log` native |
| `</body></html></head></html>` | `</body></html>` |

Engine bundle, asset base64 và code game: **không đụng tới một byte nào**.
