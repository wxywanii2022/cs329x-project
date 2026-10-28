"""Paired experiment orchestration, deterministic routing and resumable checkpoints."""

from __future__ import annotations

import copy
import random
from dataclasses import asdict
from pathlib import Path

from .adapters.base import Gateway
from .assessment import assess
from .coaching import choose_exercise, load_exercises
from .evaluation import blind_record, mechanical_checks, score_record
from .learner import learner_turn
from .profiles import load_profiles
from .schema import BEHAVIORS, CONDITIONS, ExperimentConfig, require
from .storage import Journal, RunLock, canonical, digest, fork_snapshot, freeze_snapshot, read_json, write_json
from .tasks import ScriptedTaskAgent, load_tasks, public_task


def build_bundle(config: ExperimentConfig) -> dict:
    profiles, tasks, bank = load_profiles(), load_tasks(), load_exercises()
    require(set(config.profiles) <= profiles.keys(), "Unknown profile in configuration")
    selected_tasks = []
    for pair in config.pairs:
        for form in ("A", "B"):
            require((pair, form) in tasks, f"Missing task {pair}/{form}")
            require(tasks[pair, form]["split"] == config.split, "Task split does not match experiment split")
            selected_tasks.append(tasks[pair, form])
    package = Path(__file__).parent
    files = sorted([*package.rglob("*.py"), *package.glob("prompts/*.txt")])
    return {"config": asdict(config), "profiles": [asdict(profiles[p]) for p in config.profiles],
            "tasks": selected_tasks, "exercise_bank": bank,
            "implementation_hashes": {p.relative_to(package).as_posix(): digest(p.read_text(encoding="utf-8")) for p in files}}


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig, output: Path):
        self.config, self.output = config, output
        self.bundle = build_bundle(config)
        self.config_hash = digest(self.bundle)
        self.profiles = load_profiles()
        self.tasks = load_tasks()
        self.bank = load_exercises()

    def run(self) -> dict:
        with RunLock(self.output):
            bundle_path = self.output / "frozen_inputs.json"
            if bundle_path.exists():
                require(digest(read_json(bundle_path)) == self.config_hash,
                        "Frozen inputs or implementation changed; use a new output directory")
            else:
                require(not (self.output / "events.jsonl").exists(), "Journal exists without frozen inputs")
                write_json(bundle_path, self.bundle)
            self.journal = Journal(self.output / "events.jsonl", self.config_hash)
            self.gateway = Gateway(self.config.models, self.config.budget, self.journal, self.config.seed)
            self.logged_messages = {(e["block_id"], e["branch_id"], e["phase"], e["message_id"])
                                    for e in self.journal.events if e["kind"] == "message"}
            blocks = []
            for profile_id in self.config.profiles:
                for pair in self.config.pairs:
                    for orientation in self.config.orientations:
                        for replicate in range(self.config.replicates):
                            blocks.append(self.run_block(profile_id, pair, orientation, replicate))
            packets = []
            for block in blocks:
                if block.get("pre_packet"):
                    packets.append(block["pre_packet"])
                packets.extend(b["packet"] for b in block["branches"].values() if b.get("packet"))
            random.Random(self.config.seed + 17).shuffle(packets)
            write_json(self.output / "blinded" / "scoring_order.json", packets)
            for blind_id in packets:
                self.evaluate(blind_id)
            manifest = {"config_hash": self.config_hash, "mode": self.config.mode,
                        "rubric_version": self.config.rubric_version, "blocks": blocks,
                        "task_records": len(packets),
                        "failed_branches": sum(b["status"] != "complete" for block in blocks for b in block["branches"].values()),
                        "failed_scores": sum(read_json(self.output / "scores" / f"{p}.json")["status"] != "complete" for p in packets)}
            write_json(self.output / "manifest.json", manifest)
            from .analysis import export_analysis
            export_analysis(self.output)
            return manifest

    def _session(self, *parts) -> str:
        return digest([self.config_hash, *parts])[:32]

    def _anchor(self, path: Path):
        relative = path.relative_to(self.output).as_posix()
        content_hash = digest(read_json(path))
        previous = next((e for e in self.journal.events if e["kind"] == "artifact" and e["path"] == relative), None)
        if previous:
            require(previous["content_hash"] == content_hash, f"Checkpoint changed: {relative}")
        else:
            self.journal.append("artifact", path=relative, content_hash=content_hash)

    def _message(self, state, record_messages, actor, content, block_id, branch_id, phase):
        message = {"message_id": f"m{len(record_messages) + 1:03d}", "actor": actor, "content": content}
        record_messages.append(message)
        state["messages"].append(copy.deepcopy(message))
        key = (block_id, branch_id, phase, message["message_id"])
        if key not in self.logged_messages:
            self.journal.append("message", block_id=block_id, branch_id=branch_id, phase=phase,
                                message_id=message["message_id"], actor=actor, visible_content=content)
            self.logged_messages.add(key)
        return message["message_id"]

    def _task(self, state, task, block_id, branch_id, phase):
        messages = []
        agent = ScriptedTaskAgent(task)
        session = self._session(block_id, branch_id, "learner")
        task_session = self._session(block_id, branch_id, phase, "task_agent")
        context = dict(block_id=block_id, branch_id=branch_id, phase=phase, session_id=session)
        decision_ids = {}
        add = lambda actor, text: self._message(state, messages, actor, text, block_id, branch_id, phase)
        if task["error_schedule"]["kind"] != "incomplete":
            add("environment", "Task assignment: " + canonical(public_task(task)))
            response, _ = learner_turn(self.gateway, state, public_task(task), "request",
                                        call_id=f"{block_id}/{branch_id}/{phase}/request", **context)
            decision_ids["B1"] = decision_ids["B2"] = add("learner", response["content"])
            add("task_agent", agent.opening(response["content"]))
            response, _ = learner_turn(self.gateway, state, public_task(task), "review",
                                        call_id=f"{block_id}/{branch_id}/{phase}/review", **context)
            decision_ids["B3"] = add("learner", response["content"])
            add("task_agent", agent.follow_up(response["content"]))
            disclosure_id = add("environment", agent.disclosure())
            response, _ = learner_turn(self.gateway, state, public_task(task), "correction",
                                        call_id=f"{block_id}/{branch_id}/{phase}/correction", **context)
            decision_ids["B4"] = add("learner", response["content"])
            add("task_agent", agent.finish(response["content"]))
        else:
            disclosure_id = None
        actual = {b: {"status": task["opportunities"][b], "decision_message_id": decision_ids.get(b),
                       "disclosure_message_id": disclosure_id if b == "B4" else None}
                  for b in BEHAVIORS}
        record = {"task": public_task(task), "messages": messages,
                  "opportunities": {"prescribed": copy.deepcopy(task["opportunities"]), "actual": actual},
                  "answer_key": copy.deepcopy(task["private_answer_key"]),
                  "final_artifact": agent.last_artifact, "rubric_version": task["rubric_version"],
                  "task_hash": digest(task), "task_agent_session_id": task_session,
                  "task_agent_help_count": agent.help_count,
                  "discovery": "spontaneous" if agent.discovered else "prompted" if task["error_schedule"]["kind"] == "incorrect_growth" else "not_applicable",
                  "natural_chain_completed": agent.discovered and agent.corrected}
        record["mechanical_checks"] = mechanical_checks(record)
        state["environment_state"] = {"task_hash": digest(task), "task": copy.deepcopy(task), "completed": True}
        state["artifacts"] = {"final_artifact": agent.last_artifact}
        return record

    def _packet(self, record, block_id, phase, branch_id=None):
        blind_id = self._session("blind", block_id, phase, branch_id)
        path = self.output / "blinded" / f"{blind_id}.json"
        packet = blind_record(record, blind_id)
        if path.exists():
            require(digest(read_json(path)) == digest(packet), "Blinded packet differs from its source record")
        else:
            write_json(path, packet)
        self._anchor(path)
        return blind_id

    def run_block(self, profile_id, pair, orientation, replicate):
        block_id = self._session(profile_id, pair, orientation, replicate)[:16]
        directory = self.output / "blocks" / block_id
        profile = self.profiles[profile_id]
        block = {"block_id": block_id, "profile_id": profile_id, "reporting_group": profile.reporting_group,
                 "pair_id": pair, "orientation": orientation, "replicate": replicate,
                 "branches": {}, "pre_packet": None}
        try:
            pre_path = directory / "pre.json"
            if pre_path.exists():
                saved = read_json(pre_path)
                root, pre = saved["snapshot"], saved["record"]
                fork_snapshot(root)
            else:
                state = {"block_id": block_id, "profile": asdict(profile), "background": profile.background(),
                         "messages": [], "memory": {}, "environment_state": {}, "artifacts": {},
                         "model_config": {r: asdict(m) for r, m in self.config.models.items()},
                         "config_hash": self.config_hash}
                pre = self._task(state, self.tasks[pair, orientation[0]], block_id, None, "pre")
                root = freeze_snapshot(state)
                write_json(pre_path, {"snapshot": root, "record": pre})
                self.journal.append("snapshot", block_id=block_id, phase="pre", snapshot_hash=root["snapshot_hash"])
            block["snapshot_hash"] = root["snapshot_hash"]
            self._anchor(pre_path)
            block["pre_packet"] = self._packet(pre, block_id, "pre")
        except Exception as exc:
            block["error"] = f"{type(exc).__name__}: {exc}"
            block["branches"] = {c: {"status": "failed", "error": "Pre-task failed: " + block["error"]} for c in CONDITIONS}
            self.journal.append("block_failure", block_id=block_id, status="failed", error=block["error"])
            write_json(directory / "block.json", block)
            return block
        assessment = None
        assessment_error = None
        try:
            assessment, _ = assess(self.gateway, pre, call_id=f"{block_id}/assessment",
                                   session_id=self._session(block_id, "assessment"), block_id=block_id,
                                   branch_id=None, phase="assessment")
            write_json(directory / "assessment.json", assessment)
        except Exception as exc:
            assessment_error = f"{type(exc).__name__}: {exc}"
            block["assessment_error"] = assessment_error
        order = list(CONDITIONS)
        random.Random(int(block_id, 16) ^ self.config.seed).shuffle(order)
        block["execution_order"] = order
        for condition in order:
            branch_path = directory / "branches" / condition / "result.json"
            if branch_path.exists():
                self._anchor(branch_path)
                block["branches"][condition] = read_json(branch_path)
                continue
            state = fork_snapshot(root)
            initial_hash = state.pop("snapshot_hash")
            write_json(branch_path.parent / "initial_state.json", {"snapshot_hash": initial_hash,
                       "learner_session_id": self._session(block_id, condition, "learner"),
                       "coach_session_id": self._session(block_id, condition, "coach")})
            branch = {"status": "running", "snapshot_hash": initial_hash,
                      "coaching_turns": 0, "coaching_tokens": 0, "coaching_status": "not_requested", "decision": None}
            try:
                if condition in {"full", "without_background"} and assessment_error:
                    raise RuntimeError("Required assessment unavailable: " + assessment_error)
                if condition != "no_coaching":
                    self._coach(state, pre, assessment, condition, block_id, branch)
                post = self._task(state, self.tasks[pair, orientation[1]], block_id, condition, "post")
                branch.update(status="complete", packet=self._packet(post, block_id, "post", condition),
                              record=post, final_state=state)
            except Exception as exc:
                branch.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                self.journal.append("branch_failure", block_id=block_id, branch_id=condition,
                                    status="failed", error=branch["error"])
            # Include provider usage from rejected responses too. Transport failures
            # without usage remain explicitly unknown in the journal and summary.
            actual_tokens = 0
            for event in self.journal.events:
                if event["block_id"] != block_id or event["branch_id"] != condition or event["phase"] != "coaching":
                    continue
                usage = event.get("usage") or event.get("response", {}).get("usage")
                if usage and all(type(usage.get(k)) is int for k in ("input_tokens", "output_tokens")):
                    actual_tokens += usage["input_tokens"] + usage["output_tokens"]
            branch["coaching_tokens"] = actual_tokens
            require(fork_snapshot(root)["snapshot_hash"] == initial_hash, "Root changed during branch execution")
            write_json(branch_path, branch)
            self._anchor(branch_path)
            self.journal.append("branch_end", block_id=block_id, branch_id=condition, status=branch["status"],
                                snapshot_hash=initial_hash, coaching_turns=branch["coaching_turns"],
                                coaching_tokens=branch["coaching_tokens"])
            block["branches"][condition] = branch
        # Keep manifest small: detailed records and branch histories remain in checkpoints.
        block["branches"] = {c: {k: v for k, v in b.items() if k not in {"record", "final_state"}}
                             for c, b in block["branches"].items()}
        write_json(directory / "block.json", block)
        return block

    def _coach(self, state, pre, assessment, condition, block_id, branch):
        budget = self.config.budget
        context = dict(block_id=block_id, branch_id=condition, phase="coaching")
        decision, usage = choose_exercise(self.gateway, condition, pre, assessment, state["background"], self.bank,
                                          call_id=f"{block_id}/{condition}/decision",
                                          session_id=self._session(block_id, condition, "coach"),
                                          total_token_allowance=budget.max_coaching_tokens, **context)
        branch["decision"] = decision
        branch["coaching_tokens"] += usage["input_tokens"] + usage["output_tokens"]
        if decision["action"] == "none":
            branch["coaching_status"] = "none"
            return
        exercise = next(x for x in self.bank if x["exercise_id"] == decision["exercise_id"])
        messages = []
        branch["coaching_status"] = "complete"
        for index, content in enumerate(exercise["messages"][:budget.max_coaching_turns]):
            remaining = budget.max_coaching_tokens - branch["coaching_tokens"]
            if remaining <= 0:
                branch["coaching_status"] = "budget_exhausted"
                break
            self._message(state, messages, "coach", content, block_id, condition, "coaching")
            response, usage = learner_turn(self.gateway, state, pre["task"], "practice",
                                           call_id=f"{block_id}/{condition}/practice/{index}",
                                           session_id=self._session(block_id, condition, "learner"),
                                           max_output_tokens=min(budget.max_output_tokens, remaining),
                                           total_token_allowance=remaining, **context)
            self._message(state, messages, "learner", response["content"], block_id, condition, "coaching")
            branch["coaching_tokens"] += usage["input_tokens"] + usage["output_tokens"]
            branch["coaching_turns"] += 1
            if "skip this practice" in response["content"].lower():
                branch["coaching_status"] = "declined"
                break
        if budget.max_coaching_turns < len(exercise["messages"]) and branch["coaching_status"] == "complete":
            branch["coaching_status"] = "turn_cap_reached"

    def evaluate(self, blind_id):
        path = self.output / "scores" / f"{blind_id}.json"
        if path.exists():
            self._anchor(path)
            return
        packet = read_json(self.output / "blinded" / f"{blind_id}.json")
        try:
            scores, _ = score_record(self.gateway, packet, call_id=f"score/{blind_id}",
                                     session_id=self._session("evaluator", blind_id),
                                     block_id=None, branch_id=None, phase="evaluation")
            result = {"status": "complete", "blind_record_id": blind_id,
                      "rubric_version": packet["rubric_version"], **scores}
        except Exception as exc:
            result = {"status": "failed", "blind_record_id": blind_id, "error": f"{type(exc).__name__}: {exc}"}
            self.journal.append("scoring_failure", phase="evaluation", status="failed", error=result["error"])
        write_json(path, result)
        self._anchor(path)
