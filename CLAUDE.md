# おむつ単価くらべ：運営メモ

このファイルは、Claudeとの会話が分かれても同じ前提で作業するためのメモです。
このリポジトリを読み込んだClaudeは、作業の前にここを確認し、決まったことが変わったらここも書き換えてください。
このリポジトリは**公開**です。個人的なこと（本名・個人のメール・個人用のアフィリエイトIDなど）はここにもコードにも書かないでください。

## サイト
- 公開URL：https://sunnyleaf62-oss.github.io/omutsu-tanka/
- 姉妹サイト：ミルク単価くらべ https://sunnyleaf62-oss.github.io/milk-tanka/ ／ mama-note https://sunnyleaf62-oss.github.io/mama-note/
- 公開：GitHub Pages（main ブランチの / を公開）
- 価格の更新：GitHub Actions「update.yml」。毎朝6:13（日本時間）と、products.json・fetch_prices.py を変えたときに自動で動く
- お得情報：deals.json を変えると「deals.yml」が数分で反映。毎日0:05にも動いて期限切れを消す

## アフィリエイト（ミルク単価くらべと同じキーを使う）
| モール | 仕組み | 値 |
|---|---|---|
| 楽天 | 楽天ウェブサービスAPI（ウェブアプリケーション型。許可サイトは sunnyleaf62-oss.github.io） | Secrets: RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY / RAKUTEN_AFFILIATE_ID / RAKUTEN_REFERER。計測ID `_RTLink150941`（このサイト用）は fetch_prices.py に記載 |
| Yahoo!ショッピング | 商品検索API v3 ＋ バリューコマース（審査通過済み） | Secret: YAHOO_CLIENT_ID。VCの sid=3784952 / pid=892737497 は fetch_prices.py に記載（公開される値） |
| Amazon | Creators API（認証情報バージョン 3.3） | Secrets: AMAZON_CREDENTIAL_ID / AMAZON_CREDENTIAL_SECRET / AMAZON_API_VERSION / AMAZON_PARTNER_TAG |

- AmazonのトラッキングIDは **omutsu-tanka-22**（このサイト専用）。運営者の個人用のトラッキングIDは使わない。
- 新しい「Yahoo!ショッピングアフィリエイト」（2026年1月開始・PayPayマネー払い）はAPI非対応のため、サイトではバリューコマースを使う。SNS投稿用には使ってよい。
- キーやシークレットはチャットに貼らず、GitHubの Settings → Secrets に直接入れてもらう。

## 決めたこと（運営者の方針・ミルク単価くらべと共通）
- 報酬が付かないリンクでも、いちばん安いお店を正直に表示する（わざと楽天などへ誘導しない）。
- 表記：ページ上部に「（当ページのリンクには広告が含まれています）」を小さく。フッターに「Amazonのアソシエイトとして、当サイトは適格販売により収入を得ています。」（Amazon規約で必須）。楽天・バリューコマースの社名は書かない。
- 送料が分からない送料別の出品は、目安800円を足して比べる。

## このサイトだけのこと
- 単価は「1枚あたり」。ブランド × テープ／パンツ × サイズ（新生児・S・M・L・ビッグ・ビッグより大きい）で比べる。
- 店頭の値札で使える単価計算機つき。
- 配色：オレンジ系がアクセント。
- 今のブランド：パンパース（さらさらケア・肌へのいちばん）、メリーズ（さらさらエアスルー・ファーストプレミアム）、ムーニー、ムーニーマン（汗スッキリ・マシュマロ肌ごこち）、グーン（グーンプラス・ぐんぐん吸収パンツ・ゆるうんちモレ0へ）、マミーポコ。

## 商品の追加・調整
- products.json の `lines` にブランドを足す（書き方は README.md）。全商品共通の除外ワードは `common_ng`。
- 商品名の読み取りは `python fetch_prices.py --test "商品名"` で試せる。
- 読み違いを見つけたら、data.json / debug.json の除外理由を見て、must / ng か fetch_prices.py の読み取りを直す。

## お得な日カレンダー
- ミルク単価くらべのリポジトリにある `calendar.json` / `calendar.js` を読んで表示している（`../milk-tanka/...`）。日程の更新は milk-tanka 側で行う。
- このサイトのIDは index.html の `<section id="okcal" data-amazon-tag="omutsu-tanka-22" data-rakuten-rt="_RTLink150941">` で渡している。

## 気をつけること
- 自動更新（Actions）が data.json を書き込むので、push の前に必ず `git pull --rebase` する。
- コミットのメールアドレスは必ず `sunnyleaf62-oss@users.noreply.github.com` を使う（`git -c user.name="sunnyleaf62-oss" -c user.email="sunnyleaf62-oss@users.noreply.github.com" commit ...`）。個人のメールアドレスは公開の履歴に残るので使わない。GitHubの設定で、個人のメールが入った push は「GH007」エラーで止まる。
- 2026年11月2日に履歴を書き換えた（個人情報の削除）。それより前に作ったクローンは使わず、取り直してから作業する。
