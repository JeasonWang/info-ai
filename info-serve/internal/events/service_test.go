package events

import (
	"context"
	"strings"
	"testing"
)

type fakeEventStore struct {
	listResult   EventPage
	detailResult EventDetail
	listParams   *ListEventsParams
}

func (s fakeEventStore) ListEvents(ctx context.Context, params ListEventsParams) (EventPage, error) {
	if s.listParams != nil {
		*s.listParams = params
	}
	result := s.listResult
	result.Page = params.Page
	result.PageSize = params.PageSize
	return result, nil
}

func (s fakeEventStore) GetEventDetail(ctx context.Context, id int64) (EventDetail, error) {
	return s.detailResult, nil
}

func TestServiceNormalizesListParams(t *testing.T) {
	var captured ListEventsParams
	service := NewService(fakeEventStore{listResult: EventPage{Total: 1}, listParams: &captured})

	page, err := service.ListEvents(context.Background(), ListEventsParams{
		CategoryCode: "",
		Sort:         "",
		Page:         0,
		PageSize:     0,
	})
	if err != nil {
		t.Fatalf("ListEvents returned error: %v", err)
	}
	if page.Page != 1 {
		t.Fatalf("page = %d, want 1", page.Page)
	}
	if page.PageSize != 10 {
		t.Fatalf("page_size = %d, want 10", page.PageSize)
	}
	if captured.Status != "active" {
		t.Fatalf("status = %q, want active", captured.Status)
	}
}

func TestServiceAllowsMonitoringListStatus(t *testing.T) {
	var captured ListEventsParams
	service := NewService(fakeEventStore{listResult: EventPage{Total: 1}, listParams: &captured})

	_, err := service.ListEvents(context.Background(), ListEventsParams{Status: "monitoring", Page: 1, PageSize: 10})
	if err != nil {
		t.Fatalf("ListEvents returned error: %v", err)
	}
	if captured.Status != "monitoring" {
		t.Fatalf("status = %q, want monitoring", captured.Status)
	}
}

func TestServiceNormalizesNilSourceBadges(t *testing.T) {
	service := NewService(fakeEventStore{listResult: EventPage{
		Total:    1,
		Page:     1,
		PageSize: 10,
		Items: []EventListItem{
			{
				ID:           7,
				Title:        "热点事件",
				SourceBadges: nil,
			},
		},
	}})

	page, err := service.ListEvents(context.Background(), ListEventsParams{Page: 1, PageSize: 10})

	if err != nil {
		t.Fatalf("ListEvents returned error: %v", err)
	}
	if page.Items[0].SourceBadges == nil {
		t.Fatal("source badges should be an empty array instead of nil")
	}
	if len(page.Items[0].SourceBadges) != 0 {
		t.Fatalf("source badges = %+v, want empty", page.Items[0].SourceBadges)
	}
}

func TestServiceRewritesMetadataLikeListSummaries(t *testing.T) {
	service := NewService(fakeEventStore{listResult: EventPage{
		Total:    1,
		Page:     1,
		PageSize: 10,
		Items: []EventListItem{
			{
				ID:             8,
				Title:          "Ukraine's anti-corruption court places Zelenskiy's former chief of staff under arrest",
				OneLineSummary: "Reuters category: world / europe. Reuters Published at 2026-05-14T07:00:58.011Z according to its official news sitemap.",
				PrimaryCategory: CategoryBrief{
					Code: "international",
					Name: "国际大事",
				},
				SourceBadges: []string{"路透社"},
			},
		},
	}})

	page, err := service.ListEvents(context.Background(), ListEventsParams{Page: 1, PageSize: 10})

	if err != nil {
		t.Fatalf("ListEvents returned error: %v", err)
	}
	summary := page.Items[0].OneLineSummary
	if strings.Contains(summary, "Reuters category") || strings.Contains(summary, "Published at") {
		t.Fatalf("summary still contains metadata: %q", summary)
	}
	if !strings.Contains(summary, "路透社") {
		t.Fatalf("summary = %q, want Reuters attribution", summary)
	}
	if !strings.HasSuffix(summary, "。") {
		t.Fatalf("summary = %q, want complete sentence", summary)
	}
}

