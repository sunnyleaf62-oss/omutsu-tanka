# おむつ単価くらべ

楽天市場・Yahoo!ショッピング・Amazonから紙おむつの価格を集め、送料込みの「1枚あたり」単価が安い順に `data.json` へ書き出して、`index.html` で表示します。店頭で値札を比べられる単価計算機つき。

公開URL：https://sunnyleaf62-oss.github.io/omutsu-tanka/

## ファイル
- `fetch_prices.py`：楽天・Yahoo!・Amazonから価格を取ってくる本体
- `products.json`：比較するおむつの一覧（ブランド × テープ/パンツ × サイズ）
- `.github/workflows/update.yml`：GitHubで毎朝 6:13 に自動実行する設定
- `index.html`：サイト本体

## 必要な値（ミルク単価くらべと同じキーが使えます）
| 名前 | 中身 |
|---|---|
| RAKUTEN_APP_ID | Rakuten Developersのアプリケーション ID |
| RAKUTEN_ACCESS_KEY | 同じ画面のアクセスキー（人に見せない） |
| RAKUTEN_AFFILIATE_ID | 同じ画面のアフィリエイトID |
| RAKUTEN_REFERER | 許可されたウェブサイトに入れたURL（`https://sunnyleaf62-oss.github.io/`） |
| YAHOO_CLIENT_ID | Yahoo!デベロッパーネットワークのClient ID（未設定ならYahoo!はスキップ） |
| VC_SID / VC_PID | バリューコマースのYahoo!ショッピング用 sid と pid |
| AMAZON_CREDENTIAL_ID / AMAZON_CREDENTIAL_SECRET | Creators APIの認証情報（未設定ならAmazonはスキップ） |
| AMAZON_API_VERSION | 認証情報のバージョン（例 3.3） |
| AMAZON_PARTNER_TAG | アソシエイトのトラッキングID（例 xxxx-22） |

リポジトリの Settings → Secrets and variables → Actions に登録します。コードやファイルにキーを直接書かないでください。

## 集め方のルール
- 商品名に `must` の言葉が全部入っていて、`ng`（全商品共通の `common_ng` も含む）の言葉が入っていない出品だけを使います
- 「テープ」「パンツ」の言葉で種類を確認し、サイズは商品名に出てくるサイズがちょうど1つで、目的のサイズと一致するものだけを使います（「S/M/L 選べる」などは除外）
- 「232枚(58枚×4パック)」「44枚×3個セット」などから合計枚数を読み取ります
- 送料別の出品は、送料の目安（800円）を足した「送料込み価格」で比べます
- 1枚が8円未満・120円超になるもの、中央値の6割未満のものは読み違いとして除外します
- 同じショップの重複は一番安いものだけ残し、1商品につき上位10ショップを表示します

## 商品名の読み取りを試す
```
python fetch_prices.py --test "パンパース テープ M 232枚(58枚×4パック)"
```

## ブランドの追加例（`products.json` の `lines` に足す）
```json
{
  "id": "whito", "maker": "王子ネピア", "brand": "ネピア", "name": "whito",
  "must": ["whito"], "ng": [],
  "types": {
    "テープ": {"keyword": "ネピア whito テープ", "sizes": ["新生児", "S", "M", "L"]},
    "パンツ": {"keyword": "ネピア whito パンツ", "sizes": ["M", "L", "ビッグ"]}
  }
}
```
サイズに使える名前：`新生児` `S` `M` `L` `ビッグ` `ビッグより大きい`
