# Adapter dùng chung — thử nghiệm, chưa wire vào tool

Xem mục 6 của `HANDOFF.md` trước.

| File | Là gì |
|---|---|
| `universal.js` | Adapter feature-detect cho mọi network, bản đọc được |
| `universal_nomraid.js` | Bản cho TikTok — bỏ hẳn nhánh MRAID vì TikTok cấm |
| `universal.min.js` | 3.264 B — bản đã minify, dùng để nhúng |
| `universal_nomraid.min.js` | 2.952 B |

## Cách nhúng

Nối vào **thẻ `<script>` cuối cùng** của Luna, không tạo thẻ mới:

```python
k = html.rindex("</script>")
html = html[:k] + ";" + minified_js + html[k:]
```

Riêng TikTok phải để adapter ở thẻ riêng, **sau** thẻ SDK — vì TikTok yêu cầu SDK đứng trước custom JS, và thẻ `<script src>` thì nội dung inline bị bỏ qua.

## Kết quả đã verify

Mintegral / AppLovin / Meta ra file **byte-identical nhau** (sha256 `d67daaaa…`), số thẻ `<script>` không đổi (25 → 25). Google +1 (`exitapi.js`), TikTok +2 (SDK + adapter).

Runtime cả 5 network: CTA gọi đúng API, không rơi `window.open`, AppLovin giữ nguyên funnel `LOADING → LOADED → DISPLAYED` + challenge event.

## Đánh đổi chưa quyết

File dùng chung nghĩa là bản Meta cũng chứa `ALPlayableAnalytics.trackEvent(` và `window.install(`. Meta cấm script tracking bên thứ ba — đây chỉ là lời gọi hàm có guard tới global không tồn tại, rủi ro thấp nhưng không bằng không. Nên để thành tuỳ chọn, không thành mặc định.