func TestServiceBuildsEvidenceChainFromRepresentativeSources(t *testing.T) {
	service := NewService(fakeEventStore{detailResult: EventDetail{
		Event: EventCore{ID: 9, Status: "active", SourceCount: 2},
		RepresentativeSources: []RepresentativeSource{
			{
				InfoID:              101,
				Title:               "官方通报事故救援进展",
				ChannelName:         "央视新闻",
				SourceURL:           "https://example.com/a",
				DetailFetchStatus:   "complete",
				DetailScore:         92,
				DetailContentLength: 300,
			},
			{
				InfoID:              102,
				Title:               "网友转发现场片段",
				ChannelName:         "微博",
				SourceURL:           "https://example.com/b",
				DetailFetchStatus:   "list_only",
				DetailScore:         30,
				DetailContentLength: 20,
			},
		},
	}})

	detail, err := service.GetEventDetail(context.Background(), 9)

	if err != nil {
		t.Fatalf("GetEventDetail returned error: %v", err)
	}
	if detail.EvidenceChain.UsableSourceCount != 1 {
		t.Fatalf("usable source count = %d, want 1", detail.EvidenceChain.UsableSourceCount)
	}
	if detail.EvidenceChain.WeakSourceCount != 1 {
		t.Fatalf("weak source count = %d, want 1", detail.EvidenceChain.WeakSourceCount)
	}
	if detail.EvidenceChain.EvidenceSources[0].QualityLevel != "高" {
		t.Fatalf("quality level = %q, want 高", detail.EvidenceChain.EvidenceSources[0].QualityLevel)
	}
	if detail.EvidenceChain.WeakSources[0].RiskReasons[0] != "detail_not_complete" {
		t.Fatalf("weak source reasons = %+v", detail.EvidenceChain.WeakSources[0].RiskReasons)
	}
	if len(detail.EvidenceChain.PlatformViews) != 2 {
		t.Fatalf("platform views = %+v, want 2 channels", detail.EvidenceChain.PlatformViews)
	}
}

func TestServiceBuildsControversyBriefFromRiskSignals(t *testing.T) {
	service := NewService(fakeEventStore{detailResult: EventDetail{
		Event: EventCore{
			ID:                   11,
			Status:               "monitoring",
			Title:                "九华山有人失温而亡封山？假的",
			OneLineSummary:       "相关传言正在被核验，后续应以官方和权威来源为准。",
			DisplayQualityLevel:  "weak",
			DisplayQualityReason: "single_weak_source,missing_complete_source",
			SourceCount:          1,
		},
		Summaries: map[string]string{
			"risk_notice": "当前只有单一来源，且传言仍在核验中。",
		},
		RepresentativeSources: []RepresentativeSource{
			{
				InfoID:              201,
				Title:               "九华山有人失温而亡封山？假的",
				ChannelName:         "微博",
				DetailFetchStatus:   "list_only",
				DetailScore:         30,
				DetailContentLength: 20,
			},
		},
	}})

	detail, err := service.GetEventDetail(context.Background(), 11)

	if err != nil {
		t.Fatalf("GetEventDetail returned error: %v", err)
	}
	if detail.ControversyBrief.Level != "high" {
		t.Fatalf("controversy level = %q, want high", detail.ControversyBrief.Level)
	}
	if !detail.ControversyBrief.HasRumorSignal {
		t.Fatal("expected rumor signal")
	}
	if len(detail.ControversyBrief.Signals) == 0 {
		t.Fatal("expected controversy signals")
	}
	if detail.ControversyBrief.ActionHint == "" {
		t.Fatal("expected controversy action hint")
	}
}

func TestServiceEnrichesSourceViewsWithNarrativeSignals(t *testing.T) {
	service := NewService(fakeEventStore{detailResult: EventDetail{
		Event: EventCore{ID: 12, Status: "active", SourceCount: 2},
		SourceViews: []SourceView{
			{ChannelName: "央视新闻", Summary: "官方通报事故救援进展，伤者治疗和原因调查正在推进。"},
			{ChannelName: "微博", Summary: "网友持续讨论现场视频，对事故原因提出质疑。"},
		},
	}})

	detail, err := service.GetEventDetail(context.Background(), 12)

	if err != nil {
		t.Fatalf("GetEventDetail returned error: %v", err)
	}
	if detail.SourceViews[0].Focus == "" {
		t.Fatal("expected source view focus")
	}
	if detail.SourceViews[0].Stance == "" {
		t.Fatal("expected source view stance")
	}
	if detail.SourceViews[1].DifferenceHint == "" {
		t.Fatal("expected source view difference hint")
	}
}

func TestServiceEnrichesRelatedEventsWithRelationText(t *testing.T) {
	service := NewService(fakeEventStore{detailResult: EventDetail{
		Event: EventCore{ID: 20, Status: "active", EventGeneration: 2, EvolutionStage: "recurring"},
		RelatedEvents: []RelatedEvent{
			{ID: 18, Title: "同类事件首次出现", RelationType: "previous", EvolutionType: "recurrence"},
			{ID: 23, Title: "同类事件后续更新", RelationType: "next", EvolutionType: "expansion"},
		},
	}})

	detail, err := service.GetEventDetail(context.Background(), 20)

	if err != nil {
		t.Fatalf("GetEventDetail returned error: %v", err)
	}
	if detail.RelatedEvents[0].RelationLabel == "" {
		t.Fatal("expected previous event relation label")
	}
	if detail.RelatedEvents[0].RelationReason == "" {
		t.Fatal("expected previous event relation reason")
	}
	if detail.RelatedEvents[1].RelationLabel == "" {
		t.Fatal("expected next event relation label")
	}
}

func TestEventCategoriesAreStableForFrontendTabs(t *testing.T) {
	categories := EventCategories()

	if len(categories) != 5 {
		t.Fatalf("len(categories) = %d, want 5", len(categories))
	}
	if categories[0].Code != "all" || categories[0].Name != "全网" {
		t.Fatalf("first category = %+v", categories[0])
	}
	if categories[1].Code != "tech" {
		t.Fatalf("second category = %+v, want tech", categories[1])
	}
}
