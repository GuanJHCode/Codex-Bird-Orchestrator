package store

import "context"

// RunSummary is a read-only projection of the existing task database. Actions
// describe state eligibility, not grants: mutations still require fresh event,
// revision, owner and (for resume) explicit recovery authorization.
type RunSummary struct {
	Version int            `json:"version"`
	RunID   string         `json:"run_id"`
	Counts  map[string]int `json:"counts"`
	Tasks   []SummaryTask  `json:"tasks"`
}

type SummaryTask struct {
	TaskID         string   `json:"task_id"`
	Status         string   `json:"status"`
	Group          string   `json:"group"`
	WorkRevision   int      `json:"work_revision"`
	ActiveSegments int      `json:"active_segments"`
	AllowedActions []string `json:"allowed_actions"`
}

func (d *DB) SummarizeRun(ctx context.Context, taskID, controller, token string) (RunSummary, error) {
	d.mu.Lock()
	defer d.mu.Unlock()
	if err := d.ValidateTaskOwner(ctx, taskID, controller, token); err != nil {
		return RunSummary{}, err
	}
	rows, err := d.sql.QueryContext(ctx, `
SELECT t.run_id,t.id,t.status,r.work_revision,
 (SELECT COUNT(*) FROM segment_runtime s JOIN attempts a ON a.id=s.attempt_id WHERE a.task_id=t.id AND s.status IN ('launch_requested','prepared','spawned','running','stopping','unknown')),
 (SELECT COUNT(*) FROM attempts a JOIN task_runtime ar ON ar.task_id=a.task_id WHERE ar.budget_group_id=r.budget_group_id),t.max_attempts,
 EXISTS(SELECT 1 FROM runtime_events e WHERE e.task_id=t.id AND json_extract(e.body_json,'$.kind')='result' AND e.segment_id=(SELECT s.id FROM segments s JOIN attempts a ON a.id=s.attempt_id WHERE a.task_id=t.id ORDER BY a.attempt_no DESC,s.segment_no DESC LIMIT 1)),
 EXISTS(SELECT 1 FROM runtime_questions q WHERE q.task_id=t.id AND q.status='open' AND q.work_revision=r.work_revision),
 EXISTS(SELECT 1 FROM runtime_events e JOIN segments s ON s.id=e.segment_id JOIN attempts a ON a.id=s.attempt_id WHERE a.task_id=t.id AND a.status='failed' AND a.attempt_no=(SELECT MAX(attempt_no) FROM attempts WHERE task_id=t.id) AND (json_extract(e.body_json,'$.kind')='failed' OR (json_extract(e.body_json,'$.kind')='result' AND EXISTS(SELECT 1 FROM review_decisions rd WHERE rd.event_id=e.event_id AND rd.decision='reject'))))
FROM tasks t JOIN task_runtime r ON r.task_id=t.id
WHERE t.run_id=(SELECT run_id FROM tasks WHERE id=?) ORDER BY t.id`, taskID)
	if err != nil {
		return RunSummary{}, err
	}
	defer rows.Close()
	summary := RunSummary{Version: 1, Counts: map[string]int{"pending": 0, "running": 0, "blocked": 0, "completed": 0}, Tasks: []SummaryTask{}}
	for rows.Next() {
		var task SummaryTask
		var attempts, maxAttempts int
		var result, question, failure bool
		if err := rows.Scan(&summary.RunID, &task.TaskID, &task.Status, &task.WorkRevision, &task.ActiveSegments, &attempts, &maxAttempts, &result, &question, &failure); err != nil {
			return RunSummary{}, err
		}
		task.Group = "blocked"
		task.AllowedActions = []string{"status", "collect"}
		switch task.Status {
		case "ready", "resume_queued":
			task.Group = "pending"
			task.AllowedActions = append(task.AllowedActions, "wait-events")
		case "running":
			task.Group = "running"
			task.AllowedActions = append(task.AllowedActions, "wait-events")
		case "result_ready":
			task.Group = "pending"
			if result && task.ActiveSegments == 0 {
				task.AllowedActions = append(task.AllowedActions, "accept")
			}
		case "waiting_question":
			if question && task.ActiveSegments == 0 {
				task.AllowedActions = append(task.AllowedActions, "answer")
			}
		case "interrupted":
			if task.ActiveSegments == 0 {
				task.AllowedActions = append(task.AllowedActions, "resume")
			}
		case "failed":
			if failure && task.ActiveSegments == 0 && attempts < maxAttempts && attempts < 3 {
				task.AllowedActions = append(task.AllowedActions, "retry")
			}
		case "completed", "cancelled":
			task.Group = "completed"
		}
		if task.ActiveSegments > 0 {
			task.AllowedActions = append(task.AllowedActions, "stop")
		}
		summary.Counts[task.Group]++
		summary.Tasks = append(summary.Tasks, task)
	}
	return summary, rows.Err()
}
