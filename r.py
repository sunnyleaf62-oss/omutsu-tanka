import json,os,time,urllib.request,urllib.parse,urllib.error
Q={
"産褥ショーツ":"産褥ショーツ","産褥パッド":"産褥パッド","陣痛逃しグッズ":"いきみ逃し","フェイスタオル":"フェイスタオル 今治",
"リップクリーム":"リップクリーム 妊婦","飲み物・軽食":"ゼリー飲料 ケース",
"ベビー肌着":"新生児 肌着 セット","マタニティパジャマ":"マタニティパジャマ","母乳パッド":"母乳パッド",
"はおりもの":"授乳 カーディガン","ママの退院服":"授乳服 ワンピース","円座・授乳クッション":"円座クッション 産後",
"モバイル充電器":"モバイルバッテリー","フェイスパック":"フェイスパック 大容量","メモリアルグッズ":"手形 足形 キット 赤ちゃん",
"スリッパ":"スリッパ 入院","バスタオル":"バスタオル 今治",
"おしりふき":"おしりふき 純水","紙おむつ処理器":"おむつ処理ポット","おしりふきのふた":"おしりふき ふた",
"搾乳器":"搾乳器","授乳ケープ":"授乳ケープ","調乳ポット":"調乳ポット","ベビー布団":"ベビー布団 セット",
"ベビージム":"ベビージム","加湿器":"加湿器 赤ちゃん","ベビーソープ":"ベビーソープ 泡","ベビー用スキンケア":"ベビーローション 保湿",
"ガーゼ":"ガーゼハンカチ ベビー","ベビー用綿棒":"ベビー綿棒","湯温計":"湯温計 ベビー","ベビー用衣類洗剤":"ベビー 洗濯洗剤",
"ベビー用体温計":"ベビー 体温計","鼻水吸い器":"電動 鼻水吸引器","短肌着":"短肌着","長肌着":"長肌着","コンビ肌着":"コンビ肌着",
"ツーウェイオール":"ツーウェイオール 新生児","カバーオール":"カバーオール ベビー","ベストor カーディガン":"ベビー ベスト",
"スタイ（よだれかけ）":"スタイ","帽子":"新生児 帽子","赤ちゃんの靴下":"ベビー 靴下 新生児","抱っこひも":"抱っこ紐",
"ベビーカー":"ベビーカー","チャイルドシート":"チャイルドシート 新生児","マザーズバッグ":"マザーズバッグ",
"おでかけ用ケープ":"抱っこ紐 ケープ","ベビー収納グッズ":"おむつストッカー","ベビーグッズ収納家具":"ベビー 収納 ダンボール",
"母子手帳ケース":"母子手帳ケース","マタニティショーツ":"マタニティショーツ","ハーフトップ（ワイヤーなし）":"マタニティブラ ノンワイヤー",
"マタニティウエア":"マタニティ ワンピース","マタニティパンツ":"マタニティパンツ","マタニティ用レギンス・タイツ・パンスト":"マタニティ レギンス",
"吸水ケアシート":"吸水ケア 尿もれ","ママの靴下":"着圧ソックス 妊婦"}
H={"Referer":os.environ["RAKUTEN_REFERER"].strip(),"Origin":os.environ["RAKUTEN_REFERER"].strip().rstrip("/"),"User-Agent":"Mozilla/5.0"}
def call(p):
  for v in ["20260701","20220601"]:
    u="https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/"+v+"?"+urllib.parse.urlencode(p)
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30))
    except urllib.error.HTTPError as e:
      if e.code==404: continue
      if e.code==429: time.sleep(3); return call(p)
      raise
out={}
for item,kw in Q.items():
  rows=[]
  for page in (1,2):
    try:
      d=call({"applicationId":os.environ["RAKUTEN_APP_ID"].strip(),"accessKey":os.environ["RAKUTEN_ACCESS_KEY"].strip(),"keyword":kw,"NGKeyword":"中古 福袋","sort":"-reviewCount","availability":1,"hits":30,"page":page,"format":"json","formatVersion":2})
    except Exception as e: out.setdefault("_err",{})[item]=str(e)[:300]; break
    if page==1: out.setdefault("_dbg",{})[item]=list(d)[:8]
    for it in d.get("Items") or d.get("items") or []:
      it=it.get("Item",it)
      rows.append({"name":it["itemName"][:90],"price":it["itemPrice"],"avg":float(it.get("reviewAverage") or 0),"img":((it.get("mediumImageUrls") or [""])[0] if not isinstance((it.get("mediumImageUrls") or [""])[0],dict) else it["mediumImageUrls"][0].get("imageUrl","")),"n":int(it.get("reviewCount") or 0),"shop":it["shopName"],"url":it["itemUrl"]})
    time.sleep(1.1)
  out[item]={"kw":kw,"rows":rows}; print(item,len(rows))
json.dump(out,open("out.json","w"),ensure_ascii=False)
