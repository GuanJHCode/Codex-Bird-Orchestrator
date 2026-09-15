package main

import (
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"

	"codex-cli-orchestration-design/tools/orchestrator/internal/process"
)

func TestCLILocalOwnerCollectWithoutNativeBridge(t *testing.T) {
	root, err := os.MkdirTemp("/tmp", "local-cli-")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(root)
	state, bin := filepath.Join(root, "state"), filepath.Join(root, "orchestrator")
	defer func() {
		if _, err := os.Stat(filepath.Join(state, "coordinator.pid")); err == nil {
			stopCoordinator(t, state)
		}
	}()
	if out, err := exec.Command("go", "build", "-o", bin, ".").CombinedOutput(); err != nil {
		t.Fatalf("build: %s %v", out, err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	birth, err := process.Birth(os.Getpid())
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(root, "request.json")
	write := func(v any) {
		t.Helper()
		b, _ := json.Marshal(v)
		if err := os.WriteFile(path, b, 0600); err != nil {
			t.Fatal(err)
		}
	}
	write(map[string]any{"controller_thread": "master", "origin_pid": os.Getpid(), "origin_birth": birth})
	var owner map[string]any
	if err = json.Unmarshal(runBinary(t, ctx, bin, "owner-bind", "--state-dir", state, "--request", path), &owner); err != nil {
		t.Fatal(err)
	}
	if owner["token"] != nil {
		t.Fatal("token leaked to stdout")
	}
	delete(owner, "version")
	owner["run_id"] = "local"
	owner["plan_revision"] = 1
	owner["delivery_mode"] = "collect"
	owner["tasks"] = []any{map[string]any{"id": "task", "max_attempts": 1, "adapter": map[string]any{"kind": "fake", "args": []string{"/bin/sh", "-c", "printf result"}, "directory": root}}}
	write(owner)
	var submitted struct {
		ControlFile string `json:"control_file"`
	}
	if err = json.Unmarshal(runBinary(t, ctx, bin, "submit", "--state-dir", state, "--request", path), &submitted); err != nil {
		t.Fatal(err)
	}
	for {
		s := taskStatus(t, ctx, bin, state, "task", submitted.ControlFile)
		if s.Status == "result_ready" {
			break
		}
		if ctx.Err() != nil {
			t.Fatalf("status=%s", s.Status)
		}
		time.Sleep(30 * time.Millisecond)
	}
	var collection map[string]any
	if err = json.Unmarshal(runBinary(t, ctx, bin, "collect", "--state-dir", state, "--task-id", "task", "--control-file", submitted.ControlFile), &collection); err != nil {
		t.Fatal(err)
	}
	if collection["collection_proof_sha256"] == nil {
		t.Fatalf("missing receipt: %#v", collection)
	}
}
