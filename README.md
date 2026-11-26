# hybrid-llm-12gb

12GB の GPU（RTX 5070）で、ローカル LLM とクラウド LLM を組み合わせる「ハイブリッド LLM」を作って測ったときのコードと生データです。

- 個人情報を含む依頼は必ずローカルに回すルーター（`hybrid.py`）
- クラウドが落ちても待たせないためのストリーミング呼び出しと 4 つの時間上限、半開きつきサーキットブレーカー（`hybrid.py`）
- Foundry Local（CUDA）で 7 モデルを載せた容量表（`run_capacity.py`、`bench_local.py`）
- 日本語 280 件の評価セットでの比較と、振り分けルールの評価（`e2_tasks.py`、`e2_run.py`、`e2_score.py`）
- 偽のクラウドで障害を起こす実験（`e3_fallback.py`）と、GPU なしで動く単体チェック（`check_cloud_limits.py`）

## 測定環境

NVIDIA GeForce RTX 5070 12GB、Windows、Python 3.12、
Foundry Local SDK 2.5.0、ONNX Runtime GPU 1.32.0（CUDA 13）、openai 3.59.0。

**注意**：Foundry Local の公式 CUDA 実行プロバイダーの配布が HTTP 403 を返していたため（2026 年 11 月時点）、`fl_common.py` は
pip 版 ONNX Runtime GPU を使う非公式の回避策で GPU を動かしています。この構成では temperature 0 でも実行ごとに出力が揺れることがありました
（qwen2.5-1.5b の公式 CPU 版では揺れなし）。公式の配布が直っていれば回避策は不要です。

## まず GPU なしで試す

```
pip install openai            # GPU なしのチェックに必要なのはこれだけ
python fetch_data.py          # JGLUE と MGSM を data/ に取得
python e2_tasks.py            # 評価セット data/e2_tasks.jsonl を作成（シード固定）
python e2_run.py check        # 採点ルールの自己チェック
python hybrid.py              # ブレーカーと個人情報検出の自己チェック
python check_cloud_limits.py  # クラウド呼び出しの時間上限と失敗の扱い（偽サーバー 11 通り）
```

`out/` には測定した生データ（各モデルの回答、容量表、障害実験の記録）が入っています。`e2_score.py` で、GPU なしで比較をやり直せます。

```
python e2_score.py out/e2_local_qwen3-8b-cuda-gpu_2_nothink.jsonl out/e2_local_Phi-4-cuda-gpu_2.jsonl --local-pair --lenient
```

## GPU で測り直す

`pip install foundry-local-sdk==2.5.0` を入れ、`fl_common.py` の説明にある手順で `tools/cuda-ep` を用意してから、`run_capacity.py`、`e2_run.py foundry <モデル>`、`e3_fallback.py <モデル>` を実行します。
ディスクに余裕がない場合は、環境変数 `HYBRID_PARK_DIR` に別ドライブのフォルダを指定すると、測り終えたモデルをそこへ移動します。

## 未検証のこと

Ollama・LM Studio・vLLM、実際のクラウドサービス（DeepSeek、Azure OpenAI など）、複数ユーザーの同時アクセス、DNS 障害やネットワーク切断。

## ライセンス

- コード（`*.py`）：MIT License（`LICENSE`）
- `out/` の測定データ：評価データの元になった JGLUE（Yahoo! JAPAN、CC BY-SA 4.0）と MGSM（Google Research）にもとづくため、CC BY-SA 4.0（`LICENSE-data.md`）
- 評価データそのもの（JGLUE、MGSM）は同梱していません。`fetch_data.py` が各公式の配布元から取得します。

このリポジトリのコードと文章の作成には AI（Claude）を使い、作者が確認しています。
