#!/usr/bin/env python3
"""QLoRA v0.2 + three matched evaluations; weights stay in mounted Drive.

No Git writes. Existing v0.1 datasets/results/adapters are read-only.
Lexical checks are triage, never a substitute for semantic case review.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "research/agcn-presenter-training-v1"
FROZEN_SHA = "09f7f0cb0e9fb2847a37c93ea58a5724460a88af4d5b2cf469d493feb6083bae"
V1_ADAPTER_SHA = "5652197ef5f1bc212822d071ed28cd5a9802fea62aa3f5f802e88896486a6524"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(cmd, log=None):
    print("RUN:", " ".join(map(str, cmd)), flush=True)
    if log is None:
        subprocess.run(list(map(str, cmd)), cwd=ROOT, check=True)
    else:
        with Path(log).open("a", encoding="utf-8") as handle:
            subprocess.run(list(map(str, cmd)), cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=True)


def preflight():
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    if branch != BRANCH:
        raise RuntimeError(f"Wrong branch: {branch}")
    frozen = ROOT / "training/evaluation/frozen_eval_v0.1.jsonl"
    if sha(frozen) != FROZEN_SHA:
        raise RuntimeError("Frozen evaluation bytes changed")
    cases = read_rows(frozen)
    if len(cases) != 25 or len({x["id"] for x in cases}) != 25:
        raise RuntimeError("Expected exactly 25 unique frozen cases")
    manifest = json.loads((ROOT / "training/datasets/dataset_v0.2_manifest.json").read_text())
    for entry in manifest["datasets"]:
        path = ROOT / entry["path"]
        if len(read_rows(path)) != entry["items"]:
            raise RuntimeError(f"Source count mismatch: {path}")
        run([sys.executable, "training/scripts/validate_dataset.py", path])
    run([sys.executable, "training/scripts/build_sft_corpus_v0_2.py", "training/outputs"])
    split_paths = {s: ROOT / f"training/outputs/agcn_presenter_v0.2_{s}.jsonl" for s in ("train", "validation")}
    counts = {s: len(read_rows(p)) for s, p in split_paths.items()}
    if counts != {"train": 458, "validation": 42}:
        raise RuntimeError(f"Unexpected corpus: {counts}")
    inputs = [x["input"] for e in manifest["datasets"] for x in read_rows(ROOT / e["path"])]
    fingerprints = [json.dumps(x, ensure_ascii=False, sort_keys=True) for x in inputs]
    if len(set(fingerprints)) != 500:
        raise RuntimeError("Duplicate input across corpus sources")
    v1 = json.loads((ROOT / "training/results/v0.1/agcn_training_summary.json").read_text())
    return {
        "branch": branch,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "frozen_eval_sha256": sha(frozen), "frozen_cases": 25,
        "counts": counts,
        "sources": {e["path"]: sha(ROOT / e["path"]) for e in manifest["datasets"]},
        "corpus_sha256": {s: sha(p) for s, p in split_paths.items()},
        "base_model": v1["base_model"], "base_model_revision": v1["base_model_revision"],
        "protocol_sha256": {p: sha(ROOT / p) for p in (
            "training/training_policy.py", "training/evaluation_rules.py",
            "training/scripts/run_lora_frozen_eval.py", "training/scripts/train_lora_qwen3.py")},
    }


def lexical_review(case, row):
    """Expose narrow triage signals and keep semantic dimensions pending."""
    output = row.get("model_output") or {}
    speech = output.get("speech", "")
    words = re.findall(r"\w+", speech.casefold())
    trigrams = list(zip(words, words[1:], words[2:]))
    repeated = [" ".join(t) for t, n in Counter(trigrams).items() if n > 1]
    recent = (case["input"].get("recent_speeches") or [])[-8:]
    recent_trigrams = set()
    for text in recent:
        tokens = re.findall(r"\w+", str(text).casefold())
        recent_trigrams.update(zip(tokens, tokens[1:], tokens[2:]))
    overlap = len(set(trigrams) & recent_trigrams) / max(1, len(set(trigrams)))
    checks = row.get("checks") or {}
    return {
        "automatic_failures": [k for k, v in checks.items() if v is False],
        "cta_marker_present": bool(re.search(r"carrinho|sacolinha|produto fixado|finaliz|comprar", speech, re.I)),
        "repeated_trigrams": repeated, "recent_trigram_overlap": round(overlap, 3),
        "semantic_review": {dimension: "pending" for dimension in (
            "invented_facts_in_speech", "unauthorized_scarcity", "buying_intent",
            "objection", "ignore", "cta_quality", "naturalness", "repetition")},
    }


def report(result_dir, adapter, protocol, timing):
    train = json.loads((adapter / "agcn_training_summary.json").read_text())
    lines = ["# AGCN Presenter v0.2 — Treino e comparação", "",
             "Status: treino e inferência concluídos; revisão semântica caso a caso pendente.", "",
             "Pesquisa somente; nenhuma integração na main.", "",
             "## Treinamento", "",
             f"Modelo: {protocol['base_model']} @ {protocol['base_model_revision']}",
             "Corpus: 458 treino / 42 validação; 25 testes congelados excluídos.",
             f"SHA256 teste: `{FROZEN_SHA}`",
             f"Melhor checkpoint (menor validation loss): `{train['best_checkpoint']}`",
             f"Melhor validation loss: {train['best_eval_loss']}",
             f"Métricas Trainer: {json.dumps(train.get('train_metrics'), ensure_ascii=False)}",
             f"Tempos medidos por etapa: {json.dumps(timing, ensure_ascii=False)}", "",
             "Loss não é diretamente comparável à validação v0.1: os corpora de validação diferem.", "",
             "| Época | Passo | Validation loss |", "|---|---|---|"]
    for event in train["log_history"]:
        if "eval_loss" in event:
            lines.append(f"| {event['epoch']} | {event['step']} | {event['eval_loss']} |")
    lines += ["", "## Comparação controlada", "",
              "Os três modelos são executados novamente, com o mesmo prompt, revisão do Qwen, NF4, dtype, sementes e amostragem. Qwen original = base sem adapter, com a política de treinamento. O baseline GGUF de produção é histórico e não entra nesta comparação controlada.", "",
              "Os indicadores herdados detectam JSON, fatos declarados, números, IGNORAR, alguns marcadores de oralidade, escassez e orientação de compra. Eles não comprovam fidelidade semântica da fala, resposta correta à objeção, CTA adequado ou naturalidade. `failed` no runner indica falha de parse/execução, não a soma das falhas de comportamento.", ""]
    labels = ("Qwen original", "AGCN v0.1", "AGCN v0.2")
    keys = ("qwen_original", "agcn_v0.1", "agcn_v0.2")
    data = {}
    summaries = {}
    cases = read_rows(ROOT / "training/evaluation/frozen_eval_v0.1.jsonl")
    ids = [x["id"] for x in cases]
    for key in keys:
        rows = read_rows(result_dir / f"{key}.jsonl")
        if [r["id"] for r in rows] != ids:
            raise RuntimeError(f"Evaluation IDs/order mismatch: {key}")
        data[key] = {r["id"]: r for r in rows}
        summaries[key] = json.loads((result_dir / f"{key}_summary.json").read_text())
    controlled = ("frozen_eval_sha256", "seed", "case_seed", "compute_dtype", "base_model_revision", "generation", "training_prompt_sha256", "evaluation_script_sha256", "versions")
    for name in controlled:
        if any(summaries[k][name] != summaries[keys[0]][name] for k in keys[1:]):
            raise RuntimeError(f"Unmatched evaluation protocol: {name}")
    names = summaries[keys[0]]["checks"].keys()
    lines += ["| Indicador | Qwen original | AGCN v0.1 | AGCN v0.2 |", "|---|---|---|---|"]
    for name in names:
        scores = [summaries[k]["checks"][name] for k in keys]
        lines.append("| " + name + " | " + " | ".join(f"{s['passed']}/{s['total']}" for s in scores) + " |")
    review = []
    for case in cases:
        lines += ["", f"## {case['id']}", "",
                  "Tags: " + ", ".join(case["metadata"].get("tags", [])),
                  "Comentário: " + json.dumps(case["input"].get("comment"), ensure_ascii=False),
                  "Fatos permitidos: " + json.dumps(case["input"].get("allowed_facts"), ensure_ascii=False),
                  "Regras comerciais: " + json.dumps(case["input"].get("commercial_rules"), ensure_ascii=False),
                  "Contexto completo: " + json.dumps(case["input"], ensure_ascii=False),
                  "Referência: " + json.dumps(case["target"], ensure_ascii=False), ""]
        for key, label in zip(keys, labels):
            row = data[key][case["id"]]
            triage = lexical_review(case, row)
            review.append({"id": case["id"], "model": key, **triage})
            lines += [f"**{label}:**", "", json.dumps(row.get("model_output"), ensure_ascii=False), "",
                      f"Erro: {row.get('error') or 'nenhum'}; latência: {row['latency_seconds']} s.",
                      "Falhas automáticas: " + ", ".join(triage["automatic_failures"]),
                      "Triagem CTA/repetição: " + json.dumps({k: v for k, v in triage.items() if k not in ("semantic_review", "automatic_failures")}, ensure_ascii=False), ""]
            if row.get("error"):
                lines += ["Saída bruta: " + row.get("raw", ""), ""]
        lines += ["**Revisão semântica pendente:** verificar fatos inventados inclusive quando `used_facts` está correto; escassez autorizada e quantidade; intenção de compra e passo a passo; resposta à objeção; IGNORAR interno; CTA; naturalidade; repetição diante das falas recentes."]
    (result_dir / "comparison_case_by_case.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(result_dir / "semantic_review_pending.json", review)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drive-root", default="/content/drive/MyDrive/AGCN/Presenter")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    protocol = preflight()
    if args.preflight_only:
        print(json.dumps(protocol, ensure_ascii=False, indent=2))
        return 0
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("GPU CUDA unavailable; training and evaluation have NOT run")
    drive_root = Path(args.drive_root).resolve()
    if not Path("/content/drive/MyDrive").is_dir() or not drive_root.is_relative_to(Path("/content/drive/MyDrive")):
        raise RuntimeError("Mount Google Drive first; refusing to save weights in scratch")
    old_adapter = drive_root / "agcn-presenter-v0.1-lora"
    if sha(old_adapter / "adapter_model.safetensors") != V1_ADAPTER_SHA:
        raise RuntimeError("v0.1 adapter differs from validated experiment")
    adapter = drive_root / "agcn-presenter-v0.2-lora"
    result_dir = drive_root / "Results-v0.2"
    result_dir.mkdir(parents=True, exist_ok=True)
    lock = result_dir / "experiment_protocol.json"
    if lock.exists() and json.loads(lock.read_text()) != protocol:
        raise RuntimeError("Existing v0.2 run has a different protocol; preserve it before a new experiment")
    write_json(lock, protocol)
    timing_path = result_dir / "stage_times.json"
    timing = json.loads(timing_path.read_text()) if timing_path.exists() else {}
    status = {"status": "running", "started_utc": datetime.now(timezone.utc).isoformat()}
    write_json(result_dir / "status.json", status)
    def stage(name, command):
        started = time.perf_counter()
        completed = False
        try:
            run(command, result_dir / f"{name}.log")
            completed = True
        finally:
            timing.setdefault(name, []).append({"wall_seconds": round(time.perf_counter() - started, 3), "completed": completed})
            write_json(timing_path, timing)
    try:
        run([sys.executable, "training/scripts/check_answer_only_loss.py"])
        summary_path = adapter / "agcn_training_summary.json"
        if not summary_path.exists():
            checkpoints = sorted(adapter.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[-1])) if adapter.exists() else []
            cmd = [sys.executable, "-u", "training/scripts/train_lora_qwen3.py", "--version", "0.2",
                   "--model-revision", protocol["base_model_revision"],
                   "--train", "training/outputs/agcn_presenter_v0.2_train.jsonl",
                   "--validation", "training/outputs/agcn_presenter_v0.2_validation.jsonl",
                   "--output", str(adapter), "--epochs", "4", "--learning-rate", "0.0002",
                   "--lora-r", "16", "--lora-alpha", "32", "--max-length", "2048"]
            if checkpoints:
                cmd += ["--resume-from-checkpoint", str(checkpoints[-1])]
            stage("training", cmd)
        trained = json.loads(summary_path.read_text())
        if trained.get("version") != "0.2" or trained["train_sha256"] != protocol["corpus_sha256"]["train"] or trained["validation_sha256"] != protocol["corpus_sha256"]["validation"]:
            raise RuntimeError("Adapter training summary does not match v0.2 corpus")
        for key, model_adapter in (("qwen_original", None), ("agcn_v0.1", old_adapter), ("agcn_v0.2", adapter)):
            output = result_dir / f"{key}.jsonl"
            summary = result_dir / f"{key}_summary.json"
            if summary.exists() and output.exists():
                continue
            cmd = [sys.executable, "-u", "training/scripts/run_lora_frozen_eval.py",
                   "--model-revision", protocol["base_model_revision"],
                   "--eval", "training/evaluation/frozen_eval_v0.1.jsonl",
                   "--output", str(output), "--summary", str(summary)]
            if model_adapter:
                cmd += ["--adapter", str(model_adapter)]
            stage(key, cmd)
        if sha(ROOT / "training/evaluation/frozen_eval_v0.1.jsonl") != FROZEN_SHA:
            raise RuntimeError("Frozen evaluation modified during execution")
        report(result_dir, adapter, protocol, timing)
        status.update(status="training_and_inference_complete_semantic_review_pending", adapter_sha256=sha(adapter / "adapter_model.safetensors"))
    except Exception as exc:
        status.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        status["updated_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(result_dir / "status.json", status)
    print(f"Adapter: {adapter}\nResults: {result_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
