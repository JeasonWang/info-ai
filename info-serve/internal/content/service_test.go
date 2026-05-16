package content

import "testing"

func TestApplyInfoQualityMarksWeakListOnlyDetail(t *testing.T) {
	item := InfoItem{
		Title:             "OpenAI 发布新模型",
		Content:           "OpenAI 发布新模型",
		DetailFetchStatus: "list_only",
		DetailScore:       20,
	}

	ApplyInfoQuality(&item)

	if item.QualityLevel != "weak" {
		t.Fatalf("quality level = %q, want weak", item.QualityLevel)
	}
	if !item.NeedsAttention {
		t.Fatal("list-only detail should need attention")
	}
	if item.AttentionPriority != 84 {
		t.Fatalf("attention priority = %d, want 84", item.AttentionPriority)
	}
}

func TestApplyInfoQualityMarksCompleteDetailExcellent(t *testing.T) {
	item := InfoItem{
		Title:               "OpenAI 发布新模型",
		Content:             "OpenAI 发布新模型后，开发者重点关注 API 接入节奏、推理性能和部署成本。",
		DetailFetchStatus:   "complete",
		DetailScore:         90,
		DetailContentLength: 180,
	}

	ApplyInfoQuality(&item)

	if item.QualityLevel != "excellent" {
		t.Fatalf("quality level = %q, want excellent", item.QualityLevel)
	}
	if item.NeedsAttention {
		t.Fatal("complete detail should not need attention")
	}
	if item.QualitySummary == "" {
		t.Fatal("quality summary should not be empty")
	}
}
