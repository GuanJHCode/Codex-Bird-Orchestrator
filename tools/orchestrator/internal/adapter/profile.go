package adapter

import (
	"errors"
	"regexp"
	"strings"
)

type Role string
type ModelID string
type ReasoningEffort string
type AccessMode string

const (
	Reviewer       Role       = "reviewer"
	Implementer    Role       = "implementer"
	ReadOnly       AccessMode = "read-only"
	WorkspaceWrite AccessMode = "workspace-write"
)

type ExecutionProfile struct {
	Version    int             `json:"version"`
	Role       Role            `json:"role"`
	Model      ModelID         `json:"model,omitempty"`
	Reasoning  ReasoningEffort `json:"reasoning,omitempty"`
	Permission AccessMode      `json:"permission"`
	TimeoutMS  int64           `json:"timeout_ms"`
}

type ProviderLock struct {
	Version  int       `json:"version"`
	Provider Provider  `json:"provider"`
	Protocol string    `json:"protocol"`
	Binary   BinaryPin `json:"binary"`
}

func ProtocolID(provider Provider) string {
	switch provider {
	case ProviderCodex:
		return "codex-jsonl-0.154.0"
	case ProviderClaude:
		return "claude-stream-json-v1"
	case ProviderAGY:
		return "agy-stream-json-v1"
	case ProviderGrok:
		return "grok-streaming-json-v1"
	default:
		return ""
	}
}

var modelID = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$`)

func validateProfile(req Request) error {
	if req.Lock != nil && (req.Lock.Version != 1 || req.Lock.Provider != req.Provider || req.Lock.Protocol == "" || req.Lock.Protocol != ProtocolID(req.Provider) || req.Lock.Binary != req.Binary) {
		return errors.New("provider_lock_invalid")
	}
	p := req.Profile
	if p == nil {
		return nil
	}
	if req.Lock == nil {
		return errors.New("provider_lock_invalid")
	}
	if req.Session.ID != "" {
		return errors.New("profile_resume_not_verified")
	}
	if req.Provider == ProviderCodex {
		return errors.New("codex_trial_guard_not_ready")
	}
	if p.Version != 1 || p.TimeoutMS < 1 || p.TimeoutMS > 3_600_000 {
		return errors.New("execution_profile_invalid")
	}
	if (p.Role != Reviewer || p.Permission != ReadOnly) && (p.Role != Implementer || p.Permission != WorkspaceWrite) {
		return errors.New("profile_permission_mismatch")
	}
	if p.Model != "" && !modelID.MatchString(string(p.Model)) {
		return errors.New("model_invalid")
	}
	if p.Reasoning != "" && p.Reasoning != "low" && p.Reasoning != "medium" && p.Reasoning != "high" {
		return errors.New("reasoning_unsupported")
	}
	if req.Provider != ProviderClaude && req.Provider != ProviderCodex {
		return errors.New("execution_profile_unsupported")
	}
	if len(req.Permission.Allow) > 0 || len(req.Permission.Deny) > 0 || (req.Permission.Mode != "" && req.Permission.Mode != "plan" && req.Permission.Mode != "default") {
		return errors.New("profile_legacy_permission_conflict")
	}
	if p.Role == Implementer && req.Provider != ProviderClaude {
		return errors.New("implementer_unsupported")
	}
	if p.Role == Implementer && req.Permission.Mode == "plan" {
		return errors.New("profile_legacy_permission_conflict")
	}
	return nil
}

func (i Invocation) ExecutionProfile() *ExecutionProfile {
	if i.profile == nil {
		return nil
	}
	copy := *i.profile
	return &copy
}

// CheckCapabilities checks only the flags needed by this exact request. Missing
// flags are rejected, including versions whose capabilities are not established.
func CheckCapabilities(req Request, help string) error {
	if err := validateProfile(req); err != nil {
		return err
	}
	if req.Profile == nil {
		return nil
	}
	flags := []string{"--output-format", "--input-format", "--permission-mode"}
	if req.Provider == ProviderCodex {
		return errors.New("codex_trial_guard_not_ready")
	}
	if req.Profile.Model != "" {
		flags = append(flags, "--model")
	}
	if req.Profile.Reasoning != "" {
		flags = append(flags, "--effort")
	}
	if req.Session.ID != "" {
		flags = append(flags, "--resume")
	}
	for _, flag := range flags {
		if !strings.Contains(help, flag) {
			return errors.New("provider_capability_unsupported")
		}
	}
	return nil
}
